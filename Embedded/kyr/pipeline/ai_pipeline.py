#!/usr/bin/env python3
"""
============================================================
AI Detection Pipeline - Core Implementation
============================================================
이미지를 입력받아 우선순위대로 AI 검사를 수행하는 핵심 파이프라인

처리 순서:
1. YOLO 결함 탐지 (Defect Detection)
2. 결함 없으면 → Anomaly Detection

입력: 이미지 파일 또는 폴더
출력: 결과 JSON + 시각화된 이미지
"""

import cv2
import time
import json
import argparse
import numpy as np
import torch
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from ultralytics import YOLO


# ============================================================
# Data Classes
# ============================================================

@dataclass
class PipelineResult:
    """파이프라인 처리 결과"""
    image_name: str
    timestamp: str

    # YOLO 결과
    yolo_detections: List[Dict]
    yolo_inference_ms: float
    has_defect: bool

    # Anomaly 결과
    anomaly_score: float
    anomaly_inference_ms: float
    has_anomaly: bool

    # 최종 판정
    final_status: str  # "normal", "defect", "anomaly"

    # 저장 경로
    output_image_path: str


# ============================================================
# YOLO Detector
# ============================================================

class YOLODetector:
    """YOLO 기반 결함 탐지"""

    def __init__(self, model_path: str, conf_threshold: float = 0.5):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.model = None
        self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            # TensorRT 엔진 우선 사용
            engine_path = self.model_path.replace('.pt', '.engine')
            if Path(engine_path).exists():
                print(f"[YOLO] Loading TensorRT model: {engine_path}")
                self.model = YOLO(engine_path)
            else:
                print(f"[YOLO] Loading PyTorch model: {self.model_path}")
                self.model = YOLO(self.model_path)
            print("[YOLO] ✅ Model loaded successfully")
        except Exception as e:
            print(f"[YOLO] ❌ Model load failed: {e}")
            self.model = None

    def detect(self, image: np.ndarray) -> Tuple[List[Dict], float, bool]:
        """
        결함 탐지

        Returns:
            detections: 탐지된 결함 리스트
            inference_time: 추론 시간 (ms)
            has_defect: 결함 존재 여부
        """
        if self.model is None:
            return [], 0.0, False

        start_time = time.time()
        results = self.model(image, conf=self.conf_threshold, verbose=False)
        inference_time = (time.time() - start_time) * 1000

        detections = []
        for box in results[0].boxes:
            detections.append({
                'class_id': int(box.cls[0]),
                'class_name': self.model.names[int(box.cls[0])],
                'confidence': float(box.conf[0]),
                'bbox': [float(x) for x in box.xyxy[0].tolist()]
            })

        has_defect = len(detections) > 0
        return detections, inference_time, has_defect


# ============================================================
# Anomaly Detector
# ============================================================

class AnomalyDetector:
    """Autoencoder 기반 이상 탐지"""

    def __init__(self, model_path: str, threshold: float = 0.7):
        self.model_path = model_path
        self.threshold = threshold
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            if Path(self.model_path).exists():
                print(f"[ANOMALY] Loading model: {self.model_path}")
                self.model = torch.load(self.model_path, map_location=self.device)
                self.model.eval()
                print("[ANOMALY] ✅ Model loaded successfully")
            else:
                print(f"[ANOMALY] ⚠️ Model file not found: {self.model_path}")
                print("[ANOMALY] Using placeholder mode")
                self.model = None
        except Exception as e:
            print(f"[ANOMALY] ⚠️ Model load failed: {e}")
            print("[ANOMALY] Using placeholder mode")
            self.model = None

    def detect(self, image: np.ndarray) -> Tuple[float, float, bool]:
        """
        이상 탐지

        Returns:
            anomaly_score: 이상 점수 (0~1)
            inference_time: 추론 시간 (ms)
            has_anomaly: 이상 존재 여부
        """
        start_time = time.time()

        if self.model is None:
            # Placeholder: 랜덤 점수 생성
            anomaly_score = np.random.random()
        else:
            # TODO: 실제 Autoencoder 추론 로직
            # 1. 이미지 전처리
            # 2. 모델 추론
            # 3. Reconstruction error 계산
            anomaly_score = np.random.random()

        inference_time = (time.time() - start_time) * 1000
        has_anomaly = anomaly_score > self.threshold

        return anomaly_score, inference_time, has_anomaly


# ============================================================
# AI Pipeline
# ============================================================

