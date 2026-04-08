"""
Ship Coating Quality Data Visualization
선박 도장 품질 데이터 시각화 스크립트
"""

import json
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import random
from collections import Counter

# Korean font settings for matplotlib
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows
# plt.rcParams['font.family'] = 'AppleGothic'  # Mac
plt.rcParams['axes.unicode_minus'] = False

# Data paths
IMAGE_DIR = 'Dataset/01.images'
LABEL_DIR = 'Dataset/02.labels'

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

# Colors for each category (BGR format)
COLORS = {
    101: (0, 255, 0),      # Normal - Green
    201: (255, 0, 0),      # Water Spotting - Blue
    202: (0, 165, 255),    # Sagging - Orange
    203: (0, 255, 255),    # Coating Separation - Yellow
    204: (255, 0, 255),    # Pinhole - Magenta
    205: (0, 0, 255),      # Crack - Red
    206: (255, 255, 0),    # Blister - Cyan
    207: (128, 0, 128),    # Foreign Material - Purple
    301: (255, 165, 0),    # Welding Damage - Sky
    302: (0, 128, 255),    # Scratch - Orange-Red
    303: (128, 128, 128)   # Peeling - Gray
}

# Category and subcategory display names
CATEGORY_DIRS = {
    'coating_damage': 'Coating Damage',
    'painting_defect': 'Painting Defect',
    'normal': 'Normal'
}

SUBCATEGORY_DIRS = {
    'peeling': 'Peeling',
    'scratch': 'Scratch',
    'welding_damage': 'Welding Damage',
    'crack': 'Crack',
    'coating_separation': 'Coating Separation',
    'blister': 'Blister',
    'water_spotting': 'Water Spotting',
    'foreign_material': 'Foreign Material',
    'pinhole': 'Pinhole',
    'sagging': 'Sagging',
    'deck': 'Deck',
    'engine_room': 'Engine Room',
    'stern': 'Stern',
    'bow': 'Bow',
    'cabin': 'Cabin',
    'engine_cover': 'Engine Cover',
    'outer_plate': 'Outer Plate',
    'tank': 'Tank',
    'pipe': 'Pipe',
    'hatch_cover': 'Hatch Cover'
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


def visualize_annotation(image_path, json_path, show_segmentation=True, show_bbox=True, use_korean=False):
    """
    Visualize annotations on image

    Args:
        image_path: Image file path
        json_path: JSON annotation file path
        show_segmentation: Whether to show segmentation polygons
        show_bbox: Whether to show bounding boxes
        use_korean: Use Korean labels (True) or English (False)
    """
    # Check image path
    if not os.path.exists(image_path):
        print(f"[ERROR] Image file not found: {image_path}")
        return

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"[ERROR] Cannot load image: {image_path}")
        return
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Load JSON
    data = load_json(json_path)

    # Prepare visualization
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))

    # Original image
    axes[0].imshow(img)
    axes[0].set_title('Original Image', fontsize=16)
    axes[0].axis('off')

    # Annotation overlay image
    overlay = img.copy()

    # Always use English for labels to avoid encoding issues with OpenCV
    cat_dict = CATEGORIES

    # Process each annotation
    for ann in data['annotations']:
        category_id = ann['category_id']
        category_name = cat_dict.get(category_id, 'Unknown')
        color = COLORS.get(category_id, (255, 255, 255))

        # Draw Segmentation
        if show_segmentation and 'segmentation' in ann:
            seg = ann['segmentation']
            # Reshape polygon points
            points = np.array(seg).reshape(-1, 2).astype(np.int32)

            # Semi-transparent polygon overlay
            overlay_temp = overlay.copy()
            cv2.fillPoly(overlay_temp, [points], color)
            cv2.addWeighted(overlay_temp, 0.4, overlay, 0.6, 0, overlay)

            # Polygon border
            cv2.polylines(overlay, [points], True, color, 3)

        # Draw Bounding Box
        if show_bbox and 'bbox' in ann:
            x, y, w, h = [int(v) for v in ann['bbox']]
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
            (text_width, text_height), _ = cv2.getTextSize(
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

    # Display annotation overlay image
    axes[1].imshow(overlay)
    axes[1].set_title('Labeling Visualization', fontsize=16)
    axes[1].axis('off')

    # Display metadata
    info_text = f"File: {data['images'][0]['file_name']}\n"
    info_text += f"Resolution: {data['images'][0]['width']} x {data['images'][0]['height']}\n"
    info_text += f"Annotations: {len(data['annotations'])}\n"

    for i, ann in enumerate(data['annotations'], 1):
        cat_name = cat_dict.get(ann['category_id'], 'Unknown')
        info_text += f"  #{i} {cat_name}"
        if 'area' in ann:
            info_text += f" (Area: {ann['area']:.0f}px²)"
        info_text += "\n"

    plt.figtext(0.5, 0.01, info_text, ha='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    plt.show()


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
                    'json_path': json_path
                })

    return samples


