#!/usr/bin/env python3
"""
PatchCore Lite for Jetson Orin Nano
경량화된 PatchCore - EfficientNet-B0 백본 사용

변경사항:
- Backbone: WideResNet50 → EfficientNet-B0 (1/5 크기)
- Coreset Ratio: 0.1 → 0.01 (메모리 10배 감소)
- Single Layer: layer4만 사용 (feature dimension 감소)

예상 성능:
- 모델 크기: ~50MB (원본 대비 1/10)
- 추론 속도: Jetson Orin Nano에서 10-15 FPS
- AUROC: 원본 대비 -0.02~-0.05 정도 하락 예상

Usage:
    python train_patchcore_lite.py
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
import pandas as pd
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
import mlflow.pyfunc

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

PATCHCORE_LITE_CONFIG = {
    # 이미지 설정
    'image_size': (224, 224),

    # Feature Extraction (경량화)
    'backbone': 'efficientnet_b0',  # WideResNet50 → EfficientNet-B0
    'layers': [4],  # EfficientNet의 마지막 feature layer만 사용

    # Memory Bank (극단 개선 - 정상/이상 명확한 경우)
    'coreset_sampling_ratio': 0.1,  # 0.01 → 0.1 (10배 증가, 더 많은 정상 패턴 저장)
    'num_neighbors': 1,  # 5 → 1 (1-NN, 가장 가까운 것만 - 명확한 구분)

    # Feature Reduction (비활성화 - 정보 손실 최소화)
    'use_feature_reduction': False,  # True → False (320차원 그대로 사용)
    'reduced_feature_dim': 256,  # 사용 안 함

    # 데이터
    'batch_size': 32,
    'normal_category_id': 101,
    'anomaly_category_ids': None,

    # 저장 경로
    'model_save_dir': CONFIG_ROOT / 'models' / 'anomaly_patchcore_lite',
    'results_dir': CONFIG_ROOT / 'results' / 'anomaly_patchcore_lite',
}

# ============================================================================
# PatchCore Lite Model
# ============================================================================

class PatchCoreLite:
    """
    경량화된 PatchCore for Jetson Orin Nano

    경량화 전략:
    1. 작은 백본 사용 (EfficientNet-B0)
    2. Single layer feature 사용
    3. 메모리 뱅크 크기 대폭 감소
    4. Feature dimension reduction
    """

    def __init__(self, config: Dict, device: str = 'cuda'):
        self.config = config
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        # Backbone (EfficientNet-B0)
        print(f"Loading backbone: {config['backbone']}")
        self.backbone = timm.create_model(
            config['backbone'],
            pretrained=True,
            features_only=True,
            out_indices=config['layers']  # [4] - 마지막 layer만
        )
        self.backbone.to(self.device)
        self.backbone.eval()

        # Feature dimension 확인
        with torch.no_grad():
            dummy = torch.zeros(1, 3, *config['image_size']).to(self.device)
            features = self.backbone(dummy)
            self.original_feature_dim = features[0].shape[1]
            self.patch_shape = features[0].shape[2:]

        print(f"Original feature dimension: {self.original_feature_dim}")
        print(f"Patch shape: {self.patch_shape}")

        # Feature Reduction
        self.feature_reducer = None
        if config.get('use_feature_reduction', False):
            self.reduced_dim = config['reduced_feature_dim']
            print(f"Using feature reduction: {self.original_feature_dim} → {self.reduced_dim}")

            # Sparse Random Projection (빠르고 효과적)
            self.feature_reducer = SparseRandomProjection(
                n_components=self.reduced_dim,
                random_state=RANDOM_SEED
            )
            self.feature_dim = self.reduced_dim
        else:
            self.feature_dim = self.original_feature_dim

        # Memory Bank
        self.memory_bank = None

    def extract_features(self, images: torch.Tensor) -> torch.Tensor:
        """이미지에서 feature 추출"""
        with torch.no_grad():
            # Backbone forward (single layer만)
            features = self.backbone(images)[0]  # (B, C, H, W)

            # Reshape to (B, H*W, C)
            B, C, H, W = features.shape
            features = features.permute(0, 2, 3, 1)  # (B, H, W, C)
            features = features.reshape(B, H * W, C)

            return features

    def fit(self, dataloader: DataLoader):
        """정상 데이터로 Memory Bank 구축"""
        print("\n" + "="*60)
        print("Building Lite Memory Bank")
        print("="*60)

        self.backbone.eval()
        all_features = []

        with torch.no_grad():
            for batch in tqdm(dataloader, desc="Extracting features"):
                images = batch['image'].to(self.device)

                # Feature 추출
                features = self.extract_features(images)  # (B, N_patches, C)

                # Flatten
                B, N, C = features.shape
                features = features.reshape(B * N, C)
                all_features.append(features.cpu().numpy())

        # Concatenate
        all_features = np.concatenate(all_features, axis=0)
        print(f"\nTotal features extracted: {all_features.shape[0]}")

        # Feature Reduction
        if self.feature_reducer is not None:
            print(f"\nApplying feature reduction: {all_features.shape[1]} → {self.reduced_dim}")
            all_features = self.feature_reducer.fit_transform(all_features)
            print(f"Reduced features shape: {all_features.shape}")

        # CoreSet Sampling
        print("\nApplying CoreSet Sampling...")
        self.memory_bank = self._coreset_sampling(
            all_features,
            sampling_ratio=self.config['coreset_sampling_ratio']
        )

        print(f"Memory Bank size: {self.memory_bank.shape[0]} (ratio: {self.config['coreset_sampling_ratio']:.1%})")
        print(f"Memory Bank dimension: {self.memory_bank.shape[1]}")

        # 메모리 사용량 추정
        memory_mb = (self.memory_bank.nbytes) / (1024 ** 2)
        print(f"Memory Bank size: {memory_mb:.2f} MB")

        # Torch tensor로 변환
        self.memory_bank = torch.from_numpy(self.memory_bank).float().to(self.device)

        return self

    def _coreset_sampling(self, features: np.ndarray, sampling_ratio: float) -> np.ndarray:
        """CoreSet Sampling"""
        num_samples = int(len(features) * sampling_ratio)

        # Random sampling
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

                # Feature Reduction
                if self.feature_reducer is not None:
                    B, N, C = features.shape
                    features_np = features.cpu().numpy().reshape(B * N, C)
                    features_reduced = self.feature_reducer.transform(features_np)
                    features = torch.from_numpy(features_reduced).float().to(self.device)
                    features = features.reshape(B, N, -1)

                # Anomaly score 계산
                B, N, C = features.shape
                features = features.reshape(B * N, C)

                # K-NN distance
                distances = self._compute_distances(features)

                # Image-level score
                distances = distances.reshape(B, N)
                scores = distances.max(dim=1)[0]

                all_scores.extend(scores.cpu().numpy())
                all_labels.extend(labels)

        return np.array(all_scores), np.array(all_labels)

    def _compute_distances(self, features: torch.Tensor) -> torch.Tensor:
        """Memory Bank와의 K-NN distance 계산"""
        N = features.shape[0]
        K = self.config['num_neighbors']

        # Batch 처리
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

    def save(self, filepath: Path):
        """모델 저장"""
        filepath.parent.mkdir(parents=True, exist_ok=True)

        save_dict = {
            'config': {k: str(v) if isinstance(v, Path) else v
                      for k, v in self.config.items()},
            'memory_bank': self.memory_bank.cpu().numpy(),
            'feature_dim': self.feature_dim,
            'original_feature_dim': self.original_feature_dim,
            'patch_shape': self.patch_shape,
        }

        # Feature reducer 저장
        if self.feature_reducer is not None:
            # Sparse matrix를 dense array로 변환하여 저장
            if hasattr(self.feature_reducer.components_, 'toarray'):
                # Sparse matrix인 경우
                save_dict['feature_reducer_components'] = self.feature_reducer.components_.toarray()
            else:
                # 이미 dense array인 경우
                save_dict['feature_reducer_components'] = self.feature_reducer.components_
            save_dict['reduced_dim'] = self.reduced_dim

        np.savez_compressed(filepath, **save_dict)

        # 파일 크기 확인
        file_size_mb = filepath.stat().st_size / (1024 ** 2)
        print(f"Model saved to {filepath}")
        print(f"File size: {file_size_mb:.2f} MB")

    def load(self, filepath: Path):
        """모델 로드"""
        data = np.load(filepath, allow_pickle=True)

        self.memory_bank = torch.from_numpy(data['memory_bank']).float().to(self.device)
        self.feature_dim = int(data['feature_dim'])
        self.original_feature_dim = int(data['original_feature_dim'])
        self.patch_shape = tuple(data['patch_shape'])

        # Feature reducer 로드
        if 'feature_reducer_components' in data:
            from sklearn.random_projection import SparseRandomProjection
            self.feature_reducer = SparseRandomProjection(
                n_components=int(data['reduced_dim'])
            )
            # Dense array로 저장된 components 로드
            components = data['feature_reducer_components']
            # 2D array인지 확인
            if components.ndim == 2:
                self.feature_reducer.components_ = components
            else:
                raise ValueError(f"Invalid components shape: {components.shape}, expected 2D array")
            self.reduced_dim = int(data['reduced_dim'])
            print(f"  Feature reduction: {self.original_feature_dim} → {self.reduced_dim}")

        print(f"Model loaded from {filepath}")
        print(f"Memory Bank size: {self.memory_bank.shape[0]}")

# ============================================================================
# Evaluation
# ============================================================================

def evaluate_patchcore(
    model: PatchCoreLite,
    test_loader: DataLoader,
    results_dir: Path
) -> Dict:
    """PatchCore 평가"""
    print("\n" + "="*60)
    print("Evaluating PatchCore Lite")
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
        'model': 'PatchCore-Lite',
        'backbone': 'EfficientNet-B0',
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
# MLflow Model Wrapper
# ============================================================================

class PatchCoreLiteMLflowWrapper(mlflow.pyfunc.PythonModel):
    """
    MLflow PyFunc Wrapper for PatchCore Lite

    MLflow Model Registry에 등록하여 버전 관리 및 배포 가능
    """

    def load_context(self, context):
        """MLflow에서 모델 로드 시 호출"""
        import torch
        import timm
        from sklearn.random_projection import SparseRandomProjection

        # Artifacts 경로
        model_path = context.artifacts["model"]

        # Config 로드
        data = np.load(model_path, allow_pickle=True)
        self.config = data['config'].item()

        # Device 설정
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Memory Bank 로드
        self.memory_bank = torch.from_numpy(data['memory_bank']).float().to(self.device)
        self.patch_shape = tuple(data['patch_shape'])
        self.feature_dim = int(data['feature_dim'])
        self.original_feature_dim = int(data['original_feature_dim'])

        # Feature Reducer 로드
        self.feature_reducer = None
        if 'feature_reducer_components' in data:
            self.feature_reducer = SparseRandomProjection(
                n_components=int(data['reduced_dim'])
            )
            # Dense array로 저장된 components 로드
            components = data['feature_reducer_components']
            if components.ndim == 2:
                self.feature_reducer.components_ = components
            else:
                raise ValueError(f"Invalid components shape: {components.shape}, expected 2D array")
            self.reduced_dim = int(data['reduced_dim'])

        # Backbone 로드
        self.backbone = timm.create_model(
            self.config['backbone'],
            pretrained=False,  # 학습된 가중치는 필요 없음 (feature extraction만)
            features_only=True,
            out_indices=[int(x) for x in self.config['layers']]
        )
        self.backbone.to(self.device)
        self.backbone.eval()

        print(f"Model loaded successfully (device: {self.device})")
        print(f"Memory Bank size: {self.memory_bank.shape}")

    def predict(self, context, model_input):
        """
        이미지 경로 또는 numpy array를 받아 이상 점수 반환

        Args:
            model_input: pandas DataFrame with 'image_path' column or numpy array

        Returns:
            numpy array of anomaly scores
        """
        import torch
        from PIL import Image
        import torchvision.transforms as transforms

        # Input 처리
        if isinstance(model_input, pd.DataFrame):
            # DataFrame with image paths
            image_paths = model_input['image_path'].tolist()
            images = []

            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])

            for img_path in image_paths:
                img = Image.open(img_path).convert('RGB')
                img_tensor = transform(img)
                images.append(img_tensor)

            images = torch.stack(images).to(self.device)

        else:
            # Numpy array (B, H, W, C) or (B, C, H, W)
            images = torch.from_numpy(model_input).float().to(self.device)
            if images.dim() == 4 and images.shape[-1] == 3:
                images = images.permute(0, 3, 1, 2)  # (B, H, W, C) -> (B, C, H, W)

        # Feature 추출
        with torch.no_grad():
            features = self.backbone(images)[0]  # (B, C, H, W)

            # Reshape
            B, C, H, W = features.shape
            features = features.permute(0, 2, 3, 1).reshape(B, H * W, C)

            # Feature Reduction
            if self.feature_reducer is not None:
                features_np = features.cpu().numpy().reshape(B * H * W, C)
                features_reduced = self.feature_reducer.transform(features_np)
                features = torch.from_numpy(features_reduced).float().to(self.device)
                features = features.reshape(B, H * W, -1)

            # Anomaly Score
            B, N, C = features.shape
            features = features.reshape(B * N, C)

            # K-NN Distance
            distances = self._compute_distances(features)
            distances = distances.reshape(B, N)
            scores = distances.max(dim=1)[0].cpu().numpy()

        return scores

    def _compute_distances(self, features: torch.Tensor) -> torch.Tensor:
        """Memory Bank와의 K-NN distance"""
        N = features.shape[0]
        K = 5

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

# ============================================================================
# Main
# ============================================================================

def main():
    print("="*60)
    print("Ship Coating Anomaly Detection - PatchCore Lite")
    print("Optimized for Jetson Orin Nano")
    print("="*60)

    # Random seed
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(RANDOM_SEED)

    config = PATCHCORE_LITE_CONFIG.copy()

    # MLflow 설정
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment_name = "ship-coating-anomaly-patchcore-lite"
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

    # Train: 정상만 사용 (70%)
    n_train = int(len(normal_indices) * 0.7)
    train_indices = normal_indices[:n_train]
    remaining_normal = normal_indices[n_train:]

    # Val/Test 분할
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

    # 3. 데이터셋
    print("\n[3/4] Creating datasets...")

    train_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in train_indices],
        labels=[0] * len(train_indices),
        image_size=config['image_size'],
        augment=False
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
    with mlflow.start_run(run_name=f"patchcore_lite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # 하이퍼파라미터 로깅
        mlflow.log_params({
            'model': 'PatchCore-Lite',
            'backbone': config['backbone'],
            'layers': str(config['layers']),
            'coreset_sampling_ratio': config['coreset_sampling_ratio'],
            'num_neighbors': config['num_neighbors'],
            'use_feature_reduction': config.get('use_feature_reduction', False),
            'reduced_feature_dim': config.get('reduced_feature_dim', 'N/A'),
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

        # 4. PatchCore Lite 학습
        print("\n[4/4] Training PatchCore Lite...")
        model = PatchCoreLite(config)
        model.fit(train_loader)

        # 모델 저장
        model_path = config['model_save_dir'] / 'patchcore_lite_model.npz'
        model.save(model_path)

        # Validation 평가
        print("\n[5/6] Evaluating on Validation set...")
        val_result = evaluate_patchcore(model, val_loader, config['results_dir'] / 'validation')

        # Test 평가
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

        # MLflow Model Registry에 모델 등록
        print("\n[Bonus] Registering model to MLflow Model Registry...")

        # Conda environment (dependencies)
        conda_env = {
            'channels': ['defaults', 'conda-forge'],
            'dependencies': [
                f'python={sys.version_info.major}.{sys.version_info.minor}',
                'pip',
                {
                    'pip': [
                        f'torch=={torch.__version__}',
                        'timm>=0.9.0',
                        'scikit-learn>=1.0.0',
                        'numpy>=1.21.0',
                        'pillow>=8.0.0',
                    ]
                }
            ],
            'name': 'patchcore_lite_env'
        }

        # Signature (input/output schema)
        from mlflow.models.signature import infer_signature
        import pandas as pd

        # Example input
        example_input = pd.DataFrame({
            'image_path': [str(image_paths[0])]
        })

        # 모델 등록
        artifacts = {
            "model": str(model_path)
        }

        mlflow.pyfunc.log_model(
            artifact_path="patchcore_lite_model",
            python_model=PatchCoreLiteMLflowWrapper(),
            artifacts=artifacts,
            conda_env=conda_env,
            code_paths=[str(PROJECT_ROOT / 'src')],  # code_path → code_paths (복수형)
            registered_model_name="PatchCore-Lite-ShipCoating",
            signature=infer_signature(example_input, np.array([0.5]))
        )

        print("  ✓ Model registered to MLflow Model Registry!")
        print("  Model name: PatchCore-Lite-ShipCoating")

        run_id = mlflow.active_run().info.run_id
        print(f"\n  MLflow Run ID: {run_id}")
        print(f"  View in MLflow UI: {MLFLOW_TRACKING_URI}")
        print(f"  Model Registry: {MLFLOW_TRACKING_URI}/#/models/PatchCore-Lite-ShipCoating")

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

    print("\n" + "="*60)
    print("Next Steps - TensorRT Optimization:")
    print("="*60)
    print("  1. Run: python export_to_onnx.py")
    print("  2. Run: python convert_to_tensorrt.py")
    print("  3. Deploy to Jetson Orin Nano")
    print("="*60)

if __name__ == '__main__':
    main()
