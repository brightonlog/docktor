#!/usr/bin/env python3
"""
TensorRT로 최적화된 PatchCore Lite 추론

젯슨 오린 나노에서 실시간 이상탐지 수행

Usage:
    # 단일 이미지 추론
    python inference_tensorrt.py --image path/to/image.jpg

    # 폴더 전체 추론
    python inference_tensorrt.py --folder path/to/images/

    # 벤치마크 (FPS 측정)
    python inference_tensorrt.py --benchmark
"""

import sys
import argparse
import time
from pathlib import Path
from typing import Tuple

import numpy as np
import cv2
from PIL import Image
import torch

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent  # deployment -> src -> lks
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import PROJECT_ROOT as CONFIG_ROOT

# ============================================================================
# Configuration
# ============================================================================

INFERENCE_CONFIG = {
    'model_path': CONFIG_ROOT / 'models' / 'anomaly_patchcore_lite' / 'patchcore_lite_model.npz',
    'engine_path': CONFIG_ROOT / 'models' / 'anomaly_patchcore_lite' / 'tensorrt' / 'efficientnet_b0_fp16.engine',

    'image_size': (224, 224),
    'threshold': None,  # None이면 모델에서 로드된 threshold 사용
}

# ============================================================================
# TensorRT Engine
# ============================================================================

class TensorRTEngine:
    """TensorRT 엔진 래퍼"""

    def __init__(self, engine_path):
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit  # CUDA 초기화
        except ImportError:
            raise ImportError("TensorRT or PyCUDA not installed")

        self.trt = trt
        self.cuda = cuda

        print(f"Loading TensorRT engine: {engine_path}")

        # TensorRT 로거
        self.logger = trt.Logger(trt.Logger.WARNING)

        # Engine 로드
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())

        self.context = self.engine.create_execution_context()

        # Input/Output 바인딩
        self.input_name = self.engine.get_binding_name(0)
        self.output_name = self.engine.get_binding_name(1)

        self.input_shape = self.engine.get_binding_shape(0)
        self.output_shape = self.engine.get_binding_shape(1)

        print(f"  Input shape: {self.input_shape}")
        print(f"  Output shape: {self.output_shape}")

        # 메모리 할당
        self.input_host = cuda.pagelocked_empty(
            trt.volume(self.input_shape), dtype=np.float32
        )
        self.output_host = cuda.pagelocked_empty(
            trt.volume(self.output_shape), dtype=np.float32
        )

        self.input_device = cuda.mem_alloc(self.input_host.nbytes)
        self.output_device = cuda.mem_alloc(self.output_host.nbytes)

        self.stream = cuda.Stream()

        print("  ✓ TensorRT engine loaded")

    def __call__(self, input_array: np.ndarray) -> np.ndarray:
        """추론 실행"""
        # Input 복사
        np.copyto(self.input_host, input_array.ravel())

        # GPU로 전송
        self.cuda.memcpy_htod_async(self.input_device, self.input_host, self.stream)

        # 추론
        self.context.execute_async_v2(
            bindings=[int(self.input_device), int(self.output_device)],
            stream_handle=self.stream.handle
        )

        # 결과 가져오기
        self.cuda.memcpy_dtoh_async(self.output_host, self.output_device, self.stream)
        self.stream.synchronize()

        # Reshape
        output = self.output_host.reshape(self.output_shape)
        return output

# ============================================================================
# PatchCore Lite Inference
# ============================================================================

