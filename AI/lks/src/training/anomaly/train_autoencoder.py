#!/usr/bin/env python3
"""
Convolutional AutoEncoder for Ship Coating Anomaly Detection
정상 데이터로 학습하여 결함(이상) 탐지

Usage:
    python train_autoencoder.py
"""

import os
import sys

# OpenMP 충돌 해결 (conda 환경에서 numpy/pytorch 충돌 방지)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict, Optional

import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score, f1_score, precision_recall_curve
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')  # GUI 없이 저장 가능하도록
import matplotlib.pyplot as plt

# MLflow
import mlflow
import mlflow.pytorch

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import (
    IMAGE_DIR, LABEL_DIR, PROJECT_ROOT as CONFIG_ROOT,
    NORMALIZE_MEAN, NORMALIZE_STD, RANDOM_SEED,
    MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME,
    BATCH_SIZE, LEARNING_RATE, PATIENCE
)

# ============================================================================
# Configuration
# ============================================================================

# 이상탐지 전용 설정
ANOMALY_CONFIG = {
    # 이미지 크기 (정사각형, letterbox resize 사용)
    'image_size': (640, 640),  # (width, height)

    # 학습 설정
    'epochs': 100,
    'batch_size': 16,  # 640x640 이미지로 인해 메모리 사용량 증가
    'learning_rate': 1e-3,
    'weight_decay': 1e-5,

    # Early stopping (AUROC 기준)
    'patience': 20,

    # 데이터 분할
    'train_ratio': 0.8,
    'val_ratio': 0.2,

    # 정상 카테고리 ID
    'normal_category_id': 101,

    # 이상 카테고리 ID (이 클래스만 anomaly로 처리, 나머지는 제외)
    'anomaly_category_ids': [201, 203, 204, 207],  # water_spotting, coating_separation, pinhole, foreign_material

    # 모델 저장 경로
    'model_save_dir': CONFIG_ROOT / 'models' / 'anomaly',

    # 결과 저장 경로
    'results_dir': CONFIG_ROOT / 'results' / 'anomaly',
}

# ============================================================================
# Dataset
# ============================================================================

class AnomalyDataset(Dataset):
    """이상탐지용 데이터셋"""

    def __init__(self,
                 image_paths: List[Path],
                 labels: List[int],  # 0: normal, 1: anomaly
                 image_size: Tuple[int, int] = (256, 256),
                 augment: bool = False):
        self.image_paths = image_paths
        self.labels = labels
        self.image_size = image_size
        self.augment = augment
        self.mean = np.array(NORMALIZE_MEAN, dtype=np.float32)
        self.std = np.array(NORMALIZE_STD, dtype=np.float32)

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        # 이미지 로드
        img_path = self.image_paths[idx]
        image = cv2.imread(str(img_path))
        if image is None:
            raise ValueError(f"Failed to load image: {img_path}")

        # BGR -> RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize
        image = cv2.resize(image, self.image_size)

        # 간단한 augmentation (학습 시에만)
        if self.augment:
            if random.random() > 0.5:
                image = cv2.flip(image, 1)  # 수평 뒤집기
            if random.random() > 0.5:
                image = cv2.flip(image, 0)  # 수직 뒤집기

        # Normalize
        image = image.astype(np.float32) / 255.0
        image = (image - self.mean) / self.std

        # HWC -> CHW
        image = np.transpose(image, (2, 0, 1))

        return {
            'image': torch.from_numpy(image),
            'label': torch.tensor(self.labels[idx], dtype=torch.float32),
            'path': str(img_path)
        }


