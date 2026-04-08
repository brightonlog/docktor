"""
Visualization script for preprocessing analysis
Generates plots for image size and defect distributions
"""

import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from config.dataset_config import CATEGORIES, CATEGORIES_KR


def load_statistics(stats_path):
    """Load preprocessing statistics from JSON"""
    with open(stats_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def plot_image_size_distribution(stats, output_dir):
    """Plot image size distribution"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Top 10 image sizes
    size_dist = stats['image_size_distribution']
    top_10 = list(size_dist.items())[:10]
    sizes, counts = zip(*top_10)

    ax1.barh(range(len(sizes)), counts, color='steelblue')
    ax1.set_yticks(range(len(sizes)))
    ax1.set_yticklabels(sizes)
    ax1.set_xlabel('Number of Images')
    ax1.set_title('Top 10 Image Sizes in Dataset')
    ax1.invert_yaxis()
    for i, v in enumerate(counts):
        ax1.text(v, i, f' {v:,}', va='center')

    # Image dimension statistics
    width_stats = stats['image_width_stats']
    height_stats = stats['image_height_stats']

    categories = ['Width', 'Height']
    min_vals = [width_stats['min'], height_stats['min']]
    max_vals = [width_stats['max'], height_stats['max']]
    mean_vals = [width_stats['mean'], height_stats['mean']]
    median_vals = [width_stats['median'], height_stats['median']]

    x = np.arange(len(categories))
    width = 0.2

    ax2.bar(x - 1.5*width, min_vals, width, label='Min', color='lightcoral')
    ax2.bar(x - 0.5*width, median_vals, width, label='Median', color='lightgreen')
    ax2.bar(x + 0.5*width, mean_vals, width, label='Mean', color='lightblue')
    ax2.bar(x + 1.5*width, max_vals, width, label='Max', color='plum')

    ax2.set_ylabel('Pixels')
    ax2.set_title('Image Dimension Statistics')
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'image_size_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'image_size_distribution.png'}")


def plot_defect_area_statistics(stats, output_dir):
    """Plot defect area statistics by category"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Category-wise median areas
    cat_stats = stats['category_statistics']
    categories = []
    median_areas = []
    counts = []

    for cat_id, cat_data in sorted(cat_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        cat_name = f"{cat_data['category_name']}\n({cat_data['category_name_kr']})"
        categories.append(cat_name)
        median_areas.append(cat_data['area_stats']['median'])
        counts.append(cat_data['count'])

    # Plot median areas
    colors = plt.cm.Set3(range(len(categories)))
    bars1 = ax1.barh(range(len(categories)), median_areas, color=colors)
    ax1.set_yticks(range(len(categories)))
    ax1.set_yticklabels(categories, fontsize=9)
    ax1.set_xlabel('Median Defect Area (pixels²)')
    ax1.set_title('Median Defect Area by Category')
    ax1.invert_yaxis()
    ax1.grid(axis='x', alpha=0.3)

    for i, v in enumerate(median_areas):
        ax1.text(v, i, f' {v:,.0f}', va='center', fontsize=8)

    # Plot category counts
    bars2 = ax2.barh(range(len(categories)), counts, color=colors)
    ax2.set_yticks(range(len(categories)))
    ax2.set_yticklabels(categories, fontsize=9)
    ax2.set_xlabel('Number of Defects')
    ax2.set_title('Defect Count by Category')
    ax2.invert_yaxis()
    ax2.grid(axis='x', alpha=0.3)

    for i, v in enumerate(counts):
        ax2.text(v, i, f' {v:,}', va='center', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_dir / 'defect_area_by_category.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'defect_area_by_category.png'}")


def plot_defect_size_distribution(stats, output_dir):
    """Plot defect size distribution (small, medium, large)"""
    cat_stats = stats['category_statistics']

    fig, ax = plt.subplots(figsize=(14, 8))

    categories = []
    very_small = []
    small = []
    medium = []
    large = []
    very_large = []

    for cat_id, cat_data in sorted(cat_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        cat_name = f"{cat_data['category_name']}\n({cat_data['category_name_kr']})"
        categories.append(cat_name)

        total = cat_data['count']
        dist = cat_data['size_distribution']

        very_small.append((dist.get('very_small', 0) / total * 100) if total > 0 else 0)
        small.append((dist.get('small', 0) / total * 100) if total > 0 else 0)
        medium.append((dist.get('medium', 0) / total * 100) if total > 0 else 0)
        large.append((dist.get('large', 0) / total * 100) if total > 0 else 0)
        very_large.append((dist.get('very_large', 0) / total * 100) if total > 0 else 0)

    x = np.arange(len(categories))
    width = 0.7

    p1 = ax.barh(x, very_small, width, label='Very Small (<0.1%)', color='#d62728')
    p2 = ax.barh(x, small, width, left=very_small, label='Small (0.1-1%)', color='#ff7f0e')
    p3 = ax.barh(x, medium, width, left=np.array(very_small)+np.array(small),
                 label='Medium (1-5%)', color='#2ca02c')
    p4 = ax.barh(x, large, width,
                 left=np.array(very_small)+np.array(small)+np.array(medium),
                 label='Large (5-15%)', color='#1f77b4')
    p5 = ax.barh(x, very_large, width,
                 left=np.array(very_small)+np.array(small)+np.array(medium)+np.array(large),
                 label='Very Large (>15%)', color='#9467bd')

    ax.set_yticks(x)
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlabel('Percentage (%)')
    ax.set_title('Defect Size Distribution by Category\n(Relative to Image Area)')
    ax.legend(loc='lower right', fontsize=9)
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'defect_size_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'defect_size_distribution.png'}")


def plot_bbox_dimensions(stats, output_dir):
    """Plot bounding box dimension statistics"""
    cat_stats = stats['category_statistics']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    categories = []
    width_mins = []
    width_medians = []
    width_maxs = []
    height_mins = []
    height_medians = []
    height_maxs = []

    for cat_id, cat_data in sorted(cat_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        cat_name = f"{cat_data['category_name']}\n({cat_data['category_name_kr']})"
        categories.append(cat_name)

        width_mins.append(cat_data['bbox_width_stats']['min'])
        width_medians.append(cat_data['bbox_width_stats']['median'])
        width_maxs.append(cat_data['bbox_width_stats']['max'])

        height_mins.append(cat_data['bbox_height_stats']['min'])
        height_medians.append(cat_data['bbox_height_stats']['median'])
        height_maxs.append(cat_data['bbox_height_stats']['max'])

    x = np.arange(len(categories))
    width = 0.25

    # Width plot
    ax1.bar(x - width, width_mins, width, label='Min', color='lightcoral', alpha=0.8)
    ax1.bar(x, width_medians, width, label='Median', color='steelblue', alpha=0.8)
    ax1.bar(x + width, width_maxs, width, label='Max', color='lightgreen', alpha=0.8)

    ax1.set_ylabel('Width (pixels)')
    ax1.set_title('Bounding Box Width Statistics by Category')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # Height plot
    ax2.bar(x - width, height_mins, width, label='Min', color='lightcoral', alpha=0.8)
    ax2.bar(x, height_medians, width, label='Median', color='steelblue', alpha=0.8)
    ax2.bar(x + width, height_maxs, width, label='Max', color='lightgreen', alpha=0.8)

    ax2.set_ylabel('Height (pixels)')
    ax2.set_title('Bounding Box Height Statistics by Category')
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'bbox_dimensions.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'bbox_dimensions.png'}")


def plot_coverage_statistics(stats, output_dir):
    """Plot defect coverage statistics"""
    cat_stats = stats['category_statistics']

    fig, ax = plt.subplots(figsize=(12, 8))

    categories = []
    min_coverage = []
    median_coverage = []
    mean_coverage = []
    p95_coverage = []

    for cat_id, cat_data in sorted(cat_stats.items(), key=lambda x: x[1]['coverage_stats']['median'], reverse=True):
        cat_name = f"{cat_data['category_name']}\n({cat_data['category_name_kr']})"
        categories.append(cat_name)

        min_coverage.append(cat_data['coverage_stats']['min'] * 100)
        median_coverage.append(cat_data['coverage_stats']['median'] * 100)
        mean_coverage.append(cat_data['coverage_stats']['mean'] * 100)
        p95_coverage.append(cat_data['coverage_stats']['percentile_95'] * 100)

    x = np.arange(len(categories))
    width = 0.2

    ax.bar(x - 1.5*width, min_coverage, width, label='Min', color='lightcoral')
    ax.bar(x - 0.5*width, median_coverage, width, label='Median', color='steelblue')
    ax.bar(x + 0.5*width, mean_coverage, width, label='Mean', color='lightgreen')
    ax.bar(x + 1.5*width, p95_coverage, width, label='95th Percentile', color='plum')

    ax.set_ylabel('Coverage (% of Image Area)')
    ax.set_title('Defect Coverage Statistics by Category')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=9)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'coverage_statistics.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'coverage_statistics.png'}")


def plot_preprocessing_comparison(stats, output_dir):
    """Plot preprocessing strategy comparison"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Resize options
    sizes = ['Conservative\n3024x3024', 'Balanced\n1024x1024', 'Efficient\n640x640']
    min_defect_sizes = [85.9, 29.1, 18.2]
    memory_per_batch16 = [1674.42, 192.00, 75.00]

    x = np.arange(len(sizes))

    # Plot 1: Minimum defect size after resize
    colors = ['#2ca02c', '#1f77b4', '#ff7f0e']
    bars1 = ax1.bar(x, min_defect_sizes, color=colors, alpha=0.7)
    ax1.set_ylabel('Minimum Defect Size (pixels)')
    ax1.set_title('Smallest Defect Size After Preprocessing')
    ax1.set_xticks(x)
    ax1.set_xticklabels(sizes)
    ax1.grid(axis='y', alpha=0.3)
    ax1.axhline(y=20, color='r', linestyle='--', label='Typical Detection Threshold')
    ax1.legend()

    for i, v in enumerate(min_defect_sizes):
        ax1.text(i, v + 2, f'{v:.1f}', ha='center', fontweight='bold')

    # Plot 2: Memory requirements
    bars2 = ax2.bar(x, memory_per_batch16, color=colors, alpha=0.7)
    ax2.set_ylabel('Memory per Batch (MB, batch_size=16)')
    ax2.set_title('Memory Requirements Comparison')
    ax2.set_xticks(x)
    ax2.set_xticklabels(sizes)
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_yscale('log')

    for i, v in enumerate(memory_per_batch16):
        ax2.text(i, v * 1.2, f'{v:.0f} MB', ha='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'preprocessing_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'preprocessing_comparison.png'}")


def main():
    project_root = Path(__file__).parent.parent.parent
    stats_path = project_root / "results" / "eda" / "preprocessing_statistics.json"
    output_dir = project_root / "results" / "eda"

    print("Loading statistics...")
    stats = load_statistics(stats_path)

    print("\nGenerating visualizations...")

    plot_image_size_distribution(stats, output_dir)
    plot_defect_area_statistics(stats, output_dir)
    plot_defect_size_distribution(stats, output_dir)
    plot_bbox_dimensions(stats, output_dir)
    plot_coverage_statistics(stats, output_dir)
    plot_preprocessing_comparison(stats, output_dir)

    print("\nAll visualizations generated successfully!")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
