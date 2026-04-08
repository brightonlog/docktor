"""
Ship Coating Quality Data Visualization - Save All
모든 데이터를 시각화하여 폴더로 저장하는 스크립트
"""

import json
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from tqdm import tqdm

# Korean font settings for matplotlib
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows
# plt.rcParams['font.family'] = 'AppleGothic'  # Mac
plt.rcParams['axes.unicode_minus'] = False

# Data paths
IMAGE_DIR = 'Dataset/01.images'
LABEL_DIR = 'Dataset/02.labels'
OUTPUT_DIR = 'Visualized_Dataset'

# Category definitions
CATEGORIES = {
    101: 'Normal',
    201: 'Water Spotting',
    202: 'Sagging',
    203: 'Coating Separation',
    204: 'Pinhole',
    205: 'Crack',
    206: 'Blister',
    207: 'Foreign Material',
    301: 'Welding Damage',
    302: 'Scratch',
    303: 'Peeling'
}

CATEGORIES_KR = {
    101: '정상',
    201: '워터스포팅',
    202: '흐름',
    203: '도막분리',
    204: '핀홀',
    205: '균열',
    206: '부풀음',
    207: '이물질포함',
    301: '용접손상',
    302: '스크래치',
    303: '도막떨어짐'
}

# Colors for each category (RGB format for matplotlib)
COLORS_RGB = {
    101: (0, 255, 0),      # Normal - Green
    201: (0, 0, 255),      # Water Spotting - Blue
    202: (255, 165, 0),    # Sagging - Orange
    203: (255, 255, 0),    # Coating Separation - Yellow
    204: (255, 0, 255),    # Pinhole - Magenta
    205: (255, 0, 0),      # Crack - Red
    206: (0, 255, 255),    # Blister - Cyan
    207: (128, 0, 128),    # Foreign Material - Purple
    301: (0, 165, 255),    # Welding Damage - Sky
    302: (255, 128, 0),    # Scratch - Orange-Red
    303: (128, 128, 128)   # Peeling - Gray
}

# Category and subcategory display names
CATEGORY_DIRS = {
    'coating_damage': 'Coating_Damage',
    'painting_defect': 'Painting_Defect',
    'normal': 'Normal'
}

SUBCATEGORY_DIRS = {
    'peeling': 'Peeling',
    'scratch': 'Scratch',
    'welding_damage': 'Welding_Damage',
    'crack': 'Crack',
    'coating_separation': 'Coating_Separation',
    'blister': 'Blister',
    'water_spotting': 'Water_Spotting',
    'foreign_material': 'Foreign_Material',
    'pinhole': 'Pinhole',
    'sagging': 'Sagging',
    'deck': 'Deck',
    'engine_room': 'Engine_Room',
    'stern': 'Stern',
    'bow': 'Bow',
    'cabin': 'Cabin',
    'engine_cover': 'Engine_Cover',
    'outer_plate': 'Outer_Plate',
    'tank': 'Tank',
    'pipe': 'Pipe',
    'hatch_cover': 'Hatch_Cover'
}

# Korean to English part name mapping
PART_NAME_MAPPING = {
    '갑판': 'Deck',
    '기관실': 'Engine Room',
    '선미': 'Stern',
    '선수': 'Bow',
    '선실': 'Cabin',
    '엔진커버': 'Engine Cover',
    '외판': 'Outer Plate',
    '탱크': 'Tank',
    '파이프': 'Pipe',
    '해치커버': 'Hatch Cover',
    '선체': 'Hull',
    '갑판실': 'Deck House',
    '기타': 'Other'
}