def collect_data(image_dir: Path, label_dir: Path,
                 normal_category_id: int = 101,
                 anomaly_category_ids: List[int] = None) -> Tuple[List[Path], List[int]]:
    """
    데이터 수집: 정상/결함 분류

    Args:
        image_dir: 이미지 디렉토리
        label_dir: 라벨 디렉토리
        normal_category_id: 정상 카테고리 ID
        anomaly_category_ids: 이상으로 처리할 카테고리 ID 리스트 (None이면 정상 외 모두 이상)

    Returns:
        image_paths: 이미지 경로 리스트
        labels: 라벨 리스트 (0: normal, 1: anomaly)
    """
    image_paths = []
    labels = []
    skipped_categories = set()

    # 라벨 파일 순회 (하위 디렉토리 포함)
    for label_path in label_dir.glob('**/*.json'):
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 이미지 경로 찾기 (라벨과 동일한 하위 디렉토리 구조 유지)
            rel_path = label_path.relative_to(label_dir)
            img_name = rel_path.with_suffix('.jpg')
            img_path = image_dir / img_name

            if not img_path.exists():
                # 다른 확장자 시도
                for ext in ['.png', '.jpeg', '.JPG', '.PNG']:
                    alt_path = image_dir / rel_path.with_suffix(ext)
                    if alt_path.exists():
                        img_path = alt_path
                        break

            if not img_path.exists():
                continue

            # 카테고리 확인
            annotations = data.get('annotations', [])
            if not annotations:
                continue

            # 첫 번째 annotation의 category_id로 판단
            category_id = annotations[0].get('category_id', 0)

            # 라벨링 로직
            if category_id == normal_category_id:
                # 정상
                image_paths.append(img_path)
                labels.append(0)
            elif anomaly_category_ids is None:
                # anomaly_category_ids가 None이면 정상 외 모두 이상
                image_paths.append(img_path)
                labels.append(1)
            elif category_id in anomaly_category_ids:
                # 지정된 이상 카테고리만 포함
                image_paths.append(img_path)
                labels.append(1)
            else:
                # 나머지는 제외
                skipped_categories.add(category_id)
                continue

        except Exception as e:
            print(f"Error processing {label_path}: {e}")
            continue

    if skipped_categories:
        print(f"  Skipped categories: {sorted(skipped_categories)}")

    return image_paths, labels


# ============================================================================
# Model: Convolutional AutoEncoder
# ============================================================================

class ConvAutoEncoder(nn.Module):
    """Convolutional AutoEncoder for Anomaly Detection (640x640 input)"""

    def __init__(self, in_channels: int = 3, latent_dim: int = 256):
        super().__init__()

        # Encoder: 640 -> 320 -> 160 -> 80 -> 40 -> 20 -> 10
        self.encoder = nn.Sequential(
            # 640x640 -> 320x320
            nn.Conv2d(in_channels, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(0.2, inplace=True),

            # 320x320 -> 160x160
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2, inplace=True),

            # 160x160 -> 80x80
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),

            # 80x80 -> 40x40
            nn.Conv2d(128, 256, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),

            # 40x40 -> 20x20
            nn.Conv2d(256, 512, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),

            # 20x20 -> 10x10
            nn.Conv2d(512, 512, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),
        )

        # Bottleneck: 512 * 10 * 10 = 51200
        self.fc_encode = nn.Linear(512 * 10 * 10, latent_dim)
        self.fc_decode = nn.Linear(latent_dim, 512 * 10 * 10)

        # Decoder: 10 -> 20 -> 40 -> 80 -> 160 -> 320 -> 640
        self.decoder = nn.Sequential(
            # 10x10 -> 20x20
            nn.ConvTranspose2d(512, 512, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),

            # 20x20 -> 40x40
            nn.ConvTranspose2d(512, 256, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),

            # 40x40 -> 80x80
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),

            # 80x80 -> 160x160
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),

            # 160x160 -> 320x320
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),

            # 320x320 -> 640x640
            nn.ConvTranspose2d(32, in_channels, kernel_size=4, stride=2, padding=1),
            nn.Tanh(),  # 출력 범위: [-1, 1]
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        x = self.encoder(x)
        x = x.view(x.size(0), -1)
        x = self.fc_encode(x)
        return x

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        x = self.fc_decode(z)
        x = x.view(x.size(0), 512, 10, 10)
        x = self.decoder(x)
        return x

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        z = self.encode(x)
        reconstructed = self.decode(z)
        return reconstructed, z


# ============================================================================
# Training
# ============================================================================