class PatchCoreLiteInference:
    """
    TensorRT 최적화된 PatchCore Lite 추론 클래스
    """

    def __init__(self, model_path: Path, engine_path: Path):
        print("="*60)
        print("Initializing PatchCore Lite Inference (TensorRT)")
        print("="*60)

        # Memory Bank 로드
        print("\n[1/3] Loading Memory Bank...")
        data = np.load(model_path, allow_pickle=True)

        self.memory_bank = torch.from_numpy(data['memory_bank']).float()
        self.config = data['config'].item()
        self.patch_shape = tuple(data['patch_shape'])

        # CUDA 사용 가능하면 GPU로
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.memory_bank = self.memory_bank.to(self.device)

        print(f"  Memory Bank size: {self.memory_bank.shape[0]}")
        print(f"  Feature dimension: {self.memory_bank.shape[1]}")
        print(f"  Using device: {self.device}")

        # Feature Reducer 로드
        self.feature_reducer = None
        if 'feature_reducer_components' in data:
            from sklearn.random_projection import SparseRandomProjection
            self.feature_reducer = SparseRandomProjection(
                n_components=int(data['reduced_dim'])
            )
            self.feature_reducer.components_ = data['feature_reducer_components']
            print(f"  Feature reduction: {data['original_feature_dim']} → {data['reduced_dim']}")

        # TensorRT Engine 로드
        print("\n[2/3] Loading TensorRT Engine...")
        self.engine = TensorRTEngine(engine_path)

        # Threshold (선택적)
        self.threshold = self.config.get('best_threshold', None)
        if self.threshold:
            print(f"\n  Threshold: {self.threshold:.6f}")

        print("\n[3/3] Ready for inference!")
        print("="*60)

    def preprocess(self, image_path: Path) -> np.ndarray:
        """이미지 전처리"""
        # 이미지 로드
        img = Image.open(image_path).convert('RGB')
        img = img.resize((224, 224))

        # Normalize
        img_array = np.array(img).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406]).reshape(1, 1, 3)
        std = np.array([0.229, 0.224, 0.225]).reshape(1, 1, 3)
        img_array = (img_array - mean) / std

        # (H, W, C) → (1, C, H, W)
        img_array = img_array.transpose(2, 0, 1)
        img_array = np.expand_dims(img_array, axis=0)

        return img_array.astype(np.float32)

    def extract_features(self, image: np.ndarray) -> torch.Tensor:
        """TensorRT로 feature 추출"""
        # TensorRT 추론
        features = self.engine(image)  # (1, C, H, W)

        # Reshape
        B, C, H, W = features.shape
        features = features.transpose(0, 2, 3, 1)  # (1, H, W, C)
        features = features.reshape(B, H * W, C)

        return torch.from_numpy(features).float()

    def predict(self, image_path: Path) -> Tuple[float, bool]:
        """
        단일 이미지 이상탐지

        Returns:
            anomaly_score: 이상 점수
            is_anomaly: 이상 여부 (threshold 사용 시)
        """
        # 전처리
        image = self.preprocess(image_path)

        # Feature 추출
        features = self.extract_features(image)  # (1, N, C)
        features = features.to(self.device)

        # Feature Reduction
        if self.feature_reducer is not None:
            B, N, C = features.shape
            features_np = features.cpu().numpy().reshape(B * N, C)
            features_reduced = self.feature_reducer.transform(features_np)
            features = torch.from_numpy(features_reduced).float().to(self.device)
            features = features.reshape(B, N, -1)

        # Anomaly Score 계산
        B, N, C = features.shape
        features = features.reshape(B * N, C)

        # K-NN Distance
        distances = self._compute_distances(features)

        # Image-level score
        distances = distances.reshape(B, N)
        score = distances.max(dim=1)[0].item()

        # Threshold 적용
        is_anomaly = score > self.threshold if self.threshold else None

        return score, is_anomaly

    def _compute_distances(self, features: torch.Tensor) -> torch.Tensor:
        """Memory Bank와의 K-NN distance"""
        N = features.shape[0]
        K = 5  # num_neighbors

        batch_size = 1000
        all_distances = []

        for i in range(0, N, batch_size):
            batch_features = features[i:i+batch_size]

            # L2 distance
            a_norm = (batch_features ** 2).sum(dim=1, keepdim=True)
            b_norm = (self.memory_bank ** 2).sum(dim=1, keepdim=True).T
            ab = torch.mm(batch_features, self.memory_bank.T)

            dist = a_norm + b_norm - 2 * ab

            # K-NN
            knn_dist, _ = torch.topk(dist, K, dim=1, largest=False)
            knn_dist = knn_dist.mean(dim=1)

            all_distances.append(knn_dist)

        return torch.cat(all_distances, dim=0)

    def predict_batch(self, image_paths: list) -> list:
        """배치 추론"""
        results = []
        for img_path in image_paths:
            score, is_anomaly = self.predict(img_path)
            results.append((img_path, score, is_anomaly))
        return results

    def benchmark(self, num_iterations: int = 100):
        """FPS 벤치마크"""
        print("\n" + "="*60)
        print(f"Benchmarking ({num_iterations} iterations)")
        print("="*60)

        # Dummy 이미지 생성
        dummy_image = np.random.randn(1, 3, 224, 224).astype(np.float32)

        # Warmup
        print("Warming up...")
        for _ in range(10):
            features = self.extract_features(dummy_image)

        # Benchmark
        print(f"Running {num_iterations} iterations...")
        start_time = time.time()

        for _ in range(num_iterations):
            features = self.extract_features(dummy_image)
            # KNN distance 계산도 포함
            features_flat = features.reshape(-1, features.shape[-1]).to(self.device)
            distances = self._compute_distances(features_flat)

        end_time = time.time()
        elapsed = end_time - start_time

        # 결과
        fps = num_iterations / elapsed
        latency_ms = (elapsed / num_iterations) * 1000

        print("\n" + "="*60)
        print("Benchmark Results")
        print("="*60)
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Average latency: {latency_ms:.2f}ms")
        print(f"  FPS: {fps:.2f}")
        print("="*60)

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='PatchCore Lite TensorRT Inference')
    parser.add_argument('--image', type=str, help='Single image path')
    parser.add_argument('--folder', type=str, help='Folder containing images')
    parser.add_argument('--benchmark', action='store_true', help='Run FPS benchmark')
    parser.add_argument('--engine', type=str, default='efficientnet_b0_fp16.engine',
                       help='TensorRT engine filename')
    parser.add_argument('--threshold', type=float, help='Anomaly threshold (optional)')

    args = parser.parse_args()

    config = INFERENCE_CONFIG.copy()

    # Engine 경로
    config['engine_path'] = config['engine_path'].parent / args.engine

    # Threshold 오버라이드
    if args.threshold:
        config['threshold'] = args.threshold

    # 모델 로드
    model = PatchCoreLiteInference(
        model_path=config['model_path'],
        engine_path=config['engine_path']
    )

    # Benchmark
    if args.benchmark:
        model.benchmark()
        return

    # 단일 이미지
    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: Image not found: {image_path}")
            return

        print(f"\nProcessing: {image_path}")
        start = time.time()
        score, is_anomaly = model.predict(image_path)
        elapsed = time.time() - start

        print("\n" + "="*60)
        print("Result")
        print("="*60)
        print(f"  Anomaly Score: {score:.6f}")
        if is_anomaly is not None:
            print(f"  Is Anomaly: {'YES' if is_anomaly else 'NO'}")
        print(f"  Inference Time: {elapsed*1000:.2f}ms")
        print("="*60)

    # 폴더
    elif args.folder:
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"Error: Folder not found: {folder_path}")
            return

        # 이미지 파일 수집
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp'}
        image_paths = [p for p in folder_path.iterdir()
                      if p.suffix.lower() in image_exts]

        print(f"\nFound {len(image_paths)} images")

        # 추론
        results = model.predict_batch(image_paths)

        # 결과 출력
        print("\n" + "="*60)
        print("Results")
        print("="*60)
        for img_path, score, is_anomaly in results:
            anomaly_str = "ANOMALY" if is_anomaly else "NORMAL" if is_anomaly is not None else "N/A"
            print(f"{img_path.name}: {score:.6f} ({anomaly_str})")
        print("="*60)

    else:
        print("Error: Please specify --image, --folder, or --benchmark")
        parser.print_help()

if __name__ == '__main__':
    main()
