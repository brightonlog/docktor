"""
YOLOv26n Training Script for Ship Painting Defect Detection
Features:
- 1080p resolution training (optimized for Jetson Orin Nano webcam)
- MLflow experiment tracking
- TensorBoard logging
- Weights & Biases integration
- Multi-visualization support
"""

import os
import sys
import yaml
import torch
import mlflow
import mlflow.pytorch
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO


# ============================================================
# Configuration
# ============================================================
class TrainingConfig:
    """학습 설정"""

    # 모델 설정
    MODEL_NAME = 'yolo26n.pt'  # Base model
    MODEL_PATH = None  # Will be set in __init__

    # 데이터 설정
    DATA_YAML = None  # Will be set in __init__

    # 학습 하이퍼파라미터
    EPOCHS = 40  # 보수적 학습 (early stopping 활용)
    BATCH_SIZE = 8  # Jetson Orin Nano에 맞춰 조절
    IMG_SIZE = 1088  # 1080p에 가깝게 (32의 배수)

    # Optimizer
    OPTIMIZER = 'AdamW'
    LR0 = 0.001  # Initial learning rate
    LRF = 0.01   # Final learning rate factor
    MOMENTUM = 0.937
    WEIGHT_DECAY = 0.0005

    # Augmentation
    AUGMENT = True
    HSV_H = 0.015
    HSV_S = 0.7
    HSV_V = 0.4
    DEGREES = 0.0
    TRANSLATE = 0.1
    SCALE = 0.5
    SHEAR = 0.0
    PERSPECTIVE = 0.0
    FLIPUD = 0.0
    FLIPLR = 0.5
    MOSAIC = 1.0
    MIXUP = 0.0

    # 시각화 및 로깅
    MLFLOW_TRACKING_URI = './mlruns'
    MLFLOW_EXPERIMENT_NAME = 'ship_defect_detection'
    TENSORBOARD = True
    WANDB = False  # W&B 사용 시 True로 변경

    # 저장 설정
    PROJECT = 'ship_defect_yolov26n'
    NAME = None  # Will be auto-generated

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent

        self.MODEL_PATH = base_dir / 'models' / self.MODEL_NAME
        self.DATA_YAML = base_dir / 'data' / 'yolo_dataset' / 'data.yaml'
        self.PROJECT_DIR = base_dir / 'experiments' / 'yolo_runs'
        mlruns_path = base_dir / 'experiments' / 'mlruns'
        # Windows 경로를 MLflow URI로 변환 (file:// 스킴 필요)
        self.MLFLOW_TRACKING_URI = mlruns_path.as_uri()

        # Run name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.NAME = f'yolov26n_1080p_{timestamp}'


# ============================================================
# MLflow Callback for YOLO
# ============================================================
class MLflowCallback:
    """MLflow logging callback for Ultralytics YOLO"""

    def __init__(self, config: TrainingConfig):
        self.config = config

        # MLflow 설정
        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(config.MLFLOW_EXPERIMENT_NAME)

        self.run = None

    def on_train_start(self, trainer):
        """학습 시작 시 MLflow run 시작"""
        self.run = mlflow.start_run(run_name=self.config.NAME)

        # 하이퍼파라미터 로깅
        params = {
            'model': self.config.MODEL_NAME,
            'epochs': self.config.EPOCHS,
            'batch_size': self.config.BATCH_SIZE,
            'img_size': self.config.IMG_SIZE,
            'optimizer': self.config.OPTIMIZER,
            'lr0': self.config.LR0,
            'lrf': self.config.LRF,
            'momentum': self.config.MOMENTUM,
            'weight_decay': self.config.WEIGHT_DECAY,
            'augment': self.config.AUGMENT,
            'mosaic': self.config.MOSAIC,
            'mixup': self.config.MIXUP,
        }
        mlflow.log_params(params)

    def on_train_epoch_end(self, trainer):
        """에폭 종료 시 메트릭 로깅"""
        if self.run is None:
            return

        epoch = trainer.epoch

        # Loss metrics
        if hasattr(trainer, 'loss_items') and trainer.loss_items is not None:
            loss_names = ['box_loss', 'cls_loss', 'dfl_loss']
            for name, value in zip(loss_names, trainer.loss_items):
                mlflow.log_metric(f'train/{name}', float(value), step=epoch)

        # Learning rate
        if hasattr(trainer, 'lf'):
            for i, lr in enumerate(trainer.optimizer.param_groups):
                mlflow.log_metric(f'lr/pg{i}', lr['lr'], step=epoch)

    def on_val_end(self, validator):
        """Validation 종료 시 메트릭 로깅"""
        if self.run is None:
            return

        metrics = validator.metrics

        # mAP metrics
        if hasattr(metrics, 'box'):
            mlflow.log_metric('val/mAP50', float(metrics.box.map50))
            mlflow.log_metric('val/mAP50-95', float(metrics.box.map))

            # Per-class AP
            if hasattr(metrics.box, 'ap_class_index'):
                class_names = ['blister', 'crack', 'peeling', 'sagging', 'welding_damage']
                for i, ap in enumerate(metrics.box.ap50):
                    if i < len(class_names):
                        mlflow.log_metric(f'val/AP50_{class_names[i]}', float(ap))

    def on_train_end(self, trainer):
        """학습 종료 시 모델 아티팩트 저장"""
        if self.run is None:
            return

        # Best model 저장
        best_model_path = trainer.best
        if best_model_path and Path(best_model_path).exists():
            mlflow.log_artifact(str(best_model_path), artifact_path='models')

        # 최종 메트릭
        if hasattr(trainer, 'metrics'):
            metrics = trainer.metrics
            if hasattr(metrics, 'box'):
                mlflow.log_metric('final/mAP50', float(metrics.box.map50))
                mlflow.log_metric('final/mAP50-95', float(metrics.box.map))

        mlflow.end_run()