class AnomalyTrainer:
    """AutoEncoder 학습 및 검증"""

    def __init__(self, config: Dict, device: str = 'cuda'):
        self.config = config
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        # 모델
        self.model = ConvAutoEncoder(in_channels=3, latent_dim=128).to(self.device)

        # Loss
        self.criterion = nn.MSELoss(reduction='none')

        # Optimizer
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=config['learning_rate'],
            weight_decay=config['weight_decay']
        )

        # Scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=10
        )

        # 결과 저장
        self.train_losses = []
        self.val_losses = []
        self.best_loss = float('inf')
        self.best_auroc = 0.0  # AUROC 기반 early stopping
        self.patience_counter = 0

    def compute_reconstruction_error(self, original: torch.Tensor, reconstructed: torch.Tensor) -> torch.Tensor:
        """픽셀별 재구성 오류 계산 후 이미지당 평균"""
        # (B, C, H, W) -> (B,)
        error = self.criterion(reconstructed, original)
        error = error.mean(dim=[1, 2, 3])
        return error

    def train_epoch(self, dataloader: DataLoader, epoch: int, total_epochs: int) -> float:
        """한 epoch 학습"""
        self.model.train()
        total_loss = 0.0

        pbar = tqdm(dataloader, desc=f"Epoch [{epoch}/{total_epochs}] Train", leave=False)
        for batch in pbar:
            images = batch['image'].to(self.device)

            # Forward
            reconstructed, _ = self.model(images)

            # Loss (정상 데이터만 학습하므로 모든 샘플 사용)
            loss = self.compute_reconstruction_error(images, reconstructed).mean()

            # Backward
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})

        return total_loss / len(dataloader)

    @torch.no_grad()
    def validate(self, dataloader: DataLoader, desc: str = "Validate") -> Tuple[float, np.ndarray, np.ndarray]:
        """검증 및 이상점수 계산"""
        self.model.eval()
        total_loss = 0.0
        all_scores = []
        all_labels = []

        pbar = tqdm(dataloader, desc=desc, leave=False)
        for batch in pbar:
            images = batch['image'].to(self.device)
            labels = batch['label'].numpy()

            # Forward
            reconstructed, _ = self.model(images)

            # 재구성 오류 (이상 점수)
            scores = self.compute_reconstruction_error(images, reconstructed)

            total_loss += scores.mean().item()
            all_scores.extend(scores.cpu().numpy())
            all_labels.extend(labels)

        return total_loss / len(dataloader), np.array(all_scores), np.array(all_labels)

    def train(self, train_loader: DataLoader, val_loader: DataLoader) -> Dict:
        """전체 학습 루프 (MLflow 추적 포함)"""
        print("\n" + "="*60)
        print("Starting Training")
        print("="*60)

        epochs = self.config['epochs']
        patience = self.config['patience']
        final_epoch = epochs

        epoch_pbar = tqdm(range(1, epochs + 1), desc="Training", unit="epoch")
        for epoch in epoch_pbar:
            # Train
            train_loss = self.train_epoch(train_loader, epoch, epochs)
            self.train_losses.append(train_loss)

            # Validate
            val_loss, val_scores, val_labels = self.validate(val_loader, desc=f"Epoch [{epoch}/{epochs}] Val")
            self.val_losses.append(val_loss)

            # Scheduler step
            self.scheduler.step(val_loss)

            # AUROC 계산 (결함 샘플이 있을 때만)
            auroc = 0.0
            if len(np.unique(val_labels)) > 1:
                auroc = roc_auc_score(val_labels, val_scores)

            # MLflow 메트릭 로깅
            mlflow.log_metrics({
                'train_loss': train_loss,
                'val_loss': val_loss,
                'auroc': auroc,
                'learning_rate': self.optimizer.param_groups[0]['lr']
            }, step=epoch)

            # 진행 상황 업데이트
            epoch_pbar.set_postfix({
                'train_loss': f'{train_loss:.4f}',
                'val_loss': f'{val_loss:.4f}',
                'auroc': f'{auroc:.4f}',
                'best': f'{self.best_auroc:.4f}'
            })

            # Best model 저장 (AUROC 기준)
            if auroc > self.best_auroc:
                self.best_auroc = auroc
                self.best_loss = val_loss  # 참고용으로 저장
                self.patience_counter = 0
                self.save_model('best_model.pt')
                tqdm.write(f"  -> New best model saved! (AUROC: {auroc:.4f})")
            else:
                self.patience_counter += 1

            # Early stopping (AUROC 기준)
            if self.patience_counter >= patience:
                tqdm.write(f"\nEarly stopping at epoch {epoch} (Best AUROC: {self.best_auroc:.4f})")
                final_epoch = epoch
                break

        # 최종 모델 저장
        self.save_model('final_model.pt')

        return {
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_loss,
            'best_auroc': self.best_auroc,
            'epochs_trained': final_epoch
        }

    def save_model(self, filename: str):
        """모델 저장"""
        save_dir = self.config['model_save_dir']
        save_dir.mkdir(parents=True, exist_ok=True)

        save_path = save_dir / filename

        # config의 Path 객체를 str로 변환 (PyTorch 2.6+ 호환성)
        config_serializable = self.config.copy()
        for key, value in config_serializable.items():
            if isinstance(value, Path):
                config_serializable[key] = str(value)

        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': config_serializable,
            'best_loss': self.best_loss,
            'best_auroc': self.best_auroc,
        }, save_path)

    def load_model(self, filepath: Path):
        """모델 로드"""
        checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.best_loss = checkpoint.get('best_loss', float('inf'))
        print(f"Model loaded from {filepath}")


# ============================================================================
# Evaluation
# ============================================================================

