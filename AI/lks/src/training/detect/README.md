# Training Module

YOLOv8 기반 선박 도장 결함 탐지 모델 학습 모듈

## 개요

이 모듈은 선박 도장 결함 탐지를 위한 YOLOv8 모델 학습 및 평가 파이프라인을 제공합니다.
MLflow를 활용한 파일 기반 실험 추적을 지원하며, 원격 서버 환경에 최적화되어 있습니다.

> **Note**: 원격 서버 환경에서 localhost 접근이 불가하므로 MLflow UI, Prometheus, Grafana는 비활성화되어 있습니다.
> 모든 메트릭과 모델은 로컬 파일 시스템에 저장됩니다.

## Quick Start

```bash
# 1. 데이터셋 준비
python src/training/prepare_yolo_dataset.py

# 2. 학습 스크립트에 실행 권한 부여 (최초 1회만)
chmod +x src/training/run_training.sh

# 3. 학습 실행 (간편)
./src/training/run_training.sh --model yolov8n --epochs 100 --batch 16

# 3. 학습 진행 확인 (다른 터미널)
tail -f runs/detect/train/results.csv

# 4. 학습 완료 후 평가
python src/training/evaluate.py \
    --model runs/detect/train/weights/best.pt \
    --save-dir results/evaluation

# 5. 결과 확인
ls runs/detect/train/          # 학습 결과
ls results/evaluation/          # 평가 결과
cat runs/detect/train/results.csv  # 메트릭
```

## 디렉토리 구조

```
training/
├── prepare_yolo_dataset.py    # YOLO 데이터셋 준비
├── train_yolov8.py             # YOLOv8 모델 학습 (MLflow 파일 기반)
├── prometheus_exporter.py      # Prometheus 메트릭 exporter (현재 비활성화)
├── evaluate.py                 # 모델 평가 및 분석
├── run_training.sh             # 전체 학습 파이프라인 실행 스크립트
└── README.md                   # 이 파일
```

## 주요 기능

### 1. YOLO 데이터셋 준비 (prepare_yolo_dataset.py)

JSON 형식의 어노테이션을 YOLO 포맷으로 변환하고 데이터셋을 구성합니다.

**주요 기능:**
- JSON 어노테이션 → YOLO 포맷 변환
- COCO bbox [x, y, w, h] → YOLO bbox [x_center, y_center, w, h] (정규화)
- 이미지 리사이즈 (letterbox)
- Train/Val 데이터셋 분할
- data.yaml 자동 생성
- Normal(101) 카테고리 필터링
- 최소 bbox 면적 기반 필터링

**사용법:**
```bash
python src/training/prepare_yolo_dataset.py \
    --width 1280 \
    --height 720 \
    --train-ratio 0.8 \
    --seed 42
```

**주요 파라미터:**
- `--width`: 이미지 너비 (default: 1280)
- `--height`: 이미지 높이 (default: 720)
- `--train-ratio`: 학습 데이터 비율 (default: 0.8)
- `--seed`: 랜덤 시드 (default: 42)

**출력:**
```
data/yolo_dataset/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── data.yaml
```

### 2. YOLOv8 모델 학습 (train_yolov8.py)

YOLOv8 모델을 학습하고 MLflow로 실험을 추적합니다 (파일 기반).

**주요 기능:**
- YOLOv8 모델 학습 (n/s/m/l/x 변형 지원)
- MLflow 통합 (파일 기반 실험 추적, 메트릭 로깅)
- 하이퍼파라미터 로깅
- 학습 곡선, confusion matrix 등 아티팩트 저장
- 모델 체크포인트 자동 저장
- Early stopping 지원
- Data augmentation 설정
- **원격 서버 환경 최적화**: 모든 결과를 로컬 파일로 저장

**사용법:**
```bash
python src/training/train_yolov8.py \
    --model yolov8n \
    --data data/yolo_dataset/data.yaml \
    --epochs 100 \
    --batch 16 \
    --device 0
```

**주요 파라미터:**
- `--model`: YOLOv8 모델 변형 (yolov8n/s/m/l/x)
- `--data`: data.yaml 경로
- `--epochs`: 학습 에포크 수 (default: 100)
- `--batch`: 배치 사이즈 (default: 16)
- `--device`: GPU 디바이스 (0, 1, 2, ... 또는 'cpu')
- `--name`: 실험 이름
- `--resume`: 체크포인트에서 재개
- `--pretrained`: 사전 학습된 가중치 사용

