#!/usr/bin/env python3
"""
ONNX 모델을 TensorRT로 변환 (INT8 양자화 포함)

젯슨 오린 나노에서 실행 권장

INT8 양자화를 위한 Calibration 데이터셋 필요

Usage:
    # FP16 변환 (빠름, 추천)
    python convert_to_tensorrt.py --precision fp16

    # INT8 변환 (더 빠름, calibration 필요)
    python convert_to_tensorrt.py --precision int8

Prerequisites:
    - NVIDIA TensorRT 설치 필요
    - 젯슨에서는 기본 설치되어 있음
    - Ubuntu/PC: pip install nvidia-tensorrt
"""

import sys
import argparse
from pathlib import Path
import numpy as np

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent  # deployment -> src -> lks
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import PROJECT_ROOT as CONFIG_ROOT, IMAGE_DIR, LABEL_DIR

# ============================================================================
# Configuration
# ============================================================================

TENSORRT_CONFIG = {
    'onnx_path': CONFIG_ROOT / 'models' / 'anomaly_patchcore_lite' / 'efficientnet_b0.onnx',
    'engine_save_dir': CONFIG_ROOT / 'models' / 'anomaly_patchcore_lite' / 'tensorrt',

    'image_size': (224, 224),
    'batch_size': 1,

    # Calibration (INT8용)
    'calibration_images': 500,  # Calibration에 사용할 이미지 수
}

# ============================================================================
# INT8 Calibrator
# ============================================================================

