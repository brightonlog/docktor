#!/usr/bin/env python3
"""
Statistical Analysis for Ship Coating Dataset
통계 분석 및 YOLO 학습 전략 수립
"""

import json
import os
import sys
import shutil
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter, defaultdict
from tqdm import tqdm
import seaborn as sns
from datetime import datetime
from sklearn.cluster import KMeans

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
OUTPUT_DIR = PROJECT_ROOT / f'results/eda/{TODAY}/statistical'
LATEST_DIR = PROJECT_ROOT / 'results/eda/latest/statistical'


class StatisticalAnalyzer:
    def __init__(self, image_dir, label_dir, output_dir):
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.output_dir = Path(output_dir)
        self.charts_dir = self.output_dir / 'charts'
        self.charts_dir.mkdir(parents=True, exist_ok=True)

        # Statistics storage
        self.stats = {
            'total_images': 0,
            'total_labels': 0,
            'matched_pairs': 0,
            'category_counts': defaultdict(int),
            'image_sizes': [],
            'bbox_sizes': [],
            'bbox_aspect_ratios': [],
            'annotations_per_image': [],
            'class_wise': defaultdict(lambda: {
                'bbox_widths': [],
                'bbox_heights': [],
                'bbox_areas': [],
                'image_count': 0,
                'annotation_count': 0
            })
        }

    def load_json(self, json_path):
        """Load JSON annotation file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    def get_all_files(self):
        """Get all image and label file paths"""
        images = {}
        labels = {}

        # Collect images
        for img_path in self.image_dir.rglob('*.jpg'):
            rel_path = img_path.relative_to(self.image_dir)
            key = str(rel_path.parent / img_path.stem)
            images[key] = img_path

        # Collect labels
        for label_path in self.label_dir.rglob('*.json'):
            rel_path = label_path.relative_to(self.label_dir)
            key = str(rel_path.parent / label_path.stem)
            labels[key] = label_path

        return images, labels

    def analyze_dataset(self):
        """Main analysis workflow"""
        print("\n" + "=" * 70)
        print("STATISTICAL ANALYSIS")
        print("=" * 70)

        # Get files
        images, labels = self.get_all_files()
        self.stats['total_images'] = len(images)
        self.stats['total_labels'] = len(labels)

        # Find matched pairs
        image_keys = set(images.keys())
        label_keys = set(labels.keys())
        matched = image_keys & label_keys
        self.stats['matched_pairs'] = len(matched)

        print(f"\nTotal Images: {self.stats['total_images']}")
        print(f"Total Labels: {self.stats['total_labels']}")
        print(f"Matched Pairs: {self.stats['matched_pairs']}")

        # Analyze all images
        print(f"\nAnalyzing {len(matched)} images...")
        matched_images = [images[k] for k in matched]

        for img_path in tqdm(matched_images, desc="Processing images"):
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    h, w, c = img.shape
                    self.stats['image_sizes'].append((w, h))
            except:
                pass

        # Analyze all annotations
        print(f"Analyzing {len(matched)} labels...")
        matched_labels = [labels[k] for k in matched]
        images_per_category = defaultdict(set)

        for label_path in tqdm(matched_labels, desc="Processing labels"):
            data = self.load_json(label_path)
            if not data:
                continue

            annotations = data.get('annotations', [])
            self.stats['annotations_per_image'].append(len(annotations))
            image_filename = str(label_path)

            for ann in annotations:
                cat_id = ann.get('category_id')
                if cat_id:
                    self.stats['category_counts'][cat_id] += 1
                    images_per_category[cat_id].add(image_filename)
                    self.stats['class_wise'][cat_id]['annotation_count'] += 1

                if 'bbox' in ann and ann['bbox']:
                    x, y, w, h = ann['bbox']
                    self.stats['bbox_sizes'].append((w, h))
                    if h > 0:
                        self.stats['bbox_aspect_ratios'].append(w / h)

                    if cat_id:
                        area = w * h
                        self.stats['class_wise'][cat_id]['bbox_widths'].append(w)
                        self.stats['class_wise'][cat_id]['bbox_heights'].append(h)
                        self.stats['class_wise'][cat_id]['bbox_areas'].append(area)

        # Update image counts per category
        for cat_id, image_set in images_per_category.items():
            self.stats['class_wise'][cat_id]['image_count'] = len(image_set)

        print(f"✓ Analysis complete")

    def calculate_class_weights(self):
        """Calculate class weights for imbalanced learning"""
        total_annotations = sum(self.stats['category_counts'].values())
        class_weights = {}

        for cat_id, count in self.stats['category_counts'].items():
            # Inverse frequency weighting
            weight = total_annotations / (len(self.stats['category_counts']) * count)
            class_weights[cat_id] = weight

        return class_weights

    def analyze_small_objects(self, threshold=32*32):
        """Analyze ratio of small objects"""
        if not self.stats['bbox_sizes']:
            return 0.0

        areas = [w * h for w, h in self.stats['bbox_sizes']]
        small_count = sum(1 for area in areas if area < threshold)
        small_ratio = small_count / len(areas)

        return small_ratio, small_count, len(areas)

    def cluster_bbox_sizes(self, n_clusters=9):
        """K-means clustering for anchor box optimization"""
        if not self.stats['bbox_sizes']:
            return None

        # Normalize bbox sizes
        bbox_array = np.array(self.stats['bbox_sizes'])

        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(bbox_array)

        # Get cluster centers (anchor boxes)
        anchors = kmeans.cluster_centers_
        # Sort by area
        anchors = sorted(anchors, key=lambda x: x[0] * x[1])

        return np.array(anchors)

    def generate_visualizations(self):
        """Generate core visualizations"""
        print("\n" + "=" * 70)
        print("GENERATING VISUALIZATIONS")
        print("=" * 70)

        self.plot_class_distribution()
        self.plot_bbox_analysis()
        self.plot_class_imbalance()
        self.plot_small_object_ratio()
        self.plot_bbox_clustering()

        print(f"✓ Visualizations saved to {self.charts_dir}")

    def plot_class_distribution(self):
        """Plot category distribution"""
        fig, ax = plt.subplots(figsize=(14, 6))

        categories = [CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
                     for cat_id in sorted(self.stats['category_counts'].keys())]
        counts = [self.stats['category_counts'][cat_id]
                 for cat_id in sorted(self.stats['category_counts'].keys())]

        bars = ax.bar(range(len(categories)), counts, color='steelblue', alpha=0.8, edgecolor='black')
        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=10)
        ax.set_ylabel('Annotation Count', fontsize=12)
        ax.set_title('Class Distribution', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        # Add count labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'class_distribution.png', dpi=150)
        plt.close()

    def plot_bbox_analysis(self):
        """Plot bounding box size distribution"""
        if not self.stats['bbox_sizes']:
            return

        widths = [w for w, h in self.stats['bbox_sizes']]
        heights = [h for w, h in self.stats['bbox_sizes']]
        areas = [w * h for w, h in self.stats['bbox_sizes']]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Width distribution
        axes[0, 0].hist(widths, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        axes[0, 0].set_xlabel('BBox Width (pixels)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Bounding Box Width Distribution')
        axes[0, 0].axvline(np.mean(widths), color='red', linestyle='--',
                          label=f'Mean: {np.mean(widths):.1f}')
        axes[0, 0].legend()

        # Height distribution
        axes[0, 1].hist(heights, bins=50, color='lightcoral', edgecolor='black', alpha=0.7)
        axes[0, 1].set_xlabel('BBox Height (pixels)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Bounding Box Height Distribution')
        axes[0, 1].axvline(np.mean(heights), color='red', linestyle='--',
                          label=f'Mean: {np.mean(heights):.1f}')
        axes[0, 1].legend()

        # Area distribution
        axes[1, 0].hist(areas, bins=50, color='lightgreen', edgecolor='black', alpha=0.7)
        axes[1, 0].set_xlabel('BBox Area (pixels²)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Bounding Box Area Distribution')
        axes[1, 0].axvline(np.mean(areas), color='red', linestyle='--',
                          label=f'Mean: {np.mean(areas):.0f}')
        axes[1, 0].legend()

        # Aspect ratio distribution
        if self.stats['bbox_aspect_ratios']:
            axes[1, 1].hist(self.stats['bbox_aspect_ratios'], bins=50,
                           color='plum', edgecolor='black', alpha=0.7)
            axes[1, 1].set_xlabel('Aspect Ratio (W/H)')
            axes[1, 1].set_ylabel('Frequency')
            axes[1, 1].set_title('Bounding Box Aspect Ratio Distribution')
            axes[1, 1].axvline(np.mean(self.stats['bbox_aspect_ratios']),
                              color='red', linestyle='--',
                              label=f'Mean: {np.mean(self.stats["bbox_aspect_ratios"]):.2f}')
            axes[1, 1].legend()

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'bbox_size_distribution.png', dpi=150)
        plt.close()

    def plot_class_imbalance(self):
        """Plot class imbalance with weights"""
        class_weights = self.calculate_class_weights()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        categories = [CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
                     for cat_id in sorted(self.stats['category_counts'].keys())]
        counts = [self.stats['category_counts'][cat_id]
                 for cat_id in sorted(self.stats['category_counts'].keys())]
        weights = [class_weights[cat_id]
                  for cat_id in sorted(self.stats['category_counts'].keys())]

        # Class counts
        bars1 = ax1.bar(range(len(categories)), counts, color='coral', alpha=0.8, edgecolor='black')
        ax1.set_xticks(range(len(categories)))
        ax1.set_xticklabels(categories, rotation=45, ha='right', fontsize=9)
        ax1.set_ylabel('Sample Count', fontsize=12)
        ax1.set_title('Class Imbalance (Sample Counts)', fontsize=13, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)

        # Class weights
        bars2 = ax2.bar(range(len(categories)), weights, color='steelblue', alpha=0.8, edgecolor='black')
        ax2.set_xticks(range(len(categories)))
        ax2.set_xticklabels(categories, rotation=45, ha='right', fontsize=9)
        ax2.set_ylabel('Weight', fontsize=12)
        ax2.set_title('Recommended Class Weights (Inverse Frequency)', fontsize=13, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        # Add value labels
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'class_imbalance.png', dpi=150)
        plt.close()

    def plot_small_object_ratio(self):
        """Plot small object analysis"""
        small_ratio, small_count, total_count = self.analyze_small_objects()

        fig, ax = plt.subplots(figsize=(10, 6))

        categories = ['Small Objects\n(< 32x32)', 'Medium/Large Objects\n(>= 32x32)']
        counts = [small_count, total_count - small_count]
        colors = ['#FF6B6B', '#4ECDC4']

        wedges, texts, autotexts = ax.pie(counts, labels=categories, autopct='%1.1f%%',
                                           colors=colors, startangle=90,
                                           textprops={'fontsize': 12})

        # Make percentage text bold
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(14)

        ax.set_title(f'Small Object Ratio\n(Total BBoxes: {total_count:,})',
                    fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'small_object_ratio.png', dpi=150)
        plt.close()

    def plot_bbox_clustering(self):
        """Plot bbox clustering for anchor boxes"""
        anchors = self.cluster_bbox_sizes(n_clusters=9)

        if anchors is None:
            return

        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot all bboxes
        bbox_array = np.array(self.stats['bbox_sizes'])
        ax.scatter(bbox_array[:, 0], bbox_array[:, 1],
                  alpha=0.3, s=1, c='gray', label='All BBoxes')

        # Plot anchor boxes
        ax.scatter(anchors[:, 0], anchors[:, 1],
                  c='red', s=200, marker='x', linewidths=3,
                  label='Anchor Boxes (K-means)', zorder=5)

        # Annotate anchors
        for i, (w, h) in enumerate(anchors):
            ax.annotate(f'{i+1}\n({w:.0f},{h:.0f})',
                       xy=(w, h), xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=9, fontweight='bold')

        ax.set_xlabel('Width (pixels)', fontsize=12)
        ax.set_ylabel('Height (pixels)', fontsize=12)
        ax.set_title('BBox Clustering for Anchor Box Optimization (9 clusters)',
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.charts_dir / 'bbox_clustering.png', dpi=150)
        plt.close()

    def save_report(self):
        """Save analysis report"""
        report_path = self.output_dir / 'analysis_report.txt'

        class_weights = self.calculate_class_weights()
        small_ratio, small_count, total_count = self.analyze_small_objects()
        anchors = self.cluster_bbox_sizes(n_clusters=9)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("STATISTICAL ANALYSIS REPORT\n")
            f.write("=" * 70 + "\n\n")

            # Dataset Overview
            f.write("1. DATASET OVERVIEW\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total Images: {self.stats['total_images']}\n")
            f.write(f"Total Labels: {self.stats['total_labels']}\n")
            f.write(f"Matched Pairs: {self.stats['matched_pairs']}\n")
            f.write(f"Total Annotations: {sum(self.stats['category_counts'].values())}\n\n")

            # Class Distribution
            f.write("2. CLASS DISTRIBUTION\n")
            f.write("-" * 70 + "\n")
            for cat_id in sorted(self.stats['category_counts'].keys()):
                cat_name = CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
                count = self.stats['category_counts'][cat_id]
                percentage = count / sum(self.stats['category_counts'].values()) * 100
                f.write(f"{cat_name:20s}: {count:6d} ({percentage:5.2f}%)\n")
            f.write("\n")

            # Class Imbalance
            f.write("3. CLASS IMBALANCE & WEIGHTS\n")
            f.write("-" * 70 + "\n")
            f.write("Recommended class weights for imbalanced learning:\n\n")
            for cat_id in sorted(class_weights.keys()):
                cat_name = CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
                weight = class_weights[cat_id]
                f.write(f"{cat_name:20s}: {weight:.4f}\n")
            f.write("\n")

            # Small Objects
            f.write("4. SMALL OBJECT ANALYSIS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total BBoxes: {total_count}\n")
            f.write(f"Small Objects (< 32x32): {small_count} ({small_ratio*100:.2f}%)\n")
            f.write(f"Medium/Large Objects: {total_count - small_count} ({(1-small_ratio)*100:.2f}%)\n")
            f.write("\nRecommendation:\n")
            if small_ratio > 0.3:
                f.write("  ⚠️  High ratio of small objects detected!\n")
                f.write("  → Use mosaic augmentation\n")
                f.write("  → Increase input resolution\n")
                f.write("  → Consider multi-scale training\n")
            else:
                f.write("  ✓ Small object ratio is manageable\n")
            f.write("\n")

            # BBox Statistics
            if self.stats['bbox_sizes']:
                f.write("5. BOUNDING BOX STATISTICS\n")
                f.write("-" * 70 + "\n")
                widths = [w for w, h in self.stats['bbox_sizes']]
                heights = [h for w, h in self.stats['bbox_sizes']]
                areas = [w * h for w, h in self.stats['bbox_sizes']]

                f.write(f"Width  - Mean: {np.mean(widths):.1f}, Std: {np.std(widths):.1f}, "
                       f"Min: {min(widths):.1f}, Max: {max(widths):.1f}\n")
                f.write(f"Height - Mean: {np.mean(heights):.1f}, Std: {np.std(heights):.1f}, "
                       f"Min: {min(heights):.1f}, Max: {max(heights):.1f}\n")
                f.write(f"Area   - Mean: {np.mean(areas):.1f}, Std: {np.std(areas):.1f}, "
                       f"Min: {min(areas):.1f}, Max: {max(areas):.1f}\n\n")

            # Anchor Boxes
            if anchors is not None:
                f.write("6. ANCHOR BOX RECOMMENDATIONS (K-means clustering)\n")
                f.write("-" * 70 + "\n")
                f.write("Suggested anchor boxes (width, height):\n\n")
                for i, (w, h) in enumerate(anchors):
                    f.write(f"  Anchor {i+1}: ({w:6.1f}, {h:6.1f})  [area: {w*h:8.0f}]\n")
                f.write("\n")

            # Training Recommendations
            f.write("7. TRAINING RECOMMENDATIONS\n")
            f.write("=" * 70 + "\n")
            f.write("\n✓ Use class weights to handle imbalance\n")
            if small_ratio > 0.3:
                f.write("✓ Enable mosaic augmentation for small objects\n")
            f.write("✓ Use recommended anchor boxes for faster convergence\n")
            f.write("✓ Monitor mAP for minority classes\n")
            f.write("\n")

        print(f"\n✓ Report saved to {report_path}")

    def run(self):
        """Run complete analysis"""
        print("\n" + "=" * 70)
        print("STARTING STATISTICAL ANALYSIS")
        print("=" * 70)

        self.analyze_dataset()
        self.generate_visualizations()
        self.save_report()

        print("\n" + "=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"Results saved to: {self.output_dir}")
        print("\nGenerated files:")
        print("  Charts:")
        print("    - class_distribution.png")
        print("    - bbox_size_distribution.png")
        print("    - class_imbalance.png")
        print("    - small_object_ratio.png")
        print("    - bbox_clustering.png")
        print("  Report:")
        print("    - analysis_report.txt")
        print("=" * 70)


def main():
    """Main function"""
    # Run analysis
    analyzer = StatisticalAnalyzer(IMAGE_DIR, LABEL_DIR, OUTPUT_DIR)
    analyzer.run()

    # Copy to latest
    print("\nCopying to latest...")
    if LATEST_DIR.exists():
        shutil.rmtree(LATEST_DIR)
    shutil.copytree(OUTPUT_DIR, LATEST_DIR)
    print(f"✓ Results copied to: {LATEST_DIR}")


if __name__ == "__main__":
    main()
