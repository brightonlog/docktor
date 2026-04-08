"""
Preprocessing Analysis for Image Size Strategy
Analyzes image dimensions, defect sizes, and distributions to determine optimal preprocessing strategy
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import numpy as np
from tqdm import tqdm
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.dataset_config import CATEGORIES, CATEGORIES_KR


def load_json_files(labels_dir):
    """Load all JSON files from the labels directory"""
    json_files = []
    for root, dirs, files in os.walk(labels_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files


def analyze_single_file(json_path):
    """Extract image and annotation information from a single JSON file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract image information
        if 'images' not in data or len(data['images']) == 0:
            return None

        image_info = data['images'][0]
        image_width = image_info['width']
        image_height = image_info['height']
        image_area = image_width * image_height
        aspect_ratio = image_width / image_height

        # Extract annotations
        annotations = []
        if 'annotations' in data:
            for ann in data['annotations']:
                ann_data = {
                    'category_id': ann.get('category_id'),
                    'bbox': ann.get('bbox'),
                    'area': ann.get('area'),
                    'segmentation': ann.get('segmentation')
                }

                # Calculate bbox area if not provided
                if ann_data['bbox'] and not ann_data['area']:
                    x, y, w, h = ann_data['bbox']
                    ann_data['area'] = w * h

                annotations.append(ann_data)

        return {
            'file_path': json_path,
            'width': image_width,
            'height': image_height,
            'area': image_area,
            'aspect_ratio': aspect_ratio,
            'annotations': annotations
        }

    except Exception as e:
        print(f"Error processing {json_path}: {e}")
        return None


def calculate_defect_size_category(defect_area, image_area):
    """Categorize defect size relative to image area"""
    ratio = defect_area / image_area

    if ratio < 0.001:  # < 0.1%
        return 'very_small'
    elif ratio < 0.01:  # 0.1% - 1%
        return 'small'
    elif ratio < 0.05:  # 1% - 5%
        return 'medium'
    elif ratio < 0.15:  # 5% - 15%
        return 'large'
    else:  # > 15%
        return 'very_large'


