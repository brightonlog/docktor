"""
Anomaly Detection 학습 스크립트 (TensorBoard 시각화 포함)

실시간으로 학습 상황을 모니터링할 수 있습니다.

Usage:
    # 학습 실행
    python src/anomaly_detection/train_with_tensorboard.py \
        --data-dir data/processed/train/images/normal \
        --epochs 100

    # 다른 터미널에서 TensorBoard 실행
    tensorboard --logdir=runs/anomaly_detection
"""

import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from PIL import Image
import numpy as np

# TensorBoard
try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False
    print("[Warning] TensorBoard not installed. Run: pip install tensorboard")

# sklearn for AUROC
try:
    from sklearn.metrics import roc_auc_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.anomaly_detection.models.autoencoder import (
    SSIMAnomalyAutoencoder,
    LightweightAutoencoder,
    CombinedLoss,
    count_parameters
)


class NormalImageDataset(Dataset):
    """정상 이미지 데이터셋"""

    def __init__(self, root_dir: str, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.image_paths = []

        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
            self.image_paths.extend(self.root_dir.rglob(f"*{ext}"))

        self.image_paths = sorted(set(self.image_paths))
        print(f"[Dataset] Found {len(self.image_paths)} images")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        try:
            image = Image.open(self.image_paths[idx]).convert('RGB')
        except:
            image = Image.new('RGB', (256, 256), (128, 128, 128))

        if self.transform:
            image = self.transform(image)
        return image


class AnomalyImageDataset(Dataset):
    """비정상 이미지 데이터셋 (검증용)"""

    def __init__(self, root_dir: str, transform=None, max_samples: int = 200):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.image_paths = []

        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
            self.image_paths.extend(self.root_dir.rglob(f"*{ext}"))

        self.image_paths = sorted(set(self.image_paths))

        # 샘플링
        if len(self.image_paths) > max_samples:
            indices = np.linspace(0, len(self.image_paths)-1, max_samples, dtype=int)
            self.image_paths = [self.image_paths[i] for i in indices]

        print(f"[Anomaly Dataset] Found {len(self.image_paths)} images")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        try:
            image = Image.open(self.image_paths[idx]).convert('RGB')
        except:
            image = Image.new('RGB', (256, 256), (128, 128, 128))

        if self.transform:
            image = self.transform(image)
        return image


def get_transforms(input_size: int = 256, augment: bool = True):
    if augment:
        train_transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.3),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
        ])
    else:
        train_transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
        ])

    val_transform = transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
    ])

    return train_transform, val_transform


@torch.no_grad()
def compute_auroc(
    model: nn.Module,
    normal_loader: DataLoader,
    anomaly_loader: DataLoader,
    device: torch.device,
    max_batches: int = 10
) -> float:
    """AUROC 계산 (빠른 버전)"""
    if not SKLEARN_AVAILABLE:
        return 0.0

    model.eval()
    normal_scores = []
    anomaly_scores = []

    # Normal scores
    for i, images in enumerate(normal_loader):
        if i >= max_batches:
            break
        images = images.to(device)
        recon = model(images)
        scores = ((images - recon) ** 2).mean(dim=[1, 2, 3])
        normal_scores.extend(scores.cpu().numpy())

    # Anomaly scores
    for i, images in enumerate(anomaly_loader):
        if i >= max_batches:
            break
        images = images.to(device)
        recon = model(images)
        scores = ((images - recon) ** 2).mean(dim=[1, 2, 3])
        anomaly_scores.extend(scores.cpu().numpy())

    if len(normal_scores) == 0 or len(anomaly_scores) == 0:
        return 0.0

    all_scores = np.array(normal_scores + anomaly_scores)
    labels = np.array([0] * len(normal_scores) + [1] * len(anomaly_scores))

    try:
        auroc = roc_auc_score(labels, all_scores)
    except:
        auroc = 0.0

    return auroc


def train_one_epoch(model, dataloader, criterion, optimizer, device, epoch, writer=None):
    model.train()
    total_loss, total_mse, total_ssim = 0.0, 0.0, 0.0
    num_batches = len(dataloader)

    for batch_idx, images in enumerate(dataloader):
        images = images.to(device)

        reconstructed = model(images)
        loss, loss_dict = criterion(reconstructed, images)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss_dict['total']
        total_mse += loss_dict['mse']
        total_ssim += loss_dict['ssim']

        # TensorBoard: 배치별 로깅
        if writer and batch_idx % 20 == 0:
            global_step = epoch * num_batches + batch_idx
            writer.add_scalar('Batch/Loss', loss_dict['total'], global_step)

        if (batch_idx + 1) % 50 == 0:
            print(f"  [{batch_idx+1}/{num_batches}] Loss: {loss_dict['total']:.4f}")

    return {
        'loss': total_loss / num_batches,
        'mse': total_mse / num_batches,
        'ssim': total_ssim / num_batches
    }


