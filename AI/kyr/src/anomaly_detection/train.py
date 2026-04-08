"""
Anomaly Detection 학습 스크립트

정상(Normal) 이미지만으로 Autoencoder를 학습합니다.
학습된 모델은 정상 이미지를 잘 복원하고, 비정상 이미지는 복원을 못합니다.

Usage:
    python src/anomaly_detection/train.py --config src/anomaly_detection/config.yaml
    python src/anomaly_detection/train.py --epochs 100 --batch-size 32
"""

import os
import sys
import argparse
import yaml
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from PIL import Image
import numpy as np

# MLflow 통합
try:
    import mlflow
    import mlflow.pytorch
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    print("[Warning] MLflow not installed. Experiment tracking disabled.")

# 모델 임포트
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.anomaly_detection.models.autoencoder import (
    SSIMAnomalyAutoencoder,
    LightweightAutoencoder,
    CombinedLoss,
    count_parameters
)


class NormalImageDataset(Dataset):
    """
    정상 이미지 데이터셋

    정상 이미지만 로드하여 Autoencoder 학습에 사용
    """

    def __init__(
        self,
        root_dir: str,
        transform: Optional[transforms.Compose] = None,
        extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp')
    ):
        """
        Args:
            root_dir: 정상 이미지가 있는 디렉토리
            transform: 이미지 변환
            extensions: 지원하는 이미지 확장자
        """
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.extensions = extensions

        # 이미지 파일 목록 생성
        self.image_paths = []
        for ext in extensions:
            self.image_paths.extend(self.root_dir.rglob(f"*{ext}"))
            self.image_paths.extend(self.root_dir.rglob(f"*{ext.upper()}"))

        self.image_paths = sorted(set(self.image_paths))

        if len(self.image_paths) == 0:
            raise ValueError(f"No images found in {root_dir}")

        print(f"[Dataset] Found {len(self.image_paths)} normal images")

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> torch.Tensor:
        img_path = self.image_paths[idx]

        try:
            image = Image.open(img_path).convert('RGB')
        except Exception as e:
            print(f"[Warning] Failed to load {img_path}: {e}")
            # 대체 이미지 반환
            image = Image.new('RGB', (256, 256), (128, 128, 128))

        if self.transform:
            image = self.transform(image)

        return image


def get_transforms(input_size: int = 256, augment: bool = True) -> Tuple[transforms.Compose, transforms.Compose]:
    """
    학습/검증용 이미지 변환 생성

    Args:
        input_size: 입력 이미지 크기
        augment: 데이터 증강 적용 여부

    Returns:
        train_transform, val_transform
    """
    # 공통 변환
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )

    # 학습용 변환 (증강 포함)
    if augment:
        train_transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.3),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
            transforms.ToTensor(),
            # Autoencoder는 정규화 없이 0-1 범위 사용
        ])
    else:
        train_transform = transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
        ])

    # 검증용 변환 (증강 없음)
    val_transform = transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
    ])

    return train_transform, val_transform


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    epoch: int
) -> dict:
    """
    한 에폭 학습

    Returns:
        metrics: {'loss': float, 'mse': float, 'ssim': float}
    """
    model.train()

    total_loss = 0.0
    total_mse = 0.0
    total_ssim = 0.0
    num_batches = len(dataloader)

    for batch_idx, images in enumerate(dataloader):
        images = images.to(device)

        # Forward
        reconstructed = model(images)
        loss, loss_dict = criterion(reconstructed, images)

        # Backward
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss_dict['total']
        total_mse += loss_dict['mse']
        total_ssim += loss_dict['ssim']

        # 진행 상황 출력
        if (batch_idx + 1) % 10 == 0 or batch_idx == 0:
            print(f"  Batch [{batch_idx+1}/{num_batches}] "
                  f"Loss: {loss_dict['total']:.4f} "
                  f"(MSE: {loss_dict['mse']:.4f}, SSIM: {loss_dict['ssim']:.4f})")

    return {
        'loss': total_loss / num_batches,
        'mse': total_mse / num_batches,
        'ssim': total_ssim / num_batches
    }


