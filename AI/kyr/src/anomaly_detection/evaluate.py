"""
Anomaly Detection 모델 검증 스크립트

학습된 Autoencoder가 실제로 이상 탐지를 잘 하는지 검증합니다.

검증 메트릭:
1. AUROC (Area Under ROC Curve) - 가장 중요한 지표
2. 정상/비정상 anomaly score 분포
3. 최적 threshold 자동 탐색
4. 시각적 검증 (복원 품질, 히트맵)

Usage:
    python src/anomaly_detection/evaluate.py \
        --model models/anomaly_detection/best_model.pt \
        --normal-dir data/processed/val/images/normal \
        --anomaly-dir data/processed/val/images/coating_damage
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
import json

import torch
import numpy as np
from PIL import Image
from torchvision import transforms

# 시각화
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False

# 메트릭
try:
    from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[Warning] scikit-learn not installed. Limited metrics available.")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.anomaly_detection.inference import AnomalyDetector


def collect_images(directory: str, max_samples: int = None) -> List[str]:
    """디렉토리에서 이미지 경로 수집"""
    path = Path(directory)
    images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']:
        images.extend(path.rglob(ext))
    images = sorted([str(p) for p in images])

    if max_samples and len(images) > max_samples:
        # 균등하게 샘플링
        indices = np.linspace(0, len(images)-1, max_samples, dtype=int)
        images = [images[i] for i in indices]

    return images


def compute_scores(
    detector: AnomalyDetector,
    image_paths: List[str],
    label: str = ""
) -> np.ndarray:
    """이미지들의 anomaly score 계산"""
    scores = []
    print(f"  [{label}] Processing {len(image_paths)} images...")

    for i, path in enumerate(image_paths):
        try:
            result = detector.predict(path, return_map=False)
            scores.append(result.anomaly_score)
        except Exception as e:
            print(f"    [Warning] Failed: {path}")
            continue

        if (i + 1) % 100 == 0:
            print(f"    Processed {i+1}/{len(image_paths)}")

    return np.array(scores)


def find_optimal_threshold(
    normal_scores: np.ndarray,
    anomaly_scores: np.ndarray
) -> Tuple[float, dict]:
    """
    최적 threshold 탐색

    F1-Score가 최대가 되는 지점을 찾음
    """
    all_scores = np.concatenate([normal_scores, anomaly_scores])
    labels = np.concatenate([
        np.zeros(len(normal_scores)),  # 0 = normal
        np.ones(len(anomaly_scores))   # 1 = anomaly
    ])

    # 다양한 threshold에서 F1 계산
    thresholds = np.percentile(all_scores, np.arange(1, 100))
    best_f1 = 0
    best_threshold = 0
    best_metrics = {}

    for thresh in thresholds:
        predictions = (all_scores > thresh).astype(int)

        tp = np.sum((predictions == 1) & (labels == 1))
        fp = np.sum((predictions == 1) & (labels == 0))
        fn = np.sum((predictions == 0) & (labels == 1))
        tn = np.sum((predictions == 0) & (labels == 0))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = thresh
            best_metrics = {
                'threshold': float(thresh),
                'f1_score': float(f1),
                'precision': float(precision),
                'recall': float(recall),
                'true_positive': int(tp),
                'false_positive': int(fp),
                'true_negative': int(tn),
                'false_negative': int(fn),
                'accuracy': float((tp + tn) / len(labels))
            }

    return best_threshold, best_metrics


def plot_score_distribution(
    normal_scores: np.ndarray,
    anomaly_scores: np.ndarray,
    threshold: float,
    save_path: str
):
    """Anomaly score 분포 시각화"""
    if not PLT_AVAILABLE:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 히스토그램
    ax1 = axes[0]
    ax1.hist(normal_scores, bins=50, alpha=0.7, label=f'Normal (n={len(normal_scores)})', color='green')
    ax1.hist(anomaly_scores, bins=50, alpha=0.7, label=f'Anomaly (n={len(anomaly_scores)})', color='red')
    ax1.axvline(threshold, color='black', linestyle='--', linewidth=2, label=f'Threshold: {threshold:.4f}')
    ax1.set_xlabel('Anomaly Score')
    ax1.set_ylabel('Count')
    ax1.set_title('Anomaly Score Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 박스플롯
    ax2 = axes[1]
    bp = ax2.boxplot([normal_scores, anomaly_scores], labels=['Normal', 'Anomaly'], patch_artist=True)
    bp['boxes'][0].set_facecolor('lightgreen')
    bp['boxes'][1].set_facecolor('lightcoral')
    ax2.axhline(threshold, color='black', linestyle='--', linewidth=2, label=f'Threshold: {threshold:.4f}')
    ax2.set_ylabel('Anomaly Score')
    ax2.set_title('Score Comparison')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Saved] Score distribution: {save_path}")


def plot_roc_curve(
    normal_scores: np.ndarray,
    anomaly_scores: np.ndarray,
    save_path: str
) -> float:
    """ROC 곡선 및 AUROC 계산"""
    if not PLT_AVAILABLE or not SKLEARN_AVAILABLE:
        return 0.0

    all_scores = np.concatenate([normal_scores, anomaly_scores])
    labels = np.concatenate([
        np.zeros(len(normal_scores)),
        np.ones(len(anomaly_scores))
    ])

    auroc = roc_auc_score(labels, all_scores)
    fpr, tpr, thresholds = roc_curve(labels, all_scores)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC Curve (AUROC = {auroc:.4f})')
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random (AUROC = 0.5)')
    ax.fill_between(fpr, tpr, alpha=0.3)
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve for Anomaly Detection')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Saved] ROC curve: {save_path}")

    return auroc


def visualize_reconstructions(
    detector: AnomalyDetector,
    normal_images: List[str],
    anomaly_images: List[str],
    save_dir: str,
    num_samples: int = 5
):
    """복원 품질 시각화"""
    if not PLT_AVAILABLE:
        return

    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    # 정상 이미지 샘플
    for i, img_path in enumerate(normal_images[:num_samples]):
        result = detector.predict(img_path, return_map=True)
        detector.visualize_result(
            img_path, result,
            save_path=str(save_path / f"normal_{i+1}_score_{result.anomaly_score:.4f}.png")
        )

    # 비정상 이미지 샘플
    for i, img_path in enumerate(anomaly_images[:num_samples]):
        result = detector.predict(img_path, return_map=True)
        detector.visualize_result(
            img_path, result,
            save_path=str(save_path / f"anomaly_{i+1}_score_{result.anomaly_score:.4f}.png")
        )


def evaluate(
    model_path: str,
    normal_dir: str,
    anomaly_dir: str,
    output_dir: str = "results/evaluation",
    max_samples: int = 500,
    visualize: bool = True
):
    """
    모델 평가 메인 함수
    """
    print("=" * 60)
    print("Anomaly Detection Model Evaluation")
    print("=" * 60)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 탐지기 초기화
    detector = AnomalyDetector(model_path, threshold=0.01)

    # 이미지 수집
    print("\n[1/5] Collecting images...")
    normal_images = collect_images(normal_dir, max_samples)
    anomaly_images = collect_images(anomaly_dir, max_samples)

    print(f"  Normal images: {len(normal_images)}")
    print(f"  Anomaly images: {len(anomaly_images)}")

    if len(normal_images) == 0 or len(anomaly_images) == 0:
        print("[Error] Need both normal and anomaly images for evaluation!")
        return

    # Anomaly score 계산
    print("\n[2/5] Computing anomaly scores...")
    normal_scores = compute_scores(detector, normal_images, "Normal")
    anomaly_scores = compute_scores(detector, anomaly_images, "Anomaly")

    # 통계
    print("\n[3/5] Score Statistics:")
    print(f"  Normal  - Mean: {normal_scores.mean():.6f}, Std: {normal_scores.std():.6f}, "
          f"Min: {normal_scores.min():.6f}, Max: {normal_scores.max():.6f}")
    print(f"  Anomaly - Mean: {anomaly_scores.mean():.6f}, Std: {anomaly_scores.std():.6f}, "
          f"Min: {anomaly_scores.min():.6f}, Max: {anomaly_scores.max():.6f}")

    # 분리도 (Separability)
    separation = (anomaly_scores.mean() - normal_scores.mean()) / (normal_scores.std() + anomaly_scores.std())
    print(f"\n  Separation Score: {separation:.2f}")
    print(f"  (>1.0 = Good, >2.0 = Excellent)")

    # AUROC 계산
    print("\n[4/5] Computing metrics...")
    auroc = 0.0
    if SKLEARN_AVAILABLE:
        all_scores = np.concatenate([normal_scores, anomaly_scores])
        labels = np.concatenate([np.zeros(len(normal_scores)), np.ones(len(anomaly_scores))])
        auroc = roc_auc_score(labels, all_scores)
        print(f"  AUROC: {auroc:.4f}")
        print(f"  (>0.9 = Excellent, >0.8 = Good, >0.7 = Fair)")

    # 최적 threshold
    optimal_threshold, best_metrics = find_optimal_threshold(normal_scores, anomaly_scores)
    print(f"\n  Optimal Threshold: {optimal_threshold:.6f}")
    print(f"  At this threshold:")
    print(f"    - F1 Score:  {best_metrics['f1_score']:.4f}")
    print(f"    - Precision: {best_metrics['precision']:.4f}")
    print(f"    - Recall:    {best_metrics['recall']:.4f}")
    print(f"    - Accuracy:  {best_metrics['accuracy']:.4f}")

    # 시각화
    if visualize and PLT_AVAILABLE:
        print("\n[5/5] Generating visualizations...")

        plot_score_distribution(
            normal_scores, anomaly_scores, optimal_threshold,
            str(output_path / "score_distribution.png")
        )

        if SKLEARN_AVAILABLE:
            plot_roc_curve(
                normal_scores, anomaly_scores,
                str(output_path / "roc_curve.png")
            )

        visualize_reconstructions(
            detector, normal_images, anomaly_images,
            str(output_path / "reconstructions"),
            num_samples=5
        )

    # 결과 저장
    results = {
        'model_path': model_path,
        'normal_images': len(normal_images),
        'anomaly_images': len(anomaly_images),
        'auroc': float(auroc),
        'separation_score': float(separation),
        'optimal_threshold': float(optimal_threshold),
        'metrics_at_optimal': best_metrics,
        'score_statistics': {
            'normal': {
                'mean': float(normal_scores.mean()),
                'std': float(normal_scores.std()),
                'min': float(normal_scores.min()),
                'max': float(normal_scores.max())
            },
            'anomaly': {
                'mean': float(anomaly_scores.mean()),
                'std': float(anomaly_scores.std()),
                'min': float(anomaly_scores.min()),
                'max': float(anomaly_scores.max())
            }
        }
    }

    results_file = output_path / "evaluation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # 최종 판정
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    grade = "UNKNOWN"
    if auroc >= 0.95:
        grade = "EXCELLENT"
    elif auroc >= 0.90:
        grade = "VERY GOOD"
    elif auroc >= 0.85:
        grade = "GOOD"
    elif auroc >= 0.80:
        grade = "FAIR"
    elif auroc >= 0.70:
        grade = "POOR"
    else:
        grade = "FAILED"

    print(f"\n  Model Grade: {grade}")
    print(f"  AUROC: {auroc:.4f}")
    print(f"  Recommended Threshold: {optimal_threshold:.6f}")
    print(f"\n  Results saved to: {output_path}")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description='Evaluate Anomaly Detection Model')
    parser.add_argument('--model', type=str, required=True, help='Model path')
    parser.add_argument('--normal-dir', type=str, required=True, help='Directory of normal images')
    parser.add_argument('--anomaly-dir', type=str, required=True, help='Directory of anomaly images')
    parser.add_argument('--output', type=str, default='results/evaluation', help='Output directory')
    parser.add_argument('--max-samples', type=int, default=500, help='Max samples per class')
    parser.add_argument('--no-visualize', action='store_true', help='Skip visualization')

    args = parser.parse_args()

    evaluate(
        model_path=args.model,
        normal_dir=args.normal_dir,
        anomaly_dir=args.anomaly_dir,
        output_dir=args.output,
        max_samples=args.max_samples,
        visualize=not args.no_visualize
    )


if __name__ == "__main__":
    main()