# ============================================================
# Training Functions
# ============================================================
def setup_wandb(config: TrainingConfig):
    """Weights & Biases 설정 (선택적)"""
    if not config.WANDB:
        return

    try:
        import wandb
        wandb.init(
            project=config.PROJECT,
            name=config.NAME,
            config={
                'model': config.MODEL_NAME,
                'epochs': config.EPOCHS,
                'batch_size': config.BATCH_SIZE,
                'img_size': config.IMG_SIZE,
                'optimizer': config.OPTIMIZER,
                'lr0': config.LR0,
            }
        )
        print("W&B initialized successfully")
    except ImportError:
        print("Warning: wandb not installed. Skipping W&B logging.")
        config.WANDB = False


def train(config: TrainingConfig = None):
    """
    YOLOv26n 모델 학습
    """
    if config is None:
        config = TrainingConfig()

    print("=" * 70)
    print("YOLOv26n Training for Ship Painting Defect Detection")
    print("=" * 70)
    print(f"Model: {config.MODEL_NAME}")
    print(f"Image Size: {config.IMG_SIZE} (optimized for 1080p)")
    print(f"Epochs: {config.EPOCHS}")
    print(f"Batch Size: {config.BATCH_SIZE}")
    print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print("=" * 70)

    # 데이터 존재 확인
    if not config.DATA_YAML.exists():
        print(f"Error: Data YAML not found at {config.DATA_YAML}")
        print("Run prepare_dataset.py first!")
        sys.exit(1)

    # 모델 로드
    if config.MODEL_PATH.exists():
        print(f"Loading pretrained model: {config.MODEL_PATH}")
        model = YOLO(str(config.MODEL_PATH))
    else:
        print(f"Warning: {config.MODEL_PATH} not found, using default yolov8n")
        model = YOLO('yolov8n.pt')

    # MLflow callback 설정
    mlflow_callback = MLflowCallback(config)

    # W&B 설정
    setup_wandb(config)

    # 학습 시작
    print("\nStarting training...")
    mlflow_callback.on_train_start(None)

    try:
        results = model.train(
            data=str(config.DATA_YAML),
            epochs=config.EPOCHS,
            batch=config.BATCH_SIZE,
            imgsz=config.IMG_SIZE,

            # Optimizer
            optimizer=config.OPTIMIZER,
            lr0=config.LR0,
            lrf=config.LRF,
            momentum=config.MOMENTUM,
            weight_decay=config.WEIGHT_DECAY,

            # Augmentation
            augment=config.AUGMENT,
            hsv_h=config.HSV_H,
            hsv_s=config.HSV_S,
            hsv_v=config.HSV_V,
            degrees=config.DEGREES,
            translate=config.TRANSLATE,
            scale=config.SCALE,
            shear=config.SHEAR,
            perspective=config.PERSPECTIVE,
            flipud=config.FLIPUD,
            fliplr=config.FLIPLR,
            mosaic=config.MOSAIC,
            mixup=config.MIXUP,

            # Logging
            project=str(config.PROJECT_DIR),
            name=config.NAME,

            # Training options
            patience=20,  # Early stopping patience
            save=True,
            save_period=10,  # Save every 10 epochs
            cache=True,  # Cache images for faster training
            device=0 if torch.cuda.is_available() else 'cpu',
            workers=4,
            verbose=True,
            plots=True,  # Generate plots
        )

        # MLflow에 결과 로깅
        if results:
            mlflow.log_metric('final/mAP50', float(results.results_dict.get('metrics/mAP50(B)', 0)))
            mlflow.log_metric('final/mAP50-95', float(results.results_dict.get('metrics/mAP50-95(B)', 0)))

        print("\n" + "=" * 70)
        print("Training completed!")
        print(f"Results saved to: {config.PROJECT_DIR / config.NAME}")
        print("=" * 70)

    except Exception as e:
        print(f"Training error: {e}")
        raise

    finally:
        mlflow.end_run()

    return model, results


def validate(model_path: str, data_yaml: str):
    """학습된 모델 검증"""
    model = YOLO(model_path)
    results = model.val(data=data_yaml)
    return results


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Train YOLOv26n for ship defect detection')
    parser.add_argument('--epochs', type=int, default=40, help='Number of epochs')
    parser.add_argument('--batch', type=int, default=8, help='Batch size')
    parser.add_argument('--img-size', type=int, default=1088, help='Image size')
    parser.add_argument('--wandb', action='store_true', help='Enable W&B logging')
    parser.add_argument('--resume', type=str, default=None, help='Resume from checkpoint')

    args = parser.parse_args()

    config = TrainingConfig()
    config.EPOCHS = args.epochs
    config.BATCH_SIZE = args.batch
    config.IMG_SIZE = args.img_size
    config.WANDB = args.wandb

    train(config)
