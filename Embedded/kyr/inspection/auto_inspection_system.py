"""
============================================================
Orin Car Inspection System - AUTO MODE (자동 모드)
============================================================
- 캘리브레이션 데이터 기반 자동 주행
- 30cm 구역별 자동 촬영 및 탐지
- ROI 크롭으로 보드지 영역만 표시
"""

import cv2
import time
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from flask import Flask, render_template_string, jsonify, request, Response, send_file
from ultralytics import YOLO
import numpy as np
import torch
import torchvision.transforms as transforms
from torchvision.models import wide_resnet50_2, Wide_ResNet50_2_Weights
from sklearn.neighbors import NearestNeighbors
from scipy.ndimage import gaussian_filter
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

# 모터 제어 import
from adafruit_pca9685 import PCA9685
import board
import busio


# ============================================================
# Motor Control (캘리브레이션 코드에서 가져옴)
# ============================================================

class PWMThrottleHat:
    """모터 제어 클래스 - 오린카 주행"""
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 60

    def set_throttle(self, throttle):
        """
        throttle: -1.0 (전진 최대) ~ 1.0 (후진 최대)
        0: 정지
        """
        pulse = int(0xFFFF * abs(throttle))

        if throttle < 0:  # 전진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle > 0:  # 후진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:  # 정지
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0


class MotorController:
    """모터 제어 래퍼 - 캘리브레이션 데이터 활용"""
    
    def __init__(self):
        # I2C 및 PWM 초기화
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c)
        self.pca.frequency = 100
        self.motor = PWMThrottleHat(self.pca, channel=0)
        
        # 캘리브레이션 데이터 기반 설정
        # 40% 출력, 2초로 30cm 주행
        self.default_pwm = 40 # 40%
        self.default_time = 2  # 2초
        
        print("[MOTOR] Initialized")
        print(f"[MOTOR] Default: PWM={self.default_pwm}%, TIME={self.default_time}s for 30cm")
    
    def drive_distance(self, pwm_percent=None, duration_sec=None):
        """
        지정된 출력과 시간으로 주행
        - pwm_percent: 모터 출력 (0~100%)
        - duration_sec: 주행 시간 (초)
        """
        if pwm_percent is None:
            pwm_percent = self.default_pwm
        if duration_sec is None:
            duration_sec = self.default_time
            
        # throttle 값 계산 (-1.0 ~ 0)
        throttle = -(pwm_percent / 100.0)
        
        print(f"[MOTOR] Driving: PWM={pwm_percent}%, TIME={duration_sec}s")
        
        # 주행 시작
        self.motor.set_throttle(throttle)
        time.sleep(duration_sec)
        
        # 정지
        self.motor.set_throttle(0)
        print(f"[MOTOR] Stopped")
    
    def stop(self):
        """즉시 정지"""
        self.motor.set_throttle(0)
        print("[MOTOR] Emergency stop")
    
    def cleanup(self):
        """정리 - 모터 정지 및 PWM 해제"""
        self.motor.set_throttle(0)
        self.pca.deinit()
        print("[MOTOR] Cleanup complete")


# ============================================================
# ROI (Region of Interest) 설정
# ============================================================