class AIPipeline:
    """AI 검사 파이프라인"""

    def __init__(
        self,
        yolo_model_path: str = '../models/yolo/best_fixed.pt',
        anomaly_model_path: str = '../models/anomaly_detection/best_model.pt',
        yolo_conf: float = 0.5,
        anomaly_threshold: float = 0.7,
        output_dir: str = '../pipeline_results'
    ):
        print("\n" + "=" * 70)
        print("  AI Detection Pipeline - Initialization")
        print("=" * 70)

        self.yolo = YOLODetector(yolo_model_path, yolo_conf)
        self.anomaly = AnomalyDetector(anomaly_model_path, anomaly_threshold)

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 세션별 폴더 생성
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"session_{session_timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        print(f"[PIPELINE] Output directory: {self.session_dir}")
        print("=" * 70 + "\n")

    def process_image(self, image_path: str) -> PipelineResult:
        """
        단일 이미지 처리

        처리 순서:
        1. YOLO 결함 탐지
        2. 결함이 없으면 Anomaly Detection 수행

        Args:
            image_path: 입력 이미지 경로

        Returns:
            PipelineResult 객체
        """
        image_path = Path(image_path)
        image_name = image_path.name

        print(f"\n{'='*70}")
        print(f"Processing: {image_name}")
        print(f"{'='*70}")

        # 이미지 로드
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        print(f"[INFO] Image loaded: {image.shape}")

        # Step 1: YOLO 결함 탐지
        print(f"\n[STEP 1] Running YOLO Defect Detection...")
        yolo_detections, yolo_time, has_defect = self.yolo.detect(image)

        print(f"  ⏱️  Inference time: {yolo_time:.2f} ms")
        print(f"  📊 Detections: {len(yolo_detections)}")

        if has_defect:
            print(f"  ❌ DEFECT FOUND!")
            for det in yolo_detections:
                print(f"     - {det['class_name']}: {det['confidence']:.2%}")

            final_status = "defect"
            anomaly_score = 0.0
            anomaly_time = 0.0
            has_anomaly = False
        else:
            print(f"  ✅ No defects detected")

            # Step 2: Anomaly Detection (결함이 없을 때만)
            print(f"\n[STEP 2] Running Anomaly Detection...")
            anomaly_score, anomaly_time, has_anomaly = self.anomaly.detect(image)

            print(f"  ⏱️  Inference time: {anomaly_time:.2f} ms")
            print(f"  📊 Anomaly score: {anomaly_score:.4f}")

            if has_anomaly:
                print(f"  ⚠️  ANOMALY DETECTED!")
                final_status = "anomaly"
            else:
                print(f"  ✅ Normal")
                final_status = "normal"

        # 시각화
        print(f"\n[STEP 3] Visualizing results...")
        visualized_image = self._visualize_result(
            image, yolo_detections, anomaly_score, final_status
        )

        # 저장
        output_filename = f"{image_path.stem}_result.jpg"
        output_path = self.session_dir / output_filename
        cv2.imwrite(str(output_path), visualized_image)
        print(f"  💾 Saved: {output_path.name}")

        # 결과 생성
        result = PipelineResult(
            image_name=image_name,
            timestamp=datetime.now().isoformat(),
            yolo_detections=yolo_detections,
            yolo_inference_ms=yolo_time,
            has_defect=has_defect,
            anomaly_score=anomaly_score,
            anomaly_inference_ms=anomaly_time,
            has_anomaly=has_anomaly,
            final_status=final_status,
            output_image_path=str(output_path)
        )

        print(f"\n{'='*70}")
        print(f"✅ Final Status: {final_status.upper()}")
        print(f"{'='*70}\n")

        return result

    def process_batch(self, input_path: str) -> List[PipelineResult]:
        """
        배치 처리 (폴더 또는 단일 이미지)

        Args:
            input_path: 이미지 파일 또는 폴더 경로

        Returns:
            PipelineResult 리스트
        """
        input_path = Path(input_path)

        # 이미지 파일 목록 생성
        if input_path.is_file():
            image_files = [input_path]
        elif input_path.is_dir():
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                image_files.extend(input_path.glob(ext))
            image_files = sorted(image_files)
        else:
            raise ValueError(f"Invalid input path: {input_path}")

        if not image_files:
            print(f"[WARNING] No images found in: {input_path}")
            return []

        print(f"\n{'='*70}")
        print(f"Found {len(image_files)} images to process")
        print(f"{'='*70}")

        # 배치 처리
        results = []
        for idx, image_file in enumerate(image_files, 1):
            print(f"\n[{idx}/{len(image_files)}]")
            try:
                result = self.process_image(image_file)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Failed to process {image_file.name}: {e}")

        # 통합 결과 저장
        self._save_batch_results(results)

        return results

    def _visualize_result(
        self,
        image: np.ndarray,
        yolo_detections: List[Dict],
        anomaly_score: float,
        final_status: str
    ) -> np.ndarray:
        """결과 시각화"""
        vis_image = image.copy()
        h, w = vis_image.shape[:2]

        # 결함 바운딩 박스 그리기
        for det in yolo_detections:
            bbox = det['bbox']
            x1, y1, x2, y2 = map(int, bbox)

            # BBox
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 0, 255), 3)

            # 라벨
            label = f"{det['class_name']} {det['confidence']:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(vis_image, (x1, y1 - label_size[1] - 10),
                         (x1 + label_size[0], y1), (0, 0, 255), -1)
            cv2.putText(vis_image, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # 상태별 테두리 및 텍스트
        if final_status == "defect":
            border_color = (0, 0, 255)  # 빨강
            status_text = "DEFECT DETECTED"
        elif final_status == "anomaly":
            border_color = (0, 255, 255)  # 노랑
            status_text = f"ANOMALY (score: {anomaly_score:.4f})"
        else:
            border_color = (0, 255, 0)  # 초록
            status_text = "NORMAL"

        # 테두리
        cv2.rectangle(vis_image, (0, 0), (w-1, h-1), border_color, 15)

        # 상단 중앙 텍스트
        text_size, _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_DUPLEX, 1.2, 3)
        text_x = (w - text_size[0]) // 2
        text_y = 50

        # 배경
        cv2.rectangle(vis_image,
                     (text_x - 10, text_y - text_size[1] - 10),
                     (text_x + text_size[0] + 10, text_y + 10),
                     (0, 0, 0), -1)

        # 텍스트
        cv2.putText(vis_image, status_text, (text_x, text_y),
                   cv2.FONT_HERSHEY_DUPLEX, 1.2, border_color, 3)

        # 타임스탬프
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(vis_image, timestamp, (w - 250, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return vis_image

    def _save_batch_results(self, results: List[PipelineResult]):
        """배치 결과를 JSON으로 저장"""
        results_file = self.session_dir / "results.json"

        # 통계 계산
        total = len(results)
        defects = sum(1 for r in results if r.final_status == "defect")
        anomalies = sum(1 for r in results if r.final_status == "anomaly")
        normals = sum(1 for r in results if r.final_status == "normal")

        avg_yolo_time = np.mean([r.yolo_inference_ms for r in results]) if results else 0
        avg_anomaly_time = np.mean([r.anomaly_inference_ms for r in results if r.anomaly_inference_ms > 0]) if results else 0

        output_data = {
            'session_dir': self.session_dir.name,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_images': total,
                'defect_count': defects,
                'anomaly_count': anomalies,
                'normal_count': normals,
                'avg_yolo_inference_ms': float(avg_yolo_time),
                'avg_anomaly_inference_ms': float(avg_anomaly_time)
            },
            'results': [asdict(r) for r in results]
        }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"📊 Batch Processing Summary")
        print(f"{'='*70}")
        print(f"Total images:    {total}")
        print(f"  - Defects:     {defects}")
        print(f"  - Anomalies:   {anomalies}")
        print(f"  - Normal:      {normals}")
        print(f"\nAverage inference time:")
        print(f"  - YOLO:        {avg_yolo_time:.2f} ms")
        print(f"  - Anomaly:     {avg_anomaly_time:.2f} ms")
        print(f"\n💾 Results saved: {results_file}")
        print(f"{'='*70}\n")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='AI Detection Pipeline - Process images with YOLO and Anomaly Detection'
    )
    parser.add_argument(
        'input',
        type=str,
        help='Input image file or directory'
    )
    parser.add_argument(
        '--yolo-model',
        type=str,
        default='../models/yolo/best_fixed.pt',
        help='YOLO model path (default: ../models/yolo/best_fixed.pt)'
    )
    parser.add_argument(
        '--anomaly-model',
        type=str,
        default='../models/anomaly_detection/best_model.pt',
        help='Anomaly detection model path'
    )
    parser.add_argument(
        '--yolo-conf',
        type=float,
        default=0.5,
        help='YOLO confidence threshold (default: 0.5)'
    )
    parser.add_argument(
        '--anomaly-threshold',
        type=float,
        default=0.7,
        help='Anomaly detection threshold (default: 0.7)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='../pipeline_results',
        help='Output directory (default: ../pipeline_results)'
    )

    args = parser.parse_args()

    # 파이프라인 생성
    pipeline = AIPipeline(
        yolo_model_path=args.yolo_model,
        anomaly_model_path=args.anomaly_model,
        yolo_conf=args.yolo_conf,
        anomaly_threshold=args.anomaly_threshold,
        output_dir=args.output_dir
    )

    # 처리 실행
    try:
        results = pipeline.process_batch(args.input)
        print(f"\n✅ Processing complete! Check results in: {pipeline.session_dir}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