**MLflow 추적 항목:**
- Parameters: 모델, 하이퍼파라미터, augmentation 설정
- Metrics: loss, precision, recall, mAP50, mAP50-95
- Artifacts: 모델 weights, 학습 곡선, confusion matrix, PR curve

**저장 위치:**
- MLflow 로그: `mlruns/` 디렉토리
- 모델 weights: `runs/detect/train/weights/`
- 학습 결과: `runs/detect/train/`

### 3. Prometheus 메트릭 Exporter (prometheus_exporter.py) - ⚠️ 현재 비활성화

> **Note**: 원격 서버 환경에서 localhost 접근이 불가하므로 현재 사용하지 않습니다.
> 학습 메트릭은 `runs/detect/train/results.csv` 파일에서 확인할 수 있습니다.

<details>
<summary>Prometheus exporter 정보 (참고용)</summary>

실시간 학습 메트릭을 Prometheus로 export합니다.

**주요 기능:**
- 실시간 학습 메트릭 모니터링
- Loss 메트릭 (box, cls, dfl)
- 성능 메트릭 (precision, recall, mAP)
- GPU 활용률 및 메모리 모니터링
- 학습 진행률 추적

로컬 환경에서만 사용 가능합니다.
</details>

### 4. 모델 평가 (evaluate.py)

학습된 모델을 평가하고 상세 분석 결과를 생성합니다.

**주요 기능:**
- Validation set 평가
- 클래스별 성능 메트릭 분석
- 시각화 생성 (mAP, precision-recall 등)
- 단일 이미지 추론 테스트
- 추론 속도 벤치마크

**사용법:**
```bash
python src/training/evaluate.py \
    --model runs/detect/train/weights/best.pt \
    --data data/yolo_dataset/data.yaml \
    --save-dir results/evaluation
```

**주요 파라미터:**
- `--model`: 학습된 모델 경로 (best.pt)
- `--data`: data.yaml 경로
- `--save-dir`: 결과 저장 디렉토리
- `--benchmark`: 속도 벤치마크 실행
- `--test-image`: 단일 이미지 테스트

**출력:**
```
results/evaluation/
├── metrics.csv                      # 클래스별 메트릭
├── per_class_map50.png              # 클래스별 mAP 막대 그래프
├── precision_recall_scatter.png     # Precision-Recall 산점도
└── metrics_comparison.png           # 메트릭 비교 그래프
```

**평가 메트릭:**
- mAP@0.5: IoU 0.5에서의 평균 정밀도
- mAP@0.5:0.95: IoU 0.5~0.95에서의 평균 정밀도
- Precision: 정밀도
- Recall: 재현율
- 클래스별 성능 분석

### 5. 전체 학습 파이프라인 (run_training.sh)

데이터셋 검증부터 모델 학습까지 전체 파이프라인을 자동화합니다.

**주요 기능:**
- 데이터셋 검증
- 모델 학습 실행
- 파일 기반 결과 저장

**사용법:**
```bash
./src/training/run_training.sh \
    --model yolov8n \
    --epochs 100 \
    --batch 16 \
    --device 0
```

**주요 파라미터:**
- `--model`: YOLOv8 모델 변형
- `--epochs`: 에포크 수
- `--batch`: 배치 사이즈
- `--device`: GPU 디바이스

**실행 단계:**
1. 데이터셋 확인
2. 모델 학습 실행

**결과 저장 위치:**
- 모델 weights: `runs/detect/train/weights/best.pt`
- 학습 곡선: `runs/detect/train/*.png`
- MLflow 로그: `mlruns/`
- 메트릭 CSV: `runs/detect/train/results.csv`

## 학습 워크플로우

### 전체 파이프라인

```bash
# 1. 데이터셋 준비
python src/training/prepare_yolo_dataset.py

# 2. 실행 권한 부여 (최초 1회만)
chmod +x src/training/run_training.sh

# 3. 전체 학습 파이프라인 실행
./src/training/run_training.sh --model yolov8n --epochs 100 --batch 16

# 3. 모델 평가
python src/training/evaluate.py \
    --model runs/detect/train/weights/best.pt \
    --save-dir results/evaluation \
    --benchmark
```