@torch.no_grad()
def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> dict:
    """
    검증

    Returns:
        metrics: {'loss': float, 'mse': float, 'ssim': float}
    """
    model.eval()

    total_loss = 0.0
    total_mse = 0.0
    total_ssim = 0.0
    num_batches = len(dataloader)

    for images in dataloader:
        images = images.to(device)
        reconstructed = model(images)
        loss, loss_dict = criterion(reconstructed, images)

        total_loss += loss_dict['total']
        total_mse += loss_dict['mse']
        total_ssim += loss_dict['ssim']

    return {
        'loss': total_loss / num_batches,
        'mse': total_mse / num_batches,
        'ssim': total_ssim / num_batches
    }


def save_checkpoint(
    model: nn.Module,
    optimizer: optim.Optimizer,
    epoch: int,
    loss: float,
    save_path: Path,
    is_best: bool = False
):
    """체크포인트 저장"""
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
        'model_config': {
            'in_channels': model.in_channels,
            'latent_dim': model.latent_dim,
            'input_size': model.input_size
        }
    }

    torch.save(checkpoint, save_path / f"checkpoint_epoch_{epoch}.pt")

    if is_best:
        torch.save(checkpoint, save_path / "best_model.pt")
        print(f"  [Saved] Best model (loss: {loss:.4f})")


def train(config: dict):
    """
    메인 학습 함수

    Args:
        config: 학습 설정 딕셔너리
    """
    print("=" * 60)
    print("Anomaly Detection Autoencoder 학습")
    print("=" * 60)

    # 설정 추출
    data_dir = Path(config.get('data_dir', 'data/processed/train/images/normal'))
    output_dir = Path(config.get('output_dir', 'models/anomaly_detection'))
    epochs = config.get('epochs', 100)
    batch_size = config.get('batch_size', 32)
    learning_rate = config.get('learning_rate', 1e-3)
    input_size = config.get('input_size', 256)
    latent_dim = config.get('latent_dim', 256)
    loss_alpha = config.get('loss_alpha', 0.5)  # MSE vs SSIM 비율
    model_type = config.get('model_type', 'standard')  # 'standard' or 'lightweight'
    val_split = config.get('val_split', 0.1)
    patience = config.get('patience', 20)  # Early stopping
    augment = config.get('augment', True)

    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 디바이스 설정
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n[Config]")
    print(f"  Device: {device}")
    print(f"  Data: {data_dir}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Learning rate: {learning_rate}")
    print(f"  Input size: {input_size}x{input_size}")
    print(f"  Latent dim: {latent_dim}")
    print(f"  Loss alpha (MSE weight): {loss_alpha}")
    print(f"  Model type: {model_type}")

    # 데이터셋 생성
    train_transform, val_transform = get_transforms(input_size, augment)
    full_dataset = NormalImageDataset(data_dir, transform=train_transform)

    # Train/Val 분할
    val_size = int(len(full_dataset) * val_split)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    # Val 데이터셋의 transform 변경 (증강 없음)
    val_dataset.dataset = NormalImageDataset(data_dir, transform=val_transform)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=4, pin_memory=True
    )

    print(f"\n[Dataset]")
    print(f"  Train: {len(train_dataset)} images")
    print(f"  Val: {len(val_dataset)} images")

    # 모델 생성
    if model_type == 'lightweight':
        model = LightweightAutoencoder(latent_dim=latent_dim, input_size=input_size)
    else:
        model = SSIMAnomalyAutoencoder(latent_dim=latent_dim, input_size=input_size)

    model = model.to(device)

    print(f"\n[Model]")
    print(f"  Parameters: {count_parameters(model):,}")

    # Loss & Optimizer
    criterion = CombinedLoss(alpha=loss_alpha)
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    # MLflow 설정
    if MLFLOW_AVAILABLE and config.get('use_mlflow', True):
        mlflow.set_tracking_uri(config.get('mlflow_uri', 'file:./experiments/mlruns'))
        mlflow.set_experiment(config.get('experiment_name', 'anomaly-detection'))

        mlflow.start_run(run_name=f"ae_{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        mlflow.log_params({
            'model_type': model_type,
            'epochs': epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate,
            'input_size': input_size,
            'latent_dim': latent_dim,
            'loss_alpha': loss_alpha,
            'parameters': count_parameters(model)
        })

    # 학습 루프
    best_loss = float('inf')
    patience_counter = 0

    print(f"\n{'='*60}")
    print("학습 시작")
    print(f"{'='*60}\n")

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        print(f"Epoch [{epoch}/{epochs}]")

        # 학습
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, device, epoch
        )

        # 검증
        val_metrics = validate(model, val_loader, criterion, device)

        # 스케줄러 업데이트
        scheduler.step()

        # 결과 출력
        print(f"  Train Loss: {train_metrics['loss']:.4f} "
              f"(MSE: {train_metrics['mse']:.4f}, SSIM: {train_metrics['ssim']:.4f})")
        print(f"  Val Loss: {val_metrics['loss']:.4f} "
              f"(MSE: {val_metrics['mse']:.4f}, SSIM: {val_metrics['ssim']:.4f})")
        print(f"  LR: {scheduler.get_last_lr()[0]:.6f}")

        # MLflow 로깅
        if MLFLOW_AVAILABLE and config.get('use_mlflow', True):
            mlflow.log_metrics({
                'train_loss': train_metrics['loss'],
                'train_mse': train_metrics['mse'],
                'train_ssim': train_metrics['ssim'],
                'val_loss': val_metrics['loss'],
                'val_mse': val_metrics['mse'],
                'val_ssim': val_metrics['ssim'],
                'learning_rate': scheduler.get_last_lr()[0]
            }, step=epoch)

        # Best 모델 저장
        is_best = val_metrics['loss'] < best_loss
        if is_best:
            best_loss = val_metrics['loss']
            patience_counter = 0
        else:
            patience_counter += 1

        # 체크포인트 저장 (매 10 에폭 또는 best)
        if epoch % 10 == 0 or is_best:
            save_checkpoint(model, optimizer, epoch, val_metrics['loss'], output_dir, is_best)

        # Early stopping
        if patience_counter >= patience:
            print(f"\n[Early Stopping] {patience} epochs without improvement")
            break

        print()

    # 학습 완료
    total_time = time.time() - start_time
    print(f"{'='*60}")
    print(f"학습 완료!")
    print(f"  Total time: {total_time/60:.1f} minutes")
    print(f"  Best val loss: {best_loss:.4f}")
    print(f"  Model saved: {output_dir / 'best_model.pt'}")
    print(f"{'='*60}")

    # MLflow 종료
    if MLFLOW_AVAILABLE and config.get('use_mlflow', True):
        mlflow.log_artifact(str(output_dir / "best_model.pt"))
        mlflow.end_run()

    return model, best_loss