def analyze_dataset(labels_dir, output_dir):
    """Perform comprehensive dataset analysis"""

    print("Loading JSON files...")
    json_files = load_json_files(labels_dir)
    print(f"Found {len(json_files)} JSON files")

    # Storage for statistics
    image_dimensions = []
    image_areas = []
    aspect_ratios = []

    # Category-wise statistics
    category_defect_areas = defaultdict(list)
    category_defect_counts = defaultdict(int)
    category_bbox_widths = defaultdict(list)
    category_bbox_heights = defaultdict(list)
    category_defect_coverage = defaultdict(list)
    category_size_distribution = defaultdict(lambda: defaultdict(int))

    # Overall defect statistics
    all_defect_areas = []
    all_bbox_widths = []
    all_bbox_heights = []
    defect_coverage_ratios = []

    # Image size distribution
    size_distribution = defaultdict(int)

    print("Analyzing dataset...")
    for json_path in tqdm(json_files):
        result = analyze_single_file(json_path)
        if result is None:
            continue

        # Image statistics
        image_dimensions.append((result['width'], result['height']))
        image_areas.append(result['area'])
        aspect_ratios.append(result['aspect_ratio'])

        # Categorize image size
        img_res = f"{result['width']}x{result['height']}"
        size_distribution[img_res] += 1

        # Annotation statistics
        for ann in result['annotations']:
            category_id = ann['category_id']

            if ann['bbox']:
                x, y, w, h = ann['bbox']
                bbox_area = ann['area'] if ann['area'] else w * h

                # Category-wise statistics
                category_defect_areas[category_id].append(bbox_area)
                category_defect_counts[category_id] += 1
                category_bbox_widths[category_id].append(w)
                category_bbox_heights[category_id].append(h)

                # Defect coverage
                coverage = bbox_area / result['area']
                category_defect_coverage[category_id].append(coverage)
                defect_coverage_ratios.append(coverage)

                # Size categorization
                size_cat = calculate_defect_size_category(bbox_area, result['area'])
                category_size_distribution[category_id][size_cat] += 1

                # Overall statistics
                all_defect_areas.append(bbox_area)
                all_bbox_widths.append(w)
                all_bbox_heights.append(h)

    # Calculate statistics
    print("\nCalculating statistics...")

    stats = {
        'total_images': len(json_files),
        'total_annotations': sum(category_defect_counts.values()),

        # Image dimension statistics
        'image_width_stats': {
            'min': min([w for w, h in image_dimensions]),
            'max': max([w for w, h in image_dimensions]),
            'mean': np.mean([w for w, h in image_dimensions]),
            'median': np.median([w for w, h in image_dimensions]),
            'std': np.std([w for w, h in image_dimensions]),
            'percentile_25': np.percentile([w for w, h in image_dimensions], 25),
            'percentile_75': np.percentile([w for w, h in image_dimensions], 75),
            'percentile_95': np.percentile([w for w, h in image_dimensions], 95),
        },

        'image_height_stats': {
            'min': min([h for w, h in image_dimensions]),
            'max': max([h for w, h in image_dimensions]),
            'mean': np.mean([h for w, h in image_dimensions]),
            'median': np.median([h for w, h in image_dimensions]),
            'std': np.std([h for w, h in image_dimensions]),
            'percentile_25': np.percentile([h for w, h in image_dimensions], 25),
            'percentile_75': np.percentile([h for w, h in image_dimensions], 75),
            'percentile_95': np.percentile([h for w, h in image_dimensions], 95),
        },

        'aspect_ratio_stats': {
            'min': min(aspect_ratios),
            'max': max(aspect_ratios),
            'mean': np.mean(aspect_ratios),
            'median': np.median(aspect_ratios),
            'std': np.std(aspect_ratios),
        },

        'image_area_stats': {
            'min': min(image_areas),
            'max': max(image_areas),
            'mean': np.mean(image_areas),
            'median': np.median(image_areas),
        },

        # Defect statistics
        'overall_defect_stats': {
            'total_defects': len(all_defect_areas),
            'defect_area_min': min(all_defect_areas) if all_defect_areas else 0,
            'defect_area_max': max(all_defect_areas) if all_defect_areas else 0,
            'defect_area_mean': np.mean(all_defect_areas) if all_defect_areas else 0,
            'defect_area_median': np.median(all_defect_areas) if all_defect_areas else 0,
            'defect_area_std': np.std(all_defect_areas) if all_defect_areas else 0,
            'defect_area_percentile_5': np.percentile(all_defect_areas, 5) if all_defect_areas else 0,
            'defect_area_percentile_25': np.percentile(all_defect_areas, 25) if all_defect_areas else 0,
            'defect_area_percentile_75': np.percentile(all_defect_areas, 75) if all_defect_areas else 0,
            'defect_area_percentile_95': np.percentile(all_defect_areas, 95) if all_defect_areas else 0,
            'bbox_width_min': min(all_bbox_widths) if all_bbox_widths else 0,
            'bbox_width_max': max(all_bbox_widths) if all_bbox_widths else 0,
            'bbox_width_mean': np.mean(all_bbox_widths) if all_bbox_widths else 0,
            'bbox_width_median': np.median(all_bbox_widths) if all_bbox_widths else 0,
            'bbox_height_min': min(all_bbox_heights) if all_bbox_heights else 0,
            'bbox_height_max': max(all_bbox_heights) if all_bbox_heights else 0,
            'bbox_height_mean': np.mean(all_bbox_heights) if all_bbox_heights else 0,
            'bbox_height_median': np.median(all_bbox_heights) if all_bbox_heights else 0,
        },

        # Defect coverage statistics
        'defect_coverage_stats': {
            'min': min(defect_coverage_ratios) if defect_coverage_ratios else 0,
            'max': max(defect_coverage_ratios) if defect_coverage_ratios else 0,
            'mean': np.mean(defect_coverage_ratios) if defect_coverage_ratios else 0,
            'median': np.median(defect_coverage_ratios) if defect_coverage_ratios else 0,
            'percentile_25': np.percentile(defect_coverage_ratios, 25) if defect_coverage_ratios else 0,
            'percentile_75': np.percentile(defect_coverage_ratios, 75) if defect_coverage_ratios else 0,
            'percentile_95': np.percentile(defect_coverage_ratios, 95) if defect_coverage_ratios else 0,
        },

        # Image size distribution
        'image_size_distribution': dict(sorted(size_distribution.items(),
                                              key=lambda x: x[1], reverse=True)),

        # Category-wise statistics
        'category_statistics': {}
    }

    # Calculate category-wise statistics
    for cat_id in category_defect_areas.keys():
        cat_name = CATEGORIES.get(cat_id, f'Unknown_{cat_id}')
        cat_name_kr = CATEGORIES_KR.get(cat_id, f'Unknown_{cat_id}')

        areas = category_defect_areas[cat_id]
        widths = category_bbox_widths[cat_id]
        heights = category_bbox_heights[cat_id]
        coverages = category_defect_coverage[cat_id]

        stats['category_statistics'][cat_id] = {
            'category_name': cat_name,
            'category_name_kr': cat_name_kr,
            'count': category_defect_counts[cat_id],
            'area_stats': {
                'min': min(areas),
                'max': max(areas),
                'mean': np.mean(areas),
                'median': np.median(areas),
                'std': np.std(areas),
                'percentile_5': np.percentile(areas, 5),
                'percentile_25': np.percentile(areas, 25),
                'percentile_75': np.percentile(areas, 75),
                'percentile_95': np.percentile(areas, 95),
            },
            'bbox_width_stats': {
                'min': min(widths),
                'max': max(widths),
                'mean': np.mean(widths),
                'median': np.median(widths),
            },
            'bbox_height_stats': {
                'min': min(heights),
                'max': max(heights),
                'mean': np.mean(heights),
                'median': np.median(heights),
            },
            'coverage_stats': {
                'min': min(coverages),
                'max': max(coverages),
                'mean': np.mean(coverages),
                'median': np.median(coverages),
                'percentile_95': np.percentile(coverages, 95),
            },
            'size_distribution': dict(category_size_distribution[cat_id])
        }

    return stats


