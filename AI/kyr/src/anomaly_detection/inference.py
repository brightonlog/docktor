"""
Anomaly Detection 추론 스크립트

학습된 Autoencoder를 사용하여 이상 탐지 수행

주요 기능:
1. 단일 이미지 추론
2. 디렉토리 배치 추론
3. 실시간 카메라 추론 (Jetson)
4. 이상 영역 히트맵 시각화

Usage:
    # 단일 이미지
    python inference.py --image test.jpg --model models/anomaly_detection/best_model.pt

    # 디렉토리 배치
    python inference.py --dir test_images/ --model models/anomaly_detection/best_model.pt

    # 실시간 카메라
    python inference.py --camera --model models/anomaly_detection/best_model.pt
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms

# 시각화 (선택적)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[Warning] OpenCV not installed. Visualization limited.")

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # GUI 없이 저장
    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False

# 모델 임포트
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.anomaly_detection.models.autoencoder import (
    SSIMAnomalyAutoencoder,
    LightweightAutoencoder,
)


@dataclass
class AnomalyResult:
    """이상 탐지 결과"""
    image_path: str
    anomaly_score: float
    is_anomaly: bool
    threshold: float
    inference_time_ms: float
    anomaly_map: Optional[np.ndarray] = None

    def to_dict(self) -> dict:
        return {
            'image_path': self.image_path,
            'anomaly_score': round(self.anomaly_score, 6),
            'is_anomaly': self.is_anomaly,
            'threshold': self.threshold,
            'inference_time_ms': round(self.inference_time_ms, 2)
        }


class AnomalyDetector:
    """
    이상 탐지기

    학습된 Autoencoder를 사용하여 이미지의 이상 여부를 판단합니다.

    Usage:
        detector = AnomalyDetector('models/best_model.pt', threshold=0.01)
        result = detector.predict('test.jpg')

        if result.is_anomaly:
            print(f"이상 감지! 점수: {result.anomaly_score}")
    """

    def __init__(
        self,
        model_path: str,
        threshold: float = 0.01,
        device: Optional[str] = None,
        input_size: int = 256
    ):
        """
        Args:
            model_path: 학습된 모델 경로
            threshold: 이상 판정 임계값 (이 값보다 크면 이상)
            device: 'cuda' or 'cpu' (None이면 자동 선택)
            input_size: 입력 이미지 크기
        """
        self.threshold = threshold
        self.input_size = input_size

        # 디바이스 설정
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        # 모델 로드
        self.model = self._load_model(model_path)
        self.model.eval()

        # 이미지 전처리
        self.transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
        ])

        print(f"[AnomalyDetector] Initialized")
        print(f"  Model: {model_path}")
        print(f"  Device: {self.device}")
        print(f"  Threshold: {threshold}")

    def _load_model(self, model_path: str) -> torch.nn.Module:
        """모델 로드"""
        checkpoint = torch.load(model_path, map_location=self.device)

        # 모델 설정 추출
        model_config = checkpoint.get('model_config', {})
        latent_dim = model_config.get('latent_dim', 256)
        input_size = model_config.get('input_size', 256)

        # 모델 타입 추정 (파라미터 수로 구분)
        state_dict = checkpoint['model_state_dict']

        # Lightweight 모델은 파라미터가 더 적음
        if 'encoder.0.weight' in state_dict:
            # Sequential 모델 (Lightweight)
            model = LightweightAutoencoder(latent_dim=latent_dim, input_size=input_size)
        else:
            # Standard 모델
            model = SSIMAnomalyAutoencoder(latent_dim=latent_dim, input_size=input_size)

        model.load_state_dict(state_dict)
        model = model.to(self.device)

        return model

    def preprocess(self, image: Image.Image) -> torch.Tensor:
        """이미지 전처리"""
        tensor = self.transform(image)
        return tensor.unsqueeze(0).to(self.device)

    @torch.no_grad()
    def predict(
        self,
        image_input,
        return_map: bool = False
    ) -> AnomalyResult:
        """
        이상 탐지 수행

        Args:
            image_input: 이미지 경로 (str) 또는 PIL.Image 또는 numpy.ndarray
            return_map: 이상 맵 반환 여부

        Returns:
            AnomalyResult 객체
        """
        # 이미지 로드
        image_path = "unknown"

        if isinstance(image_input, str):
            image_path = image_input
            image = Image.open(image_input).convert('RGB')
        elif isinstance(image_input, np.ndarray):
            # BGR -> RGB (OpenCV에서 온 경우)
            if len(image_input.shape) == 3 and image_input.shape[2] == 3:
                image_input = image_input[:, :, ::-1]
            image = Image.fromarray(image_input)
        elif isinstance(image_input, Image.Image):
            image = image_input.convert('RGB')
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")

        # 전처리
        input_tensor = self.preprocess(image)

        # 추론 시간 측정
        start_time = time.perf_counter()

        # 이상 점수 계산
        anomaly_score, anomaly_map = self.model.compute_anomaly_score(
            input_tensor, return_map=return_map
        )

        inference_time = (time.perf_counter() - start_time) * 1000  # ms

        # 결과 생성
        score = anomaly_score.item()
        is_anomaly = score > self.threshold

        result = AnomalyResult(
            image_path=image_path,
            anomaly_score=score,
            is_anomaly=is_anomaly,
            threshold=self.threshold,
            inference_time_ms=inference_time,
            anomaly_map=anomaly_map.cpu().numpy()[0, 0] if return_map else None
        )

        return result

    def predict_batch(
        self,
        image_paths: List[str],
        return_maps: bool = False
    ) -> List[AnomalyResult]:
        """배치 추론"""
        results = []
        for path in image_paths:
            try:
                result = self.predict(path, return_map=return_maps)
                results.append(result)
            except Exception as e:
                print(f"[Error] Failed to process {path}: {e}")
        return results

    def visualize_result(
        self,
        image_input,
        result: AnomalyResult,
        save_path: Optional[str] = None,
        show: bool = False
    ) -> Optional[np.ndarray]:
        """
        결과 시각화

        원본 이미지, 복원 이미지, 이상 히트맵을 나란히 표시

        Returns:
            시각화 이미지 (numpy array)
        """
        if not PLT_AVAILABLE:
            print("[Warning] Matplotlib not available for visualization")
            return None

        # 이미지 로드
        if isinstance(image_input, str):
            image = Image.open(image_input).convert('RGB')
        elif isinstance(image_input, np.ndarray):
            image = Image.fromarray(image_input)
        else:
            image = image_input.convert('RGB')

        # 모델 출력 얻기
        input_tensor = self.preprocess(image)
        with torch.no_grad():
            reconstructed = self.model(input_tensor)

        # Tensor -> numpy
        original = input_tensor.cpu().numpy()[0].transpose(1, 2, 0)
        recon = reconstructed.cpu().numpy()[0].transpose(1, 2, 0)

        # 이상 맵
        if result.anomaly_map is not None:
            anomaly_map = result.anomaly_map
        else:
            _, anomaly_map = self.model.compute_anomaly_score(input_tensor, return_map=True)
            anomaly_map = anomaly_map.cpu().numpy()[0, 0]

        # 시각화
        fig, axes = plt.subplots(1, 4, figsize=(16, 4))

        # 원본
        axes[0].imshow(original)
        axes[0].set_title('Original')
        axes[0].axis('off')

        # 복원
        axes[1].imshow(recon)
        axes[1].set_title('Reconstructed')
        axes[1].axis('off')

        # 차이
        diff = np.abs(original - recon).mean(axis=2)
        axes[2].imshow(diff, cmap='hot')
        axes[2].set_title('Difference')
        axes[2].axis('off')

        # 히트맵 오버레이
        axes[3].imshow(original)
        heatmap = axes[3].imshow(anomaly_map, cmap='jet', alpha=0.5)
        axes[3].set_title(f'Anomaly Map\nScore: {result.anomaly_score:.4f}')
        axes[3].axis('off')
        plt.colorbar(heatmap, ax=axes[3], fraction=0.046)

        # 이상 여부 표시
        status = "ANOMALY" if result.is_anomaly else "NORMAL"
        color = 'red' if result.is_anomaly else 'green'
        fig.suptitle(f'{status} (threshold: {result.threshold})', fontsize=14, color=color)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[Saved] Visualization: {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

        # numpy 배열로 반환
        fig.canvas.draw()
        vis_image = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        vis_image = vis_image.reshape(fig.canvas.get_width_height()[::-1] + (3,))

        return vis_image

    def set_threshold(self, threshold: float):
        """임계값 변경"""
        self.threshold = threshold
        print(f"[Threshold] Updated to {threshold}")

    def calibrate_threshold(
        self,
        normal_images: List[str],
        percentile: float = 99.0
    ) -> float:
        """
        정상 이미지로 임계값 자동 보정

        정상 이미지들의 이상 점수 분포에서 percentile 값을 임계값으로 설정

        Args:
            normal_images: 정상 이미지 경로 리스트
            percentile: 사용할 백분위수 (99 = 상위 1% 허용)

        Returns:
            보정된 임계값
        """
        print(f"[Calibration] Processing {len(normal_images)} normal images...")

        scores = []
        for path in normal_images:
            try:
                result = self.predict(path)
                scores.append(result.anomaly_score)
            except Exception as e:
                print(f"[Warning] Skipping {path}: {e}")

        if len(scores) == 0:
            print("[Error] No valid images for calibration")
            return self.threshold

        scores = np.array(scores)
        new_threshold = np.percentile(scores, percentile)

        print(f"[Calibration] Score statistics:")
        print(f"  Mean: {scores.mean():.6f}")
        print(f"  Std: {scores.std():.6f}")
        print(f"  Min: {scores.min():.6f}")
        print(f"  Max: {scores.max():.6f}")
        print(f"  {percentile}th percentile: {new_threshold:.6f}")

        self.threshold = new_threshold
        return new_threshold


def run_camera_inference(detector: AnomalyDetector, camera_id: int = 0):
    """
    실시간 카메라 추론

    Args:
        detector: AnomalyDetector 인스턴스
        camera_id: 카메라 ID (기본 0)
    """
    if not CV2_AVAILABLE:
        print("[Error] OpenCV required for camera inference")
        return

    cap = cv2.VideoCapture(camera_id)

    if not cap.isOpened():
        print(f"[Error] Cannot open camera {camera_id}")
        return

    print(f"[Camera] Starting inference (press 'q' to quit)")

    fps_history = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # BGR -> RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 추론
        result = detector.predict(rgb_frame, return_map=True)

        fps_history.append(1000 / result.inference_time_ms)
        if len(fps_history) > 30:
            fps_history.pop(0)
        avg_fps = sum(fps_history) / len(fps_history)

        # 결과 표시
        status = "ANOMALY!" if result.is_anomaly else "Normal"
        color = (0, 0, 255) if result.is_anomaly else (0, 255, 0)

        cv2.putText(frame, f"{status}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"Score: {result.anomaly_score:.4f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"FPS: {avg_fps:.1f}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # 히트맵 오버레이
        if result.anomaly_map is not None:
            heatmap = cv2.applyColorMap(
                (result.anomaly_map * 255).astype(np.uint8),
                cv2.COLORMAP_JET
            )
            heatmap = cv2.resize(heatmap, (frame.shape[1], frame.shape[0]))
            overlay = cv2.addWeighted(frame, 0.6, heatmap, 0.4, 0)
        else:
            overlay = frame

        cv2.imshow('Anomaly Detection', overlay)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Anomaly Detection Inference')
    parser.add_argument('--model', type=str, required=True, help='Model path')
    parser.add_argument('--image', type=str, default=None, help='Single image path')
    parser.add_argument('--dir', type=str, default=None, help='Directory for batch inference')
    parser.add_argument('--camera', action='store_true', help='Run camera inference')
    parser.add_argument('--camera-id', type=int, default=0, help='Camera ID')
    parser.add_argument('--threshold', type=float, default=0.01, help='Anomaly threshold')
    parser.add_argument('--input-size', type=int, default=256, help='Input image size')
    parser.add_argument('--output', type=str, default='results', help='Output directory')
    parser.add_argument('--visualize', action='store_true', help='Save visualization')
    parser.add_argument('--calibrate', type=str, default=None,
                        help='Directory of normal images for threshold calibration')

    args = parser.parse_args()

    # 출력 디렉토리
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 탐지기 초기화
    detector = AnomalyDetector(
        model_path=args.model,
        threshold=args.threshold,
        input_size=args.input_size
    )

    # 임계값 보정
    if args.calibrate:
        cal_dir = Path(args.calibrate)
        cal_images = list(cal_dir.rglob('*.jpg')) + list(cal_dir.rglob('*.png'))
        detector.calibrate_threshold([str(p) for p in cal_images[:100]])

    # 추론 모드 선택
    if args.camera:
        run_camera_inference(detector, args.camera_id)

    elif args.image:
        result = detector.predict(args.image, return_map=args.visualize)
        print(f"\n[Result] {result.image_path}")
        print(f"  Anomaly Score: {result.anomaly_score:.6f}")
        print(f"  Is Anomaly: {result.is_anomaly}")
        print(f"  Inference Time: {result.inference_time_ms:.2f} ms")

        if args.visualize:
            vis_path = output_dir / f"{Path(args.image).stem}_result.png"
            detector.visualize_result(args.image, result, save_path=str(vis_path))

    elif args.dir:
        image_dir = Path(args.dir)
        image_paths = list(image_dir.rglob('*.jpg')) + list(image_dir.rglob('*.png'))
        print(f"\n[Batch] Processing {len(image_paths)} images...")

        results = []
        anomaly_count = 0

        for path in image_paths:
            result = detector.predict(str(path), return_map=args.visualize)
            results.append(result)

            status = "ANOMALY" if result.is_anomaly else "normal"
            print(f"  {path.name}: {status} (score: {result.anomaly_score:.4f})")

            if result.is_anomaly:
                anomaly_count += 1
                if args.visualize:
                    vis_path = output_dir / f"{path.stem}_anomaly.png"
                    detector.visualize_result(str(path), result, save_path=str(vis_path))

        # 결과 저장
        results_json = output_dir / "results.json"
        with open(results_json, 'w') as f:
            json.dump([r.to_dict() for r in results], f, indent=2)

        print(f"\n[Summary]")
        print(f"  Total: {len(results)}")
        print(f"  Anomalies: {anomaly_count}")
        print(f"  Normal: {len(results) - anomaly_count}")
        print(f"  Results saved: {results_json}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
