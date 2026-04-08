# Training Setup Guide

원격 서버 환경에서의 학습 환경 설정 가이드

## 환경 특징

- 원격 리눅스 서버 환경
- localhost 접근 불가
- 파일 기반 메트릭 저장
- MLflow UI, Prometheus, Grafana 비활성화

## 필수 요구사항

### Python 패키지

```bash
pip install ultralytics>=8.0.0
pip install mlflow
pip install opencv-python
pip install pandas
pip install matplotlib
pip install seaborn
pip install pyyaml
pip install tqdm
pip install tabulate  # 모델 레지스트리 테이블 출력용
```

또는 requirements 파일이 있다면:

```bash
pip install -r requirements.txt
```

### 시스템 요구사항

- Python 3.8+
- CUDA 11.0+ (GPU 사용 시)
- 충분한 디스크 공간 (데이터셋 + 모델 + 로그)

## 디렉토리 구조 확인

학습 시작 전 필요한 디렉토리가 있는지 확인:

```bash
# 프로젝트 루트에서
ls data/extracted/01.images/
ls data/extracted/02.labels/
```

데이터가 없다면 먼저 데이터 추출 필요:

```bash
python src/extract_dataset.py
```

## 설정 파일 확인

`src/config/training_config.py` 주요 설정:

```python
# 파일 기반 MLflow
MLFLOW_TRACKING_URI = str(PROJECT_ROOT / 'mlruns')

# Prometheus 비활성화
ENABLE_PROMETHEUS = False

# 이미지 크기 (웹캠 1080p 고려)
IMAGE_WIDTH = 1280
IMAGE_HEIGHT = 720

# 학습 파라미터
EPOCHS = 100
BATCH_SIZE = 16
LEARNING_RATE = 0.01
```

필요에 따라 수정 가능.

## 학습 실행

### 방법 1: 자동화 스크립트 (권장)

```bash
# 실행 권한 부여 (최초 1회만)
chmod +x src/training/run_training.sh

# 학습 실행
./src/training/run_training.sh \
    --model yolov8n \
    --epochs 100 \
    --batch 16 \
    --device 0

# 또는 권한 없이 bash로 직접 실행
bash src/training/run_training.sh --model yolov8n --epochs 100 --batch 16
```

### 방법 2: 단계별 실행

```bash
# 1단계: 데이터셋 준비
python src/training/prepare_yolo_dataset.py \
    --width 1280 \
    --height 720 \
    --train-ratio 0.8

# 2단계: 학습 시작
python src/training/train_yolov8.py \
    --model yolov8n \
    --data data/yolo_dataset/data.yaml \
    --epochs 100 \
    --batch 16 \
    --device 0
```

## 학습 모니터링

### 실시간 메트릭 확인

```bash
# 터미널 1: 학습 실행
python src/training/train_yolov8.py --model yolov8n --epochs 100

# 터미널 2: 메트릭 모니터링
tail -f runs/detect/train/results.csv

# 터미널 3: GPU 모니터링
watch -n 1 nvidia-smi
```

### 학습 중 확인사항

- `runs/detect/train/results.csv`: 에포크별 메트릭
- `runs/detect/train/weights/`: 체크포인트 저장
- GPU 메모리 사용률
- 디스크 공간

## 결과 확인

### 학습 완료 후

```bash
# 1. 생성된 파일 확인
ls -la runs/detect/train/

# 주요 파일:
# - weights/best.pt          # 최고 성능 모델
# - weights/last.pt          # 마지막 에포크 모델
# - results.csv              # 메트릭 기록
# - confusion_matrix.png     # Confusion matrix
# - PR_curve.png             # Precision-Recall 곡선
# - F1_curve.png             # F1 곡선
# - results.png              # 학습 곡선

# 2. 메트릭 확인
cat runs/detect/train/results.csv

# 3. MLflow 로그 확인
ls -la mlruns/0/
```

### 결과 다운로드 (로컬 머신에서)

```bash
# SCP 사용
scp -r user@server:/path/to/runs/detect/train ./local_results/

# 또는 rsync (더 빠름)
rsync -avz --progress user@server:/path/to/runs/detect/train/ ./local_results/
```

## 모델 평가