class ImageCalibrator:
    """
    INT8 양자화를 위한 Calibration
    정상 이미지를 사용하여 activation range 계산
    """

    def __init__(self, calibration_images, image_size, batch_size=1):
        self.image_paths = self._collect_calibration_images(calibration_images)
        self.image_size = image_size
        self.batch_size = batch_size
        self.current_index = 0

        print(f"Calibrator initialized with {len(self.image_paths)} images")

    def _collect_calibration_images(self, num_images):
        """Calibration용 이미지 수집"""
        from training.anomaly.train_autoencoder import collect_data

        print(f"\nCollecting {num_images} calibration images...")
        image_paths, labels = collect_data(
            IMAGE_DIR, LABEL_DIR,
            normal_category_id=101,
            anomaly_category_ids=None
        )

        # 정상 이미지만 사용
        normal_images = [img for img, label in zip(image_paths, labels) if label == 0]

        # 샘플링
        import random
        random.shuffle(normal_images)
        selected = normal_images[:num_images]

        print(f"  Selected {len(selected)} normal images for calibration")
        return selected

    def get_batch(self):
        """Calibration용 배치 생성"""
        if self.current_index >= len(self.image_paths):
            return None

        # 이미지 로드 및 전처리
        from PIL import Image
        import torchvision.transforms as transforms

        transform = transforms.Compose([
            transforms.Resize(self.image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

        batch_images = []
        for i in range(self.batch_size):
            if self.current_index >= len(self.image_paths):
                break

            img_path = self.image_paths[self.current_index]
            img = Image.open(img_path).convert('RGB')
            img_tensor = transform(img)
            batch_images.append(img_tensor.numpy())

            self.current_index += 1

        if not batch_images:
            return None

        batch = np.stack(batch_images, axis=0)
        return batch

    def reset(self):
        """Calibrator 리셋"""
        self.current_index = 0

# ============================================================================
# TensorRT Conversion
# ============================================================================

def convert_onnx_to_tensorrt(onnx_path, engine_path, precision='fp16', calibrator=None):
    """
    ONNX → TensorRT 변환

    Args:
        onnx_path: ONNX 모델 경로
        engine_path: TensorRT 엔진 저장 경로
        precision: 'fp32', 'fp16', 'int8'
        calibrator: INT8용 calibrator (precision='int8'일 때 필요)
    """
    try:
        import tensorrt as trt
    except ImportError:
        print("\n❌ TensorRT not installed!")
        print("  Jetson: TensorRT is pre-installed")
        print("  Ubuntu/PC: pip install nvidia-tensorrt")
        return False

    print("="*60)
    print(f"Converting ONNX to TensorRT ({precision.upper()})")
    print("="*60)

    # TensorRT 로거
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

    # Builder 생성
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, TRT_LOGGER)

    # ONNX 파싱
    print(f"\n[1/4] Parsing ONNX model: {onnx_path}")
    with open(onnx_path, 'rb') as f:
        if not parser.parse(f.read()):
            print("Failed to parse ONNX file")
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            return False

    print("  ✓ ONNX parsed successfully")

    # Builder config
    config = builder.create_builder_config()

    # 메모리 제한 (젯슨 오린 나노: 8GB)
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 2 << 30)  # 2GB

    # Precision 설정
    print(f"\n[2/4] Setting precision: {precision.upper()}")

    if precision == 'fp16':
        if not builder.platform_has_fast_fp16:
            print("  ⚠ Warning: FP16 not supported on this platform")
        else:
            config.set_flag(trt.BuilderFlag.FP16)
            print("  ✓ FP16 enabled")

    elif precision == 'int8':
        if not builder.platform_has_fast_int8:
            print("  ⚠ Warning: INT8 not supported on this platform")
        else:
            config.set_flag(trt.BuilderFlag.INT8)

            if calibrator is None:
                print("  ❌ Error: INT8 requires calibrator")
                return False

            # Calibrator 설정
            config.int8_calibrator = calibrator
            print("  ✓ INT8 enabled with calibrator")

    # Engine 빌드
    print(f"\n[3/4] Building TensorRT engine (this may take a few minutes)...")
    serialized_engine = builder.build_serialized_network(network, config)

    if serialized_engine is None:
        print("  ❌ Failed to build engine")
        return False

    print("  ✓ Engine built successfully")

    # Engine 저장
    print(f"\n[4/4] Saving engine to: {engine_path}")
    engine_path.parent.mkdir(parents=True, exist_ok=True)

    with open(engine_path, 'wb') as f:
        f.write(serialized_engine)

    # 파일 크기
    file_size_mb = engine_path.stat().st_size / (1024 ** 2)
    print(f"  ✓ Engine saved ({file_size_mb:.2f} MB)")

    print("\n" + "="*60)
    print("Conversion Complete!")
    print("="*60)

    # 크기 비교
    onnx_size_mb = onnx_path.stat().st_size / (1024 ** 2)
    reduction = (1 - file_size_mb / onnx_size_mb) * 100

    print(f"\n  Model Size:")
    print(f"    ONNX:       {onnx_size_mb:.2f} MB")
    print(f"    TensorRT:   {file_size_mb:.2f} MB")
    print(f"    Reduction:  {reduction:.1f}%")

    print(f"\n  Next step: Test inference")
    print(f"  Run: python inference_tensorrt.py --engine {engine_path.name}")
    print("="*60)

    return True

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Convert ONNX to TensorRT')
    parser.add_argument('--precision', type=str, default='fp16',
                       choices=['fp32', 'fp16', 'int8'],
                       help='Precision mode (default: fp16)')
    parser.add_argument('--calibration-images', type=int, default=500,
                       help='Number of images for INT8 calibration (default: 500)')

    args = parser.parse_args()

    config = TENSORRT_CONFIG.copy()

    # Engine 경로
    engine_name = f"efficientnet_b0_{args.precision}.engine"
    engine_path = config['engine_save_dir'] / engine_name

    # Calibrator (INT8용)
    calibrator = None
    if args.precision == 'int8':
        print("\n[Calibration] Creating INT8 calibrator...")
        calibrator = ImageCalibrator(
            calibration_images=args.calibration_images,
            image_size=config['image_size'],
            batch_size=config['batch_size']
        )

    # 변환 실행
    success = convert_onnx_to_tensorrt(
        onnx_path=config['onnx_path'],
        engine_path=engine_path,
        precision=args.precision,
        calibrator=calibrator
    )

    if not success:
        print("\n❌ Conversion failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
