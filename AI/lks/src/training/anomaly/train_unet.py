#!/usr/bin/env python3
"""
Lightweight U-Net AutoEncoder for Ship Coating Anomaly Detection
MobileNet 기반 경량화 버전 - Jetson Orin Nano 최적화

Usage:
    python train_unet.py
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
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score, precision_recall_curve
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')
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
    MLFLOW_TRACKING_URI
)

# 기존 데이터 수집 함수 import
from training.anomaly.train_autoencoder import collect_data, AnomalyDataset

# ============================================================================
# Configuration
# ============================================================================

UNET_CONFIG = {
    # 이미지 크기 (메모리 효율 + 성능 균형)
    'image_size': (256, 256),  # 640x640 → 256x256로 축소

    # 모델 구조
    'base_channels': 64,  # [중요] 32 → 64 (복원 능력 향상)

    # 학습 설정
    'epochs': 150,  # 100 → 150 (충분한 학습)
    'batch_size': 8,   # 16 → 8 (더 큰 모델 사용으로 메모리 고려)
    'learning_rate': 2e-4,  # 5e-4 → 2e-4 (안정적인 학습)
    'weight_decay': 5e-5,   # 1e-4 → 5e-5 (복원 능력 향상)

    # Early stopping
    'patience': 15,  # 10 → 15 (충분한 학습 시간)

    # 데이터 분할
    'train_ratio': 0.8,
    'val_ratio': 0.2,

    # 정상 카테고리 ID
    'normal_category_id': 101,

    # 이상 카테고리 ID (None = 모든 비정상 카테고리 포함)
    'anomaly_category_ids': None,  # 모든 결함 타입 사용

    # 모델 저장 경로
    'model_save_dir': CONFIG_ROOT / 'models' / 'anomaly_unet',

    # 결과 저장 경로
    'results_dir': CONFIG_ROOT / 'results' / 'anomaly_unet',

    # Loss weights - MSE + SSIM Combined Loss
    'use_mse_only': False,  # Combined Loss 사용
    'mse_weight': 0.6,      # MSE 비중 (픽셀 단위 오류)
    'ssim_weight': 0.4,     # SSIM 비중 (구조적 유사성)
}

# ============================================================================
# Lightweight U-Net Model
# ============================================================================

class DepthwiseSeparableConv(nn.Module):
    """Depthwise Separable Convolution (MobileNet 스타일)"""
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super().__init__()
        self.depthwise = nn.Conv2d(
            in_channels, in_channels,
            kernel_size=kernel_size, stride=stride, padding=padding,
            groups=in_channels, bias=False
        )
        self.pointwise = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.depthwise(x)
        x = self.pointwise(x)
        x = self.bn(x)
        x = self.relu(x)
        return x


class DownBlock(nn.Module):
    """U-Net Encoder Block with Depthwise Separable Conv"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv1 = DepthwiseSeparableConv(in_channels, out_channels)
        self.conv2 = DepthwiseSeparableConv(out_channels, out_channels)
        self.pool = nn.MaxPool2d(2, 2)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        skip = x
        x = self.pool(x)
        return x, skip