### 개별 실행

```bash
# 1. 데이터셋 준비
python src/training/prepare_yolo_dataset.py

# 2. 모델 학습
python src/training/train_yolov8.py \
    --model yolov8n \
    --epochs 100 \
    --batch 16

# 3. 학습 중 메트릭 확인 (다른 터미널에서)
tail -f runs/detect/train/results.csv

# 4. 모델 평가
python src/training/evaluate.py \
    --model runs/detect/train/weights/best.pt
```

## 원격 서버에서 결과 확인하기

원격 서버 환경에서 학습 결과를 확인하는 방법:

### 1. 학습 메트릭 확인

**results.csv 파일:**
```bash
# 전체 결과 보기
cat runs/detect/train/results.csv

# 마지막 10줄 (최신 에포크)
tail -10 runs/detect/train/results.csv

# CSV를 보기 좋게 출력
column -t -s, runs/detect/train/results.csv | less -S
```

**주요 메트릭:**
- `train/box_loss`, `train/cls_loss`: 학습 loss
- `val/box_loss`, `val/cls_loss`: 검증 loss
- `metrics/precision(B)`: Precision
- `metrics/recall(B)`: Recall
- `metrics/mAP50(B)`: mAP@0.5
- `metrics/mAP50-95(B)`: mAP@0.5:0.95

### 2. 학습 곡선 및 플롯 확인

**생성된 플롯 목록:**
```bash
ls -lh runs/detect/train/*.png
```

**플롯 다운로드 (로컬 머신에서):**
```bash
# SCP로 다운로드
scp user@remote-server:/path/to/runs/detect/train/*.png ./local_results/

# 또는 rsync 사용
rsync -avz user@remote-server:/path/to/runs/detect/train/ ./local_results/
```

### 3. 모델 weights 확인

```bash
# Best 모델
ls -lh runs/detect/train/weights/best.pt

# Last 모델
ls -lh runs/detect/train/weights/last.pt

# 모델 다운로드
scp user@remote-server:/path/to/runs/detect/train/weights/best.pt ./models/
```

### 4. MLflow 실험 기록 확인

```bash
# 실험 목록
ls -la mlruns/0/

# 특정 실험의 파라미터
cat mlruns/0/<run_id>/params/*

# 특정 실험의 메트릭
cat mlruns/0/<run_id>/metrics/*
```

### 5. 학습 로그 확인

```bash
# YOLOv8 학습 로그
cat runs/detect/train/train.log

# 또는 실시간 모니터링 중이었다면
tail -f runs/detect/train/train.log
```

## 설정 파일

학습 관련 설정은 `config/training_config.py`에 정의되어 있습니다:

**주요 설정:**
- 모델 설정: MODEL_NAME, IMAGE_WIDTH, IMAGE_HEIGHT
- 학습 설정: EPOCHS, BATCH_SIZE, LEARNING_RATE
- Augmentation: MOSAIC, MIXUP, DEGREES, TRANSLATE, SCALE, FLIP
- MLOps: MLFLOW_TRACKING_URI (파일 기반), ENABLE_PROMETHEUS (False)
- 클래스 매핑: CATEGORY_TO_YOLO, CLASS_NAMES

**파일 기반 저장 설정:**
```python
# MLflow 파일 기반 저장 (원격 서버 최적화)
MLFLOW_TRACKING_URI = str(PROJECT_ROOT / 'mlruns')
ENABLE_PROMETHEUS = False  # Prometheus 비활성화
```

## 실험 추적 및 모니터링

### MLflow (파일 기반)

**기능:**
- 실험 추적 및 관리
- 하이퍼파라미터 로깅
- 메트릭 시계열 저장
- 모델 아티팩트 관리

**저장 위치:**
```
mlruns/
├── 0/                          # Default experiment
│   ├── <run_id>/
│   │   ├── artifacts/          # 모델, 플롯 등
│   │   ├── metrics/            # 메트릭 시계열
│   │   ├── params/             # 하이퍼파라미터
│   │   └── tags/               # 메타데이터
│   └── meta.yaml
└── models/                      # 등록된 모델
```