def print_dataset_statistics(samples):
    """Print dataset statistics"""
    print("=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    print(f"\nTotal samples: {len(samples)}")

    # Category statistics
    category_counts = Counter([s['category_display'] for s in samples])
    subcategory_counts = Counter([f"{s['category_display']}/{s['subcategory_display']}" for s in samples])

    print("\n=== Category Distribution ===")
    for cat, count in category_counts.items():
        print(f"{cat}: {count} samples")

    print("\n=== Subcategory Distribution ===")
    for subcat, count in sorted(subcategory_counts.items()):
        print(f"{subcat}: {count} samples")

    print("=" * 60)


def visualize_random_samples(samples, category=None, subcategory=None, num_samples=3, use_korean=False):
    """
    Visualize random samples from specified category

    Args:
        samples: List of all samples
        category: Category filter (e.g., 'coating_damage', 'painting_defect', 'normal')
        subcategory: Subcategory filter (e.g., 'crack', 'peeling')
        num_samples: Number of samples to visualize
        use_korean: Use Korean labels
    """
    filtered = samples

    if category:
        filtered = [s for s in filtered if s['category'] == category]

    if subcategory:
        filtered = [s for s in filtered if s['subcategory'] == subcategory]

    if not filtered:
        print(f"[WARNING] No samples found for category={category}, subcategory={subcategory}")
        return

    print(f"\nVisualizing {min(num_samples, len(filtered))} samples from {len(filtered)} available...")

    for sample in random.sample(filtered, min(num_samples, len(filtered))):
        print(f"\nCategory: {sample['category_display']}/{sample['subcategory_display']}")
        print(f"Image: {os.path.basename(sample['image_path'])}")
        visualize_annotation(sample['image_path'], sample['json_path'], use_korean=use_korean)


def visualize_all_defect_types(samples, num_per_type=1, use_korean=False):
    """Visualize one sample from each defect type"""
    print("\n" + "=" * 60)
    print("VISUALIZING ALL DEFECT TYPES")
    print("=" * 60)

    # Coating damage types
    print("\n--- COATING DAMAGE ---")
    for subcat in ['peeling', 'scratch', 'welding_damage']:
        filtered = [s for s in samples if s['category'] == 'coating_damage' and s['subcategory'] == subcat]
        if filtered:
            print(f"\n{SUBCATEGORY_DIRS.get(subcat, subcat)}:")
            visualize_random_samples(samples, 'coating_damage', subcat, num_per_type, use_korean)

    # Painting defect types
    print("\n--- PAINTING DEFECTS ---")
    for subcat in ['crack', 'coating_separation', 'blister', 'water_spotting',
                   'foreign_material', 'pinhole', 'sagging']:
        filtered = [s for s in samples if s['category'] == 'painting_defect' and s['subcategory'] == subcat]
        if filtered:
            print(f"\n{SUBCATEGORY_DIRS.get(subcat, subcat)}:")
            visualize_random_samples(samples, 'painting_defect', subcat, num_per_type, use_korean)

    # Normal samples
    print("\n--- NORMAL SAMPLES ---")
    normal_samples = [s for s in samples if s['category'] == 'normal']
    if normal_samples:
        visualize_random_samples(samples, 'normal', None, 1, use_korean)


def main():
    """Main function"""
    print("=" * 60)
    print("Ship Coating Quality Data Visualization")
    print("=" * 60)

    # Check if dataset exists
    if not os.path.exists(IMAGE_DIR) or not os.path.exists(LABEL_DIR):
        print(f"\n[ERROR] Dataset not found!")
        print(f"Expected paths:")
        print(f"  - Images: {IMAGE_DIR}")
        print(f"  - Labels: {LABEL_DIR}")
        print(f"\nPlease run 'python rename_to_english.py' first to create the English dataset.")
        return

    # Load all samples
    print("\nLoading dataset...")
    samples = get_all_samples()

    if not samples:
        print("[ERROR] No samples found!")
        return

    # Print statistics
    print_dataset_statistics(samples)

    # Interactive menu
    while True:
        print("\n" + "=" * 60)
        print("MENU")
        print("=" * 60)
        print("1. Visualize random samples (any category)")
        print("2. Visualize coating damage samples")
        print("3. Visualize painting defect samples")
        print("4. Visualize normal samples")
        print("5. Visualize all defect types (one sample each)")
        print("6. Visualize specific subcategory")
        print("7. Print dataset statistics")
        print("0. Exit")
        print("=" * 60)

        choice = input("\nEnter your choice (0-7): ").strip()

        if choice == '0':
            print("Exiting...")
            break

        elif choice == '1':
            num = input("How many samples? (default: 3): ").strip()
            num = int(num) if num.isdigit() else 3
            visualize_random_samples(samples, num_samples=num)

        elif choice == '2':
            num = input("How many samples? (default: 3): ").strip()
            num = int(num) if num.isdigit() else 3
            visualize_random_samples(samples, category='coating_damage', num_samples=num)

        elif choice == '3':
            num = input("How many samples? (default: 3): ").strip()
            num = int(num) if num.isdigit() else 3
            visualize_random_samples(samples, category='painting_defect', num_samples=num)

        elif choice == '4':
            num = input("How many samples? (default: 3): ").strip()
            num = int(num) if num.isdigit() else 3
            visualize_random_samples(samples, category='normal', num_samples=num)

        elif choice == '5':
            visualize_all_defect_types(samples)

        elif choice == '6':
            print("\nAvailable subcategories:")
            subcats = sorted(set([s['subcategory'] for s in samples]))
            for i, subcat in enumerate(subcats, 1):
                print(f"  {i}. {subcat} ({SUBCATEGORY_DIRS.get(subcat, subcat)})")

            subcat_choice = input("\nEnter subcategory name: ").strip()
            if subcat_choice in subcats:
                num = input("How many samples? (default: 3): ").strip()
                num = int(num) if num.isdigit() else 3
                visualize_random_samples(samples, subcategory=subcat_choice, num_samples=num)
            else:
                print("[ERROR] Invalid subcategory!")

        elif choice == '7':
            print_dataset_statistics(samples)

        else:
            print("[ERROR] Invalid choice!")


if __name__ == "__main__":
    main()
