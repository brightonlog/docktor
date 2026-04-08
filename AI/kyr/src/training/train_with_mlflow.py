#!/usr/bin/env python3
"""
YOLO Model Training with MLflow Integration
SafeDeck Project - Ship Defect Detection

학습 실행:
    python src/training/train_with_mlflow.py --model yolov11n
    python src/training/train_with_mlflow.py --model yolov11s
    python src/training/train_with_mlflow.py --model yolov26s

전체 실행 (3개 모델 순차 학습):
    python src/training/train_with_mlflow.py --all
"""

import os
import sys
import yaml
import time
import argparse
from pathlib import Path
from datetime import datetime

import mlflow
import mlflow.pytorch
from ultralytics import YOLO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Base directory (AI/kyr)
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = Path(__file__).parent / "train_config.yaml"


def load_config():
    """Load training configuration from YAML"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def setup_mlflow(config):
    """Setup MLflow tracking"""
    mlflow_config = config['mlflow']

    # Set tracking URI
    tracking_uri = BASE_DIR / mlflow_config['tracking_uri'].replace("./", "")
    tracking_uri.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(str(tracking_uri))

    # Create or get experiment
    experiment_name = mlflow_config['experiment_name']
    experiment = mlflow.get_experiment_by_name(experiment_name)

    if experiment is None:
        mlflow.create_experiment(experiment_name)

    mlflow.set_experiment(experiment_name)
    print(f"MLflow Tracking URI: {tracking_uri}")
    print(f"MLflow Experiment: {experiment_name}")

    return mlflow_config


def create_data_yaml(config):
    """Create YOLO data.yaml file for training"""
    data_config = config['data']
    names = config['names']

    # Paths relative to BASE_DIR
    data_yaml = {
        'path': str(BASE_DIR / data_config['base_dir']),
        'train': data_config['train_images'],
        'val': data_config['val_images'],
        'nc': data_config['nc'],
        'names': names
    }

    # Save to temporary file
    data_yaml_path = BASE_DIR / "data" / "processed" / "data.yaml"
    data_yaml_path.parent.mkdir(parents=True, exist_ok=True)

    with open(data_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, allow_unicode=True, default_flow_style=False)

    print(f"Data YAML created: {data_yaml_path}")
    return str(data_yaml_path)


def get_model_metrics(results):
    """Extract metrics from YOLO training results"""
    metrics = {}

    # Get final metrics from results
    if hasattr(results, 'results_dict'):
        rd = results.results_dict
        metrics['mAP50'] = rd.get('metrics/mAP50(B)', 0)
        metrics['mAP50-95'] = rd.get('metrics/mAP50-95(B)', 0)
        metrics['precision'] = rd.get('metrics/precision(B)', 0)
        metrics['recall'] = rd.get('metrics/recall(B)', 0)

        # Calculate F1 score
        p = metrics['precision']
        r = metrics['recall']
        metrics['f1_score'] = 2 * p * r / (p + r) if (p + r) > 0 else 0

    return metrics


def get_inference_metrics(model, data_yaml_path, config):
    """Benchmark inference performance"""
    import torch

    metrics = {}
    eval_config = config['evaluation']

    # Warmup
    print("\nBenchmarking inference performance...")
    dummy_input = torch.randn(1, 3, 640, 640)
    if torch.cuda.is_available():
        dummy_input = dummy_input.cuda()
        model.model.cuda()

    # Warmup runs
    for _ in range(10):
        model.predict(dummy_input, verbose=False)

    # Benchmark
    iterations = eval_config['benchmark_iterations']
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        model.predict(dummy_input, verbose=False)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms

    avg_time = sum(times) / len(times)
    metrics['inference_time_ms'] = avg_time
    metrics['fps_gpu'] = 1000 / avg_time if avg_time > 0 else 0

    # Model size
    model_path = Path(model.ckpt_path) if hasattr(model, 'ckpt_path') else None
    if model_path and model_path.exists():
        metrics['model_size_mb'] = model_path.stat().st_size / (1024 * 1024)
    else:
        metrics['model_size_mb'] = 0

    # Memory usage (if CUDA available)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        metrics['memory_usage_mb'] = torch.cuda.max_memory_allocated() / (1024 * 1024)
        torch.cuda.reset_peak_memory_stats()
    else:
        metrics['memory_usage_mb'] = 0

    return metrics


def train_model(model_name: str, config: dict, mlflow_config: dict):
    """Train a single YOLO model with MLflow tracking"""

    print("\n" + "=" * 70)
    print(f"Training Model: {model_name.upper()}")
    print("=" * 70)

    # Get model config
    model_config = config['models'][model_name]
    train_config = config['training']
    aug_config = config['augmentation']

    # Create data YAML
    data_yaml_path = create_data_yaml(config)

    # Generate run name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{mlflow_config['run_name_prefix']}_{model_name}_{timestamp}"

    # Start MLflow run
    with mlflow.start_run(run_name=run_name) as run:
        print(f"\nMLflow Run ID: {run.info.run_id}")
        print(f"MLflow Run Name: {run_name}")

        # Log parameters
        mlflow.log_params({
            "model_name": model_name,
            "model_pretrained": model_config['pretrained'],
            "epochs": train_config['epochs'],
            "batch_size": train_config['batch_size'],
            "imgsz": train_config['imgsz'],
            "optimizer": train_config['optimizer'],
            "lr0": train_config['lr0'],
            "lrf": train_config['lrf'],
            "momentum": train_config['momentum'],
            "weight_decay": train_config['weight_decay'],
            "warmup_epochs": train_config['warmup_epochs'],
            "patience": train_config['patience'],
            "mosaic": aug_config['mosaic'],
            "mixup": aug_config['mixup'],
        })

        # Load pretrained model
        pretrained_path = model_config['pretrained']

        # Check if model file exists in models/ directory
        local_model_path = BASE_DIR / "models" / pretrained_path
        if local_model_path.exists():
            pretrained_path = str(local_model_path)
            print(f"Using local model: {pretrained_path}")
        else:
            print(f"Using Ultralytics pretrained model: {pretrained_path}")

        model = YOLO(pretrained_path)

        # Training arguments
        train_args = {
            'data': data_yaml_path,
            'epochs': train_config['epochs'],
            'batch': train_config['batch_size'],
            'imgsz': train_config['imgsz'],
            'optimizer': train_config['optimizer'],
            'lr0': train_config['lr0'],
            'lrf': train_config['lrf'],
            'momentum': train_config['momentum'],
            'weight_decay': train_config['weight_decay'],
            'warmup_epochs': train_config['warmup_epochs'],
            'patience': train_config['patience'],
            'save_period': train_config['save_period'],
            'workers': train_config['workers'],
            'device': train_config['device'],
            'project': str(BASE_DIR / 'experiments' / 'runs'),
            'name': f'{model_name}_{timestamp}',
            'exist_ok': True,
            'verbose': True,
            # Augmentation
            'hsv_h': aug_config['hsv_h'],
            'hsv_s': aug_config['hsv_s'],
            'hsv_v': aug_config['hsv_v'],
            'degrees': aug_config['degrees'],
            'translate': aug_config['translate'],
            'scale': aug_config['scale'],
            'shear': aug_config['shear'],
            'perspective': aug_config['perspective'],
            'flipud': aug_config['flipud'],
            'fliplr': aug_config['fliplr'],
            'mosaic': aug_config['mosaic'],
            'mixup': aug_config['mixup'],
            'copy_paste': aug_config['copy_paste'],
        }

        # Train
        print("\nStarting training...")
        start_time = time.time()
        results = model.train(**train_args)
        training_time = time.time() - start_time

        print(f"\nTraining completed in {training_time/60:.2f} minutes")

        # Get detection metrics
        detection_metrics = get_model_metrics(results)
        print(f"\nDetection Metrics:")
        for k, v in detection_metrics.items():
            print(f"  {k}: {v:.4f}")

        # Get inference metrics
        inference_metrics = get_inference_metrics(model, data_yaml_path, config)
        print(f"\nInference Metrics:")
        for k, v in inference_metrics.items():
            print(f"  {k}: {v:.4f}")

        # Log all metrics to MLflow
        all_metrics = {
            **detection_metrics,
            **inference_metrics,
            'training_time_min': training_time / 60
        }
        mlflow.log_metrics(all_metrics)

        # Log artifacts (model weights, plots, etc.)
        run_dir = Path(train_args['project']) / train_args['name']
        if run_dir.exists():
            # Log best model
            best_model_path = run_dir / 'weights' / 'best.pt'
            if best_model_path.exists():
                mlflow.log_artifact(str(best_model_path), "weights")

            # Log training plots
            for plot_file in run_dir.glob("*.png"):
                mlflow.log_artifact(str(plot_file), "plots")

            # Log results CSV
            results_csv = run_dir / 'results.csv'
            if results_csv.exists():
                mlflow.log_artifact(str(results_csv), "results")

        # Log model to MLflow Model Registry
        mlflow.pytorch.log_model(
            pytorch_model=model.model,
            artifact_path="model",
            registered_model_name=f"safedeck-{model_name}"
        )

        print(f"\nMLflow Run completed: {run.info.run_id}")
        return run.info.run_id, all_metrics


def main():
    parser = argparse.ArgumentParser(description='Train YOLO models with MLflow')
    parser.add_argument('--model', type=str, choices=['yolov11n', 'yolov11s', 'yolov26s'],
                        help='Model to train')
    parser.add_argument('--all', action='store_true',
                        help='Train all three models sequentially')
    args = parser.parse_args()

    if not args.model and not args.all:
        parser.print_help()
        print("\nPlease specify --model or --all")
        return

    # Load configuration
    config = load_config()

    # Setup MLflow
    mlflow_config = setup_mlflow(config)

    # Models to train
    if args.all:
        models_to_train = ['yolov11n', 'yolov11s', 'yolov26s']
    else:
        models_to_train = [args.model]

    # Train each model
    results_summary = {}
    for model_name in models_to_train:
        try:
            run_id, metrics = train_model(model_name, config, mlflow_config)
            results_summary[model_name] = {
                'run_id': run_id,
                'metrics': metrics,
                'status': 'success'
            }
        except Exception as e:
            print(f"\nError training {model_name}: {e}")
            results_summary[model_name] = {
                'status': 'failed',
                'error': str(e)
            }

    # Print summary
    print("\n" + "=" * 70)
    print("TRAINING SUMMARY")
    print("=" * 70)
    for model_name, result in results_summary.items():
        print(f"\n{model_name}:")
        if result['status'] == 'success':
            print(f"  Run ID: {result['run_id']}")
            print(f"  mAP50: {result['metrics'].get('mAP50', 'N/A'):.4f}")
            print(f"  FPS: {result['metrics'].get('fps_gpu', 'N/A'):.2f}")
        else:
            print(f"  Status: FAILED - {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 70)
    print(f"MLflow UI: mlflow ui --backend-store-uri {BASE_DIR / 'experiments' / 'mlruns'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