def generate_report(stats, output_path):
    """Generate a comprehensive text report with recommendations"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PREPROCESSING STRATEGY ANALYSIS REPORT\n")
        f.write("Image Size and Defect Analysis for Ship Coating Quality Dataset\n")
        f.write("=" * 80 + "\n\n")

        # Dataset Overview
        f.write("DATASET OVERVIEW\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Images: {stats['total_images']:,}\n")
        f.write(f"Total Annotations: {stats['total_annotations']:,}\n")
        f.write(f"Average Annotations per Image: {stats['total_annotations'] / stats['total_images']:.2f}\n\n")

        # Image Dimension Statistics
        f.write("IMAGE DIMENSION STATISTICS\n")
        f.write("-" * 80 + "\n")

        f.write("\nWidth Statistics:\n")
        for key, value in stats['image_width_stats'].items():
            f.write(f"  {key}: {value:.2f} pixels\n")

        f.write("\nHeight Statistics:\n")
        for key, value in stats['image_height_stats'].items():
            f.write(f"  {key}: {value:.2f} pixels\n")

        f.write("\nAspect Ratio Statistics:\n")
        for key, value in stats['aspect_ratio_stats'].items():
            f.write(f"  {key}: {value:.4f}\n")

        f.write("\nImage Area Statistics:\n")
        for key, value in stats['image_area_stats'].items():
            f.write(f"  {key}: {value:,.0f} pixels²\n")

        # Image Size Distribution
        f.write("\n\nIMAGE SIZE DISTRIBUTION (Top 10)\n")
        f.write("-" * 80 + "\n")
        for i, (size, count) in enumerate(list(stats['image_size_distribution'].items())[:10]):
            percentage = (count / stats['total_images']) * 100
            f.write(f"{i+1}. {size}: {count:,} images ({percentage:.2f}%)\n")

        # Overall Defect Statistics
        f.write("\n\nOVERALL DEFECT STATISTICS\n")
        f.write("-" * 80 + "\n")

        defect_stats = stats['overall_defect_stats']
        f.write(f"\nTotal Defects: {defect_stats['total_defects']:,}\n")

        f.write("\nDefect Area Statistics (pixels²):\n")
        f.write(f"  Min: {defect_stats['defect_area_min']:,.2f}\n")
        f.write(f"  5th Percentile: {defect_stats['defect_area_percentile_5']:,.2f}\n")
        f.write(f"  25th Percentile: {defect_stats['defect_area_percentile_25']:,.2f}\n")
        f.write(f"  Median: {defect_stats['defect_area_median']:,.2f}\n")
        f.write(f"  Mean: {defect_stats['defect_area_mean']:,.2f}\n")
        f.write(f"  75th Percentile: {defect_stats['defect_area_percentile_75']:,.2f}\n")
        f.write(f"  95th Percentile: {defect_stats['defect_area_percentile_95']:,.2f}\n")
        f.write(f"  Max: {defect_stats['defect_area_max']:,.2f}\n")
        f.write(f"  Std Dev: {defect_stats['defect_area_std']:,.2f}\n")

        f.write("\nBounding Box Width Statistics (pixels):\n")
        f.write(f"  Min: {defect_stats['bbox_width_min']:.2f}\n")
        f.write(f"  Mean: {defect_stats['bbox_width_mean']:.2f}\n")
        f.write(f"  Median: {defect_stats['bbox_width_median']:.2f}\n")
        f.write(f"  Max: {defect_stats['bbox_width_max']:.2f}\n")

        f.write("\nBounding Box Height Statistics (pixels):\n")
        f.write(f"  Min: {defect_stats['bbox_height_min']:.2f}\n")
        f.write(f"  Mean: {defect_stats['bbox_height_mean']:.2f}\n")
        f.write(f"  Median: {defect_stats['bbox_height_median']:.2f}\n")
        f.write(f"  Max: {defect_stats['bbox_height_max']:.2f}\n")

        # Defect Coverage Statistics
        f.write("\n\nDEFECT COVERAGE STATISTICS (Defect Area / Image Area)\n")
        f.write("-" * 80 + "\n")
        coverage = stats['defect_coverage_stats']
        f.write(f"Min: {coverage['min']*100:.4f}%\n")
        f.write(f"25th Percentile: {coverage['percentile_25']*100:.4f}%\n")
        f.write(f"Median: {coverage['median']*100:.4f}%\n")
        f.write(f"Mean: {coverage['mean']*100:.4f}%\n")
        f.write(f"75th Percentile: {coverage['percentile_75']*100:.4f}%\n")
        f.write(f"95th Percentile: {coverage['percentile_95']*100:.4f}%\n")
        f.write(f"Max: {coverage['max']*100:.4f}%\n")

        # Category-wise Statistics
        f.write("\n\nCATEGORY-WISE STATISTICS\n")
        f.write("=" * 80 + "\n")

        # Sort categories by count
        sorted_categories = sorted(stats['category_statistics'].items(),
                                   key=lambda x: x[1]['count'], reverse=True)

        for cat_id, cat_stats in sorted_categories:
            f.write(f"\nCategory: {cat_stats['category_name']} ({cat_stats['category_name_kr']}) [ID: {cat_id}]\n")
            f.write("-" * 80 + "\n")
            f.write(f"Count: {cat_stats['count']:,}\n")

            f.write("\nDefect Area Statistics (pixels²):\n")
            for key, value in cat_stats['area_stats'].items():
                f.write(f"  {key}: {value:,.2f}\n")

            f.write("\nBounding Box Dimensions:\n")
            f.write("  Width:\n")
            for key, value in cat_stats['bbox_width_stats'].items():
                f.write(f"    {key}: {value:.2f} pixels\n")
            f.write("  Height:\n")
            for key, value in cat_stats['bbox_height_stats'].items():
                f.write(f"    {key}: {value:.2f} pixels\n")

            f.write("\nDefect Coverage (% of image):\n")
            for key, value in cat_stats['coverage_stats'].items():
                f.write(f"  {key}: {value*100:.4f}%\n")

            f.write("\nSize Distribution:\n")
            total_cat = cat_stats['count']
            for size_cat in ['very_small', 'small', 'medium', 'large', 'very_large']:
                count = cat_stats['size_distribution'].get(size_cat, 0)
                percentage = (count / total_cat * 100) if total_cat > 0 else 0
                f.write(f"  {size_cat}: {count} ({percentage:.2f}%)\n")

        # Recommendations
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("PREPROCESSING RECOMMENDATIONS\n")
        f.write("=" * 80 + "\n\n")

        # Analyze statistics for recommendations
        median_width = stats['image_width_stats']['median']
        median_height = stats['image_height_stats']['median']
        min_bbox_width = defect_stats['bbox_width_min']
        min_bbox_height = defect_stats['bbox_height_min']
        percentile_5_area = defect_stats['defect_area_percentile_5']

        f.write("1. IMAGE SIZE RECOMMENDATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Median Image Size: {median_width:.0f}x{median_height:.0f}\n")
        f.write(f"Smallest Defect BBox: {min_bbox_width:.0f}x{min_bbox_height:.0f}\n")
        f.write(f"5th Percentile Defect Area: {percentile_5_area:.2f} pixels²\n\n")

        # Calculate recommended sizes
        recommended_sizes = []

        # Option 1: Conservative (no detail loss)
        conservative_size = int(min(median_width, median_height))
        recommended_sizes.append(('Conservative', conservative_size,
                                 "Maintains most image detail, minimal defect loss"))

        # Option 2: Balanced (slight compression)
        balanced_size = 1024 if median_width > 2000 else 640
        recommended_sizes.append(('Balanced', balanced_size,
                                 "Good balance between detail preservation and computational efficiency"))

        # Option 3: Efficient (more compression)
        efficient_size = 640 if median_width > 2000 else 512
        recommended_sizes.append(('Efficient', efficient_size,
                                 "Faster training/inference, may lose some small defect details"))

        f.write("Recommended Preprocessing Sizes:\n\n")
        for name, size, desc in recommended_sizes:
            scale_factor = size / median_width
            min_defect_size_scaled = min_bbox_width * scale_factor
            f.write(f"{name} Approach: {size}x{size}\n")
            f.write(f"  Description: {desc}\n")
            f.write(f"  Scale Factor: {scale_factor:.4f}x\n")
            f.write(f"  Smallest Defect After Resize: ~{min_defect_size_scaled:.1f} pixels\n")
            f.write(f"  Recommended for: ")
            if 'Conservative' in name:
                f.write("Maximum accuracy, research purposes\n")
            elif 'Balanced' in name:
                f.write("Production deployment, general use\n")
            else:
                f.write("Real-time inference, mobile deployment\n")
            f.write("\n")

        f.write("\n2. ASPECT RATIO HANDLING\n")
        f.write("-" * 80 + "\n")
        aspect_mean = stats['aspect_ratio_stats']['mean']
        aspect_std = stats['aspect_ratio_stats']['std']
        f.write(f"Mean Aspect Ratio: {aspect_mean:.4f}\n")
        f.write(f"Std Dev: {aspect_std:.4f}\n\n")

        if aspect_std < 0.1:
            f.write("Recommendation: Use square resize (consistent aspect ratios)\n")
        else:
            f.write("Recommendation: Use padding or aspect-ratio-preserving resize\n")
        f.write("  - Option A: Resize with padding (preserves aspect ratio)\n")
        f.write("  - Option B: Center crop (may lose peripheral context)\n")
        f.write("  - Option C: Squeeze resize (faster but distorts shapes)\n\n")

        f.write("\n3. DEFECT SIZE CONSIDERATIONS\n")
        f.write("-" * 80 + "\n")
        f.write("Small Defect Categories (require careful handling):\n")

        small_defect_cats = []
        for cat_id, cat_stats in stats['category_statistics'].items():
            if cat_stats['area_stats']['median'] < percentile_5_area * 2:
                small_defect_cats.append((cat_stats['category_name'],
                                         cat_stats['category_name_kr'],
                                         cat_stats['area_stats']['median']))

        small_defect_cats.sort(key=lambda x: x[2])
        for name, name_kr, median_area in small_defect_cats:
            f.write(f"  - {name} ({name_kr}): median area = {median_area:.2f} pixels²\n")

        f.write("\nRecommendation:\n")
        f.write("  - Use multi-scale training for better small defect detection\n")
        f.write("  - Consider anchor size adjustments for small objects\n")
        f.write("  - Apply careful augmentation (avoid aggressive crops)\n\n")

        f.write("\n4. DATA AUGMENTATION RECOMMENDATIONS\n")
        f.write("-" * 80 + "\n")
        f.write("Based on defect coverage analysis:\n")
        median_coverage = coverage['median'] * 100

        if median_coverage < 1:
            f.write(f"  - Defects are typically small ({median_coverage:.4f}% of image)\n")
            f.write("  - Avoid aggressive random crops (use minimal crop ratios)\n")
            f.write("  - Use mosaic augmentation to increase defect visibility\n")
            f.write("  - Apply mixup/cutmix with caution\n")
        else:
            f.write(f"  - Defects are moderate-sized ({median_coverage:.4f}% of image)\n")
            f.write("  - Standard augmentation pipeline is safe\n")
            f.write("  - Random crops with 0.5-1.0 scale factor\n")

        f.write("\n\n5. FINAL RECOMMENDED PIPELINE\n")
        f.write("-" * 80 + "\n")
        f.write("Recommended preprocessing pipeline:\n\n")
        f.write("For Training:\n")
        f.write(f"  1. Resize: {balanced_size}x{balanced_size} with padding\n")
        f.write("  2. Random horizontal flip (50%)\n")
        f.write("  3. Random brightness/contrast adjustment\n")
        f.write("  4. Color jitter (slight)\n")
        f.write("  5. Random rotation (-10 to +10 degrees)\n")
        f.write("  6. Minimal crop (0.8-1.0 scale)\n\n")

        f.write("For Validation/Inference:\n")
        f.write(f"  1. Resize: {balanced_size}x{balanced_size} with padding\n")
        f.write("  2. Normalize (ImageNet stats or custom stats)\n\n")

        f.write("\n6. MEMORY AND COMPUTATION ESTIMATES\n")
        f.write("-" * 80 + "\n")
        for name, size, _ in recommended_sizes:
            memory_mb = (size * size * 3 * 4) / (1024 * 1024)  # float32
            f.write(f"{name} ({size}x{size}):\n")
            f.write(f"  Memory per image: ~{memory_mb:.2f} MB\n")
            f.write(f"  Batch size 16 memory: ~{memory_mb * 16:.2f} MB\n")
            f.write(f"  Batch size 32 memory: ~{memory_mb * 32:.2f} MB\n\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


def main():
    # Define paths
    project_root = Path(__file__).parent.parent.parent
    labels_dir = project_root / "data" / "extracted" / "02.labels"
    output_dir = project_root / "results" / "eda"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project root: {project_root}")
    print(f"Labels directory: {labels_dir}")
    print(f"Output directory: {output_dir}")

    # Run analysis
    stats = analyze_dataset(str(labels_dir), str(output_dir))

    # Save statistics as JSON
    json_output_path = output_dir / "preprocessing_statistics.json"
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\nStatistics saved to: {json_output_path}")

    # Generate report
    report_output_path = output_dir / "preprocessing_analysis_report.txt"
    generate_report(stats, str(report_output_path))
    print(f"Report saved to: {report_output_path}")

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