class UpBlock(nn.Module):
    """U-Net Decoder Block with Skip Connections"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=2, stride=2)
        self.conv1 = DepthwiseSeparableConv(out_channels * 2, out_channels)
        self.conv2 = DepthwiseSeparableConv(out_channels, out_channels)

    def forward(self, x, skip):
        x = self.up(x)

        # Skip connection과 크기 맞추기
        if x.shape != skip.shape:
            x = F.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=False)

        x = torch.cat([x, skip], dim=1)
        x = self.conv1(x)
        x = self.conv2(x)
        return x


class LightweightUNet(nn.Module):
    """
    Lightweight U-Net for Anomaly Detection
    Jetson Orin Nano 최적화 버전

    특징:
    - Depthwise Separable Convolutions 사용
    - Skip Connections로 디테일 보존
    - 경량화 설계 (~80MB)
    """

    def __init__(self, in_channels=3, base_channels=32):
        super().__init__()

        # Encoder (Downsampling)
        self.enc1 = DownBlock(in_channels, base_channels)        # 256 -> 128
        self.enc2 = DownBlock(base_channels, base_channels * 2)  # 128 -> 64
        self.enc3 = DownBlock(base_channels * 2, base_channels * 4)  # 64 -> 32
        self.enc4 = DownBlock(base_channels * 4, base_channels * 8)  # 32 -> 16

        # Bottleneck
        self.bottleneck = nn.Sequential(
            DepthwiseSeparableConv(base_channels * 8, base_channels * 16),
            DepthwiseSeparableConv(base_channels * 16, base_channels * 16),
        )

        # Decoder (Upsampling)
        self.dec4 = UpBlock(base_channels * 16, base_channels * 8)  # 16 -> 32
        self.dec3 = UpBlock(base_channels * 8, base_channels * 4)   # 32 -> 64
        self.dec2 = UpBlock(base_channels * 4, base_channels * 2)   # 64 -> 128
        self.dec1 = UpBlock(base_channels * 2, base_channels)       # 128 -> 256

        # Final output layer
        self.final = nn.Conv2d(base_channels, in_channels, kernel_size=1)
        self.activation = nn.Tanh()  # normalized 범위 [-1, 1]에 맞춤

    def forward(self, x):
        # Encoder
        x1, skip1 = self.enc1(x)
        x2, skip2 = self.enc2(x1)
        x3, skip3 = self.enc3(x2)
        x4, skip4 = self.enc4(x3)

        # Bottleneck
        x = self.bottleneck(x4)

        # Decoder with skip connections
        x = self.dec4(x, skip4)
        x = self.dec3(x, skip3)
        x = self.dec2(x, skip2)
        x = self.dec1(x, skip1)

        # Final output
        x = self.final(x)
        x = self.activation(x)

        return x


# ============================================================================
# SSIM Loss
# ============================================================================

class SSIMLoss(nn.Module):
    """Structural Similarity Index Loss"""

    def __init__(self, window_size=11, reduction='mean'):
        super().__init__()
        self.window_size = window_size
        self.reduction = reduction

    def forward(self, img1, img2):
        """
        Args:
            img1, img2: (B, C, H, W) tensors in range [0, 1]
        """
        C1 = 0.01 ** 2
        C2 = 0.03 ** 2

        # Mean
        mu1 = F.avg_pool2d(img1, self.window_size, stride=1, padding=self.window_size // 2)
        mu2 = F.avg_pool2d(img2, self.window_size, stride=1, padding=self.window_size // 2)

        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2

        # Variance
        sigma1_sq = F.avg_pool2d(img1 ** 2, self.window_size, stride=1, padding=self.window_size // 2) - mu1_sq
        sigma2_sq = F.avg_pool2d(img2 ** 2, self.window_size, stride=1, padding=self.window_size // 2) - mu2_sq
        sigma12 = F.avg_pool2d(img1 * img2, self.window_size, stride=1, padding=self.window_size // 2) - mu1_mu2

        # SSIM
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

        # Loss (1 - SSIM)
        loss = 1 - ssim_map

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'none':
            return loss.mean(dim=[1, 2, 3])
        else:
            return loss


class CombinedLoss(nn.Module):
    """MSE + SSIM Combined Loss"""

    def __init__(self, mse_weight=0.5, ssim_weight=0.5):
        super().__init__()
        self.mse_weight = mse_weight
        self.ssim_weight = ssim_weight
        self.mse = nn.MSELoss(reduction='none')
        self.ssim = SSIMLoss(reduction='none')

    def forward(self, pred, target):
        """
        Args:
            pred, target: (B, C, H, W) normalized images
        Returns:
            loss per sample: (B,)
        """
        # Denormalize to [0, 1] for SSIM
        mean = torch.tensor(NORMALIZE_MEAN, device=pred.device).view(1, 3, 1, 1)
        std = torch.tensor(NORMALIZE_STD, device=pred.device).view(1, 3, 1, 1)

        pred_denorm = pred * std + mean
        target_denorm = target * std + mean

        pred_denorm = torch.clamp(pred_denorm, 0, 1)
        target_denorm = torch.clamp(target_denorm, 0, 1)

        # MSE Loss
        mse_loss = self.mse(pred, target).mean(dim=[1, 2, 3])

        # SSIM Loss
        ssim_loss = self.ssim(pred_denorm, target_denorm)

        # Combined
        loss = self.mse_weight * mse_loss + self.ssim_weight * ssim_loss

        return loss


# ============================================================================
# Training
# ============================================================================

class UNetTrainer:
    """Lightweight U-Net 학습 및 검증"""

    def __init__(self, config: Dict, device: str = 'cuda'):
        self.config = config
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        # 모델 (config에서 base_channels 읽기)
        base_channels = config.get('base_channels', 32)
        self.model = LightweightUNet(in_channels=3, base_channels=base_channels).to(self.device)

        # Loss (config에 따라 MSE 또는 Combined Loss)
        if config.get('use_mse_only', True):
            self.criterion = nn.MSELoss(reduction='none')
            print("Loss: MSE only")
        else:
            mse_weight = config.get('mse_weight', 0.5)
            ssim_weight = config.get('ssim_weight', 0.5)
            self.criterion = CombinedLoss(mse_weight=mse_weight, ssim_weight=ssim_weight)
            print(f"Loss: Combined (MSE={mse_weight}, SSIM={ssim_weight})")

        # Optimizer
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=config['learning_rate'],
            weight_decay=config['weight_decay']
        )

        # Scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )

        # 결과 저장
        self.train_losses = []
        self.val_losses = []
        self.best_loss = float('inf')
        self.best_auroc = 0.0
        self.patience_counter = 0

        # 모델 크기 출력
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"Total parameters: {total_params:,} (~{total_params * 4 / 1024 / 1024:.1f} MB)")
        print(f"Base channels: {base_channels}")

    def compute_reconstruction_error(self, original: torch.Tensor, reconstructed: torch.Tensor) -> torch.Tensor:
        """재구성 오류 계산"""
        error = self.criterion(reconstructed, original)

        # MSE의 경우: (B, C, H, W) → (B,)
        # Combined Loss의 경우: 이미 (B,) shape
        if error.dim() > 1:
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
            reconstructed = self.model(images)

            # Loss
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
            reconstructed = self.model(images)

            # 재구성 오류 (이상 점수)
            scores = self.compute_reconstruction_error(images, reconstructed)

            total_loss += scores.mean().item()
            all_scores.extend(scores.cpu().numpy())
            all_labels.extend(labels)

        return total_loss / len(dataloader), np.array(all_scores), np.array(all_labels)

    def train(self, train_loader: DataLoader, val_loader: DataLoader) -> Dict:
        """전체 학습 루프"""
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
            val_loss, val_scores, val_labels = self.validate(
                val_loader, desc=f"Epoch [{epoch}/{epochs}] Val"
            )
            self.val_losses.append(val_loss)

            # Scheduler step
            self.scheduler.step(val_loss)

            # AUROC 계산
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
                self.best_loss = val_loss
                self.patience_counter = 0
                self.save_model('best_model.pt')
                tqdm.write(f"  -> New best model saved! (AUROC: {auroc:.4f})")
            else:
                self.patience_counter += 1

            # Early stopping
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

        # config의 Path 객체를 str로 변환
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
        self.best_auroc = checkpoint.get('best_auroc', 0.0)
        print(f"Model loaded from {filepath}")


# ============================================================================
# Evaluation (기존 코드 재사용)
# ============================================================================

def evaluate_model(trainer: UNetTrainer,
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

    # 2. 최적 임계값 찾기
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

    # 4-1. 점수 분포
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
    print("Ship Coating Anomaly Detection - Lightweight U-Net")
    print("="*60)

    # 랜덤 시드 설정
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(RANDOM_SEED)

    config = UNET_CONFIG.copy()

    # MLflow 설정
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment_name = "ship-coating-anomaly-unet"
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

    normal_indices = [i for i, l in enumerate(labels) if l == 0]
    anomaly_indices = [i for i, l in enumerate(labels) if l == 1]

    random.shuffle(normal_indices)

    # 정상 데이터: train/val 분할
    n_train = int(len(normal_indices) * config['train_ratio'])
    train_indices = normal_indices[:n_train]
    val_normal_indices = normal_indices[n_train:]

    # 검증 데이터: 정상 + 결함 일부 (정상:이상 = 4:1 비율 유지)
    random.shuffle(anomaly_indices)
    n_val_anomaly = min(len(anomaly_indices), len(val_normal_indices) // 4)  # 정상의 25%만
    val_anomaly_indices = anomaly_indices[:n_val_anomaly]

    val_indices = val_normal_indices + val_anomaly_indices
    test_indices = anomaly_indices[n_val_anomaly:]

    print(f"  Train (normal only): {len(train_indices)}")
    print(f"  Val (normal): {len(val_normal_indices)}, Val (anomaly): {len(val_anomaly_indices)}")
    print(f"  Test (anomaly): {len(test_indices)}")

    # 3. 데이터셋 생성
    print("\n[3/5] Creating datasets...")

    train_dataset = AnomalyDataset(
        image_paths=[image_paths[i] for i in train_indices],
        labels=[0] * len(train_indices),
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
    with mlflow.start_run(run_name=f"unet_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # 하이퍼파라미터 로깅
        loss_name = 'MSE' if config.get('use_mse_only', True) else f"Combined(MSE={config.get('mse_weight')},SSIM={config.get('ssim_weight')})"
        mlflow.log_params({
            'model': 'LightweightUNet',
            'image_size': f"{config['image_size'][0]}x{config['image_size'][1]}",
            'base_channels': config.get('base_channels', 32),
            'epochs': config['epochs'],
            'batch_size': config['batch_size'],
            'learning_rate': config['learning_rate'],
            'weight_decay': config['weight_decay'],
            'patience': config['patience'],
            'optimizer': 'AdamW',
            'loss': loss_name,
            'activation': 'Tanh',
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
        trainer = UNetTrainer(config)
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

        # 아티팩트 로깅
        if best_model_path.exists():
            mlflow.log_artifact(str(best_model_path), "models")

        results_img = config['results_dir'] / 'evaluation_results.png'
        if results_img.exists():
            mlflow.log_artifact(str(results_img), "results")

        results_json = config['results_dir'] / 'evaluation_report.json'
        if results_json.exists():
            mlflow.log_artifact(str(results_json), "results")

        # PyTorch 모델 로깅 및 Model Registry 등록
        model_name = "ship-coating-anomaly-unet"
        mlflow.pytorch.log_model(
            trainer.model,
            "unet_model",
            registered_model_name=model_name  # Model Registry에 자동 등록
        )

        run_id = mlflow.active_run().info.run_id
        print(f"\n  MLflow Run ID: {run_id}")
        print(f"  Model registered: {model_name}")

        # 성능이 좋으면 자동으로 Production Stage로 승격
        test_auroc = eval_result['auroc']
        if test_auroc >= 0.85:  # AUROC 0.85 이상이면 Production
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()

                # 최신 버전 찾기
                latest_versions = client.get_latest_versions(model_name, stages=["None"])
                if latest_versions:
                    version = latest_versions[0].version

                    # Production으로 승격
                    client.transition_model_version_stage(
                        name=model_name,
                        version=version,
                        stage="Production",
                        archive_existing_versions=True  # 기존 Production은 Archived로
                    )
                    print(f"  🎉 Model v{version} promoted to Production! (AUROC: {test_auroc:.4f})")
            except Exception as e:
                print(f"  Warning: Could not promote model to Production: {e}")
        else:
            print(f"  Model registered as Staging (AUROC: {test_auroc:.4f} < 0.85)")

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
    print(f"\n  MLflow UI: python -m mlflow ui --backend-store-uri {MLFLOW_TRACKING_URI}")


if __name__ == '__main__':
    main()
