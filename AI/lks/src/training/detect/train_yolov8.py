#!/usr/bin/env python3
"""
Train YOLOv8 Model with MLflow Integration
선박 도장 결함 탐지 모델 학습
"""

import os
import sys
from pathlib import Path
import yaml
import mlflow
import mlflow.pytorch
from datetime import datetime
import torch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.training_config import *

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("ERROR: ultralytics not installed. Install with: pip install ultralytics")
    YOLO_AVAILABLE = False


class YOLOv8Trainer:
    """
    YOLOv8 Trainer with MLflow Integration
    """

    def __init__(self,
                 model_name='yolov8n',
                 data_yaml=None,
                 experiment_name='ship-coating-defect-detection',
                 run_name=None):
        """
        Args:
            model_name: YOLOv8 model variant
            data_yaml: Path to data.yaml
            experiment_name: MLflow experiment name
            run_name: MLflow run name
        """
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics not installed")

        self.model_name = model_name
        self.data_yaml = data_yaml
        self.experiment_name = experiment_name
        self.run_name = run_name or f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Setup MLflow
        self.setup_mlflow()

        # Load model
        self.model = YOLO(f'{model_name}.pt')

    def setup_mlflow(self):
        """Setup MLflow tracking"""
        # Set tracking URI
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        # Set experiment
        mlflow.set_experiment(self.experiment_name)

        print(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
        print(f"MLflow experiment: {self.experiment_name}")

    def train(self,
              epochs=EPOCHS,
              batch_size=BATCH_SIZE,
              imgsz=IMAGE_HEIGHT,
              device=DEVICE,
              patience=PATIENCE,
              save_period=SAVE_PERIOD,
              **kwargs):
        """
        Train YOLOv8 model with MLflow logging

        Args:
            epochs: Number of epochs
            batch_size: Batch size
            imgsz: Image size
            device: Device (0, 1, 2, ... or 'cpu')
            patience: Early stopping patience
            save_period: Save checkpoint every N epochs
            **kwargs: Additional YOLO training arguments
        """
        # Start MLflow run
        with mlflow.start_run(run_name=self.run_name) as run:
            print(f"\nMLflow run: {run.info.run_name}")
            print(f"Run ID: {run.info.run_id}")

            # Log parameters
            params = {
                'model': self.model_name,
                'epochs': epochs,
                'batch_size': batch_size,
                'imgsz': imgsz,
                'device': device,
                'patience': patience,
                'optimizer': OPTIMIZER,
                'lr0': LEARNING_RATE,
                'weight_decay': WEIGHT_DECAY,
                'warmup_epochs': WARMUP_EPOCHS,
                'augment': AUGMENT,
                'mosaic': MOSAIC,
                'mixup': MIXUP,
                'degrees': DEGREES,
                'translate': TRANSLATE,
                'scale': SCALE,
                'fliplr': FLIPLR,
                'flipud': FLIPUD,
                'num_classes': NUM_CLASSES,
                'image_width': IMAGE_WIDTH,
                'image_height': IMAGE_HEIGHT,
            }

            mlflow.log_params(params)

            # Log dataset info
            mlflow.log_param('train_ratio', TRAIN_RATIO)
            mlflow.log_param('val_ratio', VAL_RATIO)

            # Log training config
            mlflow.log_dict(params, 'config/training_params.yaml')

            # Train model
            print("\n" + "=" * 70)
            print("STARTING TRAINING")
            print("=" * 70)

            results = self.model.train(
                data=self.data_yaml,
                epochs=epochs,
                batch=batch_size,
                imgsz=imgsz,
                device=device,
                patience=patience,
                save_period=save_period,
                # Optimizer
                optimizer=OPTIMIZER,
                lr0=LEARNING_RATE,
                weight_decay=WEIGHT_DECAY,
                warmup_epochs=WARMUP_EPOCHS,
                # Augmentation
                augment=AUGMENT,
                degrees=DEGREES,
                translate=TRANSLATE,
                scale=SCALE,
                shear=SHEAR,
                perspective=PERSPECTIVE,
                fliplr=FLIPLR,
                flipud=FLIPUD,
                mosaic=MOSAIC,
                mixup=MIXUP,
                hsv_h=HSV_H,
                hsv_s=HSV_S,
                hsv_v=HSV_V,
                # Other
                amp=AMP,
                **kwargs
            )

            print("\n" + "=" * 70)
            print("TRAINING COMPLETE")
            print("=" * 70)

            # Log final metrics
            self.log_final_metrics(results)

            # Log model
            self.log_model()

            # Log artifacts
            self.log_artifacts()

            print(f"\nMLflow run ID: {run.info.run_id}")
            print(f"MLflow UI: {MLFLOW_TRACKING_URI}")

            return results

    def log_final_metrics(self, results):
        """
        Log final training metrics to MLflow

        Args:
            results: Training results from YOLO
        """
        try:
            # Read results from CSV if available
            results_csv = Path(self.model.trainer.save_dir) / 'results.csv'

            if results_csv.exists():
                import pandas as pd
                df = pd.read_csv(results_csv)

                # Log final epoch metrics
                final_row = df.iloc[-1]

                metrics = {
                    'train/box_loss': final_row.get('train/box_loss'),
                    'train/cls_loss': final_row.get('train/cls_loss'),
                    'train/dfl_loss': final_row.get('train/dfl_loss'),
                    'val/box_loss': final_row.get('val/box_loss'),
                    'val/cls_loss': final_row.get('val/cls_loss'),
                    'val/dfl_loss': final_row.get('val/dfl_loss'),
                    'metrics/precision': final_row.get('metrics/precision(B)'),
                    'metrics/recall': final_row.get('metrics/recall(B)'),
                    'metrics/mAP50': final_row.get('metrics/mAP50(B)'),
                    'metrics/mAP50-95': final_row.get('metrics/mAP50-95(B)'),
                }

                # Remove None values
                metrics = {k: v for k, v in metrics.items() if v is not None and not pd.isna(v)}

                mlflow.log_metrics(metrics)

                print("\nFinal Metrics:")
                for k, v in metrics.items():
                    print(f"  {k}: {v:.4f}")

        except Exception as e:
            print(f"Warning: Could not log final metrics: {e}")

    def log_model(self):
        """Log trained model to MLflow and register in Model Registry"""
        try:
            # Get best model path
            best_model_path = Path(self.model.trainer.save_dir) / 'weights' / 'best.pt'

            if best_model_path.exists():
                # Log as artifact
                mlflow.log_artifact(str(best_model_path), 'models')
                print(f"\nLogged best model: {best_model_path}")

                # Register model to Model Registry
                model_uri = f"runs:/{mlflow.active_run().info.run_id}/models/best.pt"
                registered_model = mlflow.register_model(
                    model_uri=model_uri,
                    name="yolov8-ship-defect-detector"
                )

                print(f"Registered model: {registered_model.name}")
                print(f"Model version: {registered_model.version}")

                # Add model description
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                client.update_model_version(
                    name="yolov8-ship-defect-detector",
                    version=registered_model.version,
                    description=f"{self.model_name} trained on ship coating defect dataset"
                )

            # Also log last model
            last_model_path = Path(self.model.trainer.save_dir) / 'weights' / 'last.pt'
            if last_model_path.exists():
                mlflow.log_artifact(str(last_model_path), 'models')
                print(f"Logged last model: {last_model_path}")

        except Exception as e:
            print(f"Warning: Could not log model: {e}")

    def log_artifacts(self):
        """Log training artifacts to MLflow"""
        try:
            save_dir = Path(self.model.trainer.save_dir)

            # Log results CSV
            results_csv = save_dir / 'results.csv'
            if results_csv.exists():
                mlflow.log_artifact(str(results_csv), 'results')

            # Log confusion matrix
            confusion_matrix = save_dir / 'confusion_matrix.png'
            if confusion_matrix.exists():
                mlflow.log_artifact(str(confusion_matrix), 'plots')

            # Log PR curve
            pr_curve = save_dir / 'PR_curve.png'
            if pr_curve.exists():
                mlflow.log_artifact(str(pr_curve), 'plots')

            # Log F1 curve
            f1_curve = save_dir / 'F1_curve.png'
            if f1_curve.exists():
                mlflow.log_artifact(str(f1_curve), 'plots')

            # Log training plots
            for plot_file in save_dir.glob('*.png'):
                mlflow.log_artifact(str(plot_file), 'plots')

            # Log config
            args_yaml = save_dir / 'args.yaml'
            if args_yaml.exists():
                mlflow.log_artifact(str(args_yaml), 'config')

            print("\nLogged training artifacts")

        except Exception as e:
            print(f"Warning: Could not log artifacts: {e}")

    def validate(self):
        """
        Validate trained model
        """
        print("\n" + "=" * 70)
        print("VALIDATING MODEL")
        print("=" * 70)

        metrics = self.model.val(
            data=self.data_yaml,
            imgsz=IMAGE_HEIGHT,
            conf=CONF_THRESHOLD,
            iou=IOU_THRESHOLD,
        )

        print("\nValidation Metrics:")
        print(f"  mAP50: {metrics.box.map50:.4f}")
        print(f"  mAP50-95: {metrics.box.map:.4f}")
        print(f"  Precision: {metrics.box.mp:.4f}")
        print(f"  Recall: {metrics.box.mr:.4f}")

        return metrics

    def export(self, format='onnx'):
        """
        Export model to different formats

        Args:
            format: Export format (onnx, torchscript, coreml, etc.)
        """
        print(f"\nExporting model to {format}...")
        export_path = self.model.export(format=format, imgsz=IMAGE_HEIGHT)
        print(f"Exported to: {export_path}")

        return export_path


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Train YOLOv8 model')
    parser.add_argument('--model', type=str, default=MODEL_NAME,
                       choices=['yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x'],
                       help=f'YOLOv8 model variant (default: {MODEL_NAME})')
    parser.add_argument('--data', type=str,
                       default=str(YOLO_DATA_DIR / 'data.yaml'),
                       help='Path to data.yaml')
    parser.add_argument('--epochs', type=int, default=EPOCHS,
                       help=f'Number of epochs (default: {EPOCHS})')
    parser.add_argument('--batch', type=int, default=BATCH_SIZE,
                       help=f'Batch size (default: {BATCH_SIZE})')
    parser.add_argument('--imgsz', type=int, default=IMAGE_HEIGHT,
                       help=f'Image size (default: {IMAGE_HEIGHT})')
    parser.add_argument('--device', default=DEVICE,
                       help=f'Device (default: {DEVICE})')
    parser.add_argument('--name', type=str, default=None,
                       help='Run name')
    parser.add_argument('--resume', type=str, default=None,
                       help='Resume training from checkpoint')
    parser.add_argument('--pretrained', action='store_true',
                       help='Use pretrained weights')

    args = parser.parse_args()

    # Check data.yaml exists
    if not Path(args.data).exists():
        print(f"ERROR: data.yaml not found at {args.data}")
        print("Please run prepare_yolo_dataset.py first")
        sys.exit(1)

    # Initialize trainer
    trainer = YOLOv8Trainer(
        model_name=args.model,
        data_yaml=args.data,
        run_name=args.name
    )

    # Train model
    results = trainer.train(
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        resume=args.resume if args.resume else False,
    )

    # Validate
    metrics = trainer.validate()

    # Export to ONNX for production
    # trainer.export(format='onnx')

    print("\n" + "=" * 70)
    print("ALL DONE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