**메트릭 확인 방법:**
```bash
# 1. MLflow 로그 확인
ls -la mlruns/0/

# 2. 특정 실험의 메트릭 확인
cat mlruns/0/<run_id>/metrics/*

# 3. 학습 결과 CSV 확인
cat runs/detect/train/results.csv

# 4. 학습 곡선 이미지 확인
ls runs/detect/train/*.png
```

### 학습 진행 상황 모니터링

**실시간 메트릭 확인:**
```bash
# results.csv 실시간 모니터링
tail -f runs/detect/train/results.csv

# 또는 watch 명령어 사용
watch -n 5 'tail -20 runs/detect/train/results.csv'
```

**GPU 사용률 확인:**
```bash
# nvidia-smi로 GPU 모니터링
watch -n 1 nvidia-smi
```

### 로컬 환경에서 MLflow UI 사용하기 (선택사항)

SSH 포트 포워딩을 통해 로컬 머신에서 MLflow UI에 접근할 수 있습니다:

```bash
# 로컬 머신에서 실행
ssh -L 5000:localhost:5000 user@remote-server

# MLflow UI 서버 시작 (원격 서버에서)
mlflow ui --backend-store-uri mlruns/

# 로컬 브라우저에서 접속
# http://localhost:5000
```

## 모델 버전 관리 (MLflow Model Registry)

학습된 모델은 자동으로 MLflow Model Registry에 등록됩니다.

### 모델 버전 확인

```bash
# 모든 모델 버전 조회
python src/training/model_registry.py list

# 최신 버전 확인
python src/training/model_registry.py latest

# Production 스테이지의 최신 버전
python src/training/model_registry.py latest --stage Production
```

### 모델 스테이지 관리

모델 버전은 다음 스테이지를 가질 수 있습니다:
- **None**: 기본 상태
- **Staging**: 테스트 단계
- **Production**: 프로덕션 배포
- **Archived**: 보관

```bash
# 버전 1을 Staging으로 전환
python src/training/model_registry.py stage 1 Staging

# 버전 2를 Production으로 승격 (기존 Production 버전 자동 Archive)
python src/training/model_registry.py promote 2

# 버전 3을 Production으로 승격 (기존 버전 유지)
python src/training/model_registry.py promote 3 --no-archive
```

### 모델 로드

```bash
# 최신 버전 로드
python src/training/model_registry.py load

# 특정 버전 로드
python src/training/model_registry.py load --version 2

# Production 스테이지 모델 로드
python src/training/model_registry.py load --stage Production
```

### 모델 정보 확인

```bash
# 특정 버전 상세 정보 (메트릭 + 파라미터)
python src/training/model_registry.py info 1
```

**출력 예시:**
```
Model: yolov8-ship-defect-detector
Version: 1
Stage: Production
Status: READY
Run ID: abc123def456
Created: 1706179200000
Description: yolov8n trained on ship coating defect dataset

Metrics:
  metrics/mAP50: 0.8234
  metrics/mAP50-95: 0.6512
  metrics/precision: 0.7891
  metrics/recall: 0.8021
  train/box_loss: 0.0234
  val/box_loss: 0.0312

Parameters:
  model: yolov8n
  epochs: 100
  batch_size: 16
  lr0: 0.01
  imgsz: 720
```

### 모델 성능 비교

여러 모델 버전의 성능을 비교하여 최적의 모델을 선택할 수 있습니다.

**모든 버전 비교:**
```bash
python src/training/model_registry.py compare
```

**특정 버전들만 비교:**
```bash
# 버전 1, 2, 3 비교
python src/training/model_registry.py compare --versions 1 2 3
```

**출력 예시:**
```
Model Performance Comparison: yolov8-ship-defect-detector
========================================================================================
| Ver | Stage      | Model   | Epochs | Batch | mAP50  | mAP50-95 | Precision | Recall | Run ID   |
========================================================================================
| 1   | Archived   | yolov8n | 100    | 16    | 0.8234 | 0.6512   | 0.7891    | 0.8021 | abc123de |
| 2   | Staging    | yolov8s | 100    | 16    | 0.8567 | 0.6890   | 0.8234    | 0.8345 | def456ab |
| 3   | Production | yolov8n | 150    | 32    | 0.8712 | 0.7123   | 0.8456    | 0.8567 | ghi789cd |
========================================================================================

Best Models:
  Best mAP50: Version 3 (0.8712)
  Best mAP50-95: Version 3 (0.7123)
```

