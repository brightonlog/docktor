#!/usr/bin/env python3
"""
PatchCore for Ship Coating Anomaly Detection
Memory-bank 기반 이상탐지 - 학습 불필요, 높은 정확도

PatchCore 원리:
1. Pre-trained WideResNet50으로 정상 이미지 feature 추출
2. Feature를 Memory Bank에 저장 (CoreSet Sampling으로 압축)
3. 테스트 시 Nearest Neighbor Distance로 이상 점수 계산

Usage:
    python train_patchcore.py
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import roc_auc_score, precision_recall_curve
from sklearn.random_projection import SparseRandomProjection
from tqdm import tqdm
import timm
from scipy.ndimage import gaussian_filter

# MLflow
import mlflow
import mlflow.pytorch

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import (
    IMAGE_DIR, LABEL_DIR, PROJECT_ROOT as CONFIG_ROOT,
    RANDOM_SEED, MLFLOW_TRACKING_URI
)

from training.anomaly.train_autoencoder import collect_data, AnomalyDataset

# ============================================================================
# Configuration
# ============================================================================

PATCHCORE_CONFIG = {
    # 이미지 설정
    'image_size': (224, 224),  # WideResNet 표준 입력

    # Feature Extraction
    'backbone': 'wide_resnet50_2',  # timm 모델
    'layers': ['layer2', 'layer3'],  # 중간 layer feature 사용

    # Memory Bank
    'coreset_sampling_ratio': 0.1,  # 메모리 압축 비율 (10%만 저장)
    'num_neighbors': 9,  # K-NN의 K

    # 데이터
    'batch_size': 32,
    'normal_category_id': 101,
    'anomaly_category_ids': None,

    # 저장 경로
    'model_save_dir': CONFIG_ROOT / 'models' / 'anomaly_patchcore',
    'results_dir': CONFIG_ROOT / 'results' / 'anomaly_patchcore',
}

# ============================================================================
# PatchCore Model
# ============================================================================

class PatchCore:
    """
    PatchCore Anomaly Detection

    학습 단계:
    1. Backbone으로 정상 이미지 feature 추출
    2. CoreSet Sampling으로 메모리 압축
    3. Feature를 Memory Bank에 저장

    추론 단계:
    1. 테스트 이미지 feature 추출
    2. Memory Bank와 NN Distance 계산
    3. Distance가 높으면 이상
    """

    def __init__(self, config: Dict, device: str = 'cuda'):
        self.config = config
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        # Backbone (Pre-trained WideResNet)
        self.backbone = timm.create_model(
            config['backbone'],
            pretrained=True,
            features_only=True,
            out_indices=[2, 3]  # layer2, layer3
        )
        self.backbone.to(self.device)
        self.backbone.eval()

        # Feature dimension
        with torch.no_grad():
            dummy = torch.zeros(1, 3, *config['image_size']).to(self.device)
            features = self.backbone(dummy)
            self.feature_dim = sum([f.shape[1] for f in features])
            self.patch_shape = features[0].shape[2:]  # (H, W)

        print(f"Feature dimension: {self.feature_dim}")
        print(f"Patch shape: {self.patch_shape}")

        # Memory Bank (학습 후 채워짐)
        self.memory_bank = None
        self.memory_bank_coordinates = None

        # 통계
        self.train_features = []

    def extract_features(self, images: torch.Tensor) -> torch.Tensor:
        """이미지에서 multi-scale feature 추출"""
        with torch.no_grad():
            # Backbone forward
            features = self.backbone(images)

            # Multi-scale feature concatenation
            patch_features = []
            for feat in features:
                # Resize to same spatial size
                feat_resized = F.interpolate(
                    feat,
                    size=self.patch_shape,
                    mode='bilinear',
                    align_corners=False
                )
                patch_features.append(feat_resized)

            # Concatenate along channel dimension
            patch_features = torch.cat(patch_features, dim=1)  # (B, C, H, W)

            # Reshape to (B, H*W, C)
            B, C, H, W = patch_features.shape
            patch_features = patch_features.permute(0, 2, 3, 1)  # (B, H, W, C)
            patch_features = patch_features.reshape(B, H * W, C)

            return patch_features

    def fit(self, dataloader: DataLoader):
        """정상 데이터로 Memory Bank 구축"""
        print("\n" + "="*60)
        print("Building Memory Bank from Normal Samples")
        print("="*60)

        self.backbone.eval()
        all_features = []

        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Extracting features"):
                images = batch['image'].to(self.device)

                # Feature 추출
                features = self.extract_features(images)  # (B, N_patches, C)

                # List에 저장
                B, N, C = features.shape
                features = features.reshape(B * N, C)
                all_features.append(features.cpu().numpy())

        # Concatenate all features
        all_features = np.concatenate(all_features, axis=0)
        print(f"\nTotal features extracted: {all_features.shape[0]}")

        # CoreSet Sampling (메모리 압축)
        print("\nApplying CoreSet Sampling...")
        self.memory_bank = self._coreset_sampling(
            all_features,
            sampling_ratio=self.config['coreset_sampling_ratio']
        )

        print(f"Memory Bank size: {self.memory_bank.shape[0]} (ratio: {self.config['coreset_sampling_ratio']:.1%})")

        # Torch tensor로 변환
        self.memory_bank = torch.from_numpy(self.memory_bank).float().to(self.device)

        return self

    def _coreset_sampling(self, features: np.ndarray, sampling_ratio: float) -> np.ndarray:
        """
        CoreSet Sampling (Greedy k-Center)
        전체 feature를 대표하는 subset 선택
        """
        num_samples = int(len(features) * sampling_ratio)

        # Random sampling (간단한 버전, 속도 우선)
        # 더 정확한 방법: Greedy k-Center algorithm
        indices = np.random.choice(len(features), num_samples, replace=False)
        return features[indices]

    def predict(self, dataloader: DataLoader) -> Tuple[np.ndarray, np.ndarray]:
        """이상 점수 계산"""
        self.backbone.eval()
        all_scores = []
        all_labels = []

        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Computing anomaly scores"):
                images = batch['image'].to(self.device)
                labels = batch['label'].numpy()

                # Feature 추출
                features = self.extract_features(images)  # (B, N_patches, C)

                # Anomaly score 계산 (patch-level)
                B, N, C = features.shape
                features = features.reshape(B * N, C)

                # K-NN distance to Memory Bank
                distances = self._compute_distances(features)

                # Image-level score (max patch distance)
                distances = distances.reshape(B, N)
                scores = distances.max(dim=1)[0]  # (B,)

                all_scores.extend(scores.cpu().numpy())
                all_labels.extend(labels)

        return np.array(all_scores), np.array(all_labels)

    def _compute_distances(self, features: torch.Tensor) -> torch.Tensor:
        """
        Memory Bank와의 K-NN distance 계산
        """
        # Pairwise L2 distance
        # features: (N, C)
        # memory_bank: (M, C)
        # distance: (N, M)

        N = features.shape[0]
        M = self.memory_bank.shape[0]
        K = self.config['num_neighbors']

        # Batch로 처리 (메모리 효율)
        batch_size = 1000
        all_distances = []

        for i in range(0, N, batch_size):
            batch_features = features[i:i+batch_size]

            # L2 distance: ||a - b||^2 = ||a||^2 + ||b||^2 - 2<a,b>
            a_norm = (batch_features ** 2).sum(dim=1, keepdim=True)  # (B, 1)
            b_norm = (self.memory_bank ** 2).sum(dim=1, keepdim=True).T  # (1, M)
            ab = torch.mm(batch_features, self.memory_bank.T)  # (B, M)

            dist = a_norm + b_norm - 2 * ab  # (B, M)

            # K-NN (K개의 가장 가까운 거리의 평균)
            knn_dist, _ = torch.topk(dist, K, dim=1, largest=False)
            knn_dist = knn_dist.mean(dim=1)  # (B,)

            all_distances.append(knn_dist)

        return torch.cat(all_distances, dim=0)

    def save(self, filepath: Path):
        """Memory Bank 저장"""
        filepath.parent.mkdir(parents=True, exist_ok=True)

        save_dict = {
            'config': {k: str(v) if isinstance(v, Path) else v
                      for k, v in self.config.items()},
            'memory_bank': self.memory_bank.cpu().numpy(),
            'feature_dim': self.feature_dim,
            'patch_shape': self.patch_shape,
        }

        np.savez_compressed(filepath, **save_dict)
        print(f"Model saved to {filepath}")

    def load(self, filepath: Path):
        """Memory Bank 로드"""
        data = np.load(filepath, allow_pickle=True)

        self.memory_bank = torch.from_numpy(data['memory_bank']).float().to(self.device)
        self.feature_dim = int(data['feature_dim'])
        self.patch_shape = tuple(data['patch_shape'])

        print(f"Model loaded from {filepath}")
        print(f"Memory Bank size: {self.memory_bank.shape[0]}")

# ============================================================================
# Evaluation
# ============================================================================

def evaluate_patchcore(
    model: PatchCore,
    test_loader: DataLoader,
    results_dir: Path
) -> Dict:
    """PatchCore 평가"""
    print("\n" + "="*60)
    print("Evaluating PatchCore")
    print("="*60)

    # 이상 점수 계산
    scores, labels = model.predict(test_loader)

    # 결과 디렉토리
    results_dir.mkdir(parents=True, exist_ok=True)

    # AUROC
    auroc = roc_auc_score(labels, scores) if len(np.unique(labels)) > 1 else 0.0
    print(f"\nAUROC: {auroc:.4f}")

    # 최적 임계값
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
    best_idx = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]
    best_f1 = f1_scores[best_idx]

    print(f"Best Threshold: {best_threshold:.6f}")
    print(f"Best F1-Score: {best_f1:.4f}")

    # 정상/이상 점수 분포
    normal_scores = scores[labels == 0]
    anomaly_scores = scores[labels == 1]

    print(f"\nNormal scores - Mean: {normal_scores.mean():.6f}, Std: {normal_scores.std():.6f}")
    if len(anomaly_scores) > 0:
        print(f"Anomaly scores - Mean: {anomaly_scores.mean():.6f}, Std: {anomaly_scores.std():.6f}")

    # 결과 저장
    report = {
        'model': 'PatchCore',
        'auroc': float(auroc),
        'best_threshold': float(best_threshold),
        'best_f1_score': float(best_f1),
        'normal_mean': float(normal_scores.mean()),
        'normal_std': float(normal_scores.std()),
        'anomaly_mean': float(anomaly_scores.mean()) if len(anomaly_scores) > 0 else None,
        'anomaly_std': float(anomaly_scores.std()) if len(anomaly_scores) > 0 else None,
        'total_samples': len(labels),
        'normal_samples': int((labels == 0).sum()),
        'anomaly_samples': int((labels == 1).sum()),
    }

    with open(results_dir / 'evaluation_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    return report

# ============================================================================
# Main
# ============================================================================

def main():
    print("="*60)
    print("Ship Coating Anomaly Detection - PatchCore")
    print("="*60)

    # Random seed
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(RANDOM_SEED)

    config = PATCHCORE_CONFIG.copy()

    # MLflow 설정
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment_name = "ship-coating-anomaly-patchcore"
    mlflow.set_experiment(experiment_name)

    # 1. 데이터 수집
    print("\n[1/4] Collecting data...")
    image_paths, labels = collect_data(
        IMAGE_DIR, LABEL_DIR,
        normal_category_id=config['normal_category_id'],
        anomaly_category_ids=config.get('anomaly_category_ids')
    )

    n_normal = sum(1 for l in labels if l == 0)
    n_anomaly = sum(1 for l in labels if l == 1)

    print(f"  Total samples: {len(image_paths)}")
    print(f"  Normal samples: {n_normal}")
    print(f"  Anomaly samples: {n_anomaly}")

    # 2. 데이터 분할
    print("\n[2/4] Splitting data...")

    normal_indices = [i for i, l in enumerate(labels) if l == 0]
    anomaly_indices = [i for i, l in enumerate(labels) if l == 1]

    random.shuffle(normal_indices)
    random.shuffle(anomaly_indices)

    # Train: 정상만 사용 (70%) - Val/Test를 위해 더 많이 남김
    n_train = int(len(normal_indices) * 0.7)
    train_indices = normal_indices[:n_train]
    remaining_normal = normal_indices[n_train:]

    # 남은 정상을 Val:Test = 1:1 비율로 분할
    n_val_normal = len(remaining_normal) // 2
    val_normal_indices = remaining_normal[:n_val_normal]
    test_normal_indices = remaining_normal[n_val_normal:]

    # Validation: 정상 15% + 이상 1,000개
    n_val_anomaly = min(1000, len(anomaly_indices))
    val_anomaly_indices = anomaly_indices[:n_val_anomaly]
    val_indices = val_normal_indices + val_anomaly_indices

    # Test: 정상 15% + 이상 1,000개
    n_test_anomaly = min(1000, len(anomaly_indices) - n_val_anomaly)
    test_anomaly_indices = anomaly_indices[n_val_anomaly:n_val_anomaly + n_test_anomaly]
    test_indices = test_normal_indices + test_anomaly_indices

    print(f"  Train (normal only): {len(train_indices)}")
    print(f"  Validation: {len(val_indices)} (normal: {len(val_normal_indices)}, anomaly: {len(val_anomaly_indices)})")
    print(f"  Test: {len(test_indices)} (normal: {len(test_normal_indices)}, anomaly: {len(test_anomaly_indices)})")
    print(f"\n  💡 Sampling applied: Using {len(test_indices)} samples instead of {len(normal_indices[n_train:]) + len(anomaly_indices)}")

    # 3. 데이터셋
    print("\n[3/4] Creating datasets...")

    train_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in train_indices],
        labels=[0] * len(train_indices),
        image_size=config['image_size'],
        augment=False  # PatchCore는 augmentation 불필요
    )

    val_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in val_indices],
        labels=[labels[i] for i in val_indices],
        image_size=config['image_size'],
        augment=False
    )

    test_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in test_indices],
        labels=[labels[i] for i in test_indices],
        image_size=config['image_size'],
        augment=False
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=0,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=0,
        pin_memory=True
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=0,
        pin_memory=True
    )

    # MLflow Run
    with mlflow.start_run(run_name=f"patchcore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # 하이퍼파라미터 로깅
        mlflow.log_params({
            'model': 'PatchCore',
            'backbone': config['backbone'],
            'layers': str(config['layers']),
            'coreset_sampling_ratio': config['coreset_sampling_ratio'],
            'num_neighbors': config['num_neighbors'],
            'image_size': f"{config['image_size'][0]}x{config['image_size'][1]}",
            'batch_size': config['batch_size'],
        })

        # 데이터셋 정보
        mlflow.log_params({
            'total_samples': len(image_paths),
            'normal_samples': n_normal,
            'anomaly_samples': n_anomaly,
            'train_samples': len(train_indices),
            'val_samples': len(val_indices),
            'test_samples': len(test_indices),
        })

        # 4. PatchCore 학습 (Memory Bank 구축)
        print("\n[4/4] Training PatchCore...")
        model = PatchCore(config)
        model.fit(train_loader)

        # 모델 저장
        model_path = config['model_save_dir'] / 'patchcore_model.npz'
        model.save(model_path)

        # Validation 평가 (Threshold 찾기)
        print("\n[5/6] Evaluating on Validation set...")
        val_result = evaluate_patchcore(model, val_loader, config['results_dir'] / 'validation')

        # Test 평가 (최종 성능)
        print("\n[6/6] Evaluating on Test set...")
        test_result = evaluate_patchcore(model, test_loader, config['results_dir'] / 'test')

        # 메트릭 로깅
        mlflow.log_metrics({
            'val_auroc': val_result['auroc'],
            'val_f1_score': val_result['best_f1_score'],
            'val_threshold': val_result['best_threshold'],
            'test_auroc': test_result['auroc'],
            'test_f1_score': test_result['best_f1_score'],
        })

        # 아티팩트 로깅
        mlflow.log_artifact(str(model_path), "models")

        val_results_json = config['results_dir'] / 'validation' / 'evaluation_report.json'
        if val_results_json.exists():
            mlflow.log_artifact(str(val_results_json), "results")

        test_results_json = config['results_dir'] / 'test' / 'evaluation_report.json'
        if test_results_json.exists():
            mlflow.log_artifact(str(test_results_json), "results")

        # Model Registry 등록
        test_auroc = test_result['auroc']
        if test_auroc >= 0.85:
            print(f"\n  🎉 High performance model! (AUROC: {test_auroc:.4f})")

        run_id = mlflow.active_run().info.run_id
        print(f"\n  MLflow Run ID: {run_id}")

    # 최종 결과
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"  Validation AUROC: {val_result['auroc']:.4f}")
    print(f"  Validation F1-Score: {val_result['best_f1_score']:.4f}")
    print(f"  Test AUROC: {test_result['auroc']:.4f}")
    print(f"  Test F1-Score: {test_result['best_f1_score']:.4f}")
    print(f"\n  Model saved: {config['model_save_dir']}")
    print(f"  Results saved: {config['results_dir']}")

if __name__ == '__main__':
    main()
