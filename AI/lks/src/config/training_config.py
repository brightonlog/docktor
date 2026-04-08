"""
Training Configuration
웹캠 1080p (1920×1080) 고려한 학습 설정
"""

from pathlib import Path

# ============================================================================
# Image Preprocessing Config
# ============================================================================

# Webcam resolution: 1920×1080 (16:9)
# Target size: 1280×720 (16:9, 실시간 추론 가능)
IMAGE_SIZE = (1280, 720)  # (width, height)
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720

# Alternative sizes (for experimentation)
IMAGE_SIZES = {
    '1280x720': (1280, 720),   # 720p, 16:9, 웹캠 최적
    '1024x1024': (1024, 1024),  # Square, letterbox
    '960x544': (960, 544),      # 16:9, 작은 크기
    '640x640': (640, 640),      # YOLOv8 default
}

# Normalization (ImageNet)
NORMALIZE_MEAN = (0.485, 0.456, 0.406)
NORMALIZE_STD = (0.229, 0.224, 0.225)

# ============================================================================
# YOLO Model Config
# ============================================================================

# Model variant
MODEL_NAME = 'yolov8n'  # nano (가장 빠름)
# Available: yolov8n, yolov8s, yolov8m, yolov8l, yolov8x

# Number of classes (101 제외하고 결함만)
# 201-207 (7개) + 301-303 (3개) = 10개
NUM_CLASSES = 10

# Class names (YOLO format, 0-indexed)
CLASS_NAMES = [
    'water_spotting',     # 0 (category_id: 201)
    'sagging',            # 1 (category_id: 202)
    'coating_separation', # 2 (category_id: 203)
    'pinhole',            # 3 (category_id: 204)
    'crack',              # 4 (category_id: 205)
    'blister',            # 5 (category_id: 206)
    'foreign_material',   # 6 (category_id: 207)
    'welding_damage',     # 7 (category_id: 301)
    'scratch',            # 8 (category_id: 302)
    'peeling'             # 9 (category_id: 303)
]

# Category ID to YOLO class index mapping
CATEGORY_TO_YOLO = {
    201: 0,  # water_spotting
    202: 1,  # sagging
    203: 2,  # coating_separation
    204: 3,  # pinhole
    205: 4,  # crack
    206: 5,  # blister
    207: 6,  # foreign_material
    301: 7,  # welding_damage
    302: 8,  # scratch
    303: 9,  # peeling
}

# YOLO class index to category ID mapping
YOLO_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_YOLO.items()}

# ============================================================================
# Training Hyperparameters
# ============================================================================

# Training
EPOCHS = 100
BATCH_SIZE = 16
LEARNING_RATE = 0.01
WARMUP_EPOCHS = 3
WEIGHT_DECAY = 0.0005

# Optimizer
OPTIMIZER = 'AdamW'  # or 'SGD', 'Adam'
MOMENTUM = 0.937     # for SGD

# Learning rate scheduler
LR_SCHEDULER = 'cosine'  # 'cosine', 'linear', 'step'

# Early stopping
PATIENCE = 50  # epochs

# Mixed precision
AMP = True  # Automatic Mixed Precision

# Multi-GPU
DEVICE = 0  # GPU device, or 'cpu'

# ============================================================================
# Data Augmentation (YOLOv8 style)
# ============================================================================

# Geometric augmentations
AUGMENT = True
DEGREES = 10.0        # rotation
TRANSLATE = 0.1       # translation
SCALE = 0.5           # scale
SHEAR = 0.0           # shear
PERSPECTIVE = 0.0     # perspective

# Flip
FLIPLR = 0.5          # horizontal flip probability
FLIPUD = 0.5          # vertical flip probability

# Mosaic & MixUp
MOSAIC = 0.0          # mosaic probability (작은 결함 고려하여 끔)
MIXUP = 0.0           # mixup probability (작은 결함 고려하여 끔)

# Color augmentations
HSV_H = 0.015         # hue
HSV_S = 0.7           # saturation
HSV_V = 0.4           # value

# ============================================================================
# Dataset Config
# ============================================================================

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = PROJECT_ROOT / 'data'
EXTRACTED_DIR = DATA_ROOT / 'extracted'
IMAGE_DIR = EXTRACTED_DIR / '01.images'
LABEL_DIR = EXTRACTED_DIR / '02.labels'

# YOLO dataset directory
YOLO_DATA_DIR = DATA_ROOT / 'yolo_dataset'
YOLO_IMAGES_DIR = YOLO_DATA_DIR / 'images'
YOLO_LABELS_DIR = YOLO_DATA_DIR / 'labels'

# Train/Val split
TRAIN_RATIO = 0.8
VAL_RATIO = 0.2
RANDOM_SEED = 42

# Minimum annotations
MIN_BBOX_AREA = 50  # minimum bbox area in pixels

# ============================================================================
# MLOps Config
# ============================================================================

# MLflow (파일 기반 저장)
# 원격 서버 환경에서 localhost 접근 불가하므로 로컬 파일 시스템 사용
# Windows 호환성: Path.as_uri()로 file:/// URI 형식 사용
MLFLOW_TRACKING_URI = (PROJECT_ROOT / 'mlruns').as_uri()  # file:/// URI 형식
MLFLOW_EXPERIMENT_NAME = 'ship-coating-defect-detection'

# Prometheus (비활성화)
# UI 접근 불가하므로 사용하지 않음
PROMETHEUS_PORT = 8000
PROMETHEUS_METRICS_PATH = '/metrics'
ENABLE_PROMETHEUS = False  # Prometheus exporter 비활성화

# Model checkpoints
CHECKPOINT_DIR = PROJECT_ROOT / 'checkpoints'
RUNS_DIR = PROJECT_ROOT / 'runs'

# Logging
LOG_INTERVAL = 10  # log every N batches
SAVE_PERIOD = 10   # save checkpoint every N epochs

# ============================================================================
# Evaluation Config
# ============================================================================

# Confidence threshold
CONF_THRESHOLD = 0.25

# IoU threshold for NMS
IOU_THRESHOLD = 0.45

# IoU threshold for evaluation
EVAL_IOU_THRESHOLD = 0.5

# mAP calculation
MAP_50 = True   # mAP@0.5
MAP_50_95 = True  # mAP@0.5:0.95

# ============================================================================
# Inference Config (오린카 웹캠)
# ============================================================================

# Webcam settings
WEBCAM_RESOLUTION = (1920, 1080)
WEBCAM_FPS = 30

# Real-time inference
INFERENCE_SIZE = (1280, 720)  # 웹캠 해상도와 동일 비율
INFERENCE_CONF_THRESHOLD = 0.4  # 높은 confidence만
INFERENCE_IOU_THRESHOLD = 0.45

# Visualization
SHOW_LABELS = True
SHOW_CONF = True
LINE_THICKNESS = 2