@torch.no_grad()
def validate(model, dataloader, criterion, device):
    model.eval()
    total_loss, total_mse, total_ssim = 0.0, 0.0, 0.0

    for images in dataloader:
        images = images.to(device)
        reconstructed = model(images)
        loss, loss_dict = criterion(reconstructed, images)

        total_loss += loss_dict['total']
        total_mse += loss_dict['mse']
        total_ssim += loss_dict['ssim']

    num_batches = len(dataloader)
    return {
        'loss': total_loss / num_batches,
        'mse': total_mse / num_batches,
        'ssim': total_ssim / num_batches
    }


def log_images_to_tensorboard(writer, model, images, epoch, tag="Reconstruction"):
    """복원 이미지를 TensorBoard에 로깅"""
    model.eval()
    with torch.no_grad():
        recon = model(images[:4])

    # 원본 vs 복원 비교
    comparison = torch.cat([images[:4], recon], dim=0)
    writer.add_images(f'{tag}/Original_vs_Reconstructed', comparison, epoch, dataformats='NCHW')

    # 차이 맵
    diff = torch.abs(images[:4] - recon).mean(dim=1, keepdim=True)
    diff = diff / diff.max()  # 정규화
    writer.add_images(f'{tag}/Difference_Map', diff, epoch, dataformats='NCHW')


