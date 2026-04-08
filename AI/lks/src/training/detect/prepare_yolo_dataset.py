#!/usr/bin/env python3
"""
Prepare YOLO Dataset
Convert JSON annotations to YOLO format and organize dataset
"""

import json
import shutil
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
import sys
import random
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.training_config import (
    IMAGE_DIR, LABEL_DIR, YOLO_DATA_DIR, YOLO_IMAGES_DIR, YOLO_LABELS_DIR,
    TRAIN_RATIO, VAL_RATIO, RANDOM_SEED, MIN_BBOX_AREA,
    CATEGORY_TO_YOLO, CLASS_NAMES, NUM_CLASSES,
    IMAGE_WIDTH, IMAGE_HEIGHT
)
from preprocessing.image_preprocessor import letterbox_resize


class YOLODatasetPreparer:
    """
    Prepare YOLO format dataset from JSON annotations
    """

    def __init__(self,
                 image_dir,
                 label_dir,
                 output_dir,
                 image_size=(1280, 720),
                 train_ratio=0.8,
                 random_seed=42):
        """
        Args:
            image_dir: Path to images directory
            label_dir: Path to labels (JSON) directory
            output_dir: Path to output YOLO dataset directory
            image_size: Target image size (width, height)
            train_ratio: Train split ratio
            random_seed: Random seed for reproducibility
        """
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.output_dir = Path(output_dir)
        self.image_size = image_size
        self.train_ratio = train_ratio
        self.random_seed = random_seed

        # Set random seed
        random.seed(self.random_seed)
        np.random.seed(self.random_seed)

        # Create output directories
        self.train_img_dir = self.output_dir / 'images' / 'train'
        self.val_img_dir = self.output_dir / 'images' / 'val'
        self.train_lbl_dir = self.output_dir / 'labels' / 'train'
        self.val_lbl_dir = self.output_dir / 'labels' / 'val'

        for d in [self.train_img_dir, self.val_img_dir, self.train_lbl_dir, self.val_lbl_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def load_json(self, json_path):
        """Load JSON annotation file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {json_path}: {e}")
            return None

    def bbox_to_yolo_format(self, bbox, img_width, img_height):
        """
        Convert COCO bbox [x, y, w, h] to YOLO format [x_center, y_center, w, h] (normalized)

        Args:
            bbox: [x, y, width, height] in pixels
            img_width: Image width
            img_height: Image height

        Returns:
            [x_center, y_center, width, height] normalized to 0-1
        """
        x, y, w, h = bbox

        # Calculate center
        x_center = x + w / 2
        y_center = y + h / 2

        # Normalize
        x_center_norm = x_center / img_width
        y_center_norm = y_center / img_height
        w_norm = w / img_width
        h_norm = h / img_height

        # Clip to [0, 1]
        x_center_norm = np.clip(x_center_norm, 0, 1)
        y_center_norm = np.clip(y_center_norm, 0, 1)
        w_norm = np.clip(w_norm, 0, 1)
        h_norm = np.clip(h_norm, 0, 1)

        return [x_center_norm, y_center_norm, w_norm, h_norm]

    def process_annotation(self, json_path, img_path, output_img_path, output_label_path):
        """
        Process single annotation file

        Args:
            json_path: Path to JSON annotation
            img_path: Path to image
            output_img_path: Output image path
            output_label_path: Output label txt path

        Returns:
            success: Whether processing succeeded
        """
        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            return False

        original_h, original_w = img.shape[:2]

        # Load annotation
        data = self.load_json(json_path)
        if not data or 'annotations' not in data:
            return False

        annotations = data['annotations']

        # Resize image first (letterbox)
        resized_img, scale, pad = letterbox_resize(
            img,
            target_size=self.image_size,
            fill_value=(114, 114, 114)
        )

        pad_w, pad_h = pad
        target_w, target_h = self.image_size

        # Filter and convert annotations
        yolo_annotations = []

        for ann in annotations:
            cat_id = ann.get('category_id')

            # Skip Normal (101)
            if cat_id == 101:
                continue

            # Check if category is valid
            if cat_id not in CATEGORY_TO_YOLO:
                continue

            # Get YOLO class index
            yolo_class = CATEGORY_TO_YOLO[cat_id]

            # Get bbox
            if 'bbox' not in ann or not ann['bbox']:
                continue

            bbox = ann['bbox']  # [x, y, w, h] in original image

            # Check minimum area
            if bbox[2] * bbox[3] < MIN_BBOX_AREA:
                continue

            # Transform bbox to resized image coordinates
            x, y, w, h = bbox
            # Apply scale and padding
            new_x = x * scale + pad_w
            new_y = y * scale + pad_h
            new_w = w * scale
            new_h = h * scale

            # Check if bbox is within image bounds
            if new_x + new_w <= 0 or new_y + new_h <= 0:
                continue
            if new_x >= target_w or new_y >= target_h:
                continue

            # Clip bbox to image bounds
            new_x = max(0, new_x)
            new_y = max(0, new_y)
            new_w = min(new_w, target_w - new_x)
            new_h = min(new_h, target_h - new_y)

            # Convert to YOLO format (normalized to target size)
            yolo_bbox = self.bbox_to_yolo_format([new_x, new_y, new_w, new_h], target_w, target_h)

            # Add to annotations
            yolo_annotations.append([yolo_class] + yolo_bbox)

        # Skip if no valid annotations
        if len(yolo_annotations) == 0:
            return False

        # Save resized image
        cv2.imwrite(str(output_img_path), resized_img)

        # Save YOLO labels
        with open(output_label_path, 'w') as f:
            for ann in yolo_annotations:
                # Format: <class> <x_center> <y_center> <width> <height>
                line = f"{ann[0]} {ann[1]:.6f} {ann[2]:.6f} {ann[3]:.6f} {ann[4]:.6f}\n"
                f.write(line)

        return True

    def collect_samples(self):
        """
        Collect all valid samples

        Returns:
            samples: List of (image_path, label_path) tuples
        """
        samples = []

        # Walk through label directory
        for label_path in self.label_dir.rglob('*.json'):
            # Find corresponding image
            rel_path = label_path.relative_to(self.label_dir)
            img_path = self.image_dir / rel_path.parent / (label_path.stem + '.jpg')

            if not img_path.exists():
                continue

            # Load and check annotation
            data = self.load_json(label_path)
            if not data or 'annotations' not in data:
                continue

            # Check if has valid defect annotations (not just 101)
            has_defect = False
            for ann in data['annotations']:
                cat_id = ann.get('category_id')
                if cat_id and cat_id != 101 and cat_id in CATEGORY_TO_YOLO:
                    if 'bbox' in ann and ann['bbox']:
                        has_defect = True
                        break

            if has_defect:
                samples.append((img_path, label_path))

        return samples

    def prepare_dataset(self):
        """
        Prepare complete YOLO dataset
        """
        print("\n" + "=" * 70)
        print("PREPARING YOLO DATASET")
        print("=" * 70)
        print(f"Image size: {self.image_size}")
        print(f"Train ratio: {self.train_ratio}")
        print(f"Random seed: {self.random_seed}")

        # Collect samples
        print("\nCollecting samples...")
        samples = self.collect_samples()
        print(f"Found {len(samples)} valid samples")

        if len(samples) == 0:
            print("No valid samples found!")
            return

        # Shuffle samples
        random.shuffle(samples)

        # Split train/val
        n_train = int(len(samples) * self.train_ratio)
        train_samples = samples[:n_train]
        val_samples = samples[n_train:]

        print(f"Train samples: {len(train_samples)}")
        print(f"Val samples: {len(val_samples)}")

        # Process train samples
        print("\nProcessing train samples...")
        train_count = 0
        for img_path, label_path in tqdm(train_samples, desc="Train"):
            output_img_path = self.train_img_dir / img_path.name
            output_label_path = self.train_lbl_dir / (img_path.stem + '.txt')

            success = self.process_annotation(
                label_path, img_path, output_img_path, output_label_path
            )
            if success:
                train_count += 1

        # Process val samples
        print("\nProcessing val samples...")
        val_count = 0
        for img_path, label_path in tqdm(val_samples, desc="Val"):
            output_img_path = self.val_img_dir / img_path.name
            output_label_path = self.val_lbl_dir / (img_path.stem + '.txt')

            success = self.process_annotation(
                label_path, img_path, output_img_path, output_label_path
            )
            if success:
                val_count += 1

        print("\n" + "=" * 70)
        print("DATASET PREPARATION COMPLETE")
        print("=" * 70)
        print(f"Train: {train_count} samples")
        print(f"Val: {val_count} samples")
        print(f"Total: {train_count + val_count} samples")
        print(f"Output directory: {self.output_dir}")
        print("=" * 70)

        # Create data.yaml
        self.create_yaml()

        return train_count, val_count

    def create_yaml(self):
        """
        Create data.yaml for YOLOv8
        """
        yaml_path = self.output_dir / 'data.yaml'

        data_yaml = {
            'path': str(self.output_dir.absolute()),
            'train': 'images/train',
            'val': 'images/val',
            'nc': NUM_CLASSES,
            'names': CLASS_NAMES
        }

        with open(yaml_path, 'w') as f:
            yaml.dump(data_yaml, f, default_flow_style=False, sort_keys=False)

        print(f"\nCreated data.yaml: {yaml_path}")

        # Print content
        print("\ndata.yaml content:")
        print("-" * 70)
        with open(yaml_path, 'r') as f:
            print(f.read())
        print("-" * 70)


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Prepare YOLO dataset')
    parser.add_argument('--width', type=int, default=IMAGE_WIDTH,
                       help=f'Image width (default: {IMAGE_WIDTH})')
    parser.add_argument('--height', type=int, default=IMAGE_HEIGHT,
                       help=f'Image height (default: {IMAGE_HEIGHT})')
    parser.add_argument('--train-ratio', type=float, default=TRAIN_RATIO,
                       help=f'Train ratio (default: {TRAIN_RATIO})')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED,
                       help=f'Random seed (default: {RANDOM_SEED})')
    args = parser.parse_args()

    image_size = (args.width, args.height)

    # Prepare dataset
    preparer = YOLODatasetPreparer(
        image_dir=IMAGE_DIR,
        label_dir=LABEL_DIR,
        output_dir=YOLO_DATA_DIR,
        image_size=image_size,
        train_ratio=args.train_ratio,
        random_seed=args.seed
    )

    preparer.prepare_dataset()


if __name__ == "__main__":
    main()
