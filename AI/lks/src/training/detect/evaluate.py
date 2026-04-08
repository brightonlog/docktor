#!/usr/bin/env python3
"""
Evaluate YOLOv8 Model
모델 성능 평가 및 상세 분석
"""

import sys
from pathlib import Path
import cv2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.training_config import *
from config.dataset_config import CATEGORIES

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("ERROR: ultralytics not installed")
    YOLO_AVAILABLE = False


class YOLOv8Evaluator:
    """
    YOLOv8 Model Evaluator
    """

    def __init__(self, model_path, data_yaml):
        """
        Args:
            model_path: Path to trained model
            data_yaml: Path to data.yaml
        """
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics not installed")

        self.model_path = Path(model_path)
        self.data_yaml = data_yaml

        # Load model
        print(f"Loading model: {self.model_path}")
        self.model = YOLO(str(self.model_path))

    def evaluate(self, save_dir=None):
        """
        Evaluate model on validation set

        Args:
            save_dir: Directory to save results

        Returns:
            metrics: Validation metrics
        """
        print("\n" + "=" * 70)
        print("MODEL EVALUATION")
        print("=" * 70)

        # Run validation
        metrics = self.model.val(
            data=self.data_yaml,
            imgsz=IMAGE_HEIGHT,
            conf=CONF_THRESHOLD,
            iou=IOU_THRESHOLD,
            save_json=True,
            plots=True
        )

        # Print summary
        print("\n" + "=" * 70)
        print("EVALUATION RESULTS")
        print("=" * 70)
        print(f"mAP@0.5: {metrics.box.map50:.4f}")
        print(f"mAP@0.5:0.95: {metrics.box.map:.4f}")
        print(f"Precision: {metrics.box.mp:.4f}")
        print(f"Recall: {metrics.box.mr:.4f}")
        print("=" * 70)

        # Per-class metrics
        print("\nPer-Class Metrics:")
        print("-" * 70)
        print(f"{'Class':<25} {'Precision':>12} {'Recall':>12} {'mAP@0.5':>12}")
        print("-" * 70)

        for i, class_name in enumerate(CLASS_NAMES):
            if i < len(metrics.box.p):
                prec = metrics.box.p[i] if hasattr(metrics.box, 'p') else 0
                rec = metrics.box.r[i] if hasattr(metrics.box, 'r') else 0
                map50 = metrics.box.ap50[i] if hasattr(metrics.box, 'ap50') else 0

                print(f"{class_name:<25} {prec:>12.4f} {rec:>12.4f} {map50:>12.4f}")

        print("-" * 70)

        # Save detailed results
        if save_dir:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)

            # Save metrics to CSV
            self.save_metrics_csv(metrics, save_dir)

            # Create visualizations
            self.create_visualizations(metrics, save_dir)

        return metrics

    def save_metrics_csv(self, metrics, save_dir):
        """
        Save metrics to CSV file

        Args:
            metrics: Validation metrics
            save_dir: Save directory
        """
        csv_path = save_dir / 'metrics.csv'

        # Create dataframe
        data = {
            'class': CLASS_NAMES,
            'precision': [],
            'recall': [],
            'map50': [],
            'map50_95': []
        }

        for i in range(len(CLASS_NAMES)):
            if i < len(metrics.box.p):
                data['precision'].append(metrics.box.p[i] if hasattr(metrics.box, 'p') else 0)
                data['recall'].append(metrics.box.r[i] if hasattr(metrics.box, 'r') else 0)
                data['map50'].append(metrics.box.ap50[i] if hasattr(metrics.box, 'ap50') else 0)
                data['map50_95'].append(metrics.box.ap[i] if hasattr(metrics.box, 'ap') else 0)
            else:
                data['precision'].append(0)
                data['recall'].append(0)
                data['map50'].append(0)
                data['map50_95'].append(0)

        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)

        print(f"\nSaved metrics to: {csv_path}")

    def create_visualizations(self, metrics, save_dir):
        """
        Create visualization plots

        Args:
            metrics: Validation metrics
            save_dir: Save directory
        """
        # Set style
        sns.set_style("whitegrid")

        # 1. Per-class mAP bar plot
        fig, ax = plt.subplots(figsize=(12, 6))

        map50_values = []
        for i in range(len(CLASS_NAMES)):
            if i < len(metrics.box.ap50):
                map50_values.append(metrics.box.ap50[i])
            else:
                map50_values.append(0)

        colors = sns.color_palette("husl", len(CLASS_NAMES))
        bars = ax.bar(CLASS_NAMES, map50_values, color=colors)

        ax.set_xlabel('Class')
        ax.set_ylabel('mAP@0.5')
        ax.set_title('Per-Class mAP@0.5')
        ax.set_ylim([0, 1])
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}',
                   ha='center', va='bottom', fontsize=8)

        plt.savefig(save_dir / 'per_class_map50.png', dpi=300, bbox_inches='tight')
        plt.close()

        # 2. Precision-Recall scatter
        fig, ax = plt.subplots(figsize=(10, 8))

        prec_values = []
        rec_values = []
        for i in range(len(CLASS_NAMES)):
            if i < len(metrics.box.p):
                prec_values.append(metrics.box.p[i] if hasattr(metrics.box, 'p') else 0)
                rec_values.append(metrics.box.r[i] if hasattr(metrics.box, 'r') else 0)
            else:
                prec_values.append(0)
                rec_values.append(0)

        scatter = ax.scatter(rec_values, prec_values, s=100, c=colors, alpha=0.6)

        # Add labels
        for i, class_name in enumerate(CLASS_NAMES):
            ax.annotate(class_name, (rec_values[i], prec_values[i]),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=8, alpha=0.8)

        ax.set_xlabel('Recall')
        ax.set_ylabel('Precision')
        ax.set_title('Precision vs Recall by Class')
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_dir / 'precision_recall_scatter.png', dpi=300, bbox_inches='tight')
        plt.close()

        # 3. Metrics comparison
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(CLASS_NAMES))
        width = 0.25

        ax.bar(x - width, prec_values, width, label='Precision', color='skyblue')
        ax.bar(x, rec_values, width, label='Recall', color='lightcoral')
        ax.bar(x + width, map50_values, width, label='mAP@0.5', color='lightgreen')

        ax.set_xlabel('Class')
        ax.set_ylabel('Score')
        ax.set_title('Metrics Comparison by Class')
        ax.set_xticks(x)
        ax.set_xticklabels(CLASS_NAMES, rotation=45, ha='right')
        ax.set_ylim([0, 1])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(save_dir / 'metrics_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved visualizations to: {save_dir}")

    def predict_sample(self, image_path, save_path=None, conf_threshold=0.25):
        """
        Run inference on single image

        Args:
            image_path: Path to image
            save_path: Path to save visualization
            conf_threshold: Confidence threshold

        Returns:
            results: Prediction results
        """
        print(f"\nRunning inference on: {image_path}")

        # Run prediction
        results = self.model.predict(
            source=str(image_path),
            imgsz=IMAGE_HEIGHT,
            conf=conf_threshold,
            save=save_path is not None,
            save_txt=False,
            save_conf=True
        )

        # Print detections
        if len(results) > 0:
            result = results[0]
            if result.boxes is not None and len(result.boxes) > 0:
                print(f"Found {len(result.boxes)} detections:")
                for box in result.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = CLASS_NAMES[cls]
                    print(f"  - {class_name}: {conf:.3f}")
            else:
                print("No detections found")

        return results

    def benchmark_speed(self, num_iterations=100):
        """
        Benchmark inference speed

        Args:
            num_iterations: Number of iterations

        Returns:
            avg_time: Average inference time in ms
        """
        print(f"\nBenchmarking speed ({num_iterations} iterations)...")

        import time

        # Create dummy input
        dummy_img = np.random.randint(0, 255, (IMAGE_HEIGHT, IMAGE_WIDTH, 3), dtype=np.uint8)

        # Warmup
        for _ in range(10):
            _ = self.model.predict(dummy_img, imgsz=IMAGE_HEIGHT, verbose=False)

        # Benchmark
        times = []
        for _ in range(num_iterations):
            start = time.time()
            _ = self.model.predict(dummy_img, imgsz=IMAGE_HEIGHT, verbose=False)
            end = time.time()
            times.append((end - start) * 1000)  # ms

        avg_time = np.mean(times)
        std_time = np.std(times)
        fps = 1000 / avg_time

        print(f"Average inference time: {avg_time:.2f} ± {std_time:.2f} ms")
        print(f"Throughput: {fps:.2f} FPS")

        return avg_time


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Evaluate YOLOv8 model')
    parser.add_argument('--model', type=str, required=True,
                       help='Path to trained model (best.pt)')
    parser.add_argument('--data', type=str,
                       default=str(YOLO_DATA_DIR / 'data.yaml'),
                       help='Path to data.yaml')
    parser.add_argument('--save-dir', type=str, default='results/evaluation',
                       help='Save directory for results')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run speed benchmark')
    parser.add_argument('--test-image', type=str, default=None,
                       help='Test on single image')
    args = parser.parse_args()

    # Create evaluator
    evaluator = YOLOv8Evaluator(
        model_path=args.model,
        data_yaml=args.data
    )

    # Evaluate on validation set
    save_dir = Path(args.save_dir)
    metrics = evaluator.evaluate(save_dir=save_dir)

    # Benchmark speed
    if args.benchmark:
        evaluator.benchmark_speed()

    # Test on single image
    if args.test_image:
        results = evaluator.predict_sample(
            args.test_image,
            save_path=save_dir / 'predictions'
        )

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
