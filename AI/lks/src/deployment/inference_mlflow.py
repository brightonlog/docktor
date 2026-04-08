#!/usr/bin/env python3
"""
MLflow Model Registry에서 PatchCore Lite 모델 로드 및 추론

MLflow에 등록된 모델을 사용하여 이상탐지 수행

Usage:
    # 최신 Production 모델 사용
    python inference_mlflow.py --image path/to/image.jpg

    # 특정 버전 사용
    python inference_mlflow.py --image path/to/image.jpg --version 2

    # Run ID로 로드
    python inference_mlflow.py --image path/to/image.jpg --run-id abc123

    # 폴더 전체 추론
    python inference_mlflow.py --folder path/to/images/
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent  # deployment -> src -> lks
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import MLFLOW_TRACKING_URI
import mlflow
import mlflow.pyfunc

# ============================================================================
# MLflow Model Loader
# ============================================================================

def load_model_from_registry(model_name: str = "PatchCore-Lite-ShipCoating",
                            version: int = None,
                            stage: str = "Production"):
    """
    MLflow Model Registry에서 모델 로드

    Args:
        model_name: 모델 이름
        version: 모델 버전 (None이면 stage 사용)
        stage: 스테이지 ("Production", "Staging", "None")

    Returns:
        Loaded MLflow model
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    if version is not None:
        model_uri = f"models:/{model_name}/{version}"
        print(f"Loading model: {model_name} version {version}")
    else:
        model_uri = f"models:/{model_name}/{stage}"
        print(f"Loading model: {model_name} ({stage})")

    model = mlflow.pyfunc.load_model(model_uri)
    print("✓ Model loaded successfully")

    return model

def load_model_from_run(run_id: str, artifact_path: str = "patchcore_lite_model"):
    """
    특정 Run ID에서 모델 로드

    Args:
        run_id: MLflow Run ID
        artifact_path: 모델 artifact 경로

    Returns:
        Loaded MLflow model
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    model_uri = f"runs:/{run_id}/{artifact_path}"
    print(f"Loading model from run: {run_id}")

    model = mlflow.pyfunc.load_model(model_uri)
    print("✓ Model loaded successfully")

    return model

# ============================================================================
# Inference
# ============================================================================

def predict_single_image(model, image_path: Path):
    """단일 이미지 추론"""
    # Input 생성
    input_df = pd.DataFrame({
        'image_path': [str(image_path)]
    })

    # 추론
    score = model.predict(input_df)[0]

    return score

def predict_batch(model, image_paths: list):
    """배치 추론"""
    # Input 생성
    input_df = pd.DataFrame({
        'image_path': [str(p) for p in image_paths]
    })

    # 추론
    scores = model.predict(input_df)

    return scores

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='PatchCore Lite MLflow Inference')
    parser.add_argument('--image', type=str, help='Single image path')
    parser.add_argument('--folder', type=str, help='Folder containing images')

    # Model loading options
    parser.add_argument('--model-name', type=str, default='PatchCore-Lite-ShipCoating',
                       help='Model name in registry')
    parser.add_argument('--version', type=int, help='Model version')
    parser.add_argument('--stage', type=str, default='Production',
                       choices=['Production', 'Staging', 'None'],
                       help='Model stage (default: Production)')
    parser.add_argument('--run-id', type=str, help='Load from specific run ID')

    parser.add_argument('--threshold', type=float, help='Anomaly threshold')

    args = parser.parse_args()

    print("="*60)
    print("PatchCore Lite - MLflow Inference")
    print("="*60)

    # 모델 로드
    if args.run_id:
        model = load_model_from_run(args.run_id)
    else:
        model = load_model_from_registry(
            model_name=args.model_name,
            version=args.version,
            stage=args.stage
        )

    # 단일 이미지
    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: Image not found: {image_path}")
            return

        print(f"\nProcessing: {image_path}")

        # 추론
        score = predict_single_image(model, image_path)

        # 결과
        print("\n" + "="*60)
        print("Result")
        print("="*60)
        print(f"  Anomaly Score: {score:.6f}")

        if args.threshold:
            is_anomaly = score > args.threshold
            print(f"  Threshold: {args.threshold:.6f}")
            print(f"  Is Anomaly: {'YES' if is_anomaly else 'NO'}")

        print("="*60)

    # 폴더
    elif args.folder:
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"Error: Folder not found: {folder_path}")
            return

        # 이미지 파일 수집
        image_exts = {'.jpg', '.jpeg', '.png', '.bmp'}
        image_paths = [p for p in folder_path.iterdir()
                      if p.suffix.lower() in image_exts]

        print(f"\nFound {len(image_paths)} images")

        # 추론
        scores = predict_batch(model, image_paths)

        # 결과 출력
        print("\n" + "="*60)
        print("Results")
        print("="*60)

        for img_path, score in zip(image_paths, scores):
            if args.threshold:
                is_anomaly = score > args.threshold
                anomaly_str = "ANOMALY" if is_anomaly else "NORMAL"
                print(f"{img_path.name}: {score:.6f} ({anomaly_str})")
            else:
                print(f"{img_path.name}: {score:.6f}")

        print("="*60)

        # 통계
        print("\nStatistics:")
        print(f"  Mean score: {np.mean(scores):.6f}")
        print(f"  Std score: {np.std(scores):.6f}")
        print(f"  Min score: {np.min(scores):.6f}")
        print(f"  Max score: {np.max(scores):.6f}")

        if args.threshold:
            n_anomalies = sum(s > args.threshold for s in scores)
            print(f"  Anomalies detected: {n_anomalies}/{len(scores)} ({n_anomalies/len(scores)*100:.1f}%)")

        print("="*60)

    else:
        print("Error: Please specify --image or --folder")
        parser.print_help()

if __name__ == '__main__':
    main()