def load_config(config_path: str) -> dict:
    """YAML 설정 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Anomaly Detection Autoencoder Training')
    parser.add_argument('--config', type=str, default=None, help='Config file path')
    parser.add_argument('--data-dir', type=str, default=None, help='Normal images directory')
    parser.add_argument('--output-dir', type=str, default='models/anomaly_detection')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--input-size', type=int, default=256)
    parser.add_argument('--latent-dim', type=int, default=256)
    parser.add_argument('--model-type', choices=['standard', 'lightweight'], default='standard')
    parser.add_argument('--no-mlflow', action='store_true', help='Disable MLflow tracking')

    args = parser.parse_args()

    # 설정 로드
    if args.config:
        config = load_config(args.config)
    else:
        config = {}

    # CLI 인자로 설정 오버라이드
    if args.data_dir:
        config['data_dir'] = args.data_dir
    if 'data_dir' not in config:
        config['data_dir'] = 'data/processed/train/images/normal'

    config['output_dir'] = args.output_dir
    config['epochs'] = args.epochs
    config['batch_size'] = args.batch_size
    config['learning_rate'] = args.lr
    config['input_size'] = args.input_size
    config['latent_dim'] = args.latent_dim
    config['model_type'] = args.model_type
    config['use_mlflow'] = not args.no_mlflow

    # 학습 실행
    train(config)


if __name__ == "__main__":
    main()