@dataclass
class ROIConfig:
    """ROI 설정 - 화면에서 보드지 영역만 크롭"""
    
    # 크롭 영역 (픽셀 단위, 640x480 해상도 기준)
    # 기본값 - roi_config.txt가 없을 때 사용
    x_start: int = 160
    x_end: int = 480
    y_start: int = 60
    y_end: int = 420
    
    # 실제 물리적 크기 (cm)
    real_width_cm: float = 30.0
    real_height_cm: float = 85.0
    
    def __post_init__(self):
        """roi_config.txt 파일이 있으면 자동으로 읽어옴"""
        self.load_from_file()
    
    def load_from_file(self):
        """roi_config.txt에서 ROI 설정 로드"""
        script_dir = Path(__file__).parent
        config_file = script_dir / 'roi_config.txt'

        if config_file.exists():
            print(f"[ROI] Loading config from: {config_file}")
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=')
                                key = key.strip()
                                value = int(value.strip())

                                if key == 'x_start':
                                    self.x_start = value
                                elif key == 'x_end':
                                    self.x_end = value
                                elif key == 'y_start':
                                    self.y_start = value
                                elif key == 'y_end':
                                    self.y_end = value

                print(f"[ROI] Loaded: ({self.x_start}, {self.y_start}) -> ({self.x_end}, {self.y_end})")
                print(f"[ROI] Size: {self.x_end - self.x_start} x {self.y_end - self.y_start} pixels")
            except Exception as e:
                print(f"[ROI] Warning: Failed to load config file: {e}")
                print(f"[ROI] Using default values")
        else:
            print(f"[ROI] Config file not found: {config_file}")
            print(f"[ROI] Using default values: ({self.x_start}, {self.y_start}) -> ({self.x_end}, {self.y_end})")
            print(f"[ROI] Tip: Run web_roi_config.py to adjust ROI")

    def save_to_file(self):
        """roi_config.txt에 현재 ROI 설정 저장"""
        script_dir = Path(__file__).parent
        config_file = script_dir / 'roi_config.txt'

        try:
            with open(config_file, 'w') as f:
                f.write("# ROI Configuration\n")
                f.write("# Target Box coordinates (pixels, 640x480 resolution)\n")
                f.write(f"x_start={self.x_start}\n")
                f.write(f"x_end={self.x_end}\n")
                f.write(f"y_start={self.y_start}\n")
                f.write(f"y_end={self.y_end}\n")

            print(f"[ROI] Saved to: {config_file}")
            print(f"[ROI] Values: ({self.x_start}, {self.y_start}) -> ({self.x_end}, {self.y_end})")
            return True
        except Exception as e:
            print(f"[ROI] ERROR: Failed to save config file: {e}")
            return False
    
    def crop_frame(self, frame: np.ndarray) -> np.ndarray:
        """프레임에서 ROI 영역만 크롭"""
        return frame[self.y_start:self.y_end, self.x_start:self.x_end]
    
    def draw_roi_overlay(self, frame: np.ndarray, color=(0, 255, 0), thickness=2) -> np.ndarray:
        """원본 프레임에 ROI 영역 표시 (디버깅용)"""
        frame_copy = frame.copy()
        cv2.rectangle(frame_copy, 
                     (self.x_start, self.y_start), 
                     (self.x_end, self.y_end), 
                     color, thickness)
        
        # ROI 크기 정보 표시
        text = f"ROI: {self.real_width_cm}cm x {self.real_height_cm}cm"
        cv2.putText(frame_copy, text, (self.x_start, self.y_start - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame_copy

    def bbox_to_real_coordinates(self, bbox: List[float], zone_id: int = 0) -> Tuple[float, float]:
        """
        bbox 중앙 좌표를 실제 cm 좌표로 변환

        Args:
            bbox: [x1, y1, x2, y2] ROI 내 픽셀 좌표
            zone_id: Zone 번호 (0부터 시작, 각 zone은 30cm 간격)

        Returns:
            (absolute_x_cm, absolute_y_cm): 전체 검사 영역 기준 절대 좌표
        """
        # ROI 픽셀 크기
        roi_width_px = self.x_end - self.x_start
        roi_height_px = self.y_end - self.y_start

        # 픽셀당 cm 비율
        px_to_cm_x = self.real_width_cm / roi_width_px
        px_to_cm_y = self.real_height_cm / roi_height_px

        # bbox 중앙 좌표 (픽셀)
        bbox_center_x_px = (bbox[0] + bbox[2]) / 2
        bbox_center_y_px = (bbox[1] + bbox[3]) / 2

        # ROI 내 상대 좌표 (cm)
        relative_x_cm = bbox_center_x_px * px_to_cm_x
        relative_y_cm = bbox_center_y_px * px_to_cm_y

        # Zone 번호를 고려한 절대 좌표 (cm)
        # 각 zone은 30cm씩 오른쪽으로 이동
        absolute_x_cm = relative_x_cm + (zone_id * 30.0)
        absolute_y_cm = relative_y_cm

        return absolute_x_cm, absolute_y_cm


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
    
    # 모터 설정 (캘리브레이션 기반)
    motor_pwm: int = 40  # %
    motor_time: float = 2  # 초
    
    zone_types: List[str] = None

    def __post_init__(self):
        if self.zone_types is None:
            # 모든 zone에서 YOLO → PatchCore 2단계 탐지 수행
            self.zone_types = [
                'detection',  # Zone 0
                'detection',  # Zone 1
                'detection',  # Zone 2
                'detection',  # Zone 3
                'detection',  # Zone 4
                'detection'   # Zone 5
            ]

    @property
    def num_zones(self) -> int:
        return self.total_length_cm // self.zone_length_cm


# ============================================================
# Camera Controller with ROI
# ============================================================

class CameraController:
    """카메라 제어 클래스 - ROI 크롭 기능 포함"""

    def __init__(self, roi_config: ROIConfig = None):
        self.camera = None
        self.roi_config = roi_config if roi_config else ROIConfig()
        self.init_camera()

    def init_camera(self):
        """카메라 초기화"""
        pipeline = (
            "v4l2src device=/dev/video0 ! "
            "image/jpeg, width=640, height=480, framerate=30/1 ! "
            "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true"
        )

        print("[CAMERA] Initializing...")
        self.camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        if not self.camera.isOpened():
            print("[CAMERA] GStreamer failed, trying V4L2...")
            self.camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        if self.camera.isOpened():
            print("[CAMERA] Initialized successfully")
            print(f"[CAMERA] ROI: {self.roi_config.x_end - self.roi_config.x_start}x"
                  f"{self.roi_config.y_end - self.roi_config.y_start} pixels "
                  f"({self.roi_config.real_width_cm}x{self.roi_config.real_height_cm} cm)")
        else:
            print("[CAMERA] ERROR: Initialization failed")

    def capture_frame(self, crop_roi=False) -> Optional[np.ndarray]:
        """
        프레임 캡처
        - crop_roi: True이면 ROI만 크롭하여 반환
        """
        if not self.camera or not self.camera.isOpened():
            print("[CAMERA] ERROR: Not available")
            return None

        success, frame = self.camera.read()
        if not success:
            return None
            
        if crop_roi:
            return self.roi_config.crop_frame(frame)
        else:
            return frame

    def capture_with_roi_overlay(self) -> Optional[np.ndarray]:
        """ROI 영역 표시된 전체 프레임 캡처 (디버깅용)"""
        frame = self.capture_frame(crop_roi=False)
        if frame is None:
            return None
        return self.roi_config.draw_roi_overlay(frame)

    def save_image(self, frame: np.ndarray, filepath: str):
        """이미지 저장"""
        cv2.imwrite(filepath, frame)
        print(f"[CAMERA] Saved: {filepath}")

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

    def __init__(self, model_path: str, conf_threshold: float = 0.5, device: str = 'cpu'):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.device = device
        self.model = None
        self.model_loaded = self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            if not Path(self.model_path).exists():
                print(f"[YOLO] ERROR: Model not found: {self.model_path}")
                return False

            # 모델 타입 확인
            if self.model_path.endswith('.engine'):
                print(f"[YOLO] Loading TensorRT Engine: {self.model_path} (GPU only)")
                self.model = YOLO(self.model_path, task='detect')
            elif self.model_path.endswith('.pt'):
                print(f"[YOLO] Loading PyTorch: {self.model_path} on {self.device}")
                self.model = YOLO(self.model_path, task='detect')
                # Device 설정
                self.model.to(self.device)
            else:
                print(f"[YOLO] Loading model: {self.model_path} on {self.device}")
                self.model = YOLO(self.model_path, task='detect')
                self.model.to(self.device)

            if self.model is None:
                print("[YOLO] ERROR: Model is None")
                return False

            print(f"[YOLO] Model loaded successfully on {self.device}")
            print(f"[YOLO] Classes: {list(self.model.names.values())}")
            return True

        except Exception as e:
            print(f"[YOLO] ERROR: Load failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float, bool]:
        """결함 탐지 - ROI 크롭된 프레임에서 수행"""
        if self.model is None:
            print("[YOLO] ERROR: Model not loaded")
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
            print(f"[YOLO] ERROR: Detection failed: {e}")
            return [], 0.0, False

    def visualize(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """탐지 결과 시각화"""
        vis_frame = frame.copy()
        
        for det in detections:
            bbox = det['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # 바운딩 박스
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
            # 라벨
            label = f"{det['class_name']}: {det['confidence']:.2f}"
            cv2.putText(vis_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return vis_frame


# ============================================================
# PatchCore Anomaly Detector
# ============================================================

class PatchCoreDetector:
    """PatchCore 기반 이상 탐지 - TensorRT EfficientNet"""

    def __init__(self, model_path: str, threshold: float = 30.0):
        self.model_path = model_path
        self.threshold = threshold
        print(f"[PATCHCORE] Initializing TensorRT-based PatchCore")

        # Memory bank 및 설정
        self.memory_bank = None
        self.feature_dim = None
        self.knn = None

        # TensorRT 설정
        self.trt_logger = trt.Logger(trt.Logger.WARNING)
        self.engine = None
        self.context = None
        self.stream = None

        # Input/Output buffers
        self.input_shape = (1, 3, 224, 224)  # NCHW
        self.output_shape = None
        self.d_input = None
        self.d_output = None
        self.h_input = None
        self.h_output = None

        # 전처리
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

        self.model_loaded = self.load_model()

    def load_model(self):
        """PatchCore 모델 로드 - TensorRT Engine + Memory Bank"""
        try:
            # model_path는 디렉토리 경로
            model_dir = Path(self.model_path)

            # 1. Memory bank 로드 (.npz 파일 자동 검색)
            npz_files = list(model_dir.glob("*.npz"))
            if not npz_files:
                print(f"[PATCHCORE] ERROR: No .npz file found in: {model_dir}")
                return False

            npz_path = npz_files[0]  # 첫 번째 .npz 파일 사용
            print(f"[PATCHCORE] Loading memory bank: {npz_path}")
            data = np.load(npz_path, allow_pickle=True)
            self.memory_bank = data['memory_bank']
            self.feature_dim = int(data['feature_dim'])

            print(f"[PATCHCORE] Memory bank: {self.memory_bank.shape}")
            print(f"[PATCHCORE] Feature dim: {self.feature_dim}")

            # 2. K-NN 초기화
            self.knn = NearestNeighbors(n_neighbors=1, metric='euclidean')
            self.knn.fit(self.memory_bank)
            print("[PATCHCORE] K-NN initialized (k=1)")

            # 3. TensorRT Engine 로드 (.engine 파일 자동 검색)
            engine_files = list(model_dir.glob("*.engine"))
            if not engine_files:
                print(f"[PATCHCORE] ERROR: No .engine file found in: {model_dir}")
                return False

            engine_path = engine_files[0]  # 첫 번째 .engine 파일 사용
            print(f"[PATCHCORE] Loading TensorRT engine: {engine_path}")
            with open(engine_path, 'rb') as f:
                runtime = trt.Runtime(self.trt_logger)
                self.engine = runtime.deserialize_cuda_engine(f.read())

            if self.engine is None:
                print("[PATCHCORE] ERROR: Failed to load engine")
                return False

            self.context = self.engine.create_execution_context()
            self.stream = cuda.Stream()

            # 4. Input/Output buffer 할당
            # Input: [1, 3, 224, 224]
            input_size = int(np.prod(self.input_shape))
            self.h_input = cuda.pagelocked_empty(input_size, dtype=np.float32)
            self.d_input = cuda.mem_alloc(self.h_input.nbytes)

            # Output shape 확인 (EfficientNet-B0 feature)
            # EfficientNet-B0 layer 4: [1, 320, 7, 7]
            self.output_shape = (1, 320, 7, 7)
            output_size = int(np.prod(self.output_shape))
            self.h_output = cuda.pagelocked_empty(output_size, dtype=np.float32)
            self.d_output = cuda.mem_alloc(self.h_output.nbytes)

            print(f"[PATCHCORE] Input shape: {self.input_shape}")
            print(f"[PATCHCORE] Output shape: {self.output_shape}")
            print("[PATCHCORE] TensorRT engine loaded successfully")
            return True

        except Exception as e:
            print(f"[PATCHCORE] ERROR: Load failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _extract_features(self, frame: np.ndarray) -> np.ndarray:
        """이미지에서 feature 추출 - TensorRT (v8.x+ 호환)"""
        # 1. 전처리
        img_tensor = self.transform(frame)  # [3, 224, 224]
        img_np = img_tensor.numpy()  # numpy array

        # 2. Input buffer에 복사
        np.copyto(self.h_input, img_np.ravel())
        cuda.memcpy_htod(self.d_input, self.h_input)

        # 3. TensorRT 추론 (동기 방식 - TensorRT 8.x+)
        self.context.execute_v2(bindings=[int(self.d_input), int(self.d_output)])

        # 4. Output buffer에서 결과 가져오기
        cuda.memcpy_dtoh(self.h_output, self.d_output)

        # 5. Feature reshape
        # EfficientNet-B0 layer 4 output: [1, 320, 7, 7]
        features = self.h_output.reshape(self.output_shape)  # [1, 320, 7, 7]

        # 6. Convert to torch tensor
        features = torch.from_numpy(features)

        # 7. Reshape to patches (학습 코드와 동일)
        # [1, 320, 7, 7] → [1, 7, 7, 320] → [49, 320]
        batch, channels, h, w = features.shape
        features = features.permute(0, 2, 3, 1).reshape(-1, channels)  # [49, 320]

        return features.numpy()

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float, bool]:
        """이상 탐지 수행 - 이상/정상 분류만"""
        if not self.model_loaded:
            print("[PATCHCORE] ERROR: Model not loaded")
            return [], 0.0, False

        try:
            start_time = time.time()

            # Feature 추출
            features = self._extract_features(frame)

            # K-NN search
            distances, _ = self.knn.kneighbors(features)

            # Anomaly score (평균 거리)
            anomaly_scores = distances.mean(axis=1)

            # Anomaly map (7x7) - EfficientNet-B0 layer 4 output은 7x7
            anomaly_map = anomaly_scores.reshape(7, 7)

            # Gaussian smoothing (노이즈 감소, 안정성 향상)
            anomaly_map = gaussian_filter(anomaly_map, sigma=2)

            # Max score
            max_score = anomaly_map.max()

            inference_time = (time.time() - start_time) * 1000

            # 디버깅: anomaly score 출력
            print(f"    [DEBUG] Anomaly Score: {max_score:.2f} (Threshold: {self.threshold})")

            # Threshold 적용 - 이상/정상 분류만
            is_anomaly = max_score > self.threshold

            if is_anomaly:
                print(f"    [DEBUG] ✓ ANOMALY DETECTED! ({max_score:.2f} > {self.threshold})")
            else:
                print(f"    [DEBUG] ✗ Normal ({max_score:.2f} <= {self.threshold})")

            detections = []
            if is_anomaly:
                # Bbox 없이 전체 영역에 대한 이상 분류 정보만 포함
                detections.append({
                    'class_id': -1,
                    'class_name': 'anomaly',
                    'confidence': float(max_score),
                    'bbox': None  # Bbox 없음
                })

            return detections, inference_time, is_anomaly

        except Exception as e:
            print(f"[PATCHCORE] ERROR: Detection failed: {e}")
            import traceback
            traceback.print_exc()
            return [], 0.0, False


# ============================================================
# Auto Inspection System
# ============================================================

class AutoInspectionSystem:
    """자동 주행 검사 시스템"""

    def __init__(self, config: InspectionConfig, motor: MotorController,
                 camera: CameraController, yolo_detector: YOLODetector,
                 patchcore_detector: Optional[PatchCoreDetector] = None):
        self.config = config
        self.motor = motor
        self.camera = camera
        self.yolo_detector = yolo_detector
        self.patchcore_detector = patchcore_detector

        self.results: List[DetectionResult] = []
        self.current_zone = 0
        self.is_active = False
        self.is_online_mode = False  # Track online mode state
        self.online_session_dir = None  # Online mode session directory
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 결과 저장 디렉토리
        script_dir = Path(__file__).parent
        self.output_dir = script_dir.parent / 'inspection_results'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("[SYSTEM] Auto Inspection System initialized")
        print(f"[SYSTEM] YOLO: {'✓' if yolo_detector.model_loaded else '✗'}")
        print(f"[SYSTEM] PatchCore: {'✓' if patchcore_detector and patchcore_detector.model_loaded else '✗'}")
        print(f"[SYSTEM] Output: {self.output_dir}")

    def start_session(self):
        """세션 시작"""
        self.is_active = True
        self.results = []
        self.current_zone = 0
        
        # 세션 폴더 생성
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"auto_session_{session_timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 70)
        print("🚗 Auto Inspection Session Started")
        print(f"Total zones: {self.config.num_zones}")
        print(f"Session: {self.session_dir.name}")
        print(f"Motor: PWM={self.config.motor_pwm}%, TIME={self.config.motor_time}s")
        print("=" * 70)

    def inspect_current_zone(self) -> DetectionResult:
        """현재 Zone 검사 - 촬영 및 탐지"""
        zone_id = self.current_zone
        zone_type = self.config.zone_types[zone_id]
        timestamp = datetime.now().isoformat()
        
        print(f"\n[Zone {zone_id + 1}/{self.config.num_zones}] Inspecting...")
        print(f"  Type: {zone_type}")
        
        # ROI 크롭된 프레임 캡처
        print("  📷 Capturing ROI frame...")
        roi_frame = self.camera.capture_frame(crop_roi=True)
        
        # 실시간 모니터링용 (ROI 크롭 버전)
        with self.frame_lock:
            self.current_frame = roi_frame.copy() if roi_frame is not None else None
        
        if roi_frame is None:
            print("  [ERROR] Capture failed")
            return DetectionResult(
                zone_id=zone_id, zone_type=zone_type, timestamp=timestamp,
                detections=[], image_path='', inference_time_ms=0.0,
                is_defective=False
            )
        
        # 탐지 수행 (2단계 하이브리드 - 모든 zone에서 수행)
        detections = []
        inference_time = 0.0
        is_defective = False
        detection_method = 'none'

        # 1단계: YOLO 결함 탐지
        print("  🔍 [Stage 1] Running YOLO detection...")
        yolo_detections, yolo_time, yolo_defect = self.yolo_detector.detect(roi_frame)
        print(f"    YOLO: {len(yolo_detections)} defects ({yolo_time:.2f}ms)")

        if yolo_defect:
            # YOLO가 결함을 발견
            detections = yolo_detections
            inference_time = yolo_time
            is_defective = True
            detection_method = 'yolo'
            for det in detections:
                print(f"      - {det['class_name']}: {det['confidence']:.2f}")

        elif self.patchcore_detector and self.patchcore_detector.model_loaded:
            # 2단계: YOLO가 결함을 못 찾으면 PatchCore 이상 탐지
            print("  🔍 [Stage 2] Running PatchCore anomaly detection...")
            patchcore_detections, patchcore_time, patchcore_anomaly = \
                self.patchcore_detector.detect(roi_frame)
            print(f"    PatchCore: {len(patchcore_detections)} anomalies ({patchcore_time:.2f}ms)")

            if patchcore_anomaly:
                detections = patchcore_detections
                inference_time = yolo_time + patchcore_time
                is_defective = True
                detection_method = 'patchcore'
                for det in detections:
                    print(f"      - {det['class_name']}: {det['confidence']:.2f}")
            else:
                # 둘 다 결함을 못 찾음
                inference_time = yolo_time + patchcore_time
                detection_method = 'both_negative'
                print("    ✓ No defects found")
        else:
            # PatchCore 없음, YOLO만 사용
            inference_time = yolo_time
            detection_method = 'yolo_only'
            print("    ✓ No defects found (YOLO only)")

        # 시각화 (패딩 기반)
        print("  🎨 Visualizing...")
        zone_text = f"Zone {zone_id + 1} - {zone_type.upper()}"
        vis_frame = self._visualize_detections(
            roi_frame, detections, detection_method,
            mode='auto',
            zone_info=zone_text,
            timestamp=timestamp,
            zone_id=zone_id
        )
        
        # 저장
        image_filename = f"zone_{zone_id:02d}_{zone_type}.jpg"
        image_path = str(self.session_dir / image_filename)
        self.camera.save_image(vis_frame, image_path)
        
        result = DetectionResult(
            zone_id=zone_id, zone_type=zone_type, timestamp=timestamp,
            detections=detections, image_path=image_path,
            inference_time_ms=inference_time, is_defective=is_defective
        )
        
        self.results.append(result)
        print(f"[Zone {zone_id + 1}] Complete")

        return result

    # class_id별 BGR 색상
    _BBOX_COLORS = {
        0: (0, 255, 255),    # blister        — 노랑
        1: (0, 0, 255),      # crack          — 빨강
        2: (0, 255, 0),      # peeling        — 초록
        3: (255, 255, 0),    # sagging        — 청록
        4: (255, 0, 255),    # welding_damage — 자홍
    }
    _BBOX_COLOR_DEFAULT = (200, 200, 200)  # 미정의 클래스 fallback

    def _draw_yolo_bbox_on_frame(self, frame: np.ndarray, detections: List[Dict]) -> None:
        """이미지 내부에 YOLO bbox 클래스별 색상으로 표시 (in-place)"""
        for det in detections:
            bbox = det.get('bbox')
            if bbox is not None:
                x1, y1, x2, y2 = map(int, bbox)
                color = self._BBOX_COLORS.get(det.get('class_id'), self._BBOX_COLOR_DEFAULT)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                label = det['class_name']
                cv2.putText(frame, label, (x1 + 2, y1 - 3),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    def _visualize_detections(self, frame: np.ndarray, detections: List[Dict],
                             method: str, mode: str = 'auto',
                             zone_info: str = None, timestamp: str = None,
                             zone_id: int = 0) -> np.ndarray:
        """ROI 이미지에 YOLO bbox만 그려서 반환 (결함 정보 표시는 프론트에서 처리)"""
        vis = frame.copy()
        yolo_dets = [d for d in detections if d.get('bbox') is not None]
        if yolo_dets:
            self._draw_yolo_bbox_on_frame(vis, yolo_dets)
        return vis

    def move_to_next_zone(self) -> bool:
        """다음 Zone으로 이동 - 모터로 30cm 주행"""
        self.current_zone += 1
        
        if self.current_zone >= self.config.num_zones:
            self.finish_session()
            return False
        
        print(f"\n[MOVE] Moving to Zone {self.current_zone + 1}...")
        print(f"  Target: 30cm forward")
        
        try:
            # 30cm 주행 (캘리브레이션 기반)
            self.motor.drive_distance(
                pwm_percent=self.config.motor_pwm,
                duration_sec=self.config.motor_time
            )
            
            # 안정화 대기 (0.7초)
            print("  ⏳ Stabilizing...")
            time.sleep(0.7)
            
            print(f"  ✓ Arrived at Zone {self.current_zone + 1}")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Movement failed: {e}")
            self.motor.stop()
            return False

    def run_auto_inspection(self):
        """전체 자동 검사 실행"""
        print("\n" + "=" * 70)
        print("🤖 Starting Full Auto Inspection")
        print("=" * 70)
        
        for zone_idx in range(self.config.num_zones):
            if not self.is_active:
                print("\n[SYSTEM] Session stopped")
                break
            
            # 현재 Zone 검사
            result = self.inspect_current_zone()
            
            # 마지막 Zone이 아니면 다음 Zone으로 이동
            if zone_idx < self.config.num_zones - 1:
                success = self.move_to_next_zone()
                if not success:
                    print("[ERROR] Failed to move, stopping inspection")
                    break
            else:
                # 마지막 Zone 완료
                self.finish_session()

    def finish_session(self):
        """세션 종료"""
        self.is_active = False

        print("\n" + "=" * 70)
        print("✅ Auto Inspection Complete!")
        print(f"Zones: {len(self.results)}")
        print(f"Defects: {sum(1 for r in self.results if r.is_defective)}")
        print("=" * 70)

        self.save_results()

    def run_online_mode(self):
        """온라인 모드 - 연속 촬영 및 탐지 (모터 이동 없음, 자동 저장 없음)"""
        print("\n" + "=" * 70)
        print("🔄 Online Mode Started")
        print("=" * 70)

        # Create online session directory
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.online_session_dir = self.output_dir / f"online_session_{session_timestamp}"
        self.online_session_dir.mkdir(parents=True, exist_ok=True)
        print(f"[ONLINE MODE] Session directory: {self.online_session_dir.name}")

        # 임시 이미지 경로
        self.online_temp_image = self.online_session_dir / "current_frame.jpg"

        frame_count = 0

        while self.is_online_mode:
            # Capture ROI frame
            roi_frame = self.camera.capture_frame(crop_roi=True)

            if roi_frame is None:
                time.sleep(0.1)
                continue

            # Run detection (YOLO + PatchCore hybrid)
            detections = []
            is_defective = False
            detection_method = 'none'

            # Stage 1: YOLO
            yolo_detections, yolo_time, yolo_defect = self.yolo_detector.detect(roi_frame)

            if yolo_defect:
                detections = yolo_detections
                is_defective = True
                detection_method = 'yolo'
            elif self.patchcore_detector and self.patchcore_detector.model_loaded:
                # Stage 2: PatchCore
                patchcore_detections, patchcore_time, patchcore_anomaly = \
                    self.patchcore_detector.detect(roi_frame)

                if patchcore_anomaly:
                    detections = patchcore_detections
                    is_defective = True
                    detection_method = 'patchcore'

            # Visualize (패딩 기반)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            vis_frame = self._visualize_detections(
                roi_frame, detections, detection_method,
                mode='online',
                zone_info=None,
                timestamp=timestamp,
                zone_id=0  # Online 모드는 zone 0으로 고정
            )

            # Update display frame (thread-safe)
            with self.frame_lock:
                self.current_frame = vis_frame

            # 임시 이미지로 저장 (프론트엔드에서 표시용)
            self.camera.save_image(vis_frame, str(self.online_temp_image))

            frame_count += 1
            time.sleep(0.5)  # 2 FPS (더 안정적)

        print(f"\n[ONLINE MODE] Stopped (processed {frame_count} frames)")

    def save_online_snapshot(self):
        """온라인 모드 - 현재 프레임 및 탐지 결과 저장"""
        if not self.is_online_mode:
            return {'success': False, 'message': 'Online mode not active'}

        with self.frame_lock:
            if self.current_frame is None:
                return {'success': False, 'message': 'No frame available'}

            frame_to_save = self.current_frame.copy()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"online_snapshot_{timestamp}.jpg"
        filepath = str(self.online_session_dir / filename)

        # Save image
        self.camera.save_image(frame_to_save, filepath)

        return {
            'success': True,
            'message': 'Snapshot saved',
            'filepath': filepath,
            'filename': filename
        }

    def save_results(self):
        """결과 저장"""
        results_file = self.session_dir / "inspection_results.json"
        
        results_data = {
            'mode': 'auto',
            'session_folder': self.session_dir.name,
            'config': asdict(self.config),
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(r) for r in self.results],
            'summary': {
                'total_zones': len(self.results),
                'defective_zones': sum(1 for r in self.results if r.is_defective),
            }
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"[INFO] Results saved: {results_file}")

    def generate_frames(self):
        """실시간 카메라 피드 (Flask용)"""
        global show_target_box

        while True:
            # 온라인 모드: current_frame 사용 (패딩 기반 시각화가 이미 적용됨)
            if self.is_online_mode:
                with self.frame_lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                    else:
                        # Waiting 화면
                        frame = np.zeros((540, 240, 3), dtype=np.uint8)  # 패딩 포함 크기 (40+430+70)
                        cv2.putText(frame, "Waiting...", (70, 270),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            else:
                # 일반 모드 또는 Auto 모드: Full 프레임 캡처
                frame = self.camera.capture_frame(crop_roi=False)

                if frame is None:
                    # 검은 화면
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "No Feed", (250, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                else:
                    # Target Box (ROI) 표시만 (깔끔하게)
                    if show_target_box:
                        roi = self.camera.roi_config
                        cv2.rectangle(frame,
                                     (roi.x_start, roi.y_start),
                                     (roi.x_end, roi.y_end),
                                     (0, 255, 0), 2)

                # 가로 중앙 크롭 (타겟박스 기준 좌우 100px)
                roi = self.camera.roi_config
                height, width = frame.shape[:2]
                start_x = max(0, roi.x_start - 100)
                end_x = min(width, roi.x_end + 100)
                frame = frame[:, start_x:end_x]

            # JPEG 인코딩
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            time.sleep(0.03)

    def cleanup(self):
        """정리"""
        print("[SYSTEM] Cleanup...")
        self.motor.stop()


# ============================================================
# Flask Web Application
# ============================================================

app = Flask(__name__)
inspection_system: Optional[AutoInspectionSystem] = None
motor_controller: Optional[MotorController] = None
camera_controller: Optional[CameraController] = None
yolo_detector: Optional[YOLODetector] = None
patchcore_detector: Optional[PatchCoreDetector] = None
show_target_box: bool = True  # Target Box 표시 여부

# 전역 초기화 (프로그램 시작 시 1회)
def init_global_resources():
    """전역 리소스 초기화 - 카메라, 모터, YOLO, PatchCore (All on GPU)"""
    global motor_controller, camera_controller, yolo_detector, patchcore_detector

    print("\n[INIT] Initializing global resources...")
    print("[INIT] Mode: All GPU (YOLO TensorRT + PatchCore TensorRT)")
    print("=" * 70)

    # 모터 초기화
    motor_controller = MotorController()

    # ROI 설정 및 카메라 초기화
    roi_config = ROIConfig()
    camera_controller = CameraController(roi_config)

    script_dir = Path(__file__).parent

    # YOLO GPU (TensorRT)
    yolo_model_path = script_dir.parent / 'models' / 'yolo' / 'best_fixed.engine'
    yolo_detector = YOLODetector(str(yolo_model_path), conf_threshold=0.5, device='cuda')

    # PatchCore GPU (TensorRT EfficientNet-B0)
    patchcore_model_dir = script_dir.parent / 'models' / 'anomaly_patchcore_lite_v2'
    patchcore_detector = PatchCoreDetector(str(patchcore_model_dir), threshold=30.0)

    if not yolo_detector.model_loaded:
        raise RuntimeError("YOLO model load failed!")

    if not patchcore_detector.model_loaded:
        print("[WARN] PatchCore model load failed - will use YOLO only")

    print("=" * 70)
    print("[INIT] All resources initialized\n")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🚢 Docktor 자동 주행 탐지</title>
    <meta charset="UTF-8">
    <style>
        :root {
            --camera-width: 1100px;  /* 카메라 화면 크기 조절 */
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: #f8f9fa;
            color: #1a1f36;
            padding: 0;
            min-height: 100vh;
        }
        .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 10px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            border: 1px solid #e5e7eb;
            text-align: center;
            display: flex;
            flex-direction: column;
        }
        .card h2 {
            color: #1e3a8a;
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 8px;
            text-align: center;
        }
        .monitoring-grid {
            display: grid;
            grid-template-columns: 8fr 3fr;
            gap: 10px;
            margin-bottom: 10px;
        }
        @media (max-width: 1024px) {
            .monitoring-grid {
                grid-template-columns: 1fr;
            }
        }
        .latest-result-container {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            border: 1px solid #e5e7eb;
            text-align: center;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .latest-result-container h2 {
            color: #1e3a8a;
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 20px;
        }
        .latest-result-img {
            max-width: 100%;
            margin: 0 auto;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex: 1;
            min-height: 450px;
        }
        .latest-result-img img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            display: block;
            border-radius: 8px;
        }
        .no-result {
            padding: 40px;
            color: #9ca3af;
            font-size: 1.1em;
        }
        .video-container {
            position: relative;
            text-align: center;
            background: transparent;
            border-radius: 8px;
            padding: 0;
            border: 1px solid #e5e7eb;
            max-width: var(--camera-width);
            margin: 0 auto;
        }
        .video-container img {
            width: 100%;
            height: auto;
            display: block;
            border-radius: 8px;
        }
        .roi-info {
            display: none;
        }
        .controls {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .btn {
            padding: 12px 28px;
            font-size: 1em;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        .btn:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-start {
            background: #1e3a8a;
            color: white;
        }
        .btn-start:hover:not(:disabled) {
            background: #1e40af;
        }
        .btn-stop {
            background: #dc2626;
            color: white;
        }
        .btn-stop:hover:not(:disabled) {
            background: #b91c1c;
        }
        .btn-toggle {
            background: #3b82f6;
            color: white;
        }
        .btn-toggle:hover {
            background: #2563eb;
        }
        .btn-toggle.off {
            background: #9ca3af;
        }
        .btn-online {
            background: #0ea5e9;
            color: white;
        }
        .btn-online:hover:not(:disabled) {
            background: #0284c7;
        }
        .btn-save {
            background: #10b981;
            color: white;
        }
        .btn-save:hover:not(:disabled) {
            background: #059669;
        }
        .status {
            text-align: center;
            font-size: 1.2em;
            margin: 20px 0;
            padding: 20px;
            background: #f0f4ff;
            border-radius: 8px;
            color: #1e3a8a;
            font-weight: 500;
            border: 1px solid #dbe4ff;
        }
        .zone-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        @media (max-width: 1024px) {
            .zone-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        @media (max-width: 640px) {
            .zone-grid {
                grid-template-columns: 1fr;
            }
        }
        .zone-card {
            background: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            border: 2px solid #e5e7eb;
            transition: all 0.3s;
        }
        .zone-card:hover {
            box-shadow: 0 4px 12px rgba(30, 58, 138, 0.1);
        }
        .zone-card.current {
            animation: pulse 2s infinite;
            border-color: #fbbf24;
            box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.1);
        }
        .zone-card.completed {
            border-color: #10b981;
            background: #f0fdf4;
        }
        .zone-card.defect {
            border-color: #ef4444;
            background: #fef2f2;
        }
        .zone-card img {
            width: 100%;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #e5e7eb;
        }
        .zone-method {
            font-size: 0.85em;
            color: #1e3a8a;
            margin: 8px 0;
            font-weight: 500;
        }
        .zone-defect-name {
            font-weight: 600;
            color: #dc2626;
            margin: 8px 0;
            font-size: 1.05em;
        }
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.1);
            }
            50% {
                transform: scale(1.02);
                box-shadow: 0 0 0 6px rgba(251, 191, 36, 0.2);
            }
        }
        .slider-group {
            margin-bottom: 20px;
        }
        .slider-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #1e3a8a;
            font-size: 0.95em;
        }
        .slider-group input[type="range"] {
            width: 100%;
            height: 8px;
            border-radius: 5px;
            background: #e5e7eb;
            outline: none;
            -webkit-appearance: none;
        }
        .slider-group input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #1e3a8a;
            cursor: pointer;
        }
        .slider-group input[type="range"]::-moz-range-thumb {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #1e3a8a;
            cursor: pointer;
            border: none;
        }
        .roi-size-info {
            text-align: center;
            font-size: 1.1em;
            color: #1e3a8a;
            font-weight: 600;
            padding: 15px;
            background: #f0f4ff;
            border-radius: 8px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">

        <div class="monitoring-grid">
            <!-- 왼쪽: 실시간 모니터링 -->
            <div class="card">
                <h2>📹 실시간 모니터링</h2>
                <div class="video-container">
                    <div class="roi-info">
                        🎯 Target Box: 30cm x 85cm 검사 영역
                    </div>
                    <img src="/video_feed" alt="Camera Feed">
                </div>
            </div>

            <!-- 오른쪽: 최근 검사 결과 -->
            <div class="latest-result-container">
                <h2>📍 최근 검사 결과</h2>
                <div id="latestResult" class="latest-result-img">
                    <div class="no-result">검사를 시작하면 결과가 표시됩니다</div>
                </div>
            </div>
        </div>

        <div class="card" id="roiPanel" style="display: none;">
            <h2 style="margin-bottom: 20px;">⚙️ ROI (Target Box) 범위 조정</h2>
            <div style="max-width: 600px; margin: 0 auto;">
                <div class="slider-group">
                    <label>X 시작 (Left): <span id="valXStart">160</span>px</label>
                    <input type="range" id="sliderXStart" min="0" max="320" value="160"
                           oninput="updateROI()">
                </div>
                <div class="slider-group">
                    <label>X 끝 (Right): <span id="valXEnd">480</span>px</label>
                    <input type="range" id="sliderXEnd" min="320" max="640" value="480"
                           oninput="updateROI()">
                </div>
                <div class="slider-group">
                    <label>Y 시작 (Top): <span id="valYStart">60</span>px</label>
                    <input type="range" id="sliderYStart" min="0" max="240" value="60"
                           oninput="updateROI()">
                </div>
                <div class="slider-group">
                    <label>Y 끝 (Bottom): <span id="valYEnd">420</span>px</label>
                    <input type="range" id="sliderYEnd" min="240" max="480" value="420"
                           oninput="updateROI()">
                </div>
                <div class="roi-size-info">
                    ROI 크기: <span id="roiWidth">320</span> x <span id="roiHeight">360</span> pixels
                </div>
                <div class="controls" style="margin-top: 20px;">
                    <button class="btn btn-start" onclick="saveROI()">
                        💾 저장
                    </button>
                    <button class="btn btn-toggle" onclick="resetROI()">
                        🔄 리셋
                    </button>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="controls">
                <button class="btn btn-start" id="btnStart" onclick="startAuto()">
                    🚀 자동 검사 시작
                </button>
                <button class="btn btn-online" id="btnOnline" onclick="startOnline()">
                    🔄 온라인 모드
                </button>
                <button class="btn btn-stop" id="btnStop" onclick="stopAuto()" disabled style="display: none;">
                    🛑 중지
                </button>
                <button class="btn btn-stop" id="btnStopOnline" onclick="stopOnline()" disabled style="display: none;">
                    🛑 온라인 중지
                </button>
                <button class="btn btn-save" id="btnSave" onclick="saveCurrent()" disabled style="display: none;">
                    💾 저장
                </button>
                <button class="btn btn-toggle" id="btnToggleBox" onclick="toggleTargetBox()">
                    📦 Target Box: ON
                </button>
                <button class="btn btn-toggle" id="btnToggleROI" onclick="toggleROIPanel()">
                    ⚙️ ROI 조정
                </button>
            </div>
            <div class="status" id="status">자동 검사 시작 버튼을 눌러주세요</div>
        </div>

        <div class="card" id="zoneResultsCard">
            <h2 style="margin-bottom: 20px;">📍 Zone 검사 결과</h2>
            <div class="zone-grid" id="zones"></div>
        </div>
    </div>

    <script>
        let roiPanelVisible = false;

        function startAuto() {
            if(confirm('자동 검사를 시작하시겠습니까? (약 20초 소요)')) {
                document.getElementById('btnStart').disabled = true;
                document.getElementById('btnOnline').disabled = true;
                document.getElementById('btnStop').disabled = false;
                document.getElementById('btnStop').style.display = 'inline-block';
                document.getElementById('status').innerHTML = '🚗 자동 검사 진행 중...';

                fetch('/api/start_auto', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if(!data.success) {
                            alert(data.message);
                            resetButtons();
                        }
                    });
            }
        }

        function stopAuto() {
            if(confirm('정말 중지하시겠습니까?')) {
                fetch('/api/stop', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        resetButtons();
                    });
            }
        }

        function startOnline() {
            if(confirm('온라인 모드를 시작하시겠습니까? (모터 이동 없이 연속 검사만 수행)')) {
                // Disable start buttons
                document.getElementById('btnStart').disabled = true;
                document.getElementById('btnOnline').disabled = true;

                // Show online controls
                document.getElementById('btnStopOnline').disabled = false;
                document.getElementById('btnStopOnline').style.display = 'inline-block';
                document.getElementById('btnSave').disabled = false;
                document.getElementById('btnSave').style.display = 'inline-block';

                // Hide auto stop button
                document.getElementById('btnStop').style.display = 'none';

                document.getElementById('status').innerHTML = '🔄 온라인 모드 실행 중...';

                fetch('/api/start_online', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if(!data.success) {
                            alert(data.message);
                            resetButtons();
                        }
                    });
            }
        }

        function stopOnline() {
            if(confirm('온라인 모드를 중지하시겠습니까?')) {
                fetch('/api/stop_online', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.message);
                        resetButtons();
                    });
            }
        }

        function saveCurrent() {
            document.getElementById('btnSave').disabled = true;

            fetch('/api/save_current', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if(data.success) {
                        alert('✅ ' + data.message + ' - 파일: ' + data.filename);
                    } else {
                        alert('❌ ' + data.message);
                    }
                    document.getElementById('btnSave').disabled = false;
                });
        }

        function resetButtons() {
            // Enable start buttons
            document.getElementById('btnStart').disabled = false;
            document.getElementById('btnOnline').disabled = false;

            // Hide and disable online controls
            document.getElementById('btnStopOnline').disabled = true;
            document.getElementById('btnStopOnline').style.display = 'none';
            document.getElementById('btnSave').disabled = true;
            document.getElementById('btnSave').style.display = 'none';

            // Hide auto stop button
            document.getElementById('btnStop').disabled = true;
            document.getElementById('btnStop').style.display = 'none';

            document.getElementById('status').innerHTML = '자동 검사 시작 버튼을 눌러주세요';
        }

        function toggleTargetBox() {
            fetch('/api/toggle_target_box', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    const btn = document.getElementById('btnToggleBox');
                    if(data.show_target_box) {
                        btn.textContent = '📦 Target Box: ON';
                        btn.classList.remove('off');
                    } else {
                        btn.textContent = '📦 Target Box: OFF';
                        btn.classList.add('off');
                    }
                });
        }

        function toggleROIPanel() {
            roiPanelVisible = !roiPanelVisible;
            const panel = document.getElementById('roiPanel');
            const btn = document.getElementById('btnToggleROI');

            if(roiPanelVisible) {
                panel.style.display = 'block';
                btn.classList.add('off');
                loadROI();
            } else {
                panel.style.display = 'none';
                btn.classList.remove('off');
            }
        }

        function loadROI() {
            fetch('/api/roi_config')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('sliderXStart').value = data.x_start;
                    document.getElementById('sliderXEnd').value = data.x_end;
                    document.getElementById('sliderYStart').value = data.y_start;
                    document.getElementById('sliderYEnd').value = data.y_end;
                    updateROIDisplay();
                });
        }

        function updateROI() {
            const xStart = parseInt(document.getElementById('sliderXStart').value);
            const xEnd = parseInt(document.getElementById('sliderXEnd').value);
            const yStart = parseInt(document.getElementById('sliderYStart').value);
            const yEnd = parseInt(document.getElementById('sliderYEnd').value);

            // 실시간 서버 업데이트
            fetch('/api/roi_config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x_start: xStart,
                    x_end: xEnd,
                    y_start: yStart,
                    y_end: yEnd
                })
            });

            updateROIDisplay();
        }

        function updateROIDisplay() {
            const xStart = parseInt(document.getElementById('sliderXStart').value);
            const xEnd = parseInt(document.getElementById('sliderXEnd').value);
            const yStart = parseInt(document.getElementById('sliderYStart').value);
            const yEnd = parseInt(document.getElementById('sliderYEnd').value);

            document.getElementById('valXStart').textContent = xStart;
            document.getElementById('valXEnd').textContent = xEnd;
            document.getElementById('valYStart').textContent = yStart;
            document.getElementById('valYEnd').textContent = yEnd;

            const width = xEnd - xStart;
            const height = yEnd - yStart;
            document.getElementById('roiWidth').textContent = width;
            document.getElementById('roiHeight').textContent = height;
        }

        function saveROI() {
            if(confirm('현재 ROI 설정을 저장하시겠습니까?')) {
                fetch('/api/roi_save', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        if(data.success) {
                            alert('✅ ' + data.message);
                        } else {
                            alert('❌ ' + data.message);
                        }
                    });
            }
        }

        function resetROI() {
            if(confirm('저장된 ROI 설정으로 리셋하시겠습니까?')) {
                loadROI();
            }
        }

        function updateUI() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    // Status
                    const statusEl = document.getElementById('status');

                    if (data.is_online_mode) {
                        // Online mode status
                        statusEl.innerHTML = '🔄 온라인 모드 실행 중 - 연속 탐지 중...';

                        // Ensure correct button states
                        document.getElementById('btnStart').disabled = true;
                        document.getElementById('btnOnline').disabled = true;
                        document.getElementById('btnStopOnline').disabled = false;
                        document.getElementById('btnStopOnline').style.display = 'inline-block';
                        document.getElementById('btnSave').disabled = false;
                        document.getElementById('btnSave').style.display = 'inline-block';
                        document.getElementById('btnStop').style.display = 'none';

                    } else if (data.is_active) {
                        // Auto mode status
                        statusEl.innerHTML = `🎯 Zone ${data.current_zone + 1} / ${data.total_zones} 검사 중...`;

                        // Ensure correct button states for auto mode
                        document.getElementById('btnStart').disabled = true;
                        document.getElementById('btnOnline').disabled = true;
                        document.getElementById('btnStop').disabled = false;
                        document.getElementById('btnStop').style.display = 'inline-block';
                        document.getElementById('btnStopOnline').style.display = 'none';
                        document.getElementById('btnSave').style.display = 'none';

                    } else {
                        // Idle status
                        statusEl.innerHTML = data.completed_zones > 0
                            ? `✅ 검사 완료 - ${data.completed_zones} zones, ${data.defective_zones} defects`
                            : '자동 검사 시작 버튼을 눌러주세요';

                        // Reset buttons when inspection completes
                        if(data.completed_zones > 0) {
                            resetButtons();
                        }
                    }

                    // 온라인 모드일 때는 Zone 결과 카드 숨기기
                    const zoneResultsCard = document.getElementById('zoneResultsCard');
                    if (zoneResultsCard) {
                        if (data.is_online_mode) {
                            zoneResultsCard.style.display = 'none';
                        } else {
                            zoneResultsCard.style.display = '';
                        }
                    }

                    // Zones with results
                    const zonesEl = document.getElementById('zones');

                    // 온라인 모드가 아닐 때만 zones 영역 초기화
                    if (!data.is_online_mode) {
                        zonesEl.innerHTML = '';
                    }

                    // 최근 검사 결과 업데이트 (오른쪽 패널)
                    const latestResultEl = document.getElementById('latestResult');
                    if (data.zone_results && data.zone_results.length > 0) {
                        const latestResult = data.zone_results[data.zone_results.length - 1];
                        const pathParts = latestResult.image_path.split('/');
                        const resultsIdx = pathParts.indexOf('inspection_results');
                        const relativePath = resultsIdx >= 0
                            ? pathParts.slice(resultsIdx + 1).join('/')
                            : pathParts.slice(-2).join('/');

                        let content = `<img src="/images/${relativePath}" alt="Latest Result" style="border-radius: 8px;">`;
                        content += `<div style="margin-top: 15px; font-size: 1.1em; font-weight: bold; color: #1e3a8a;">Zone ${latestResult.zone_id + 1}</div>`;

                        if (latestResult.detection_method === 'yolo') {
                            content += `<div class="zone-method">🔍 YOLO 객체 탐지</div>`;
                        } else if (latestResult.detection_method === 'patchcore') {
                            content += `<div class="zone-method">🔬 PatchCore 이상 탐지</div>`;
                        } else {
                            content += `<div class="zone-method">✅ 정상</div>`;
                        }

                        if (latestResult.is_defective && latestResult.defects.length > 0) {
                            latestResult.defects.forEach(defect => {
                                content += `<div class="zone-defect-name">⚠️ ${defect.class_name}</div>`;
                                if (defect.class_name === 'anomaly') {
                                    content += `<div style="font-size: 0.9em; color: #fbbf24;">이상도: ${defect.confidence.toFixed(1)}</div>`;
                                } else {
                                    content += `<div style="font-size: 0.9em; color: #fbbf24;">신뢰도: ${(defect.confidence * 100).toFixed(1)}%</div>`;
                                }
                            });
                        }

                        latestResultEl.innerHTML = content;
                        latestResultEl.className = 'latest-result-img';
                    } else if (data.is_online_mode && data.online_session_name) {
                        const timestamp = new Date().getTime();
                        // 이미지만 업데이트하여 깜빡임 방지
                        let imgEl = latestResultEl.querySelector('img');
                        if (imgEl) {
                            // 이미지만 src 업데이트
                            imgEl.src = `/images/${data.online_session_name}/current_frame.jpg?t=${timestamp}`;
                        } else {
                            // 처음 한 번만 전체 생성
                            latestResultEl.innerHTML = `
                                <img src="/images/${data.online_session_name}/current_frame.jpg?t=${timestamp}"
                                     alt="Online Detection"
                                     style="border-radius: 8px;">
                            `;
                        }
                        latestResultEl.className = 'latest-result-img';
                    } else {
                        latestResultEl.innerHTML = '<div class="no-result">검사를 시작하면 결과가 표시됩니다</div>';
                        latestResultEl.className = 'latest-result-img';
                    }

                    // Online mode: Show single detection result card
                    if (data.is_online_mode && data.online_session_name) {
                        const timestamp = new Date().getTime(); // Force image reload
                        let onlineCard = zonesEl.querySelector('.zone-card.current');

                        if (onlineCard) {
                            // 기존 카드가 있으면 이미지만 업데이트
                            const imgEl = onlineCard.querySelector('img');
                            if (imgEl) {
                                imgEl.src = `/images/${data.online_session_name}/current_frame.jpg?t=${timestamp}`;
                            }
                        } else {
                            // 처음 한 번만 카드 생성
                            onlineCard = document.createElement('div');
                            onlineCard.className = 'zone-card current';
                            onlineCard.innerHTML = `
                                <div style="font-size: 1.2em; font-weight: bold;">🔄 Online Mode</div>
                                <img src="/images/${data.online_session_name}/current_frame.jpg?t=${timestamp}"
                                     alt="Online Detection">
                                <div class="zone-method">연속 탐지 중...</div>
                            `;
                            zonesEl.appendChild(onlineCard);
                        }
                        return; // Skip normal zone display
                    }

                    // Zone 결과를 맵으로 변환
                    const resultsMap = {};
                    if (data.zone_results) {
                        data.zone_results.forEach(result => {
                            resultsMap[result.zone_id] = result;
                        });
                    }

                    data.zone_types.forEach((type, idx) => {
                        const isCurrent = data.is_active && idx === data.current_zone;
                        const isCompleted = idx < data.completed_zones;
                        const result = resultsMap[idx];

                        const zoneCard = document.createElement('div');
                        let className = 'zone-card';
                        if (isCurrent) className += ' current';
                        if (isCompleted && result && result.is_defective) className += ' defect';
                        else if (isCompleted) className += ' completed';
                        zoneCard.className = className;

                        let content = `<div style="font-size: 1.2em; font-weight: bold;">Zone ${idx + 1}</div>`;

                        if (isCompleted && result) {
                            // 완료된 Zone: 결과 표시
                            // image_path에서 inspection_results/ 이후 경로 추출
                            const pathParts = result.image_path.split('/');
                            const resultsIdx = pathParts.indexOf('inspection_results');
                            const relativePath = resultsIdx >= 0
                                ? pathParts.slice(resultsIdx + 1).join('/')
                                : pathParts.slice(-2).join('/');  // 최소한 session_dir/filename

                            // 이미지 표시
                            content += `<img src="/images/${relativePath}" alt="Zone ${idx + 1} Result">`;

                            // 탐지 방법 표시
                            if (result.detection_method === 'yolo') {
                                content += `<div class="zone-method">🔍 YOLO 객체 탐지</div>`;
                            } else if (result.detection_method === 'patchcore') {
                                content += `<div class="zone-method">🔬 PatchCore 이상 탐지</div>`;
                            } else {
                                content += `<div class="zone-method">✅ 정상</div>`;
                            }

                            // 결함 정보 표시
                            if (result.is_defective && result.defects.length > 0) {
                                result.defects.forEach(defect => {
                                    content += `<div class="zone-defect-name">⚠️ ${defect.class_name}</div>`;
                                    if (defect.class_name === 'anomaly') {
                                        content += `<div style="font-size: 0.85em; color: #fbbf24;">이상도: ${defect.confidence.toFixed(1)}</div>`;
                                    } else {
                                        content += `<div style="font-size: 0.85em; color: #fbbf24;">신뢰도: ${(defect.confidence * 100).toFixed(1)}%</div>`;
                                    }
                                });
                            }
                        } else if (isCurrent) {
                            // 현재 검사 중
                            content += `<div style="font-size: 1.5em; margin: 20px 0;">🎯</div>`;
                            content += `<div style="font-size: 0.9em; color: #fbbf24;">검사 중...</div>`;
                        } else {
                            // 대기 중
                            content += `<div style="font-size: 1.5em; margin: 20px 0;">⏳</div>`;
                            content += `<div style="font-size: 0.9em; color: #aaa;">대기 중</div>`;
                        }

                        zoneCard.innerHTML = content;
                        zonesEl.appendChild(zoneCard);
                    });
                });
        }

        // Initialize target box button state
        function initTargetBoxButton() {
            fetch('/api/target_box_status')
                .then(res => res.json())
                .then(data => {
                    const btn = document.getElementById('btnToggleBox');
                    if(data.show_target_box) {
                        btn.textContent = '📦 Target Box: ON';
                        btn.classList.remove('off');
                    } else {
                        btn.textContent = '📦 Target Box: OFF';
                        btn.classList.add('off');
                    }
                });
        }

        // Initial load & periodic update
        initTargetBoxButton();
        updateUI();
        setInterval(updateUI, 1000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/images/<path:filepath>')
def serve_image(filepath):
    """저장된 이미지 제공"""
    from pathlib import Path

    # filepath는 "auto_session_xxx/zone_xx.jpg" 형태
    script_dir = Path(__file__).parent
    results_dir = script_dir.parent / 'inspection_results'

    image_path = results_dir / filepath
    if image_path.exists() and image_path.is_file():
        return send_file(str(image_path), mimetype='image/jpeg')

    return "Image not found", 404


@app.route('/video_feed')
def video_feed():
    """실시간 비디오 스트림 - ROI만 표시"""
    global inspection_system, camera_controller
    
    if inspection_system:
        return Response(inspection_system.generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        # 시스템 없을 때 카메라 프리뷰 (깔끔하게)
        def preview():
            global show_target_box

            while True:
                frame = camera_controller.capture_frame(crop_roi=False)
                if frame is None:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "No Feed", (250, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                else:
                    # Target Box (ROI) 표시만 (깔끔하게)
                    if show_target_box:
                        roi = camera_controller.roi_config
                        cv2.rectangle(frame,
                                     (roi.x_start, roi.y_start),
                                     (roi.x_end, roi.y_end),
                                     (0, 255, 0), 2)

                    # 가로 중앙 크롭 (타겟박스 기준 좌우 100px)
                    roi = camera_controller.roi_config
                    height, width = frame.shape[:2]
                    start_x = max(0, roi.x_start - 100)
                    end_x = min(width, roi.x_end + 100)
                    frame = frame[:, start_x:end_x]

                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(0.03)

        return Response(preview(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/start_auto', methods=['POST'])
def api_start_auto():
    """자동 검사 시작"""
    global inspection_system, motor_controller, camera_controller, yolo_detector, patchcore_detector

    if inspection_system and inspection_system.is_active:
        return jsonify({'success': False, 'message': '이미 진행 중입니다'})

    # 시스템 생성 (YOLO + PatchCore 2단계 하이브리드)
    config = InspectionConfig()
    inspection_system = AutoInspectionSystem(
        config, motor_controller, camera_controller,
        yolo_detector, patchcore_detector
    )
    inspection_system.start_session()
    
    # 별도 스레드에서 자동 검사 실행
    def run_inspection():
        inspection_system.run_auto_inspection()
    
    threading.Thread(target=run_inspection, daemon=True).start()
    
    return jsonify({'success': True, 'message': '자동 검사 시작'})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """중지"""
    global inspection_system

    if inspection_system:
        inspection_system.is_active = False
        inspection_system.motor.stop()
        return jsonify({'success': True, 'message': '중지됨'})

    return jsonify({'success': False, 'message': '진행 중인 세션 없음'})


@app.route('/api/start_online', methods=['POST'])
def api_start_online():
    """온라인 모드 시작"""
    global inspection_system, motor_controller, camera_controller, yolo_detector, patchcore_detector

    # Check if auto mode is running
    if inspection_system and inspection_system.is_active:
        return jsonify({'success': False, 'message': '자동 검사가 진행 중입니다'})

    # Check if online mode already running
    if inspection_system and inspection_system.is_online_mode:
        return jsonify({'success': False, 'message': '이미 온라인 모드가 실행 중입니다'})

    # Create system if not exists
    if not inspection_system:
        config = InspectionConfig()
        inspection_system = AutoInspectionSystem(
            config, motor_controller, camera_controller,
            yolo_detector, patchcore_detector
        )

    # Start online mode
    inspection_system.is_online_mode = True

    # Run in separate thread
    def run_online():
        inspection_system.run_online_mode()

    threading.Thread(target=run_online, daemon=True).start()

    return jsonify({'success': True, 'message': '온라인 모드 시작'})


@app.route('/api/stop_online', methods=['POST'])
def api_stop_online():
    """온라인 모드 중지"""
    global inspection_system

    if not inspection_system or not inspection_system.is_online_mode:
        return jsonify({'success': False, 'message': '온라인 모드가 실행 중이 아닙니다'})

    inspection_system.is_online_mode = False

    return jsonify({'success': True, 'message': '온라인 모드 중지됨'})


@app.route('/api/save_current', methods=['POST'])
def api_save_current():
    """현재 프레임 저장 (온라인 모드 전용)"""
    global inspection_system

    if not inspection_system or not inspection_system.is_online_mode:
        return jsonify({'success': False, 'message': '온라인 모드가 실행 중이 아닙니다'})

    result = inspection_system.save_online_snapshot()

    return jsonify(result)


@app.route('/api/toggle_target_box', methods=['POST'])
def api_toggle_target_box():
    """Target Box 표시 on/off"""
    global show_target_box

    show_target_box = not show_target_box

    return jsonify({
        'success': True,
        'show_target_box': show_target_box,
        'message': f"Target Box {'ON' if show_target_box else 'OFF'}"
    })


@app.route('/api/target_box_status')
def api_target_box_status():
    """Target Box 표시 상태 조회"""
    global show_target_box

    return jsonify({
        'show_target_box': show_target_box
    })


@app.route('/api/status')
def api_status():
    """상태 조회"""
    global inspection_system

    if not inspection_system:
        config = InspectionConfig()
        return jsonify({
            'is_active': False,
            'is_online_mode': False,
            'current_zone': 0,
            'total_zones': config.num_zones,
            'completed_zones': 0,
            'defective_zones': 0,
            'zone_types': config.zone_types,
            'zone_results': []
        })

    # 모든 Zone 결과 수집 (결함 여부 관계없이)
    zone_results = []
    for result in inspection_system.results:
        defects = []
        detection_method = 'none'

        for det in result.detections:
            defects.append({
                'class_name': det['class_name'],
                'confidence': det['confidence']
            })
            # 탐지 방법 판단
            if det['class_name'] == 'anomaly':
                detection_method = 'patchcore'
            else:
                detection_method = 'yolo'

        zone_results.append({
            'zone_id': result.zone_id,
            'image_path': result.image_path,
            'defects': defects,
            'is_defective': result.is_defective,
            'detection_method': detection_method,
            'timestamp': result.timestamp
        })

    # Get online session directory name if in online mode
    online_session_name = None
    if inspection_system.is_online_mode and inspection_system.online_session_dir:
        online_session_name = inspection_system.online_session_dir.name

    return jsonify({
        'is_active': inspection_system.is_active,
        'is_online_mode': inspection_system.is_online_mode,
        'online_session_name': online_session_name,
        'current_zone': inspection_system.current_zone,
        'total_zones': inspection_system.config.num_zones,
        'completed_zones': len(inspection_system.results),
        'defective_zones': sum(1 for r in inspection_system.results if r.is_defective),
        'zone_types': inspection_system.config.zone_types,
        'zone_results': zone_results
    })


@app.route('/api/roi_config')
def api_roi_config():
    """현재 ROI 설정 조회"""
    global camera_controller

    if camera_controller:
        roi = camera_controller.roi_config
        return jsonify({
            'x_start': roi.x_start,
            'x_end': roi.x_end,
            'y_start': roi.y_start,
            'y_end': roi.y_end,
            'real_width_cm': roi.real_width_cm,
            'real_height_cm': roi.real_height_cm
        })

    return jsonify({'error': 'Camera not initialized'}), 500


@app.route('/api/roi_config', methods=['POST'])
def api_roi_config_update():
    """ROI 설정 업데이트 (임시, 파일에 저장 안함)"""
    global camera_controller

    if not camera_controller:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500

    data = request.json
    roi = camera_controller.roi_config

    # 값 업데이트
    roi.x_start = int(data.get('x_start', roi.x_start))
    roi.x_end = int(data.get('x_end', roi.x_end))
    roi.y_start = int(data.get('y_start', roi.y_start))
    roi.y_end = int(data.get('y_end', roi.y_end))

    print(f"[ROI] Updated (temporary): ({roi.x_start}, {roi.y_start}) -> ({roi.x_end}, {roi.y_end})")

    return jsonify({
        'success': True,
        'message': 'ROI updated (not saved)',
        'roi': {
            'x_start': roi.x_start,
            'x_end': roi.x_end,
            'y_start': roi.y_start,
            'y_end': roi.y_end
        }
    })


@app.route('/api/roi_save', methods=['POST'])
def api_roi_save():
    """ROI 설정을 파일에 저장"""
    global camera_controller

    if not camera_controller:
        return jsonify({'success': False, 'message': 'Camera not initialized'}), 500

    roi = camera_controller.roi_config
    success = roi.save_to_file()

    if success:
        return jsonify({
            'success': True,
            'message': 'ROI 설정이 저장되었습니다'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'ROI 저장 실패'
        }), 500


if __name__ == '__main__':
    print("=" * 70)
    print("  Orin Car Auto Inspection System")
    print("=" * 70)
    print("  🚗 AUTO MODE - Calibrated Drive")
    print("  📦 30cm 구역별 자동 주행 검사")
    print("  🎯 YOLO + PatchCore 하이브리드 탐지")
    print("=" * 70)

    try:
        # 전역 리소스 초기화
        init_global_resources()

        # Flask 로깅 끄기 (API 요청 로그 숨기기)
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        print("  Access: http://<Jetson IP>:5004")
        print("=" * 70)

        app.run(host='0.0.0.0', port=5004, debug=False, threaded=True)

    finally:
        # 정리
        if inspection_system:
            inspection_system.cleanup()
        if motor_controller:
            motor_controller.cleanup()
        if camera_controller:
            camera_controller.release()
        print("[INFO] Cleanup complete")