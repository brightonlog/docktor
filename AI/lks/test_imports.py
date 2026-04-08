#!/usr/bin/env python3
"""
모든 경로 및 import 검증 스크립트
"""

import sys
from pathlib import Path

print("="*60)
print("경로 및 Import 검증")
print("="*60)

# 1. 현재 작업 디렉토리
print(f"\n1. 현재 작업 디렉토리:")
print(f"   {Path.cwd()}")

# 2. 각 파일의 PROJECT_ROOT 시뮬레이션
print(f"\n2. PROJECT_ROOT 검증:")

test_files = [
    "src/training/anomaly/train_patchcore_lite.py",
    "src/training/anomaly/validate_patchcore_lite.py",
    "src/deployment/export_to_onnx.py",
    "src/deployment/convert_to_tensorrt.py",
    "src/deployment/inference_tensorrt.py",
    "src/deployment/inference_mlflow.py",
]

for file_rel_path in test_files:
    file_path = Path.cwd() / file_rel_path
    if file_path.exists():
        # PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
        project_root = file_path.parent.parent.parent.parent
        print(f"   {file_rel_path}")
        print(f"      → PROJECT_ROOT: {project_root}")
        print(f"      → 올바름: {project_root == Path.cwd()}")
    else:
        print(f"   {file_rel_path} - 파일 없음!")

# 3. Import 테스트
print(f"\n3. Import 테스트:")

errors = []

# 3.1 training_config
try:
    sys.path.insert(0, str(Path.cwd() / 'src'))
    from config.training_config import (
        IMAGE_DIR, LABEL_DIR, PROJECT_ROOT,
        RANDOM_SEED, MLFLOW_TRACKING_URI
    )
    print(f"   ✓ config.training_config")
    print(f"      - IMAGE_DIR: {IMAGE_DIR}")
    print(f"      - LABEL_DIR: {LABEL_DIR}")
    print(f"      - PROJECT_ROOT: {PROJECT_ROOT}")
except Exception as e:
    print(f"   ✗ config.training_config: {e}")
    errors.append(f"config.training_config: {e}")

# 3.2 train_autoencoder (collect_data, AnomalyDataset)
try:
    from training.anomaly.train_autoencoder import collect_data, AnomalyDataset
    print(f"   ✓ training.anomaly.train_autoencoder")
except Exception as e:
    print(f"   ✗ training.anomaly.train_autoencoder: {e}")
    errors.append(f"train_autoencoder: {e}")

# 3.3 train_patchcore_lite
try:
    from training.anomaly.train_patchcore_lite import (
        PatchCoreLite, PATCHCORE_LITE_CONFIG
    )
    print(f"   ✓ training.anomaly.train_patchcore_lite")
    print(f"      - Backbone: {PATCHCORE_LITE_CONFIG['backbone']}")
    print(f"      - Coreset ratio: {PATCHCORE_LITE_CONFIG['coreset_sampling_ratio']}")
except Exception as e:
    print(f"   ✗ training.anomaly.train_patchcore_lite: {e}")
    errors.append(f"train_patchcore_lite: {e}")

# 4. 필수 디렉토리 확인
print(f"\n4. 필수 디렉토리 확인:")

required_dirs = [
    "src/config",
    "src/training/anomaly",
    "src/deployment",
    "models",
    "results",
]

for dir_path in required_dirs:
    full_path = Path.cwd() / dir_path
    exists = full_path.exists()
    print(f"   {'✓' if exists else '✗'} {dir_path}: {'존재' if exists else '없음'}")
    if not exists:
        errors.append(f"디렉토리 없음: {dir_path}")

# 5. 데이터 디렉토리 확인
print(f"\n5. 데이터 디렉토리 확인:")
try:
    from config.training_config import IMAGE_DIR, LABEL_DIR
    print(f"   IMAGE_DIR: {IMAGE_DIR}")
    print(f"      존재: {IMAGE_DIR.exists()}")
    print(f"   LABEL_DIR: {LABEL_DIR}")
    print(f"      존재: {LABEL_DIR.exists()}")
except Exception as e:
    print(f"   ✗ 확인 실패: {e}")
    errors.append(f"데이터 디렉토리: {e}")

# 최종 결과
print(f"\n" + "="*60)
if not errors:
    print("✓ 모든 검증 통과!")
    print("="*60)
    print("\n실행 가능한 명령어:")
    print("  python src/training/anomaly/train_patchcore_lite.py")
    print("  python src/training/anomaly/validate_patchcore_lite.py --num_samples 200")
    print("  python src/deployment/export_to_onnx.py")
else:
    print("✗ 검증 실패!")
    print("="*60)
    print("\n오류 목록:")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")

print("="*60)
