#!/usr/bin/env python3
"""
PatchCore 검증 스크립트

Usage:
    python validate_patchcore.py
    python validate_patchcore.py --model path/to/model.npz --num_samples 200
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import (
    roc_auc_score, roc_curve, confusion_matrix,
    precision_recall_curve, precision_score, recall_score, f1_score
)
from tqdm import tqdm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import (
    IMAGE_DIR, LABEL_DIR, PROJECT_ROOT as CONFIG_ROOT,
    RANDOM_SEED
)

from training.anomaly.train_patchcore import (
    PatchCore, PATCHCORE_CONFIG
)

from training.anomaly.train_autoencoder import (
    AnomalyDataset, collect_data
)

# ============================================================================
# Validation
# ============================================================================

def prepare_validation_dataset(
    image_dir: Path,
    label_dir: Path,
    num_samples: int = 200,
    normal_category_id: int = 101
):
    """검증 데이터셋 준비"""
    all_image_paths, all_labels = collect_data(
        image_dir, label_dir,
        normal_category_id=normal_category_id,
        anomaly_category_ids=None
    )

    normal_indices = [i for i, l in enumerate(all_labels) if l == 0]
    anomaly_indices = [i for i, l in enumerate(all_labels) if l == 1]

    samples_per_class = num_samples // 2

    random.shuffle(normal_indices)
    random.shuffle(anomaly_indices)

    selected_normal = normal_indices[:min(samples_per_class, len(normal_indices))]
    selected_anomaly = anomaly_indices[:min(samples_per_class, len(anomaly_indices))]

    selected_indices = selected_normal + selected_anomaly
    random.shuffle(selected_indices)

    val_image_paths = [all_image_paths[i] for i in selected_indices]
    val_labels = [all_labels[i] for i in selected_indices]

    print(f"\nValidation Dataset:")
    print(f"  Normal samples: {len(selected_normal)}")
    print(f"  Anomaly samples: {len(selected_anomaly)}")
    print(f"  Total: {len(val_image_paths)}")

    return val_image_paths, val_labels


def save_results_to_csv(
    image_paths: list,
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    save_path: Path
):
    """결과 CSV 저장"""
    df_data = []
    for path, score, label in zip(image_paths, scores, labels):
        df_data.append({
            'image_path': path,
            'true_label': 'anomaly' if label == 1 else 'normal',
            'anomaly_score': score,
            'predicted_label': 'anomaly' if score > threshold else 'normal',
            'is_correct': (score > threshold) == (label == 1)
        })

    df = pd.DataFrame(df_data)
    df = df.sort_values('anomaly_score', ascending=False)

    df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"\nResults saved to: {save_path}")

    return df


def visualize_results(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    save_dir: Path
):
    """결과 시각화"""
    save_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 1. Score Distribution
    ax = axes[0, 0]
    normal_scores = scores[labels == 0]
    anomaly_scores = scores[labels == 1]

    ax.hist(normal_scores, bins=30, alpha=0.7, label='Normal', color='blue')
    ax.hist(anomaly_scores, bins=30, alpha=0.7, label='Anomaly', color='red')
    ax.axvline(threshold, color='green', linestyle='--', linewidth=2,
               label=f'Threshold={threshold:.4f}')
    ax.set_xlabel('Anomaly Score', fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('Score Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. ROC Curve
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

    # 3. Confusion Matrix
    ax = axes[1, 0]
    predictions = (scores > threshold).astype(int)
    cm = confusion_matrix(labels, predictions)

    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=['Normal', 'Anomaly'],
                yticklabels=['Normal', 'Anomaly'])
    ax.set_xlabel('Predicted', fontsize=11)
    ax.set_ylabel('True', fontsize=11)
    ax.set_title('Confusion Matrix', fontsize=12, fontweight='bold')

    # 4. Statistics
    ax = axes[1, 1]
    ax.axis('off')

    precision = precision_score(labels, predictions, zero_division=0)
    recall = recall_score(labels, predictions, zero_division=0)
    f1 = f1_score(labels, predictions, zero_division=0)
    accuracy = (predictions == labels).mean()

    tn, fp, fn, tp = cm.ravel()
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    stats_text = f"""
    Validation Statistics (PatchCore)
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

    print(f"Visualization saved to: {save_dir}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Validate PatchCore model')
    parser.add_argument('--model', type=str,
                        default=str(CONFIG_ROOT / 'models' / 'anomaly_patchcore' / 'patchcore_model.npz'),
                        help='Path to model file')
    parser.add_argument('--num_samples', type=int, default=200,
                        help='Number of validation samples')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size for validation')

    args = parser.parse_args()

    print("="*60)
    print("PatchCore Validation")
    print("="*60)

    # Random seed
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)

    config = PATCHCORE_CONFIG.copy()
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
    print("\n[1/4] Loading model...")
    model = PatchCore(config)
    model.load(model_path)

    # 2. 검증 데이터셋
    print("\n[2/4] Preparing validation dataset...")
    val_image_paths, val_labels = prepare_validation_dataset(
        IMAGE_DIR, LABEL_DIR,
        num_samples=args.num_samples,
        normal_category_id=config['normal_category_id']
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
    print("\n[3/4] Running validation...")
    scores, labels = model.predict(val_loader)

    # 4. 최적 임계값
    print("\n[4/4] Finding optimal threshold...")
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
    best_idx = np.argmax(f1_scores)
    threshold = thresholds[best_idx] if best_idx < len(thresholds) else thresholds[-1]
    best_f1 = f1_scores[best_idx]

    print(f"Optimal threshold: {threshold:.6f} (F1={best_f1:.4f})")

    # 5. 결과 저장
    print("\n[5/5] Saving results...")

    # CSV
    csv_path = results_dir / 'validation_results.csv'
    df = save_results_to_csv(val_image_paths, scores, labels, threshold, csv_path)

    # 통계
    auroc = roc_auc_score(labels, scores)
    predictions = (scores > threshold).astype(int)

    stats = {
        'model': 'PatchCore',
        'timestamp': timestamp,
        'model_path': str(model_path),
        'num_samples': len(labels),
        'normal_samples': int((labels == 0).sum()),
        'anomaly_samples': int((labels == 1).sum()),
        'auroc': float(auroc),
        'threshold': float(threshold),
        'f1_score': float(best_f1),
        'accuracy': float((predictions == labels).mean()),
        'precision': float(precision_score(labels, predictions, zero_division=0)),
        'recall': float(recall_score(labels, predictions, zero_division=0)),
    }

    with open(results_dir / 'validation_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

    # 시각화
    visualize_results(scores, labels, threshold, results_dir)

    # 최종 결과
    print("\n" + "="*60)
    print("Validation Complete!")
    print("="*60)
    print(f"Model: PatchCore")
    print(f"AUROC: {auroc:.4f}")
    print(f"F1-Score: {best_f1:.4f}")
    print(f"Accuracy: {stats['accuracy']:.4f}")
    print(f"Precision: {stats['precision']:.4f}")
    print(f"Recall: {stats['recall']:.4f}")
    print(f"\nResults saved to: {results_dir}")
    print(f"  - CSV: {csv_path.name}")
    print(f"  - Stats: validation_stats.json")
    print(f"  - Plots: validation_results.png")


if __name__ == '__main__':
    main()