def evaluate_model(trainer: AnomalyTrainer,
                   test_loader: DataLoader,
                   results_dir: Path) -> Dict:
    """모델 평가 및 시각화"""

    print("\n" + "="*60)
    print("Evaluating Model")
    print("="*60)

    # 테스트 데이터로 점수 계산
    _, scores, labels = trainer.validate(test_loader, desc="Evaluating")

    # 결과 저장 디렉토리
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. AUROC
    auroc = roc_auc_score(labels, scores) if len(np.unique(labels)) > 1 else 0.0
    print(f"\nAUROC: {auroc:.4f}")

    # 2. 최적 임계값 찾기 (F1-score 최대화)
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
    best_idx = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]
    best_f1 = f1_scores[best_idx]

    print(f"Best Threshold: {best_threshold:.6f}")
    print(f"Best F1-Score: {best_f1:.4f}")

    # 3. 정상/결함 점수 분포
    normal_scores = scores[labels == 0]
    anomaly_scores = scores[labels == 1]

    print(f"\nNormal scores - Mean: {normal_scores.mean():.6f}, Std: {normal_scores.std():.6f}")
    if len(anomaly_scores) > 0:
        print(f"Anomaly scores - Mean: {anomaly_scores.mean():.6f}, Std: {anomaly_scores.std():.6f}")

    # 4. 시각화
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # 4-1. 점수 분포 히스토그램
    ax = axes[0, 0]
    ax.hist(normal_scores, bins=50, alpha=0.7, label='Normal', color='blue')
    if len(anomaly_scores) > 0:
        ax.hist(anomaly_scores, bins=50, alpha=0.7, label='Anomaly', color='red')
    ax.axvline(best_threshold, color='green', linestyle='--', label=f'Threshold={best_threshold:.4f}')
    ax.set_xlabel('Reconstruction Error')
    ax.set_ylabel('Count')
    ax.set_title('Score Distribution')
    ax.legend()

    # 4-2. Precision-Recall Curve
    ax = axes[0, 1]
    ax.plot(recall, precision, 'b-', label=f'AUROC={auroc:.4f}')
    ax.scatter(recall[best_idx], precision[best_idx], color='red', s=100,
               label=f'Best F1={best_f1:.4f}', zorder=5)
    ax.set_xlabel('Recall')
    ax.set_ylabel('Precision')
    ax.set_title('Precision-Recall Curve')
    ax.legend()
    ax.grid(True)

    # 4-3. 학습 곡선
    ax = axes[1, 0]
    ax.plot(trainer.train_losses, label='Train Loss')
    ax.plot(trainer.val_losses, label='Val Loss')
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Loss')
    ax.set_title('Training Curve')
    ax.legend()
    ax.grid(True)

    # 4-4. Box plot
    ax = axes[1, 1]
    data_to_plot = [normal_scores]
    labels_plot = ['Normal']
    if len(anomaly_scores) > 0:
        data_to_plot.append(anomaly_scores)
        labels_plot.append('Anomaly')
    ax.boxplot(data_to_plot, labels=labels_plot)
    ax.set_ylabel('Reconstruction Error')
    ax.set_title('Score Box Plot')

    plt.tight_layout()
    plt.savefig(results_dir / 'evaluation_results.png', dpi=150)
    plt.close()

    print(f"\nResults saved to {results_dir}")

    # 결과 리포트 저장
    report = {
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
    """메인 실행 함수"""

    print("="*60)
    print("Ship Coating Anomaly Detection - AutoEncoder Training")
    print("="*60)

    # 랜덤 시드 설정
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(RANDOM_SEED)

    config = ANOMALY_CONFIG.copy()

    # MLflow 설정
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment_name = "ship-coating-anomaly-detection"
    mlflow.set_experiment(experiment_name)
    print(f"\nMLflow Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"MLflow Experiment: {experiment_name}")

    # 1. 데이터 수집
    print("\n[1/5] Collecting data...")
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

    if len(image_paths) == 0:
        print("Error: No data found!")
        return

    # 2. 데이터 분할
    print("\n[2/5] Splitting data...")

    # 정상 데이터만 분리
    normal_indices = [i for i, l in enumerate(labels) if l == 0]
    anomaly_indices = [i for i, l in enumerate(labels) if l == 1]

    random.shuffle(normal_indices)

    # 정상 데이터: train/val 분할 (학습은 정상만)
    n_train = int(len(normal_indices) * config['train_ratio'])
    train_indices = normal_indices[:n_train]
    val_normal_indices = normal_indices[n_train:]

    # 검증 데이터: 정상 + 결함 일부
    n_val_anomaly = min(len(anomaly_indices), len(val_normal_indices))
    random.shuffle(anomaly_indices)
    val_anomaly_indices = anomaly_indices[:n_val_anomaly]

    val_indices = val_normal_indices + val_anomaly_indices
    test_indices = anomaly_indices[n_val_anomaly:]  # 남은 결함은 테스트용

    print(f"  Train (normal only): {len(train_indices)}")
    print(f"  Val (normal): {len(val_normal_indices)}, Val (anomaly): {len(val_anomaly_indices)}")
    print(f"  Test (anomaly): {len(test_indices)}")

    # 3. 데이터셋 생성
    print("\n[3/5] Creating datasets...")

    train_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in train_indices],
        labels=[0] * len(train_indices),  # 모두 정상
        image_size=config['image_size'],
        augment=True
    )

    val_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in val_indices],
        labels=[labels[i] for i in val_indices],
        image_size=config['image_size'],
        augment=False
    )

    # 테스트: 남은 결함 + 일부 정상
    test_normal_indices = random.sample(normal_indices, min(100, len(normal_indices) // 5))
    test_all_indices = test_normal_indices + test_indices

    test_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in test_all_indices],
        labels=[labels[i] for i in test_all_indices],
        image_size=config['image_size'],
        augment=False
    )

    # DataLoader
    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'],
                              shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=config['batch_size'],
                            shuffle=False, num_workers=0, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=config['batch_size'],
                             shuffle=False, num_workers=0, pin_memory=True)

    # MLflow Run 시작
    with mlflow.start_run(run_name=f"autoencoder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # 하이퍼파라미터 로깅
        mlflow.log_params({
            'model': 'ConvAutoEncoder',
            'image_size': f"{config['image_size'][0]}x{config['image_size'][1]}",
            'latent_dim': 256,
            'epochs': config['epochs'],
            'batch_size': config['batch_size'],
            'learning_rate': config['learning_rate'],
            'weight_decay': config['weight_decay'],
            'patience': config['patience'],
            'optimizer': 'Adam',
            'loss': 'MSE',
        })

        # 데이터셋 정보 로깅
        mlflow.log_params({
            'total_samples': len(image_paths),
            'normal_samples': n_normal,
            'anomaly_samples': n_anomaly,
            'train_samples': len(train_indices),
            'val_samples': len(val_indices),
            'test_samples': len(test_all_indices),
        })

        # 4. 학습
        print("\n[4/5] Training model...")
        trainer = AnomalyTrainer(config)
        training_result = trainer.train(train_loader, val_loader)

        # 5. 평가
        print("\n[5/5] Evaluating model...")

        # Best 모델 로드
        best_model_path = config['model_save_dir'] / 'best_model.pt'
        if best_model_path.exists():
            trainer.load_model(best_model_path)

        eval_result = evaluate_model(trainer, test_loader, config['results_dir'])

        # 최종 메트릭 로깅
        mlflow.log_metrics({
            'best_val_loss': training_result['best_val_loss'],
            'best_val_auroc': training_result['best_auroc'],
            'epochs_trained': training_result['epochs_trained'],
            'test_auroc': eval_result['auroc'],
            'test_f1_score': eval_result['best_f1_score'],
            'best_threshold': eval_result['best_threshold'],
        })

        # 아티팩트 로깅 (모델, 결과 이미지)
        if best_model_path.exists():
            mlflow.log_artifact(str(best_model_path), "models")

        results_img = config['results_dir'] / 'evaluation_results.png'
        if results_img.exists():
            mlflow.log_artifact(str(results_img), "results")

        results_json = config['results_dir'] / 'evaluation_report.json'
        if results_json.exists():
            mlflow.log_artifact(str(results_json), "results")

        # PyTorch 모델 로깅
        mlflow.pytorch.log_model(trainer.model, "autoencoder_model")

        print(f"\n  MLflow Run ID: {mlflow.active_run().info.run_id}")

    # 최종 결과 출력
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"  Best Val AUROC: {training_result['best_auroc']:.4f}")
    print(f"  Best Val Loss: {training_result['best_val_loss']:.6f}")
    print(f"  Epochs Trained: {training_result['epochs_trained']}")
    print(f"  Test AUROC: {eval_result['auroc']:.4f}")
    print(f"  Test F1-Score: {eval_result['best_f1_score']:.4f}")
    print(f"\n  Model saved: {config['model_save_dir']}")
    print(f"  Results saved: {config['results_dir']}")
    print(f"\n  MLflow UI: mlflow ui --backend-store-uri {MLFLOW_TRACKING_URI}")


if __name__ == '__main__':
    main()
