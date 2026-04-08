#!/usr/bin/env python3
"""
AutoEncoder 검증 스크립트
학습된 모델을 테스트 데이터셋으로 검증하고 결과를 시각화/저장

Usage:
    python validate_autoencoder.py --model path/to/best_model.pt
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict

import numpy as np
import cv2
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import (
    roc_auc_score, roc_curve, confusion_matrix,
    classification_report, f1_score, precision_score, recall_score
)
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import (
    IMAGE_DIR, LABEL_DIR, PROJECT_ROOT as CONFIG_ROOT,
    NORMALIZE_MEAN, NORMALIZE_STD, RANDOM_SEED
)

# train_autoencoder에서 클래스 import
from training.anomaly.train_autoencoder import (
    ConvAutoEncoder, AnomalyDataset, collect_data, ANOMALY_CONFIG
)

# ============================================================================
# Configuration
# ============================================================================

VALIDATION_CONFIG = {
    'num_samples': 100,  # 검증 샘플 수 (정상/이상 각 50개)
    'normal_per_anomaly': 1,  # 정상:이상 비율
    'image_size': (640, 640),
    'batch_size': 16,
    'results_dir': CONFIG_ROOT / 'validation_results' / 'anomaly',
}

# ============================================================================
# Validation Functions
# ============================================================================

def load_model(model_path: Path, device: str = 'cuda') -> ConvAutoEncoder:
    """학습된 모델 로드"""
    device = torch.device(device if torch.cuda.is_available() else 'cpu')

    # 모델 생성
    model = ConvAutoEncoder(in_channels=3, latent_dim=128).to(device)

    # 체크포인트 로드 (PyTorch 2.6+ 호환성)
    # Path 객체가 포함된 checkpoint를 로드하기 위해 weights_only=False 사용
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    print(f"Model loaded from {model_path}")
    print(f"Best AUROC: {checkpoint.get('best_auroc', 'N/A'):.4f}")

    return model, device


def prepare_validation_dataset(
    image_dir: Path,
    label_dir: Path,
    num_samples: int = 100,
    normal_category_id: int = 101,
    anomaly_category_ids: List[int] = None
) -> Tuple[List[Path], List[int]]:
    """검증용 데이터셋 준비 (정상/이상 균등하게)"""

    # 전체 데이터 수집
    all_image_paths, all_labels = collect_data(
        image_dir, label_dir,
        normal_category_id=normal_category_id,
        anomaly_category_ids=anomaly_category_ids
    )

    # 정상/이상 분리
    normal_indices = [i for i, l in enumerate(all_labels) if l == 0]
    anomaly_indices = [i for i, l in enumerate(all_labels) if l == 1]

    # 샘플링
    samples_per_class = num_samples // 2

    random.shuffle(normal_indices)
    random.shuffle(anomaly_indices)

    selected_normal = normal_indices[:min(samples_per_class, len(normal_indices))]
    selected_anomaly = anomaly_indices[:min(samples_per_class, len(anomaly_indices))]

    # 결합
    selected_indices = selected_normal + selected_anomaly
    random.shuffle(selected_indices)

    val_image_paths = [all_image_paths[i] for i in selected_indices]
    val_labels = [all_labels[i] for i in selected_indices]

    print(f"\nValidation Dataset:")
    print(f"  Normal samples: {len(selected_normal)}")
    print(f"  Anomaly samples: {len(selected_anomaly)}")
    print(f"  Total: {len(val_image_paths)}")

    return val_image_paths, val_labels


@torch.no_grad()
def validate_model(
    model: ConvAutoEncoder,
    dataloader: DataLoader,
    device: torch.device,
    criterion: nn.Module
) -> Tuple[List[Dict], np.ndarray, np.ndarray]:
    """모델 검증 및 상세 결과 수집"""

    model.eval()
    results = []
    all_scores = []
    all_labels = []

    print("\nRunning validation...")
    for batch in tqdm(dataloader, desc="Validating"):
        images = batch['image'].to(device)
        labels = batch['label'].numpy()
        paths = batch['path']

        # Forward
        reconstructed, _ = model(images)

        # 재구성 오류 계산
        errors = criterion(reconstructed, images)
        errors = errors.mean(dim=[1, 2, 3]).cpu().numpy()

        # 결과 저장
        for i in range(len(images)):
            results.append({
                'image_path': paths[i],
                'true_label': int(labels[i]),
                'reconstruction_error': float(errors[i]),
                'original_image': images[i].cpu().numpy(),
                'reconstructed_image': reconstructed[i].cpu().numpy(),
            })

        all_scores.extend(errors)
        all_labels.extend(labels)

    return results, np.array(all_scores), np.array(all_labels)


def find_optimal_threshold(labels: np.ndarray, scores: np.ndarray) -> Tuple[float, float]:
    """F1-score 최대화 임계값 찾기"""
    from sklearn.metrics import precision_recall_curve

    precision, recall, thresholds = precision_recall_curve(labels, scores)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
    best_idx = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]
    best_f1 = f1_scores[best_idx]

    return best_threshold, best_f1


def save_results_to_csv(results: List[Dict], threshold: float, save_path: Path):
    """결과를 CSV 파일로 저장"""

    df_data = []
    for r in results:
        df_data.append({
            'image_path': r['image_path'],
            'true_label': 'anomaly' if r['true_label'] == 1 else 'normal',
            'reconstruction_error': r['reconstruction_error'],
            'predicted_label': 'anomaly' if r['reconstruction_error'] > threshold else 'normal',
            'is_correct': (r['reconstruction_error'] > threshold) == (r['true_label'] == 1)
        })

    df = pd.DataFrame(df_data)
    df = df.sort_values('reconstruction_error', ascending=False)

    df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\nResults saved to: {save_path}")

    return df


def visualize_results(
    results: List[Dict],
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    save_dir: Path
):
    """검증 결과 시각화"""

    save_dir.mkdir(parents=True, exist_ok=True)

    # 1. 원본 vs 재구성 이미지 (오류가 큰 상위 10개)
    print("\nGenerating reconstruction comparison...")
    sorted_indices = np.argsort(scores)[::-1][:10]  # Top 10 highest errors

    fig, axes = plt.subplots(2, 10, figsize=(20, 4))
    for idx, i in enumerate(sorted_indices):
        result = results[i]

        # 원본 이미지 (denormalize)
        orig = result['original_image'].transpose(1, 2, 0)
        orig = orig * np.array(NORMALIZE_STD) + np.array(NORMALIZE_MEAN)
        orig = np.clip(orig, 0, 1)

        # 재구성 이미지 (denormalize)
        recon = result['reconstructed_image'].transpose(1, 2, 0)
        recon = recon * np.array(NORMALIZE_STD) + np.array(NORMALIZE_MEAN)
        recon = np.clip(recon, 0, 1)

        # 시각화
        axes[0, idx].imshow(orig)
        axes[0, idx].axis('off')
        axes[0, idx].set_title(f"{'Anom' if result['true_label']==1 else 'Norm'}", fontsize=8)

        axes[1, idx].imshow(recon)
        axes[1, idx].axis('off')
        axes[1, idx].set_title(f"Err:{result['reconstruction_error']:.3f}", fontsize=8)

    axes[0, 0].set_ylabel('Original', fontsize=10)
    axes[1, 0].set_ylabel('Reconstructed', fontsize=10)

    plt.tight_layout()
    plt.savefig(save_dir / 'reconstruction_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 2. 전체 결과 시각화 (점수 분포, ROC, 혼동행렬)
    print("Generating evaluation plots...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 2-1. 점수 분포
    ax = axes[0, 0]
    normal_scores = scores[labels == 0]
    anomaly_scores = scores[labels == 1]

    ax.hist(normal_scores, bins=30, alpha=0.7, label='Normal', color='blue')
    ax.hist(anomaly_scores, bins=30, alpha=0.7, label='Anomaly', color='red')
    ax.axvline(threshold, color='green', linestyle='--', linewidth=2,
               label=f'Threshold={threshold:.4f}')
    ax.set_xlabel('Reconstruction Error', fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('Score Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2-2. ROC Curve
    ax = axes[0, 1]
    fpr, tpr, _ = roc_curve(labels, scores)
    auroc = roc_auc_score(labels, scores)

    ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC={auroc:.4f})')
    ax.plot([0, 1], [0, 1], 'r--', linewidth=1, label='Random')
    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title('ROC Curve', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2-3. 혼동행렬
    ax = axes[1, 0]
    predictions = (scores > threshold).astype(int)
    cm = confusion_matrix(labels, predictions)

    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['Normal', 'Anomaly'],
                yticklabels=['Normal', 'Anomaly'])
    ax.set_xlabel('Predicted', fontsize=11)
    ax.set_ylabel('True', fontsize=11)
    ax.set_title('Confusion Matrix', fontsize=12, fontweight='bold')

    # 2-4. 통계 요약
    ax = axes[1, 1]
    ax.axis('off')

    # 성능 메트릭 계산
    precision = precision_score(labels, predictions, zero_division=0)
    recall = recall_score(labels, predictions, zero_division=0)
    f1 = f1_score(labels, predictions, zero_division=0)
    accuracy = (predictions == labels).mean()

    tn, fp, fn, tp = cm.ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    stats_text = f"""
    Validation Statistics
    {'='*35}

    Total Samples: {len(labels)}
    Normal: {(labels==0).sum()}  |  Anomaly: {(labels==1).sum()}

    Performance Metrics
    {'='*35}
    AUROC: {auroc:.4f}
    Accuracy: {accuracy:.4f}
    Precision: {precision:.4f}
    Recall: {recall:.4f}
    F1-Score: {f1:.4f}
    Specificity: {specificity:.4f}

    Threshold: {threshold:.6f}

    Confusion Matrix
    {'='*35}
    True Positive:  {tp}
    True Negative:  {tn}
    False Positive: {fp}
    False Negative: {fn}

    Score Statistics
    {'='*35}
    Normal Mean:  {normal_scores.mean():.6f}
    Normal Std:   {normal_scores.std():.6f}
    Anomaly Mean: {anomaly_scores.mean():.6f}
    Anomaly Std:  {anomaly_scores.std():.6f}
    """

    ax.text(0.1, 0.95, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig(save_dir / 'validation_results.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Visualizations saved to: {save_dir}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Validate AutoEncoder model')
    parser.add_argument('--model', type=str,
                        default=str(CONFIG_ROOT / 'models' / 'anomaly' / 'best_model.pt'),
                        help='Path to model checkpoint')
    parser.add_argument('--num_samples', type=int, default=100,
                        help='Number of validation samples')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='Batch size for validation')

    args = parser.parse_args()

    print("="*60)
    print("AutoEncoder Validation")
    print("="*60)

    # 랜덤 시드 설정
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)

    # 설정
    config = VALIDATION_CONFIG.copy()
    config['num_samples'] = args.num_samples
    config['batch_size'] = args.batch_size

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        return

    # 결과 저장 디렉토리
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = config['results_dir'] / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nResults will be saved to: {results_dir}")

    # 1. 모델 로드
    print("\n[1/5] Loading model...")
    model, device = load_model(model_path)

    # 2. 검증 데이터셋 준비
    print("\n[2/5] Preparing validation dataset...")
    val_image_paths, val_labels = prepare_validation_dataset(
        IMAGE_DIR, LABEL_DIR,
        num_samples=config['num_samples'],
        normal_category_id=ANOMALY_CONFIG['normal_category_id'],
        anomaly_category_ids=ANOMALY_CONFIG.get('anomaly_category_ids')
    )

    val_dataset = AnomalyDataset(
        image_paths=val_image_paths,
        labels=val_labels,
        image_size=config['image_size'],
        augment=False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=0
    )

    # 3. 검증 실행
    print("\n[3/5] Running validation...")
    criterion = nn.MSELoss(reduction='none')
    results, scores, labels = validate_model(model, val_loader, device, criterion)

    # 4. 최적 임계값 찾기
    print("\n[4/5] Finding optimal threshold...")
    threshold, f1 = find_optimal_threshold(labels, scores)
    print(f"Optimal threshold: {threshold:.6f} (F1={f1:.4f})")

    # 5. 결과 저장 및 시각화
    print("\n[5/5] Saving results...")

    # CSV 저장
    csv_path = results_dir / 'validation_results.csv'
    df = save_results_to_csv(results, threshold, csv_path)

    # 통계 저장
    auroc = roc_auc_score(labels, scores)
    predictions = (scores > threshold).astype(int)

    stats = {
        'timestamp': timestamp,
        'model_path': str(model_path),
        'num_samples': len(labels),
        'normal_samples': int((labels == 0).sum()),
        'anomaly_samples': int((labels == 1).sum()),
        'auroc': float(auroc),
        'threshold': float(threshold),
        'f1_score': float(f1),
        'accuracy': float((predictions == labels).mean()),
        'precision': float(precision_score(labels, predictions, zero_division=0)),
        'recall': float(recall_score(labels, predictions, zero_division=0)),
    }

    with open(results_dir / 'validation_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

    # 시각화
    visualize_results(results, scores, labels, threshold, results_dir)

    # 최종 결과 출력
    print("\n" + "="*60)
    print("Validation Complete!")
    print("="*60)
    print(f"AUROC: {auroc:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print(f"Accuracy: {stats['accuracy']:.4f}")
    print(f"Precision: {stats['precision']:.4f}")
    print(f"Recall: {stats['recall']:.4f}")
    print(f"\nResults saved to: {results_dir}")
    print(f"  - CSV: {csv_path.name}")
    print(f"  - Stats: validation_stats.json")
    print(f"  - Plots: validation_results.png, reconstruction_comparison.png")


if __name__ == '__main__':
    main()
