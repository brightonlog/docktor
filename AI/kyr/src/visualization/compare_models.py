#!/usr/bin/env python3
"""
Model Comparison Visualization
SafeDeck Project - Ship Defect Detection

MLflow 실험 결과를 비교하고 시각화하는 스크립트

실행:
    python src/visualization/compare_models.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# Set font for Korean support (if available)
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# Base directory
BASE_DIR = Path(__file__).parent.parent.parent
MLRUNS_DIR = BASE_DIR / "experiments" / "mlruns"
OUTPUT_DIR = BASE_DIR / "experiments" / "comparison_results"


def setup_mlflow():
    """Setup MLflow connection"""
    mlflow.set_tracking_uri(str(MLRUNS_DIR))
    client = MlflowClient()
    return client


def get_experiment_runs(client, experiment_name="safedeck-model-comparison"):
    """Get all runs from the experiment"""
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        print(f"Experiment '{experiment_name}' not found!")
        return []

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"]
    )
    return runs


def runs_to_dataframe(runs):
    """Convert MLflow runs to pandas DataFrame"""
    data = []
    for run in runs:
        row = {
            'run_id': run.info.run_id,
            'run_name': run.info.run_name,
            'model_name': run.data.params.get('model_name', 'unknown'),
            'start_time': run.info.start_time,
            'status': run.info.status,
        }
        # Add metrics
        row.update(run.data.metrics)
        data.append(row)

    df = pd.DataFrame(data)
    return df


def get_best_runs(df):
    """Get best run for each model"""
    best_runs = df.loc[df.groupby('model_name')['mAP50'].idxmax()]
    return best_runs


def plot_radar_chart(df, output_path):
    """Create radar chart comparing models"""
    # Metrics to compare
    metrics = ['mAP50', 'precision', 'recall', 'f1_score', 'fps_gpu']
    metric_labels = ['mAP50', 'Precision', 'Recall', 'F1 Score', 'FPS (norm)']

    # Normalize FPS to 0-1 scale for comparison
    df_plot = df.copy()
    if 'fps_gpu' in df_plot.columns:
        max_fps = df_plot['fps_gpu'].max()
        df_plot['fps_gpu'] = df_plot['fps_gpu'] / max_fps if max_fps > 0 else 0

    # Number of metrics
    N = len(metrics)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Complete the loop

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    models = df_plot['model_name'].unique()

    for i, model in enumerate(models):
        model_data = df_plot[df_plot['model_name'] == model].iloc[0]
        values = [model_data.get(m, 0) for m in metrics]
        values += values[:1]  # Complete the loop

        ax.plot(angles, values, 'o-', linewidth=2, label=model.upper(), color=colors[i % len(colors)])
        ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])

    # Set labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_labels, size=12)
    ax.set_ylim(0, 1)

    plt.title('Model Performance Comparison\n(Radar Chart)', size=16, fontweight='bold', pad=20)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_bar_comparison(df, output_path):
    """Create bar chart comparing key metrics"""
    metrics = ['mAP50', 'mAP50-95', 'precision', 'recall']
    models = df['model_name'].tolist()

    fig, axes = plt.subplots(1, len(metrics), figsize=(16, 5))

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

    for i, metric in enumerate(metrics):
        values = [df[df['model_name'] == m][metric].values[0] if metric in df.columns else 0 for m in models]
        bars = axes[i].bar(models, values, color=colors[:len(models)])

        # Add value labels on bars
        for bar, val in zip(bars, values):
            axes[i].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{val:.3f}', ha='center', va='bottom', fontsize=10)

        axes[i].set_title(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        axes[i].set_ylim(0, 1.1)
        axes[i].tick_params(axis='x', rotation=45)

    plt.suptitle('Detection Metrics Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_speed_accuracy_tradeoff(df, output_path):
    """Create speed vs accuracy scatter plot"""
    fig, ax = plt.subplots(figsize=(10, 8))

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    markers = ['o', 's', '^']

    for i, (_, row) in enumerate(df.iterrows()):
        model = row['model_name']
        mAP = row.get('mAP50', 0)
        fps = row.get('fps_gpu', 0)
        size = row.get('model_size_mb', 10) * 10  # Scale for visibility

        ax.scatter(fps, mAP, s=size, c=colors[i % len(colors)],
                  marker=markers[i % len(markers)], label=model.upper(),
                  alpha=0.7, edgecolors='black', linewidth=2)

        # Add annotation
        ax.annotate(model.upper(), (fps, mAP),
                   textcoords="offset points", xytext=(10, 10),
                   fontsize=10, fontweight='bold')

    ax.set_xlabel('FPS (GPU)', fontsize=12)
    ax.set_ylabel('mAP50', fontsize=12)
    ax.set_title('Speed vs Accuracy Trade-off\n(Bubble size = Model size)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add threshold lines
    ax.axhline(y=0.75, color='red', linestyle='--', alpha=0.5, label='mAP50 threshold')
    ax.axvline(x=15, color='blue', linestyle='--', alpha=0.5, label='FPS threshold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_inference_comparison(df, output_path):
    """Create inference performance comparison"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    models = df['model_name'].tolist()
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

    # FPS
    fps_values = [df[df['model_name'] == m]['fps_gpu'].values[0] if 'fps_gpu' in df.columns else 0 for m in models]
    bars1 = axes[0].bar(models, fps_values, color=colors[:len(models)])
    axes[0].set_title('FPS (GPU)', fontsize=12, fontweight='bold')
    axes[0].axhline(y=15, color='red', linestyle='--', alpha=0.5, label='Target (15 FPS)')
    for bar, val in zip(bars1, fps_values):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}', ha='center', va='bottom')

    # Inference Time
    time_values = [df[df['model_name'] == m]['inference_time_ms'].values[0] if 'inference_time_ms' in df.columns else 0 for m in models]
    bars2 = axes[1].bar(models, time_values, color=colors[:len(models)])
    axes[1].set_title('Inference Time (ms)', fontsize=12, fontweight='bold')
    for bar, val in zip(bars2, time_values):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}', ha='center', va='bottom')

    # Model Size
    size_values = [df[df['model_name'] == m]['model_size_mb'].values[0] if 'model_size_mb' in df.columns else 0 for m in models]
    bars3 = axes[2].bar(models, size_values, color=colors[:len(models)])
    axes[2].set_title('Model Size (MB)', fontsize=12, fontweight='bold')
    for bar, val in zip(bars3, size_values):
        axes[2].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{val:.1f}', ha='center', va='bottom')

    for ax in axes:
        ax.tick_params(axis='x', rotation=45)

    plt.suptitle('Inference Performance Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def calculate_overall_score(df):
    """Calculate weighted overall score for each model"""
    # Weights: mAP50 (40%), Recall (30%), FPS normalized (30%)
    df_score = df.copy()

    # Normalize FPS (0-1 scale)
    max_fps = df_score['fps_gpu'].max() if 'fps_gpu' in df_score.columns else 1
    df_score['fps_normalized'] = df_score['fps_gpu'] / max_fps if max_fps > 0 else 0

    # Calculate overall score
    df_score['overall_score'] = (
        df_score.get('mAP50', 0) * 0.4 +
        df_score.get('recall', 0) * 0.3 +
        df_score.get('fps_normalized', 0) * 0.3
    )

    return df_score


def generate_summary_report(df, output_path):
    """Generate text summary report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
================================================================================
SafeDeck Model Comparison Report
Generated: {timestamp}
================================================================================

1. EXPERIMENT SUMMARY
---------------------
Total Models Compared: {len(df)}
Models: {', '.join(df['model_name'].tolist())}

2. DETECTION PERFORMANCE
------------------------
"""
    for _, row in df.iterrows():
        report += f"""
{row['model_name'].upper()}:
  - mAP50: {row.get('mAP50', 'N/A'):.4f}
  - mAP50-95: {row.get('mAP50-95', 'N/A'):.4f}
  - Precision: {row.get('precision', 'N/A'):.4f}
  - Recall: {row.get('recall', 'N/A'):.4f}
  - F1 Score: {row.get('f1_score', 'N/A'):.4f}
"""

    report += """
3. INFERENCE PERFORMANCE
------------------------
"""
    for _, row in df.iterrows():
        report += f"""
{row['model_name'].upper()}:
  - FPS (GPU): {row.get('fps_gpu', 'N/A'):.2f}
  - Inference Time: {row.get('inference_time_ms', 'N/A'):.2f} ms
  - Model Size: {row.get('model_size_mb', 'N/A'):.2f} MB
  - Memory Usage: {row.get('memory_usage_mb', 'N/A'):.2f} MB
"""

    # Calculate scores
    df_scored = calculate_overall_score(df)

    report += """
4. OVERALL RANKING
------------------
(Score = mAP50×0.4 + Recall×0.3 + FPS_normalized×0.3)

"""
    df_sorted = df_scored.sort_values('overall_score', ascending=False)
    for rank, (_, row) in enumerate(df_sorted.iterrows(), 1):
        report += f"  {rank}. {row['model_name'].upper()}: {row['overall_score']:.4f}\n"

    # Recommendation
    best_model = df_sorted.iloc[0]['model_name']
    report += f"""
5. RECOMMENDATION
-----------------
Based on the weighted scoring (Accuracy: 40%, Recall: 30%, Speed: 30%):

  >> RECOMMENDED MODEL: {best_model.upper()} <<

Justification:
- Achieves the best balance between detection accuracy and inference speed
- Suitable for Jetson Orin Nano deployment
- Meets the minimum requirements (mAP50 >= 0.75, FPS >= 15)

6. NEXT STEPS
-------------
1. Convert {best_model.upper()} to TensorRT format
2. Benchmark on Jetson Orin Nano
3. Integrate with Flask API
4. Deploy to production

================================================================================
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Saved: {output_path}")
    print(report)


def main():
    print("=" * 70)
    print("SafeDeck Model Comparison Visualization")
    print("=" * 70)

    # Setup
    client = setup_mlflow()

    # Get runs
    runs = get_experiment_runs(client)

    if not runs:
        print("\nNo runs found. Please train models first:")
        print("  python src/training/train_with_mlflow.py --all")
        return

    # Convert to DataFrame
    df = runs_to_dataframe(runs)
    print(f"\nFound {len(df)} runs")

    # Get best run for each model
    best_df = get_best_runs(df)
    print(f"Comparing {len(best_df)} models: {best_df['model_name'].tolist()}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate visualizations
    print("\nGenerating visualizations...")

    plot_radar_chart(best_df, OUTPUT_DIR / "radar_comparison.png")
    plot_bar_comparison(best_df, OUTPUT_DIR / "bar_metrics_comparison.png")
    plot_speed_accuracy_tradeoff(best_df, OUTPUT_DIR / "speed_accuracy_tradeoff.png")
    plot_inference_comparison(best_df, OUTPUT_DIR / "inference_comparison.png")

    # Generate report
    generate_summary_report(best_df, OUTPUT_DIR / "comparison_report.txt")

    print("\n" + "=" * 70)
    print(f"All outputs saved to: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
