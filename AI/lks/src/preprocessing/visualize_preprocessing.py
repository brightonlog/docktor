#!/usr/bin/env python3
"""
Visualize Preprocessing Results
Before/After comparison of image preprocessing
"""

import json
import cv2
import numpy as np
import argparse
import random
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.dataset_config import CATEGORIES, COLORS_RGB
from preprocessing.image_preprocessor import ImagePreprocessor

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
IMAGE_DIR = PROJECT_ROOT / 'data/extracted/01.images'
LABEL_DIR = PROJECT_ROOT / 'data/extracted/02.labels'

# Output directory
TODAY = datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR = PROJECT_ROOT / f'results/preprocessing/{TODAY}'
LATEST_DIR = PROJECT_ROOT / 'results/preprocessing/latest'


class PreprocessingVisualizer:
    def __init__(self, image_dir, label_dir, output_dir, target_size=(1024, 1024)):
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.output_dir = Path(output_dir)
        self.target_size = target_size
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create preprocessor
        self.preprocessor = ImagePreprocessor(
            target_size=target_size,
            normalize=False  # Don't normalize for visualization
        )

    def load_json(self, json_path):
        """Load JSON annotation file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    def draw_annotations(self, image, annotations, metadata=None):
        """
        Draw annotations on image

        Args:
            image: Image (H, W, C) in RGB
            annotations: List of annotation dicts
            metadata: Optional metadata for coordinate transformation

        Returns:
            annotated_image: Image with annotations drawn
        """
        img_rgb = image.copy()

        for ann in annotations:
            cat_id = ann.get('category_id')
            if not cat_id:
                continue

            cat_name = CATEGORIES.get(cat_id, 'Unknown')
            color = COLORS_RGB.get(cat_id, (255, 255, 255))

            # Transform annotation if metadata provided
            if metadata:
                ann = self.preprocessor.preprocess_annotation(ann, metadata)

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
                font_scale = 0.6
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

        return img_rgb

    def create_comparison(self, original_img, processed_img, title_left="Original", title_right="Preprocessed"):
        """
        Create side-by-side comparison image

        Args:
            original_img: Original image (H, W, C)
            processed_img: Processed image (H, W, C)
            title_left: Title for left image
            title_right: Title for right image

        Returns:
            comparison_image: Side-by-side comparison
        """
        # Resize original to match processed for comparison
        h, w = processed_img.shape[:2]
        original_resized = cv2.resize(original_img, (w, h))

        # Add titles
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        thickness = 3
        color = (255, 255, 255)
        bg_color = (0, 0, 0)

        # Add title to original
        original_with_title = original_resized.copy()
        (text_width, text_height), baseline = cv2.getTextSize(
            title_left, font, font_scale, thickness
        )
        cv2.rectangle(original_with_title, (10, 10),
                     (text_width + 30, text_height + 30), bg_color, -1)
        cv2.putText(original_with_title, title_left, (20, text_height + 20),
                   font, font_scale, color, thickness, cv2.LINE_AA)

        # Add title to processed
        processed_with_title = processed_img.copy()
        cv2.rectangle(processed_with_title, (10, 10),
                     (text_width + 30, text_height + 30), bg_color, -1)
        cv2.putText(processed_with_title, title_right, (20, text_height + 20),
                   font, font_scale, color, thickness, cv2.LINE_AA)

        # Concatenate horizontally
        comparison = np.hstack([original_with_title, processed_with_title])

        return comparison

    def visualize_sample(self, image_path, label_path, output_prefix):
        """
        Visualize preprocessing for a single sample

        Args:
            image_path: Path to image
            label_path: Path to label JSON
            output_prefix: Output file prefix

        Returns:
            success: Whether visualization succeeded
        """
        # Load image
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            return False

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # Load labels
        data = self.load_json(label_path)
        if not data or 'annotations' not in data:
            return False

        annotations = data['annotations']

        # 1. Original image with annotations
        original_annotated = self.draw_annotations(img_rgb, annotations)

        # 2. Preprocess image
        processed_img, metadata = self.preprocessor.preprocess_image(img_bgr)
        # Convert to uint8 for visualization
        processed_uint8 = (processed_img * 255).astype(np.uint8)

        # 3. Preprocessed image with annotations
        processed_annotated = self.draw_annotations(processed_uint8, annotations, metadata)

        # 4. Create comparisons
        # Without annotations
        comparison_clean = self.create_comparison(
            img_rgb, processed_uint8,
            f"Original ({img_rgb.shape[1]}x{img_rgb.shape[0]})",
            f"Preprocessed ({processed_uint8.shape[1]}x{processed_uint8.shape[0]})"
        )

        # With annotations
        comparison_annotated = self.create_comparison(
            original_annotated, processed_annotated,
            f"Original + Labels",
            f"Preprocessed + Labels"
        )

        # Save images
        cv2.imwrite(str(output_prefix.parent / f"{output_prefix.name}_comparison.png"),
                   cv2.cvtColor(comparison_clean, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(output_prefix.parent / f"{output_prefix.name}_annotated.png"),
                   cv2.cvtColor(comparison_annotated, cv2.COLOR_RGB2BGR))

        # Save metadata
        metadata_text = (
            f"Original size: {img_rgb.shape[1]}x{img_rgb.shape[0]}\n"
            f"Preprocessed size: {processed_uint8.shape[1]}x{processed_uint8.shape[0]}\n"
            f"Scale factor: {metadata['scale']:.4f}\n"
            f"Padding (w, h): {metadata['pad']}\n"
            f"Number of annotations: {len(annotations)}\n"
        )

        with open(output_prefix.parent / f"{output_prefix.name}_metadata.txt", 'w') as f:
            f.write(metadata_text)

        return True

    def run(self, num_samples_per_category=3):
        """
        Run preprocessing visualization

        Args:
            num_samples_per_category: Number of samples to visualize per category
        """
        print("\n" + "=" * 70)
        print("PREPROCESSING VISUALIZATION")
        print("=" * 70)
        print(f"Target size: {self.target_size}")
        print(f"Samples per category: {num_samples_per_category}")

        # Collect samples by category
        print("\nCollecting samples...")
        category_samples = {}

        for label_path in self.label_dir.rglob('*.json'):
            data = self.load_json(label_path)
            if not data or 'annotations' not in data:
                continue

            # Get categories with bbox and segmentation
            for ann in data['annotations']:
                cat_id = ann.get('category_id')
                if not cat_id:
                    continue

                # Only use samples with bbox and segmentation
                if 'bbox' not in ann or 'segmentation' not in ann:
                    continue
                if not ann['bbox'] or not ann['segmentation']:
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
                    break

        # Process each category
        total_saved = 0

        for cat_id, samples in sorted(category_samples.items()):
            cat_name = CATEGORIES.get(cat_id, f'Unknown-{cat_id}')
            cat_name_clean = cat_name.lower().replace(' ', '_')

            # Random sample
            n_samples = min(num_samples_per_category, len(samples))
            if n_samples == 0:
                continue

            selected = random.sample(samples, n_samples)

            print(f"\n{cat_name}: {n_samples} samples")

            # Create category output directory
            category_dir = self.output_dir / cat_name_clean
            category_dir.mkdir(exist_ok=True)

            # Visualize each sample
            for i, sample in enumerate(selected):
                output_prefix = category_dir / f"{cat_name_clean}_sample_{i+1:03d}"

                success = self.visualize_sample(
                    sample['image_path'],
                    sample['label_path'],
                    output_prefix
                )

                if success:
                    total_saved += 1

        print("\n" + "=" * 70)
        print("VISUALIZATION COMPLETE")
        print("=" * 70)
        print(f"Total samples visualized: {total_saved}")
        print(f"Output directory: {self.output_dir}")
        print("=" * 70)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Visualize preprocessing results')
    parser.add_argument('--samples', type=int, default=3,
                       help='Number of samples per category (default: 3)')
    parser.add_argument('--size', type=int, default=1024,
                       help='Target image size (default: 1024)')
    args = parser.parse_args()

    target_size = (args.size, args.size)

    # Run visualization
    visualizer = PreprocessingVisualizer(
        IMAGE_DIR, LABEL_DIR, OUTPUT_DIR,
        target_size=target_size
    )
    visualizer.run(num_samples_per_category=args.samples)

    # Copy to latest
    print("\nCopying to latest...")
    import shutil
    if LATEST_DIR.exists():
        shutil.rmtree(LATEST_DIR)
    shutil.copytree(OUTPUT_DIR, LATEST_DIR)
    print(f"✓ Results copied to: {LATEST_DIR}")


if __name__ == "__main__":
    main()