**최고 성능 모델 찾기:**
```bash
# mAP50 기준 최고 모델
python src/training/model_registry.py best --metric mAP50

# mAP50-95 기준 최고 모델
python src/training/model_registry.py best --metric mAP50-95

# Precision 기준 최고 모델
python src/training/model_registry.py best --metric precision

# Recall 기준 최고 모델
python src/training/model_registry.py best --metric recall
```

**출력 예시:**
```
Best model by mAP50:
  Version: 3
  Stage: Production
  mAP50: 0.8712
  Run ID: ghi789cd
```

### 모델 선택 기준

**메트릭 선택 가이드:**

1. **mAP50** (권장)
   - IoU 0.5에서의 평균 정밀도
   - 일반적인 객체 탐지 성능 지표
   - **사용 시기**: 대부분의 경우 기본 선택

2. **mAP50-95**
   - IoU 0.5~0.95에서의 평균 정밀도
   - 더 엄격한 평가 기준
   - **사용 시기**: 정확한 위치 파악이 중요한 경우

3. **Precision (정밀도)**
   - 탐지한 결함 중 실제 결함 비율
   - False Positive 최소화
   - **사용 시기**: 오탐지(False Alarm)를 줄이고 싶을 때

4. **Recall (재현율)**
   - 실제 결함 중 탐지한 결함 비율
   - False Negative 최소화
   - **사용 시기**: 결함을 놓치면 안 되는 경우 (안전 중시)

**실전 예시:**

```bash
# 1. 모든 모델 비교
python src/training/model_registry.py compare

# 2. 최고 성능 모델 확인
python src/training/model_registry.py best --metric mAP50

# 3. 해당 버전 상세 정보 확인
python src/training/model_registry.py info 3

# 4. 성능 좋은 모델을 Staging으로
python src/training/model_registry.py stage 3 Staging

# 5. 검증 후 Production으로 승격
python src/training/model_registry.py promote 3
```

### 모델 버전 삭제

```bash
# 특정 버전 삭제
python src/training/model_registry.py delete 1
```

### Python 코드에서 모델 사용

```python
from training.model_registry import ModelRegistry

# Registry 초기화
registry = ModelRegistry()

# Production 모델 로드
model_path = registry.load_model(stage='Production')

# YOLO 모델로 사용
from ultralytics import YOLO
model = YOLO(model_path)

# 추론
results = model.predict('image.jpg')
```

### 실전 모델 관리 워크플로우

**시나리오 1: 여러 실험 중 최고 모델 찾기**

```bash
# 1. yolov8n으로 실험
./src/training/run_training.sh --model yolov8n --epochs 100 --batch 16

# 2. yolov8s로 실험
./src/training/run_training.sh --model yolov8s --epochs 100 --batch 16

# 3. yolov8n을 더 오래 학습
./src/training/run_training.sh --model yolov8n --epochs 150 --batch 32

# 4. 모든 모델 성능 비교
python src/training/model_registry.py compare

# 5. 최고 성능 모델 확인
python src/training/model_registry.py best --metric mAP50

# 6. 최고 모델을 Production으로
python src/training/model_registry.py promote 3
```

**시나리오 2: 기존 모델 개선**

```bash
# 1. 현재 Production 모델 확인
python src/training/model_registry.py latest --stage Production

# 2. 성능 확인
python src/training/model_registry.py info 2

# 3. 새로운 실험 (하이퍼파라미터 튜닝)
./src/training/run_training.sh --model yolov8n --epochs 200 --batch 32

# 4. 이전 버전과 비교
python src/training/model_registry.py compare --versions 2 3

# 5. 새 모델이 더 좋으면 Staging으로
python src/training/model_registry.py stage 3 Staging

# 6. 실전 테스트 후 Production 승격
python src/training/model_registry.py promote 3
```

**시나리오 3: 용도별 모델 선택**

