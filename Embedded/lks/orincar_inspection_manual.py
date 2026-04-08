#!/usr/bin/env python3
"""
============================================================
Orin Car Inspection System - MANUAL MODE (수동 모드)
============================================================
- 모터 없이 손으로 오린카를 밀면서 실습할 수 있는 버전
- 각 Zone마다 수동으로 촬영 및 탐지
- 웹 UI에서 Zone별로 제어
"""

import cv2
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from flask import Flask, render_template_string, jsonify, request, Response
from ultralytics import YOLO
import numpy as np
import torch

# 시각화 유틸리티 import
from visualization_utils import visualize_inspection_result, add_timestamp


# ============================================================
# Data Classes
# ============================================================

@dataclass
class DetectionResult:
    """단일 탐지 결과"""
    zone_id: int
    zone_type: str
    timestamp: str
    detections: List[Dict]
    image_path: str
    inference_time_ms: float
    is_defective: bool


@dataclass
class InspectionConfig:
    """검사 설정"""
    total_length_cm: int = 180
    zone_length_cm: int = 30
    yolo_conf_threshold: float = 0.5
    anomaly_threshold: float = 0.7

    zone_types: List[str] = None

    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = [
                'normal',   # Zone 0
                'normal',   # Zone 1
                'anomaly',  # Zone 2
                'defect',   # Zone 3
                'defect',   # Zone 4
                'defect'    # Zone 5
            ]

    @property
    def num_zones(self) -> int:
        return self.total_length_cm // self.zone_length_cm


# ============================================================
# Camera Controller
# ============================================================

class CameraController:
    """카메라 제어 클래스"""

    def __init__(self):
        self.camera = None
        self.init_camera()

    def init_camera(self):
        """카메라 초기화"""
        pipeline = (
            "v4l2src device=/dev/video0 ! "
            "image/jpeg, width=640, height=480, framerate=30/1 ! "
            "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true"
        )

        print("[INFO] Initializing camera...")
        self.camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        if not self.camera.isOpened():
            print("[WARN] GStreamer failed, trying V4L2...")
            self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        if self.camera.isOpened():
            print("[SUCCESS] Camera initialized")
        else:
            print("[ERROR] Camera initialization failed")

    def capture_frame(self) -> Optional[np.ndarray]:
        """프레임 캡처"""
        if not self.camera or not self.camera.isOpened():
            print("[ERROR] Camera not available")
            return None

        success, frame = self.camera.read()
        if success:
            return frame
        return None

    def save_image(self, frame: np.ndarray, filepath: str):
        """이미지 저장"""
        cv2.imwrite(filepath, frame)
        print(f"[CAMERA] Image saved: {filepath}")

    def release(self):
        """카메라 해제"""
        if self.camera:
            self.camera.release()
            print("[CAMERA] Released")


# ============================================================
# YOLO Detector
# ============================================================

class YOLODetector:
    """YOLO 기반 결함 탐지"""

    def __init__(self, model_path: str, conf_threshold: float = 0.5):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.model = None
        self.model_loaded = self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            # 모델 파일 존재 확인
            if not Path(self.model_path).exists():
                print(f"[ERROR] YOLO model file not found: {self.model_path}")
                self.model = None
                return False

            engine_path = self.model_path.replace('.pt', '.engine')
            if Path(engine_path).exists():
                print(f"[YOLO] Loading TensorRT model: {engine_path}")
                self.model = YOLO(engine_path)
            else:
                print(f"[YOLO] Loading PyTorch model: {self.model_path}")
                self.model = YOLO(self.model_path)

            # 모델 로드 검증
            if self.model is None:
                print("[ERROR] YOLO model is None after loading")
                return False

            print("[YOLO] Model loaded successfully")
            print(f"[YOLO] Model classes: {list(self.model.names.values())}")
            return True

        except Exception as e:
            print(f"[ERROR] YOLO model load failed: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            return False

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float, bool]:
        """결함 탐지"""
        if self.model is None:
            print("[ERROR] YOLO model not loaded, cannot detect")
            return [], 0.0, False

        try:
            start_time = time.time()
            results = self.model(frame, conf=self.conf_threshold, verbose=False)
            inference_time = (time.time() - start_time) * 1000

            detections = []
            for box in results[0].boxes:
                detections.append({
                    'class_id': int(box.cls[0]),
                    'class_name': self.model.names[int(box.cls[0])],
                    'confidence': float(box.conf[0]),
                    'bbox': box.xyxy[0].tolist()
                })

            is_defective = len(detections) > 0
            return detections, inference_time, is_defective

        except Exception as e:
            print(f"[ERROR] YOLO detection failed: {e}")
            return [], 0.0, False