```bash
python src/training/evaluate.py \
    --model runs/detect/train/weights/best.pt \
    --data data/yolo_dataset/data.yaml \
    --save-dir results/evaluation \
    --benchmark

# 평가 결과 확인
ls results/evaluation/
# - metrics.csv                   # 클래스별 메트릭
# - per_class_map50.png          # 클래스별 mAP
# - precision_recall_scatter.png # Precision-Recall 분포
# - metrics_comparison.png       # 메트릭 비교
```

## 문제 해결

### Permission Denied (권한 오류)

```bash
# 에러 발생 시
bash: ./src/training/run_training.sh: Permission denied

# 해결 방법 1: 실행 권한 부여
chmod +x src/training/run_training.sh
./src/training/run_training.sh --model yolov8n --epochs 100

# 해결 방법 2: bash로 직접 실행
bash src/training/run_training.sh --model yolov8n --epochs 100

# 해결 방법 3: python 스크립트 직접 실행
python src/training/train_yolov8.py --model yolov8n --epochs 100
```

### CUDA Out of Memory

```bash
# 배치 사이즈 줄이기
python src/training/train_yolov8.py --batch 8

# 더 작은 모델 사용
python src/training/train_yolov8.py --model yolov8n
```

### 데이터셋 없음

```bash
# data.yaml 확인
cat data/yolo_dataset/data.yaml

# 없으면 데이터셋 준비 다시 실행
python src/training/prepare_yolo_dataset.py
```

### 디스크 공간 부족

```bash
# 디스크 사용량 확인
df -h

# 이전 실험 정리
rm -rf runs/detect/train_old
rm -rf mlruns/.trash
```

### 학습이 멈춤

```bash
# GPU 상태 확인
nvidia-smi

# 프로세스 확인
ps aux | grep python

# 학습 재개 (체크포인트에서)
python src/training/train_yolov8.py \
    --resume runs/detect/train/weights/last.pt
```

## 고급 설정

### 하이퍼파라미터 튜닝

`src/config/training_config.py` 수정:

```python
# Learning rate
LEARNING_RATE = 0.001  # 기본: 0.01

# Batch size
BATCH_SIZE = 32        # 기본: 16

# Augmentation
MOSAIC = 0.5          # 기본: 0.0
MIXUP = 0.1           # 기본: 0.0
```

### 여러 모델 비교

```bash
# YOLOv8n (가장 빠름)
./src/training/run_training.sh --model yolov8n --epochs 100

# YOLOv8s (균형)
./src/training/run_training.sh --model yolov8s --epochs 100

# YOLOv8m (높은 정확도)
./src/training/run_training.sh --model yolov8m --epochs 100
```

### 실험 관리

```bash
# 실험명 지정
python src/training/train_yolov8.py \
    --name experiment_001_yolov8n_baseline

# 여러 실험 결과 비교
ls runs/detect/
```

## 체크리스트

학습 시작 전:

- [ ] 데이터셋 준비 완료 (`data/yolo_dataset/`)
- [ ] GPU 사용 가능 (`nvidia-smi`)
- [ ] 충분한 디스크 공간 (최소 10GB)
- [ ] 필수 패키지 설치 완료
- [ ] 설정 파일 확인 (`training_config.py`)
- [ ] 학습 스크립트 실행 권한 부여 (`chmod +x src/training/run_training.sh`)

학습 중:

- [ ] 메트릭 모니터링 (`tail -f results.csv`)
- [ ] GPU 메모리 확인 (`nvidia-smi`)
- [ ] Loss 감소 확인
- [ ] 주기적으로 체크포인트 확인

학습 완료 후:

- [ ] 최종 메트릭 확인 (mAP, precision, recall)
- [ ] 학습 곡선 확인 (overfitting 여부)
- [ ] 모델 평가 실행
- [ ] 결과 백업 (weights, plots, logs)

## 참고 자료

- [README.md](./README.md): 상세 문서
- [YOLOv8 공식 문서](https://docs.ultralytics.com/)
- [MLflow 문서](https://mlflow.org/docs/latest/index.html)

## 지원

문제가 발생하면:

1. 로그 확인: `runs/detect/train/train.log`
2. GPU 상태: `nvidia-smi`
3. 디스크 공간: `df -h`
4. 프로세스: `ps aux | grep python`