```bash
# 1. 모든 모델 비교
python src/training/model_registry.py compare

# 2. 안전 중시 (높은 Recall) 모델 찾기
python src/training/model_registry.py best --metric recall

# 3. 정확도 중시 (높은 Precision) 모델 찾기
python src/training/model_registry.py best --metric precision

# 4. 종합 성능 (mAP) 모델 찾기
python src/training/model_registry.py best --metric mAP50

# 5. 용도에 맞는 모델을 각각 스테이지 설정
# 안전 중시 모델 → Production
python src/training/model_registry.py promote 5

# 정확도 중시 모델 → Staging (필요시 사용)
python src/training/model_registry.py stage 3 Staging
```

**시나리오 4: 모델 롤백**

```bash
# 1. Production 모델에 문제 발생
# 2. 이전 버전들 비교
python src/training/model_registry.py compare

# 3. 이전에 잘 작동하던 버전 확인
python src/training/model_registry.py info 2

# 4. 해당 버전을 다시 Production으로
python src/training/model_registry.py promote 2

# 5. 문제 있던 버전은 Archive
python src/training/model_registry.py stage 4 Archived
```

### 모델 성능 모니터링

**정기적인 성능 체크:**

```bash
# 주간 리포트 생성 스크립트 예시
#!/bin/bash

echo "=== Weekly Model Performance Report ==="
echo ""

# 모든 모델 비교
python src/training/model_registry.py compare

# Production 모델 상세 정보
echo ""
echo "=== Current Production Model ==="
python src/training/model_registry.py latest --stage Production

# 최고 성능 모델
echo ""
echo "=== Best Performing Model ==="
python src/training/model_registry.py best --metric mAP50
```

**MLflow로 상세 분석:**

```bash
# SSH 포트 포워딩
ssh -L 5000:localhost:5000 user@server

# MLflow UI 시작
mlflow ui --backend-store-uri mlruns/

# 브라우저에서 http://localhost:5000 접속
# - 학습 곡선 비교
# - 하이퍼파라미터 영향 분석
# - 클래스별 성능 확인
```

## 결함 클래스

학습 대상 결함 클래스 (총 10개):

**도장 결함 (201-207):**
1. **Water Spotting (물얼룩)**: category_id 201
2. **Sagging (흘러내림)**: category_id 202
3. **Coating Separation (도장 분리)**: category_id 203
4. **Pinhole (핀홀)**: category_id 204
5. **Crack (균열)**: category_id 205
6. **Blister (기포)**: category_id 206
7. **Foreign Material (이물질)**: category_id 207

**용접 및 기타 결함 (301-303):**
8. **Welding Damage (용접 손상)**: category_id 301
9. **Scratch (긁힘)**: category_id 302
10. **Peeling (박락)**: category_id 303

> **Note**: Normal(101) 카테고리는 학습에서 제외됩니다.

## 모델 변형

YOLOv8 모델 크기별 변형:

| 모델 | 파라미터 | mAP | 속도 | 용도 |
|------|---------|-----|------|------|
| yolov8n | 3.2M | 중 | 매우 빠름 | 실시간 추론, 엣지 디바이스 |
| yolov8s | 11.2M | 중상 | 빠름 | 균형잡힌 선택 |
| yolov8m | 25.9M | 상 | 보통 | 높은 정확도 |
| yolov8l | 43.7M | 상상 | 느림 | 최고 정확도 |
| yolov8x | 68.2M | 최상 | 매우 느림 | 연구용 |

## 성능 최적화

### Augmentation 설정

```python
# Geometric augmentation
DEGREES = 10.0          # 회전 범위
TRANSLATE = 0.1         # 이동 범위
SCALE = 0.5             # 스케일 범위
FLIPLR = 0.5            # 좌우 반전 확률

# Color augmentation
HSV_H = 0.015           # Hue 변화
HSV_S = 0.7             # Saturation 변화
HSV_V = 0.4             # Value 변화

# Advanced augmentation
MOSAIC = 1.0            # Mosaic augmentation
MIXUP = 0.1             # MixUp augmentation
```

### 하이퍼파라미터 튜닝

```python
# Optimizer
OPTIMIZER = 'AdamW'
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0005
WARMUP_EPOCHS = 3.0

# Training
BATCH_SIZE = 16
EPOCHS = 100
PATIENCE = 50           # Early stopping
```

## 트러블슈팅

### 일반적인 문제

