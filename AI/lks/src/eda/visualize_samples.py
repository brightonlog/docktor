#!/usr/bin/env python3
"""
Visualize Sample Images with Labels
라벨링 품질 검증 및 데이터 시각화
"""

import json
import os
import sys
import random
import shutil
import cv2
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.dataset_config import CATEGORIES, COLORS_RGB

# Paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
IMAGE_DIR = PROJECT_ROOT / 'data/extracted/01.images'
LABEL_DIR = PROJECT_ROOT / 'data/extracted/02.labels'

# Output directory
TODAY = datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR = PROJECT_ROOT / f'results/eda/{TODAY}/samples'
LATEST_DIR = PROJECT_ROOT / 'results/eda/latest/samples'


class SampleVisualizer:
    def __init__(self, image_dir, label_dir, output_dir, samples_per_class=5):
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.output_dir = Path(output_dir)
        self.samples_per_class = samples_per_class
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_json(self, json_path):
        """Load JSON annotation file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    def get_samples_by_category(self):
        """Get sample file paths grouped by category"""
        category_samples = {}

        # Walk through label directory
        for label_path in self.label_dir.rglob('*.json'):
            data = self.load_json(label_path)
            if not data or 'annotations' not in data:
                continue

            # Get category from annotations
            for ann in data['annotations']:
                cat_id = ann.get('category_id')
                if not cat_id:
                    continue

                if cat_id not in category_samples:
                    category_samples[cat_id] = []

                # Find corresponding image
                rel_path = label_path.relative_to(self.label_dir)
                img_path = self.image_dir / rel_path.parent / (label_path.stem + '.jpg')

                if img_path.exists():
                    category_samples[cat_id].append({
                        'image_path': img_path,
                        'label_path': label_path,
                        'category_id': cat_id
                    })
                    break  # One sample per image

        return category_samples

    def visualize_sample(self, image_path, label_path, output_path):
        """Visualize single sample with bounding boxes"""
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            return False

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Load labels
        data = self.load_json(label_path)
        if not data:
            return False

        # Draw annotations
        for ann in data['annotations']:
            cat_id = ann['category_id']
            cat_name = CATEGORIES.get(cat_id, 'Unknown')
            color = COLORS_RGB.get(cat_id, (255, 255, 255))

            # Draw segmentation polygon
            if 'segmentation' in ann and ann['segmentation']:
                seg = ann['segmentation']
                points = np.array(seg).reshape(-1, 2).astype(np.int32)

                # Semi-transparent polygon
                overlay = img_rgb.copy()
                cv2.fillPoly(overlay, [points], color)
                img_rgb = cv2.addWeighted(overlay, 0.3, img_rgb, 0.7, 0)

                # Polygon border
                cv2.polylines(img_rgb, [points], True, color, 2)

            # Draw bounding box
            if 'bbox' in ann and ann['bbox']:
                x, y, w, h = [int(v) for v in ann['bbox']]

                # Rectangle
                cv2.rectangle(img_rgb, (x, y), (x+w, y+h), color, 3)

                # Label background
                label = f"{cat_name}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, font, font_scale, thickness
                )

                # Draw background
                cv2.rectangle(img_rgb,
                            (x, y - text_height - 10),
                            (x + text_width + 10, y),
                            color, -1)

                # Draw text
                cv2.putText(img_rgb, label,
                           (x + 5, y - 5),
                           font, font_scale,
                           (255, 255, 255), thickness, cv2.LINE_AA)

        # Save
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(output_path), img_bgr)

        return True

    def run(self):
        """Run visualization for all categories"""
        print("\n" + "=" * 70)
        print("SAMPLE VISUALIZATION")
        print("=" * 70)

        # Get samples by category
        print("\nCollecting samples...")
        category_samples = self.get_samples_by_category()

        print(f"Found {len(category_samples)} categories")

        # Process each category
        total_saved = 0

        for cat_id, samples in sorted(category_samples.items()):
            cat_name = CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
            cat_name_clean = cat_name.lower().replace(' ', '_')

            # Random sample
            n_samples = min(self.samples_per_class, len(samples))
            selected = random.sample(samples, n_samples)

            print(f"\n{cat_name}: {n_samples} samples")

            # Create category output directory
            category_dir = self.output_dir / cat_name_clean
            category_dir.mkdir(exist_ok=True)

            # Visualize each sample
            for i, sample in enumerate(tqdm(selected, desc=f"  Processing")):
                output_path = category_dir / f"{cat_name_clean}_sample_{i+1:03d}.png"

                success = self.visualize_sample(
                    sample['image_path'],
                    sample['label_path'],
                    output_path
                )

                if success:
                    total_saved += 1

        print("\n" + "=" * 70)
        print("VISUALIZATION COMPLETE")
        print("=" * 70)
        print(f"Total samples saved: {total_saved}")
        print(f"Output directory: {self.output_dir}")
        print("=" * 70)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Visualize dataset samples')
    parser.add_argument('--samples', type=int, default=5,
                       help='Number of samples per class (default: 5)')
    args = parser.parse_args()

    # Run visualization
    visualizer = SampleVisualizer(IMAGE_DIR, LABEL_DIR, OUTPUT_DIR,
                                  samples_per_class=args.samples)
    visualizer.run()

    # Copy to latest
    print("\nCopying to latest...")
    if LATEST_DIR.exists():
        shutil.rmtree(LATEST_DIR)
    shutil.copytree(OUTPUT_DIR, LATEST_DIR)
    print(f"✓ Results copied to: {LATEST_DIR}")


if __name__ == "__main__":
    main()