# ============================================================
# Anomaly Detector
# ============================================================

class AnomalyDetector:
    """Autoencoder 기반 이상 탐지 (Placeholder)"""

    def __init__(self, model_path: str, threshold: float = 0.7):
        self.model_path = model_path
        self.threshold = threshold
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            print(f"[ANOMALY] Loading model: {self.model_path}")
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()
            print("[ANOMALY] Model loaded successfully")
        except Exception as e:
            print(f"[WARN] Anomaly model load failed: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float, bool]:
        """이상 탐지 (Placeholder)"""
        if self.model is None:
            print("[WARN] Anomaly model not available, using random detection")
            reconstruction_error = np.random.random()
        else:
            # TODO: 실제 Autoencoder 추론 로직 구현
            reconstruction_error = np.random.random()

        inference_time = 10.0  # Placeholder
        is_anomaly = reconstruction_error > self.threshold

        detections = []
        if is_anomaly:
            detections.append({
                'type': 'anomaly',
                'score': float(reconstruction_error),
                'description': f'Anomaly detected (score: {reconstruction_error:.4f})'
            })

        return detections, inference_time, is_anomaly


# ============================================================
# Manual Inspection System
# ============================================================

class ManualInspectionSystem:
    """수동 검사 시스템"""

    def __init__(self, config: InspectionConfig, camera: CameraController = None):
        self.config = config
        # 전역 카메라를 받거나, 없으면 새로 생성
        self.camera = camera if camera else CameraController()
        self.owns_camera = (camera is None)  # 카메라를 직접 생성했는지 여부

        # 스크립트 파일 위치 기준으로 경로 계산
        script_dir = Path(__file__).parent
        models_dir = script_dir.parent / 'models'

        # 모델 로드
        print("\n[SYSTEM] Loading AI models...")
        print(f"[SYSTEM] Script directory: {script_dir}")
        print(f"[SYSTEM] Models directory: {models_dir}")

        yolo_model_path = models_dir / 'yolo' / 'best_fixed.pt'
        anomaly_model_path = models_dir / 'anomaly_detection' / 'best_model.pt'

        print(f"[SYSTEM] YOLO model path: {yolo_model_path}")
        print(f"[SYSTEM] Anomaly model path: {anomaly_model_path}")

        self.yolo = YOLODetector(
            model_path=str(yolo_model_path),
            conf_threshold=config.yolo_conf_threshold
        )
        self.anomaly = AnomalyDetector(
            model_path=str(anomaly_model_path),
            threshold=config.anomaly_threshold
        )

        # 모델 로드 상태 검증
        if not self.yolo.model_loaded:
            print("\n" + "=" * 70)
            print("❌ CRITICAL ERROR: YOLO model failed to load!")
            print("   Please check:")
            print("   1. Model file exists: ../models/yolo/best_fixed.pt")
            print("   2. Model file is not corrupted")
            print("   3. Enough memory available")
            print("=" * 70)
            raise RuntimeError("YOLO model load failed - cannot start system")

        print("[SYSTEM] ✅ YOLO model loaded successfully")
        if self.anomaly.model is not None:
            print("[SYSTEM] ✅ Anomaly model loaded successfully")
        else:
            print("[SYSTEM] ⚠️  Anomaly model not loaded (using YOLO for all zones)")

        self.results: List[DetectionResult] = []
        self.current_zone = 0
        self.is_active = False
        self.current_frame = None  # 실시간 모니터링용
        self.frame_lock = threading.Lock()  # 프레임 동기화

        # 결과 저장 디렉토리 (스크립트 위치 기준)
        self.output_dir = script_dir.parent / 'inspection_results'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[SYSTEM] Output directory: {self.output_dir.absolute()}")
        print("[SYSTEM] System initialization complete\n")

    def start_session(self):
        """세션 시작"""
        self.is_active = True
        self.results = []
        self.current_zone = 0

        # 세션별 폴더 생성
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"session_{session_timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 70)
        print("🖐️  Manual Inspection Session Started")
        print(f"Total zones: {self.config.num_zones}")
        print(f"Session folder: {self.session_dir.name}")
        print("Move the car manually and capture each zone!")
        print("=" * 70)

    def inspect_current_zone(self) -> DetectionResult:
        """현재 Zone 검사"""
        zone_id = self.current_zone
        zone_type = self.config.zone_types[zone_id]
        timestamp = datetime.now().isoformat()

        print(f"\n[Zone {zone_id + 1}/{self.config.num_zones}] Inspecting...")
        print(f"  Type: {zone_type}")

        # 카메라 촬영
        print(f"  📷 Capturing image...")
        frame = self.camera.capture_frame()

        # 실시간 모니터링용 프레임 업데이트
        with self.frame_lock:
            self.current_frame = frame.copy() if frame is not None else None

        if frame is None:
            print("  [ERROR] Failed to capture frame")
            return DetectionResult(
                zone_id=zone_id,
                zone_type=zone_type,
                timestamp=timestamp,
                detections=[],
                image_path='',
                inference_time_ms=0.0,
                is_defective=False
            )

        # 탐지 수행
        detections = []
        inference_time = 0.0
        is_defective = False

        if zone_type == 'normal':
            print(f"  ✓ Normal zone - No detection")

        else:  # 'anomaly' 또는 'defect' 모두 YOLO 사용
            print(f"  🔍 Running YOLO defect detection...")
            detections, inference_time, is_defective = self.yolo.detect(frame)
            print(f"  Result: {len(detections)} defects detected ({inference_time:.2f}ms)")
            if detections:
                for det in detections:
                    print(f"    - {det['class_name']}: {det['confidence']:.2f}")

        # 시각화된 이미지 생성
        print(f"  🎨 Visualizing results...")
        try:
            visualized_frame = visualize_inspection_result(
                frame.copy(), zone_id, zone_type, detections, is_defective
            )
        except Exception as e:
            print(f"  [WARN] Visualization failed: {e}, using original frame")
            visualized_frame = frame.copy()

        # 타임스탬프 추가
        try:
            visualized_frame = add_timestamp(visualized_frame, timestamp)
        except Exception as e:
            print(f"  [WARN] Timestamp add failed: {e}")

        # 시각화된 이미지 저장 (세션 폴더에)
        image_filename = f"zone_{zone_id:02d}_{zone_type}.jpg"
        image_path = str(self.session_dir / image_filename)

        # 저장 시도 및 결과 확인
        success = cv2.imwrite(image_path, visualized_frame)
        if success:
            print(f"  💾 Saved: {self.session_dir.name}/{image_filename}")
            # 파일이 실제로 존재하는지 확인
            if not Path(image_path).exists():
                print(f"  [ERROR] File was not created: {image_path}")
        else:
            print(f"  [ERROR] Failed to save image: {image_path}")
            print(f"  Frame shape: {visualized_frame.shape}, dtype: {visualized_frame.dtype}")

        result = DetectionResult(
            zone_id=zone_id,
            zone_type=zone_type,
            timestamp=timestamp,
            detections=detections,
            image_path=image_path,
            inference_time_ms=inference_time,
            is_defective=is_defective
        )

        self.results.append(result)
        print(f"[Zone {zone_id + 1}] Complete")

        return result

    def next_zone(self) -> bool:
        """다음 Zone으로 이동"""
        self.current_zone += 1
        if self.current_zone >= self.config.num_zones:
            self.finish_session()
            return False
        return True

    def finish_session(self):
        """세션 종료"""
        self.is_active = False
        print("\n" + "=" * 70)
        print("✅ Manual Inspection Session Complete!")
        print(f"Total zones inspected: {len(self.results)}")
        print(f"Defective zones: {sum(1 for r in self.results if r.is_defective)}")
        print("=" * 70)
        self.save_results()

    def save_results(self):
        """결과 저장 (세션 폴더에)"""
        results_file = self.session_dir / "inspection_results.json"

        results_data = {
            'mode': 'manual',
            'session_folder': self.session_dir.name,
            'config': asdict(self.config),
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(r) for r in self.results],
            'summary': {
                'total_zones': len(self.results),
                'defective_zones': sum(1 for r in self.results if r.is_defective),
                'normal_zones': sum(1 for r in self.results if r.zone_type == 'normal'),
                'anomaly_zones': sum(1 for r in self.results if r.zone_type == 'anomaly'),
                'defect_zones': sum(1 for r in self.results if r.zone_type == 'defect'),
            }
        }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Results saved: {self.session_dir.name}/inspection_results.json")

    def generate_frames(self):
        """실시간 카메라 피드 생성 (웹 UI용)"""
        while True:
            # 현재 프레임 가져오기
            with self.frame_lock:
                if self.current_frame is not None:
                    frame = self.current_frame.copy()
                else:
                    # 프레임이 없으면 카메라에서 직접 캡처
                    frame = self.camera.capture_frame()

            if frame is None:
                # 검은 화면 생성
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "No Camera Feed", (200, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # Zone 정보 오버레이
            if self.is_active:
                zone_text = f"Zone {self.current_zone + 1}/{self.config.num_zones}"
                zone_type = self.config.zone_types[self.current_zone]
                status_text = f"{zone_type.upper()}"

                cv2.putText(frame, zone_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(frame, status_text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # JPEG 인코딩
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            # 스트리밍 형식으로 yield
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            time.sleep(0.03)  # ~30 FPS

    def cleanup(self):
        """정리"""
        # 자신이 생성한 카메라만 해제 (전역 카메라는 해제하지 않음)
        if self.owns_camera and self.camera:
            self.camera.release()
            print("[INFO] System cleanup complete (camera released)")
        else:
            print("[INFO] System cleanup complete (camera shared)")


# ============================================================
# Flask Web Application
# ============================================================

app = Flask(__name__)
inspection_system = None
global_camera = None  # 전역 카메라 (리소스 충돌 방지)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Orin Car Manual Inspection</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .manual-badge {
            display: inline-block;
            background: #f59e0b;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 1em;
            font-weight: bold;
            margin-top: 10px;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        .instructions {
            background: rgba(245, 158, 11, 0.2);
            border-left: 4px solid #f59e0b;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .instructions h3 {
            margin-bottom: 15px;
            color: #fbbf24;
        }
        .instructions ol {
            margin-left: 20px;
            line-height: 1.8;
        }
        .controls {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
            margin: 20px 0;
        }
        .btn {
            padding: 15px 30px;
            font-size: 1.1em;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            text-transform: uppercase;
        }
        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-start {
            background: #10b981;
            color: white;
        }
        .btn-capture {
            background: #3b82f6;
            color: white;
            font-size: 1.3em;
            padding: 20px 40px;
        }
        .btn-next {
            background: #f59e0b;
            color: white;
        }
        .btn-finish {
            background: #ef4444;
            color: white;
        }
        .status {
            text-align: center;
            font-size: 1.3em;
            margin: 20px 0;
            padding: 20px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 8px;
        }
        .current-zone {
            font-size: 2em;
            font-weight: bold;
            color: #fbbf24;
            margin: 15px 0;
        }
        .zone-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .zone-card {
            background: rgba(255, 255, 255, 0.08);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 3px solid transparent;
        }
        .zone-card.normal { border-color: #10b981; }
        .zone-card.anomaly { border-color: #f59e0b; }
        .zone-card.defect { border-color: #ef4444; }
        .zone-card.current {
            animation: pulse 2s infinite;
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.5);
        }
        .zone-card.completed {
            background: rgba(16, 185, 129, 0.2);
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        .zone-title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .zone-type {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            margin: 5px 0;
        }
        .type-normal { background: #10b981; }
        .type-anomaly { background: #f59e0b; }
        .type-defect { background: #ef4444; }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .summary-item {
            background: rgba(255, 255, 255, 0.08);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .summary-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .summary-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        .last-detection {
            background: rgba(255, 255, 255, 0.08);
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            text-align: left;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖐️ Orin Car Manual Inspection</h1>
            <div class="manual-badge">MANUAL MODE - Hand Control</div>
            <p style="margin-top: 15px;">손으로 오린카를 밀면서 검사하세요!</p>
        </div>

        <div class="card instructions">
            <h3>📋 사용 방법</h3>
            <ol>
                <li><strong>"세션 시작"</strong> 버튼을 눌러 검사를 시작합니다</li>
                <li>오린카를 <strong>Zone 0 위치</strong>에 놓습니다</li>
                <li><strong>"현재 Zone 촬영"</strong> 버튼을 눌러 촬영 및 탐지합니다</li>
                <li>오린카를 <strong>손으로 30cm</strong> 앞으로 밉니다</li>
                <li><strong>"다음 Zone"</strong> 버튼을 누릅니다</li>
                <li><strong>3~5번 과정</strong>을 반복합니다 (총 6개 Zone)</li>
                <li>모든 Zone 완료 시 자동으로 결과가 저장됩니다</li>
            </ol>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">📹 실시간 모니터링</h2>
            <div style="text-align: center;">
                <img src="/video_feed" style="max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);" alt="Camera Feed">
            </div>
        </div>

        <div class="card">
            <div class="controls">
                <button class="btn btn-start" id="btnStart" onclick="startSession()">
                    🚀 세션 시작
                </button>
            </div>

            <div class="status" id="status">세션 시작 버튼을 눌러주세요</div>

            <div id="activeControls" style="display: none;">
                <div class="current-zone" id="currentZone">Zone 1</div>

                <div class="controls">
                    <button class="btn btn-capture" id="btnCapture" onclick="captureZone()">
                        📷 현재 Zone 촬영
                    </button>
                </div>

                <div class="controls">
                    <button class="btn btn-next" id="btnNext" onclick="nextZone()" disabled>
                        ➡️ 다음 Zone
                    </button>
                    <button class="btn btn-finish" onclick="finishSession()">
                        🏁 세션 종료
                    </button>
                </div>

                <div class="last-detection" id="lastDetection" style="display: none;">
                    <strong>마지막 탐지 결과:</strong>
                    <div id="detectionInfo" style="margin-top: 10px;"></div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">📍 Zone 진행 상황</h2>
            <div class="zone-grid" id="zones"></div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">📈 통계</h2>
            <div class="summary" id="summary"></div>
        </div>
    </div>

    <script>
        let isActive = false;
        let currentZone = 0;
        let zoneCaptured = false;

        function startSession() {
            fetch('/api/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        isActive = true;
                        currentZone = 0;
                        zoneCaptured = false;
                        document.getElementById('btnStart').disabled = true;
                        document.getElementById('activeControls').style.display = 'block';
                        updateUI();
                    }
                    alert(data.message);
                });
        }

        function captureZone() {
            document.getElementById('btnCapture').disabled = true;
            document.getElementById('status').innerHTML = '📷 촬영 및 탐지 중...';

            fetch('/api/capture', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    zoneCaptured = true;
                    document.getElementById('btnCapture').disabled = false;
                    document.getElementById('btnNext').disabled = false;

                    // 탐지 결과 표시
                    const detectionDiv = document.getElementById('lastDetection');
                    const infoDiv = document.getElementById('detectionInfo');

                    let info = `<strong>Zone ${data.zone_id + 1} (${data.zone_type})</strong><br>`;
                    info += `추론 시간: ${data.inference_time_ms.toFixed(2)} ms<br>`;
                    info += `결함 여부: ${data.is_defective ? '❌ 결함 발견' : '✅ 정상'}<br>`;

                    if (data.detections && data.detections.length > 0) {
                        info += `<br><strong>탐지된 결함:</strong><br>`;
                        data.detections.forEach(det => {
                            if (det.class_name) {
                                info += `- ${det.class_name} (${(det.confidence * 100).toFixed(1)}%)<br>`;
                            } else if (det.description) {
                                info += `- ${det.description}<br>`;
                            }
                        });
                    }

                    infoDiv.innerHTML = info;
                    detectionDiv.style.display = 'block';

                    updateUI();
                });
        }

        function nextZone() {
            if (!zoneCaptured) {
                alert('먼저 현재 Zone을 촬영해주세요!');
                return;
            }

            fetch('/api/next', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.finished) {
                        alert('✅ 모든 Zone 검사 완료!');
                        isActive = false;
                        document.getElementById('activeControls').style.display = 'none';
                        document.getElementById('btnStart').disabled = false;
                    } else {
                        currentZone = data.current_zone;
                        zoneCaptured = false;
                        document.getElementById('btnNext').disabled = true;
                        document.getElementById('lastDetection').style.display = 'none';
                        alert(`다음 Zone으로 이동합니다. 오린카를 30cm 앞으로 밀어주세요!`);
                    }
                    updateUI();
                });
        }

        function finishSession() {
            if (confirm('정말 세션을 종료하시겠습니까?')) {
                fetch('/api/finish', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        isActive = false;
                        document.getElementById('activeControls').style.display = 'none';
                        document.getElementById('btnStart').disabled = false;
                        updateUI();
                    });
            }
        }

        function updateUI() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    // Status
                    const statusEl = document.getElementById('status');
                    if (data.is_active) {
                        const action = zoneCaptured ? '오린카를 30cm 밀고 "다음 Zone" 클릭' : '"현재 Zone 촬영" 클릭';
                        statusEl.innerHTML = `🎯 Zone ${data.current_zone + 1} / ${data.total_zones} - ${action}`;
                    } else {
                        statusEl.innerHTML = data.completed_zones > 0
                            ? `✅ 검사 완료 - ${data.completed_zones} zones`
                            : '세션 시작 버튼을 눌러주세요';
                    }

                    // Current zone
                    document.getElementById('currentZone').innerHTML =
                        `Zone ${data.current_zone + 1} - ${data.zone_types[data.current_zone].toUpperCase()}`;

                    // Zones
                    const zonesEl = document.getElementById('zones');
                    zonesEl.innerHTML = '';
                    data.zone_types.forEach((type, idx) => {
                        const isCurrent = data.is_active && idx === data.current_zone;
                        const isCompleted = idx < data.completed_zones;
                        const zoneCard = document.createElement('div');
                        zoneCard.className = `zone-card ${type} ${isCurrent ? 'current' : ''} ${isCompleted ? 'completed' : ''}`;
                        zoneCard.innerHTML = `
                            <div class="zone-title">Zone ${idx + 1}</div>
                            <span class="zone-type type-${type}">${type.toUpperCase()}</span>
                            <div style="margin-top: 10px; font-size: 1.5em;">
                                ${isCurrent ? '🎯' : isCompleted ? '✅' : '⏳'}
                            </div>
                        `;
                        zonesEl.appendChild(zoneCard);
                    });

                    // Summary
                    const summaryEl = document.getElementById('summary');
                    summaryEl.innerHTML = `
                        <div class="summary-item">
                            <div class="summary-label">Total Zones</div>
                            <div class="summary-value">${data.total_zones}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Completed</div>
                            <div class="summary-value">${data.completed_zones}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-label">Defective</div>
                            <div class="summary-value" style="color: #ef4444;">${data.defective_zones}</div>
                        </div>
                    `;
                });
        }

        // Initial load
        updateUI();
        setInterval(updateUI, 3000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """메인 페이지"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed')
def video_feed():
    """실시간 비디오 스트림"""
    global inspection_system, global_camera

    # 전역 카메라 초기화 (최초 1회)
    if global_camera is None:
        global_camera = CameraController()

    if not inspection_system:
        # 시스템이 없으면 카메라 프리뷰만 보여주기
        def preview_feed():
            while True:
                frame = global_camera.capture_frame()

                if frame is None:
                    # 카메라 실패시 에러 메시지
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "Camera Error", (200, 220),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame, "Check camera connection", (140, 260),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                else:
                    # 대기 중 메시지 오버레이
                    cv2.putText(frame, "Waiting for session start", (120, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, "Press 'Start Session' button", (100, 450),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

                time.sleep(0.03)  # ~30 FPS

        return Response(preview_feed(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

    return Response(inspection_system.generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/start', methods=['POST'])
def api_start():
    """세션 시작"""
    global inspection_system, global_camera

    if inspection_system and inspection_system.is_active:
        return jsonify({
            'success': False,
            'message': '이미 세션이 진행 중입니다'
        })

    # 전역 카메라 초기화 (아직 안 되어있으면)
    if global_camera is None:
        global_camera = CameraController()

    config = InspectionConfig()
    # 전역 카메라를 전달하여 시스템 생성
    inspection_system = ManualInspectionSystem(config, camera=global_camera)
    inspection_system.start_session()

    return jsonify({
        'success': True,
        'message': '세션이 시작되었습니다! Zone 0에서 촬영을 시작하세요.'
    })


@app.route('/api/capture', methods=['POST'])
def api_capture():
    """현재 Zone 촬영"""
    global inspection_system

    if not inspection_system or not inspection_system.is_active:
        return jsonify({
            'success': False,
            'message': '세션이 시작되지 않았습니다'
        })

    result = inspection_system.inspect_current_zone()

    return jsonify({
        'success': True,
        'zone_id': result.zone_id,
        'zone_type': result.zone_type,
        'detections': result.detections,
        'inference_time_ms': result.inference_time_ms,
        'is_defective': result.is_defective
    })


@app.route('/api/next', methods=['POST'])
def api_next():
    """다음 Zone으로"""
    global inspection_system

    if not inspection_system or not inspection_system.is_active:
        return jsonify({
            'success': False,
            'message': '세션이 시작되지 않았습니다'
        })

    has_next = inspection_system.next_zone()

    return jsonify({
        'success': True,
        'finished': not has_next,
        'current_zone': inspection_system.current_zone
    })


@app.route('/api/finish', methods=['POST'])
def api_finish():
    """세션 종료"""
    global inspection_system

    if not inspection_system:
        return jsonify({
            'success': False,
            'message': '세션이 없습니다'
        })

    inspection_system.finish_session()

    return jsonify({
        'success': True,
        'message': f'세션이 종료되었습니다. 총 {len(inspection_system.results)}개 Zone 검사 완료.'
    })


@app.route('/api/status')
def api_status():
    """상태 조회"""
    global inspection_system

    if not inspection_system:
        config = InspectionConfig()
        return jsonify({
            'is_active': False,
            'current_zone': 0,
            'total_zones': config.num_zones,
            'completed_zones': 0,
            'defective_zones': 0,
            'zone_types': config.zone_types
        })

    return jsonify({
        'is_active': inspection_system.is_active,
        'current_zone': inspection_system.current_zone,
        'total_zones': inspection_system.config.num_zones,
        'completed_zones': len(inspection_system.results),
        'defective_zones': sum(1 for r in inspection_system.results if r.is_defective),
        'zone_types': inspection_system.config.zone_types
    })


@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({'status': 'ok', 'mode': 'manual'})


if __name__ == '__main__':
    print("=" * 70)
    print("  Orin Car Manual Inspection System")
    print("=" * 70)
    print("  🖐️  MANUAL MODE - Hand Control")
    print("  손으로 오린카를 밀면서 검사하세요!")
    print("=" * 70)
    print("  Access URL: http://<Jetson IP>:5003")
    print("  Example: http://192.168.0.100:5003")
    print("=" * 70)

    try:
        app.run(host='0.0.0.0', port=5003, debug=False, threaded=True)
    finally:
        if inspection_system:
            inspection_system.cleanup()
        if global_camera:
            global_camera.release()
            print("[INFO] Global camera released")