**1. Permission denied (실행 권한 오류)**
```bash
# 에러 메시지
bash: ./src/training/run_training.sh: Permission denied

# 해결 방법
chmod +x src/training/run_training.sh

# 또는 bash로 직접 실행
bash src/training/run_training.sh --model yolov8n --epochs 100
```

**2. CUDA out of memory**
```bash
# 배치 사이즈 감소
python src/training/train_yolov8.py --batch 8

# 작은 모델 사용
python src/training/train_yolov8.py --model yolov8n
```

**3. data.yaml not found**
```bash
# 데이터셋 준비 먼저 실행
python src/training/prepare_yolo_dataset.py
```

**4. MLflow 로그 확인**
```bash
# MLflow 디렉토리 확인
ls -la mlruns/

# 최신 실험 확인
ls -lt mlruns/0/ | head -5

# 메트릭 확인
find mlruns -name "*.csv" -o -name "metrics"
```

**5. 학습 진행 상황 확인**
```bash
# results.csv 확인
cat runs/detect/train/results.csv

# 실시간 모니터링
tail -f runs/detect/train/results.csv

# 학습 곡선 확인
ls runs/detect/train/*.png
```

**6. 디스크 공간 부족**
```bash
# 디스크 사용량 확인
df -h

# 이전 실험 결과 정리
rm -rf runs/detect/train*_old
rm -rf mlruns/.trash
```

## 모델 레지스트리 명령어 Quick Reference

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `list` | 모든 버전 조회 | `python src/training/model_registry.py list` |
| `latest` | 최신 버전 확인 | `python src/training/model_registry.py latest --stage Production` |
| `info` | 버전 상세 정보 | `python src/training/model_registry.py info 1` |
| `compare` | 성능 비교 | `python src/training/model_registry.py compare --versions 1 2 3` |
| `best` | 최고 성능 모델 | `python src/training/model_registry.py best --metric mAP50` |
| `stage` | 스테이지 변경 | `python src/training/model_registry.py stage 1 Staging` |
| `promote` | Production 승격 | `python src/training/model_registry.py promote 2` |
| `load` | 모델 로드 | `python src/training/model_registry.py load --stage Production` |
| `delete` | 버전 삭제 | `python src/training/model_registry.py delete 1` |

## FAQ

**Q: 어떤 메트릭으로 모델을 선택해야 하나요?**

A: 용도에 따라 다릅니다:
- 일반적인 경우: `mAP50` (가장 균형잡힌 지표)
- 오탐지 최소화: `precision` (정확도 우선)
- 결함 놓침 최소화: `recall` (안전 우선)
- 정밀한 위치: `mAP50-95` (엄격한 평가)

**Q: 모델 버전이 너무 많아지면 어떻게 하나요?**

A: 주기적으로 정리하세요:
```bash
# 성능 낮은 버전 Archive
python src/training/model_registry.py stage 1 Archived

# 불필요한 버전 삭제
python src/training/model_registry.py delete 1
```

**Q: Production 모델을 바꿨는데 성능이 더 나빠졌어요.**

A: 롤백하세요:
```bash
# 이전 버전으로 롤백
python src/training/model_registry.py promote 2

# 문제 버전 Archive
python src/training/model_registry.py stage 3 Archived
```

**Q: 여러 실험을 돌렸는데 어떤 게 최고인지 모르겠어요.**

A: 비교 기능을 사용하세요:
```bash
# 모든 버전 성능 한눈에 비교
python src/training/model_registry.py compare

# 자동으로 최고 성능 찾기
python src/training/model_registry.py best --metric mAP50
```

**Q: 모델 파일이 어디에 저장되나요?**

A: 두 곳에 저장됩니다:
- 학습 직후: `runs/detect/train/weights/best.pt`
- MLflow Registry: `mlruns/0/<run_id>/artifacts/models/best.pt`

Registry에서 로드하면 자동으로 파일을 찾아줍니다.

**Q: 로컬에서 결과를 보고 싶어요.**

A: SCP로 다운로드하거나 SSH 포트 포워딩을 사용하세요:
```bash
# 파일 다운로드
scp -r user@server:/path/to/mlruns ./local_mlruns

# 로컬에서 MLflow UI
mlflow ui --backend-store-uri ./local_mlruns
```

## 참고 자료

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

## 라이센스

이 프로젝트는 SSAFY 자율 프로젝트의 일부입니다.