def load_json(json_path):
    """Load JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def visualize_and_save_annotation(image_path, json_path, output_path, show_segmentation=True, show_bbox=True, use_korean=False):
    """
    Visualize annotations on image and save to file

    Args:
        image_path: Image file path
        json_path: JSON annotation file path
        output_path: Output image path
        show_segmentation: Whether to show segmentation polygons
        show_bbox: Whether to show bounding boxes
        use_korean: Use Korean labels (True) or English (False)

    Returns:
        bool: Success or failure
    """
    # Check image path
    if not os.path.exists(image_path):
        print(f"[ERROR] Image file not found: {image_path}")
        return False

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"[ERROR] Cannot load image: {image_path}")
        return False
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Load JSON
    try:
        data = load_json(json_path)
    except Exception as e:
        print(f"[ERROR] Cannot load JSON: {json_path}, Error: {e}")
        return False

    # Create figure with higher DPI for better quality
    fig = plt.figure(figsize=(16, 8), dpi=150)

    # Create two subplots
    ax1 = plt.subplot(1, 2, 1)
    ax2 = plt.subplot(1, 2, 2)

    # Original image
    ax1.imshow(img)
    ax1.set_title('Original Image', fontsize=14, fontweight='bold')
    ax1.axis('off')

    # Annotation overlay image
    overlay = img.copy()

    # Always use English for labels to avoid encoding issues with OpenCV
    cat_dict = CATEGORIES

    # Process each annotation
    annotations_info = []
    for ann in data['annotations']:
        category_id = ann['category_id']
        category_name = cat_dict.get(category_id, 'Unknown')
        color = COLORS_RGB.get(category_id, (255, 255, 255))

        # Draw Segmentation
        if show_segmentation and 'segmentation' in ann and ann['segmentation']:
            seg = ann['segmentation']
            # Reshape polygon points
            points = np.array(seg).reshape(-1, 2).astype(np.int32)

            # Semi-transparent polygon overlay
            overlay_temp = overlay.copy()
            cv2.fillPoly(overlay_temp, [points], color)
            overlay = cv2.addWeighted(overlay_temp, 0.3, overlay, 0.7, 0)

            # Polygon border (BGR for cv2)
            cv2.polylines(overlay, [points], True, color, 2)

        # Draw Bounding Box
        if show_bbox and 'bbox' in ann and ann['bbox']:
            x, y, w, h = [int(v) for v in ann['bbox']]

            # Draw rectangle
            cv2.rectangle(overlay, (x, y), (x+w, y+h), color, 3)

            # Prepare label text
            label = f"{category_name}"
            if 'attributes' in ann and 'part' in ann['attributes']:
                part_name = ann['attributes']['part']
                # Convert Korean part name to English
                part_name_en = PART_NAME_MAPPING.get(part_name, part_name)
                label += f" ({part_name_en})"

            # Calculate text size
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, thickness
            )

            # Draw text background (filled rectangle)
            padding = 5
            cv2.rectangle(
                overlay,
                (x, y - text_height - padding * 2),
                (x + text_width + padding * 2, y),
                color,
                -1  # Filled
            )

            # Draw text
            cv2.putText(
                overlay,
                label,
                (x + padding, y - padding),
                font,
                font_scale,
                (255, 255, 255),  # White text
                thickness,
                cv2.LINE_AA
            )

        # Store annotation info
        annotations_info.append({
            'category_id': category_id,
            'category_name': category_name,
            'area': ann.get('area', 0)
        })

    # Display annotation overlay image
    ax2.imshow(overlay)
    ax2.set_title('Labeled Image', fontsize=14, fontweight='bold')
    ax2.axis('off')

    # Add metadata text below the images
    info_text = f"File: {data['images'][0]['file_name']}\n"
    info_text += f"Resolution: {data['images'][0]['width']} x {data['images'][0]['height']}\n"
    info_text += f"Annotations: {len(data['annotations'])}\n"

    for i, ann_info in enumerate(annotations_info, 1):
        info_text += f"  #{i} {ann_info['category_name']}"
        if ann_info['area'] > 0:
            info_text += f" (Area: {ann_info['area']:.0f}px²)"
        info_text += "\n"

    plt.figtext(0.5, 0.02, info_text, ha='center', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)

    # Save figure
    try:
        # Create output directory if not exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, bbox_inches='tight', dpi=150)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"[ERROR] Cannot save image: {output_path}, Error: {e}")
        plt.close(fig)
        return False


def get_all_samples():
    """Collect all sample file paths"""
    samples = []

    for category in ['coating_damage', 'painting_defect', 'normal']:
        label_category_dir = os.path.join(LABEL_DIR, category)

        if not os.path.exists(label_category_dir):
            continue

        for subcategory in os.listdir(label_category_dir):
            subcategory_dir = os.path.join(label_category_dir, subcategory)

            if not os.path.isdir(subcategory_dir):
                continue

            for json_file in os.listdir(subcategory_dir):
                if not json_file.endswith('.json'):
                    continue

                json_path = os.path.join(subcategory_dir, json_file)

                # Find image file
                image_filename = json_file.replace('.json', '')
                # Try JPG or jpg extension
                image_path_jpg = os.path.join(IMAGE_DIR, category, subcategory, image_filename + '.JPG')
                image_path_jpg_lower = os.path.join(IMAGE_DIR, category, subcategory, image_filename + '.jpg')

                if os.path.exists(image_path_jpg):
                    image_path = image_path_jpg
                elif os.path.exists(image_path_jpg_lower):
                    image_path = image_path_jpg_lower
                else:
                    continue

                samples.append({
                    'category': category,
                    'category_display': CATEGORY_DIRS.get(category, category),
                    'subcategory': subcategory,
                    'subcategory_display': SUBCATEGORY_DIRS.get(subcategory, subcategory),
                    'image_path': image_path,
                    'json_path': json_path,
                    'filename': image_filename
                })

    return samples


def process_all_samples(use_korean=False):
    """Process and save all samples"""
    print("=" * 60)
    print("Processing All Samples")
    print("=" * 60)

    # Load all samples
    print("\nLoading dataset...")
    samples = get_all_samples()

    if not samples:
        print("[ERROR] No samples found!")
        return

    print(f"Total samples to process: {len(samples)}")

    # Statistics
    category_counts = Counter([s['category_display'] for s in samples])
    print("\n=== Category Distribution ===")
    for cat, count in category_counts.items():
        print(f"{cat}: {count} samples")

    # Process each sample
    print(f"\nSaving visualizations to: {OUTPUT_DIR}")
    print("Processing...")

    success_count = 0
    error_count = 0

    for sample in tqdm(samples, desc="Visualizing samples"):
        # Create output path
        output_subdir = os.path.join(
            OUTPUT_DIR,
            sample['category_display'],
            sample['subcategory_display']
        )
        output_filename = f"{sample['filename']}_labeled.png"
        output_path = os.path.join(output_subdir, output_filename)

        # Visualize and save
        success = visualize_and_save_annotation(
            sample['image_path'],
            sample['json_path'],
            output_path,
            use_korean=use_korean
        )

        if success:
            success_count += 1
        else:
            error_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total processed: {len(samples)}")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("=" * 60)


def main():
    """Main function"""
    print("=" * 60)
    print("Ship Coating Quality Data - Visualize All")
    print("=" * 60)

    # Check if dataset exists
    if not os.path.exists(IMAGE_DIR) or not os.path.exists(LABEL_DIR):
        print(f"\n[ERROR] Dataset not found!")
        print(f"Expected paths:")
        print(f"  - Images: {IMAGE_DIR}")
        print(f"  - Labels: {LABEL_DIR}")
        print(f"\nPlease run 'python rename_to_english.py' first to create the English dataset.")
        return

    # Ask user preference
    print("\nThis script will visualize and save all dataset samples.")
    print(f"Output directory: {OUTPUT_DIR}")
    print("Note: Labels will be displayed in English to avoid encoding issues.")

    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    # Process all samples
    process_all_samples(use_korean=False)


if __name__ == "__main__":
    main()
