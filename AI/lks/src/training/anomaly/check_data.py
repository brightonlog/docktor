#!/usr/bin/env python3
"""
데이터 상태 확인 스크립트
"""

import sys
from pathlib import Path
import random

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import IMAGE_DIR, LABEL_DIR, RANDOM_SEED
from training.anomaly.train_autoencoder import collect_data
from training.anomaly.train_unet import UNET_CONFIG

def main():
    print("="*60)
    print("Data Status Check")
    print("="*60)

    random.seed(RANDOM_SEED)

    config = UNET_CONFIG.copy()

    # 데이터 수집
    print("\n[1] Collecting data...")
    image_paths, labels = collect_data(
        IMAGE_DIR, LABEL_DIR,
        normal_category_id=config['normal_category_id'],
        anomaly_category_ids=config.get('anomaly_category_ids')
    )

    n_normal = sum(1 for l in labels if l == 0)
    n_anomaly = sum(1 for l in labels if l == 1)

    print(f"\n[2] Total samples: {len(image_paths)}")
    print(f"    - Normal: {n_normal}")
    print(f"    - Anomaly: {n_anomaly}")

    # 데이터 분할 시뮬레이션
    normal_indices = [i for i, l in enumerate(labels) if l == 0]
    anomaly_indices = [i for i, l in enumerate(labels) if l == 1]

    random.shuffle(normal_indices)

    n_train = int(len(normal_indices) * config['train_ratio'])
    train_indices = normal_indices[:n_train]
    val_normal_indices = normal_indices[n_train:]

    n_val_anomaly = min(len(anomaly_indices), len(val_normal_indices))
    random.shuffle(anomaly_indices)
    val_anomaly_indices = anomaly_indices[:n_val_anomaly]

    print(f"\n[3] Data split:")
    print(f"    - Train (normal only): {len(train_indices)}")
    print(f"    - Val (normal): {len(val_normal_indices)}")
    print(f"    - Val (anomaly): {len(val_anomaly_indices)}")
    print(f"    - Test (anomaly): {len(anomaly_indices) - n_val_anomaly}")

    # 경고
    print(f"\n[4] Warnings:")
    if n_normal < 200:
        print("    ⚠️  WARNING: Too few normal samples! Need at least 200.")
        print(f"       You have: {n_normal}")

    if n_anomaly < 50:
        print("    ⚠️  WARNING: Too few anomaly samples! Need at least 50.")
        print(f"       You have: {n_anomaly}")

    if len(train_indices) < 100:
        print("    ⚠️  WARNING: Training set too small! Need at least 100.")
        print(f"       You have: {len(train_indices)}")

    if len(val_anomaly_indices) < 20:
        print("    ⚠️  WARNING: Validation anomaly set too small!")
        print(f"       You have: {len(val_anomaly_indices)}")

    # 정상 카테고리 상세
    print(f"\n[5] Anomaly category filter:")
    print(f"    - Normal ID: {config['normal_category_id']}")
    print(f"    - Anomaly IDs: {config.get('anomaly_category_ids')}")

    if n_normal == 0 or n_anomaly == 0:
        print("\n❌ CRITICAL: No data available for training!")
        print("   Check if IMAGE_DIR and LABEL_DIR are correct:")
        print(f"   - IMAGE_DIR: {IMAGE_DIR}")
        print(f"   - LABEL_DIR: {LABEL_DIR}")
    elif n_normal >= 200 and n_anomaly >= 50:
        print("\n✅ Data looks good! You can proceed with training.")
    else:
        print("\n⚠️  Data is insufficient. Consider:")
        print("   - Adding more data")
        print("   - Adjusting anomaly_category_ids filter")
        print("   - Using all anomaly categories (set anomaly_category_ids=None)")

if __name__ == '__main__':
    main()
