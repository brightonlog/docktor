# 선박 도장 결함 탐지 AI 서버

선박 외판 도장 결함을 자동으로 탐지하고, MLOps 파이프라인을 통해 모델을 관리하며, Jetson Orin Nano에서 실행 가능한 온디바이스 AI 시스템

## 프로젝트 목표

1. **결함 탐지 (Defect Detection)**: YOLOv8 기반 도장 결함 객체 탐지
2. **이상 탐지 (Anomaly Detection)**: 정상/비정상 분류 및 이상치 탐지
3. **MLOps 구축**: 모델 실험 관리, 서빙, 모니터링 자동화
4. **온디바이스 배포**: Jetson Orin Nano 최적화 및 배포
5. **API 서빙**: Flask 기반 REST API로 SpringBoot 서버와 통신

## 시스템 아키텍처

```
AI Server (Flask)                Backend Server (SpringBoot)
┌─────────────────────┐         ┌──────────────────────┐
│ Flask API           │◄────────┤ REST API Client      │
│  - 추론 엔드포인트   │  HTTP   │  - 이미지 업로드      │
│  - 모델 관리        │────────►│  - 결과 처리          │
└─────────────────────┘         └──────────────────────┘
         │
         ▼
┌─────────────────────┐
│ MLOps Pipeline      │
│  - MLFlow           │
│  - BentoML          │
│  - Prometheus       │
│  - Grafana          │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Model Deployment    │
│  - Jetson Orin Nano │
│  - TensorRT         │
└─────────────────────┘
```

## 디렉토리 구조

```
AI/lks/
├── data/                       # 데이터셋
│   ├── raw/                    # 원본 데이터 (AI Hub 데이터셋)
│   ├── processed/              # 전처리된 데이터
│   └── models/                 # 데이터 관련 모델 파일
│
├── models/                     # 학습된 모델 저장소
│   ├── detection/              # 결함 탐지 모델 (.pt, .onnx)
│   ├── anomaly/                # 이상 탐지 모델
│   └── jetson/                 # Jetson 최적화 모델 (TensorRT)
│
├── notebooks/                  # 실험 및 분석용 Jupyter Notebook
│
├── src/                        # 소스 코드
│   ├── training/               # 모델 학습
│   │   ├── detection/          # 결함 탐지 학습 코드
│   │   └── anomaly/            # 이상 탐지 학습 코드
│   ├── inference/              # 추론 파이프라인
│   └── api/                    # Flask API 서버
│
├── mlops/                      # MLOps 구성
│   ├── mlflow/                 # MLFlow 실험 관리
│   ├── bentoml/                # BentoML 모델 서빙
│   └── monitoring/             # Prometheus + Grafana
│
├── deployment/                 # 배포 관련
│   └── jetson/                 # Jetson Orin Nano 최적화
│
├── config/                     # 설정 파일
│
├── requirements.txt            # Python 의존성
└── README.md
```

## 기술 스택

### AI/ML
- **Object Detection**: YOLOv8, Ultralytics
- **Anomaly Detection**: AutoEncoder, Isolation Forest
- **Framework**: PyTorch, OpenCV, NumPy

### MLOps
- **Experiment Tracking**: MLFlow
- **Model Serving**: BentoML
- **Monitoring**: Prometheus, Grafana

### API & Communication
- **API Server**: Flask
- **Backend Integration**: REST API (with SpringBoot)

### Deployment
- **Edge Device**: Jetson Orin Nano
- **Optimization**: TensorRT, ONNX

## 개발 로드맵

### Phase 1: 데이터 준비 및 기본 모델 학습
- [ ] AI Hub 데이터셋 다운로드 및 전처리
- [ ] YOLOv8 결함 탐지 모델 학습
- [ ] 이상 탐지 모델 구현

### Phase 2: MLOps 파이프라인 구축
- [ ] MLFlow 실험 관리 시스템 구축
- [ ] BentoML 모델 서빙 환경 구성
- [ ] Prometheus + Grafana 모니터링 대시보드 구축

### Phase 3: API 서버 개발
- [ ] Flask REST API 엔드포인트 구현
- [ ] SpringBoot 서버와 통신 인터페이스 설계
- [ ] 이미지 업로드 및 추론 파이프라인 구현

### Phase 4: 온디바이스 배포
- [ ] 모델 경량화 (ONNX, TensorRT 변환)
- [ ] Jetson Orin Nano 환경 구성
- [ ] 실시간 추론 성능 최적화

## 시작하기

### 환경 설정
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 모델 학습
```bash
# 결함 탐지 모델 학습
python src/training/detection/train.py

# 이상 탐지 모델 학습
python src/training/anomaly/train.py
```

### API 서버 실행
```bash
# Flask 서버 시작
python src/api/app.py
```

## API 명세 (예정)

### 결함 탐지
```
POST /api/v1/detect
Content-Type: multipart/form-data

Request:
- image: 선박 이미지 파일

Response:
{
  "detections": [
    {
      "class": "crack",
      "confidence": 0.95,
      "bbox": [x1, y1, x2, y2]
    }
  ]
}
```

### 이상 탐지
```
POST /api/v1/anomaly
Content-Type: multipart/form-data

Request:
- image: 선박 이미지 파일

Response:
{
  "is_anomaly": true,
  "anomaly_score": 0.87
}
```

## 개발자

- **AI 파트 - lks**
- **브랜치**: AI-lks
- **작업 시작일**: 2026-01-20