def train(config: dict):
    print("=" * 60)
    print("Anomaly Detection Training (with TensorBoard)")
    print("=" * 60)

    # 설정
    data_dir = Path(config['data_dir'])
    anomaly_dir = config.get('anomaly_dir', None)
    output_dir = Path(config.get('output_dir', 'models/anomaly_detection'))
    epochs = config.get('epochs', 100)
    batch_size = config.get('batch_size', 32)
    learning_rate = config.get('learning_rate', 1e-3)
    input_size = config.get('input_size', 256)
    latent_dim = config.get('latent_dim', 256)
    model_type = config.get('model_type', 'standard')
    auroc_interval = config.get('auroc_interval', 5)  # 몇 에폭마다 AUROC 계산

    output_dir.mkdir(parents=True, exist_ok=True)

    # 디바이스
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n[Config]")
    print(f"  Device: {device}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")

    # TensorBoard 설정
    writer = None
    if TENSORBOARD_AVAILABLE:
        log_dir = f"runs/anomaly_detection/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        writer = SummaryWriter(log_dir)
        print(f"\n[TensorBoard] Logging to: {log_dir}")
        print(f"  Run: tensorboard --logdir=runs/anomaly_detection")

    # 데이터셋
    train_transform, val_transform = get_transforms(input_size, augment=True)

    full_dataset = NormalImageDataset(data_dir, transform=train_transform)
    val_size = int(len(full_dataset) * 0.1)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    # Windows에서는 num_workers=0 사용 (멀티프로세싱 이슈)
    num_workers = 0 if os.name == 'nt' else 4
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)

    # 비정상 데이터셋 (AUROC 계산용)
    anomaly_loader = None
    if anomaly_dir and Path(anomaly_dir).exists():
        anomaly_dataset = AnomalyImageDataset(anomaly_dir, transform=val_transform, max_samples=200)
        anomaly_loader = DataLoader(anomaly_dataset, batch_size=batch_size, shuffle=False, num_workers=2)
        print(f"[AUROC] Will compute every {auroc_interval} epochs")

    print(f"\n[Dataset] Train: {train_size}, Val: {val_size}")

    # 모델
    if model_type == 'lightweight':
        model = LightweightAutoencoder(latent_dim=latent_dim, input_size=input_size)
    else:
        model = SSIMAnomalyAutoencoder(latent_dim=latent_dim, input_size=input_size)

    model = model.to(device)
    print(f"[Model] Parameters: {count_parameters(model):,}")

    # Loss & Optimizer
    criterion = CombinedLoss(alpha=0.5)
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    # Resume from checkpoint
    start_epoch = 1
    best_loss = float('inf')
    best_auroc = 0.0
    resume_path = config.get('resume', None)

    if resume_path and Path(resume_path).exists():
        print(f"\n[Resume] Loading checkpoint: {resume_path}")
        checkpoint = torch.load(resume_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_loss = checkpoint.get('loss', float('inf'))
        print(f"  Resuming from epoch {start_epoch}")
        print(f"  Previous best loss: {best_loss:.4f}")

        # Scheduler를 해당 에폭까지 진행
        for _ in range(checkpoint['epoch']):
            scheduler.step()

    # TensorBoard: 모델 구조
    if writer:
        dummy = torch.randn(1, 3, input_size, input_size).to(device)
        writer.add_graph(model, dummy)

    print(f"\n{'='*60}")
    print("Starting Training...")
    print(f"{'='*60}\n")

    for epoch in range(start_epoch, epochs + 1):
        print(f"Epoch [{epoch}/{epochs}]")

        # 학습
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch, writer)

        # 검증
        val_metrics = validate(model, val_loader, criterion, device)

        # 학습률
        current_lr = scheduler.get_last_lr()[0]
        scheduler.step()

        # 출력
        print(f"  Train Loss: {train_metrics['loss']:.4f} | Val Loss: {val_metrics['loss']:.4f} | LR: {current_lr:.6f}")

        # TensorBoard 로깅
        if writer:
            writer.add_scalars('Loss', {
                'train': train_metrics['loss'],
                'val': val_metrics['loss']
            }, epoch)

            writer.add_scalars('MSE', {
                'train': train_metrics['mse'],
                'val': val_metrics['mse']
            }, epoch)

            writer.add_scalars('SSIM_Loss', {
                'train': train_metrics['ssim'],
                'val': val_metrics['ssim']
            }, epoch)

            writer.add_scalar('Learning_Rate', current_lr, epoch)

            # 이미지 로깅 (매 10 에폭)
            if epoch % 10 == 0:
                sample_images = next(iter(val_loader))[:4].to(device)
                log_images_to_tensorboard(writer, model, sample_images, epoch, "Validation")

        # AUROC 계산 (주기적)
        if anomaly_loader and epoch % auroc_interval == 0:
            auroc = compute_auroc(model, val_loader, anomaly_loader, device)
            print(f"  AUROC: {auroc:.4f}")

            if writer:
                writer.add_scalar('AUROC', auroc, epoch)

            if auroc > best_auroc:
                best_auroc = auroc

        # Best 모델 저장
        if val_metrics['loss'] < best_loss:
            best_loss = val_metrics['loss']
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': val_metrics['loss'],
                'model_config': {
                    'latent_dim': latent_dim,
                    'input_size': input_size
                }
            }, output_dir / "best_model.pt")
            print(f"  [Saved] Best model (loss: {best_loss:.4f})")

        print()

    # 학습 완료
    print("=" * 60)
    print("Training Complete!")
    print(f"  Best Val Loss: {best_loss:.4f}")
    if best_auroc > 0:
        print(f"  Best AUROC: {best_auroc:.4f}")
    print(f"  Model: {output_dir / 'best_model.pt'}")
    print("=" * 60)

    if writer:
        writer.close()

    return model


def main():
    parser = argparse.ArgumentParser(description='Train Anomaly Detection with TensorBoard')
    parser.add_argument('--data-dir', type=str, default='data/processed/train/images/normal')
    parser.add_argument('--anomaly-dir', type=str, default='data/processed/val/images/coating_damage',
                        help='Anomaly images for AUROC calculation during training')
    parser.add_argument('--output-dir', type=str, default='models/anomaly_detection')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--input-size', type=int, default=256)
    parser.add_argument('--model-type', choices=['standard', 'lightweight'], default='standard')
    parser.add_argument('--auroc-interval', type=int, default=5, help='Compute AUROC every N epochs')
    parser.add_argument('--resume', type=str, default=None,
                        help='Path to checkpoint to resume from (e.g., models/anomaly_detection/checkpoint_epoch_5.pt)')

    args = parser.parse_args()

    config = {
        'data_dir': args.data_dir,
        'anomaly_dir': args.anomaly_dir,
        'output_dir': args.output_dir,
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.lr,
        'input_size': args.input_size,
        'model_type': args.model_type,
        'auroc_interval': args.auroc_interval,
        'resume': args.resume,
    }

    train(config)


if __name__ == "__main__":
    main()
