#!/usr/bin/env python3
"""
Anomaly Detection Analysis
이상 탐지 모델 학습 전략 수립을 위한 분석
"""

import json
import os
import sys
import shutil
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm
import seaborn as sns
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.dataset_config import CATEGORIES

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
IMAGE_DIR = PROJECT_ROOT / 'data/extracted/01.images'
LABEL_DIR = PROJECT_ROOT / 'data/extracted/02.labels'

# Output directory
TODAY = datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR = PROJECT_ROOT / f'results/eda/{TODAY}/anomaly'
LATEST_DIR = PROJECT_ROOT / 'results/eda/latest/anomaly'


class AnomalyAnalyzer:
    def __init__(self, image_dir, label_dir, output_dir):
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.output_dir = Path(output_dir)
        self.charts_dir = self.output_dir / 'charts'
        self.charts_dir.mkdir(parents=True, exist_ok=True)

        # Normal class ID
        self.NORMAL_ID = 101

        # Statistics
        self.stats = {
            'normal': {
                'images': [],
                'rgb_means': [],
                'rgb_stds': [],
                'brightness': [],
                'contrast': []
            },
            'defect': defaultdict(lambda: {
                'images': [],
                'rgb_means': [],
                'rgb_stds': [],
                'brightness': [],
                'contrast': []
            })
        }

    def load_json(self, json_path):
        """Load JSON annotation file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    def analyze_image_features(self, img_path):
        """Extract image features"""
        img = cv2.imread(str(img_path))
        if img is None:
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # RGB statistics
        rgb_mean = np.mean(img_rgb, axis=(0, 1))
        rgb_std = np.std(img_rgb, axis=(0, 1))

        # Brightness (average of RGB)
        brightness = np.mean(rgb_mean)

        # Contrast (average of std)
        contrast = np.mean(rgb_std)

        return {
            'rgb_mean': rgb_mean,
            'rgb_std': rgb_std,
            'brightness': brightness,
            'contrast': contrast
        }

    def collect_data(self):
        """Collect normal and defect data"""
        print("\n" + "=" * 70)
        print("COLLECTING DATA FOR ANOMALY ANALYSIS")
        print("=" * 70)

        # Walk through images
        all_images = list(self.image_dir.rglob('*.JPG'))
        print(f"\nAnalyzing {len(all_images)} images...")

        for img_path in tqdm(all_images, desc="Processing"):
            # Get corresponding label
            rel_path = img_path.relative_to(self.image_dir)
            label_path = self.label_dir / rel_path.parent / (img_path.stem + '.json')

            if not label_path.exists():
                continue

            # Load label
            data = self.load_json(label_path)
            if not data or 'annotations' not in data:
                continue

            # Extract features
            features = self.analyze_image_features(img_path)
            if not features:
                continue

            # Categorize by annotation
            is_normal = True
            defect_types = set()

            for ann in data['annotations']:
                cat_id = ann.get('category_id')
                if cat_id and cat_id != self.NORMAL_ID:
                    is_normal = False
                    defect_types.add(cat_id)

            # Store features
            if is_normal:
                self.stats['normal']['images'].append(str(img_path))
                self.stats['normal']['rgb_means'].append(features['rgb_mean'])
                self.stats['normal']['rgb_stds'].append(features['rgb_std'])
                self.stats['normal']['brightness'].append(features['brightness'])
                self.stats['normal']['contrast'].append(features['contrast'])
            else:
                for defect_id in defect_types:
                    self.stats['defect'][defect_id]['images'].append(str(img_path))
                    self.stats['defect'][defect_id]['rgb_means'].append(features['rgb_mean'])
                    self.stats['defect'][defect_id]['rgb_stds'].append(features['rgb_std'])
                    self.stats['defect'][defect_id]['brightness'].append(features['brightness'])
                    self.stats['defect'][defect_id]['contrast'].append(features['contrast'])

        print(f"\n✓ Normal images: {len(self.stats['normal']['images'])}")
        print(f"✓ Defect images: {sum(len(d['images']) for d in self.stats['defect'].values())}")

    def generate_visualizations(self):
        """Generate anomaly detection visualizations"""
        print("\n" + "=" * 70)
        print("GENERATING VISUALIZATIONS")
        print("=" * 70)

        self.plot_normal_distribution()
        self.plot_normal_vs_defect()
        self.plot_defect_diversity()

        print(f"✓ Visualizations saved to {self.charts_dir}")

    def plot_normal_distribution(self):
        """Plot normal data distribution"""
        if not self.stats['normal']['brightness']:
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Brightness distribution
        axes[0, 0].hist(self.stats['normal']['brightness'], bins=30,
                       color='green', alpha=0.7, edgecolor='black')
        axes[0, 0].set_xlabel('Brightness')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Normal Data: Brightness Distribution')
        axes[0, 0].axvline(np.mean(self.stats['normal']['brightness']),
                          color='red', linestyle='--',
                          label=f'Mean: {np.mean(self.stats["normal"]["brightness"]):.1f}')
        axes[0, 0].legend()

        # Contrast distribution
        axes[0, 1].hist(self.stats['normal']['contrast'], bins=30,
                       color='blue', alpha=0.7, edgecolor='black')
        axes[0, 1].set_xlabel('Contrast (Std)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Normal Data: Contrast Distribution')
        axes[0, 1].axvline(np.mean(self.stats['normal']['contrast']),
                          color='red', linestyle='--',
                          label=f'Mean: {np.mean(self.stats["normal"]["contrast"]):.1f}')
        axes[0, 1].legend()

        # RGB mean distribution
        rgb_means = np.array(self.stats['normal']['rgb_means'])
        axes[1, 0].hist(rgb_means[:, 0], bins=30, alpha=0.5, label='R', color='red')
        axes[1, 0].hist(rgb_means[:, 1], bins=30, alpha=0.5, label='G', color='green')
        axes[1, 0].hist(rgb_means[:, 2], bins=30, alpha=0.5, label='B', color='blue')
        axes[1, 0].set_xlabel('Pixel Value')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Normal Data: RGB Channel Means')
        axes[1, 0].legend()

        # Brightness vs Contrast scatter
        axes[1, 1].scatter(self.stats['normal']['brightness'],
                          self.stats['normal']['contrast'],
                          alpha=0.5, s=10)
        axes[1, 1].set_xlabel('Brightness')
        axes[1, 1].set_ylabel('Contrast')
        axes[1, 1].set_title('Normal Data: Brightness vs Contrast')
        axes[1, 1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'normal_distribution.png', dpi=150)
        plt.close()

    def plot_normal_vs_defect(self):
        """Plot normal vs defect comparison"""
        if not self.stats['normal']['brightness'] or not self.stats['defect']:
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Collect all defect data
        all_defect_brightness = []
        all_defect_contrast = []
        for defect_data in self.stats['defect'].values():
            all_defect_brightness.extend(defect_data['brightness'])
            all_defect_contrast.extend(defect_data['contrast'])

        # Brightness comparison
        axes[0].hist(self.stats['normal']['brightness'], bins=30, alpha=0.6,
                    label='Normal', color='green', edgecolor='black')
        axes[0].hist(all_defect_brightness, bins=30, alpha=0.6,
                    label='Defect', color='red', edgecolor='black')
        axes[0].set_xlabel('Brightness')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Normal vs Defect: Brightness Distribution')
        axes[0].legend()
        axes[0].grid(alpha=0.3)

        # Contrast comparison
        axes[1].hist(self.stats['normal']['contrast'], bins=30, alpha=0.6,
                    label='Normal', color='green', edgecolor='black')
        axes[1].hist(all_defect_contrast, bins=30, alpha=0.6,
                    label='Defect', color='red', edgecolor='black')
        axes[1].set_xlabel('Contrast (Std)')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Normal vs Defect: Contrast Distribution')
        axes[1].legend()
        axes[1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'normal_vs_defect.png', dpi=150)
        plt.close()

    def plot_defect_diversity(self):
        """Plot defect type diversity"""
        if not self.stats['defect']:
            return

        fig, axes = plt.subplots(2, 1, figsize=(14, 10))

        # Defect counts
        defect_names = [CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
                       for cat_id in sorted(self.stats['defect'].keys())]
        defect_counts = [len(self.stats['defect'][cat_id]['images'])
                        for cat_id in sorted(self.stats['defect'].keys())]

        bars = axes[0].bar(range(len(defect_names)), defect_counts,
                          color='coral', alpha=0.8, edgecolor='black')
        axes[0].set_xticks(range(len(defect_names)))
        axes[0].set_xticklabels(defect_names, rotation=45, ha='right')
        axes[0].set_ylabel('Image Count')
        axes[0].set_title('Defect Type Distribution')
        axes[0].grid(axis='y', alpha=0.3)

        # Add count labels
        for bar in bars:
            height = bar.get_height()
            axes[0].text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom')

        # Brightness by defect type
        brightness_data = []
        labels = []
        for cat_id in sorted(self.stats['defect'].keys()):
            if self.stats['defect'][cat_id]['brightness']:
                brightness_data.append(self.stats['defect'][cat_id]['brightness'])
                labels.append(CATEGORIES.get(cat_id, f'Unknown-{cat_id}'))

        if brightness_data:
            bp = axes[1].boxplot(brightness_data, labels=labels, patch_artist=True)
            for patch in bp['boxes']:
                patch.set_facecolor('lightcoral')

            axes[1].set_xticklabels(labels, rotation=45, ha='right')
            axes[1].set_ylabel('Brightness')
            axes[1].set_title('Brightness Distribution by Defect Type')
            axes[1].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'defect_diversity.png', dpi=150)
        plt.close()

    def save_reports(self):
        """Save analysis reports"""
        # Normal statistics
        normal_stats_path = self.output_dir / 'normal_stats.txt'
        with open(normal_stats_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("NORMAL DATA STATISTICS\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Total Normal Images: {len(self.stats['normal']['images'])}\n\n")

            if self.stats['normal']['brightness']:
                f.write("Brightness Statistics:\n")
                f.write(f"  Mean: {np.mean(self.stats['normal']['brightness']):.2f}\n")
                f.write(f"  Std:  {np.std(self.stats['normal']['brightness']):.2f}\n")
                f.write(f"  Min:  {np.min(self.stats['normal']['brightness']):.2f}\n")
                f.write(f"  Max:  {np.max(self.stats['normal']['brightness']):.2f}\n\n")

                f.write("Contrast Statistics:\n")
                f.write(f"  Mean: {np.mean(self.stats['normal']['contrast']):.2f}\n")
                f.write(f"  Std:  {np.std(self.stats['normal']['contrast']):.2f}\n")
                f.write(f"  Min:  {np.min(self.stats['normal']['contrast']):.2f}\n")
                f.write(f"  Max:  {np.max(self.stats['normal']['contrast']):.2f}\n\n")

                rgb_means = np.array(self.stats['normal']['rgb_means'])
                f.write("RGB Channel Means:\n")
                f.write(f"  R: {np.mean(rgb_means[:, 0]):.2f} ± {np.std(rgb_means[:, 0]):.2f}\n")
                f.write(f"  G: {np.mean(rgb_means[:, 1]):.2f} ± {np.std(rgb_means[:, 1]):.2f}\n")
                f.write(f"  B: {np.mean(rgb_means[:, 2]):.2f} ± {np.std(rgb_means[:, 2]):.2f}\n")

        # Anomaly detection strategy
        strategy_path = self.output_dir / 'anomaly_strategy.txt'
        with open(strategy_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ANOMALY DETECTION STRATEGY RECOMMENDATIONS\n")
            f.write("=" * 70 + "\n\n")

            f.write("1. DATA PREPARATION\n")
            f.write("-" * 70 + "\n")
            f.write(f"✓ Normal images available: {len(self.stats['normal']['images'])}\n")
            f.write(f"✓ Defect types: {len(self.stats['defect'])}\n\n")

            variation = np.std(self.stats['normal']['brightness']) if self.stats['normal']['brightness'] else 0
            f.write("2. NORMAL DATA CHARACTERISTICS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Brightness variation: {variation:.2f}\n")
            if variation < 20:
                f.write("  → Low variation: AutoEncoder should work well\n")
            else:
                f.write("  → High variation: Consider using VAE or robust features\n")
            f.write("\n")

            f.write("3. RECOMMENDED APPROACHES\n")
            f.write("-" * 70 + "\n")
            f.write("Based on data characteristics, consider:\n\n")
            f.write("A. AutoEncoder-based Methods:\n")
            f.write("   - Reconstruction error as anomaly score\n")
            f.write("   - Train only on normal data\n")
            f.write("   - Threshold: Mean + 2*Std of reconstruction error\n\n")

            f.write("B. Feature-based Methods:\n")
            f.write("   - One-Class SVM\n")
            f.write("   - Isolation Forest\n")
            f.write("   - Extract features: brightness, contrast, texture\n\n")

            f.write("C. Deep Learning Methods:\n")
            f.write("   - Variational AutoEncoder (VAE)\n")
            f.write("   - f-AnoGAN\n")
            f.write("   - PatchCore\n\n")

            f.write("4. EVALUATION STRATEGY\n")
            f.write("-" * 70 + "\n")
            f.write("✓ Use normal data for training only\n")
            f.write("✓ Validate on mixed normal + defect data\n")
            f.write("✓ Metrics: AUROC, F1-score, Precision-Recall\n")
            f.write("✓ Monitor per-defect-type performance\n\n")

            f.write("5. NEXT STEPS\n")
            f.write("-" * 70 + "\n")
            f.write("1. Split normal data: 80% train, 20% validation\n")
            f.write("2. Implement AutoEncoder baseline\n")
            f.write("3. Compare with traditional methods (One-Class SVM)\n")
            f.write("4. Fine-tune threshold for optimal F1-score\n")
            f.write("5. Analyze failure cases\n")

        print(f"\n✓ Reports saved to {self.output_dir}")

    def run(self):
        """Run complete analysis"""
        print("\n" + "=" * 70)
        print("STARTING ANOMALY DETECTION ANALYSIS")
        print("=" * 70)

        self.collect_data()
        self.generate_visualizations()
        self.save_reports()

        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"Results saved to: {self.output_dir}")
        print("\nGenerated files:")
        print("  Charts:")
        print("    - normal_distribution.png")
        print("    - normal_vs_defect.png")
        print("    - defect_diversity.png")
        print("  Reports:")
        print("    - normal_stats.txt")
        print("    - anomaly_strategy.txt")
        print("=" * 70)


def main():
    """Main function"""
    # Run analysis
    analyzer = AnomalyAnalyzer(IMAGE_DIR, LABEL_DIR, OUTPUT_DIR)
    analyzer.run()

    # Copy to latest
    print("\nCopying to latest...")
    if LATEST_DIR.exists():
        shutil.rmtree(LATEST_DIR)
    shutil.copytree(OUTPUT_DIR, LATEST_DIR)
    print(f"✓ Results copied to: {LATEST_DIR}")


if __name__ == "__main__":
    main()
