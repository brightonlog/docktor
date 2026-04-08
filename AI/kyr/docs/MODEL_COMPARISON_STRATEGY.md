# YOLO 모델 비교 실험 전략

SafeDeck 프로젝트의 최적 모델 선정을 위한 YOLOv11n, YOLOv11s, YOLOv26s 비교 실험 전략

---

## 1. 실험 목표

### 1.1 핵심 목표
- 세 가지 YOLO 모델(YOLOv11n, YOLOv11s, YOLOv26s) 중 **Jetson Orin Nano 환경에서 최적의 모델** 선정
- 정확도(Accuracy)와 추론 속도(Inference Speed) 간의 **최적 균형점** 찾기
- MLflow를 통한 **재현 가능한 실험 관리**

### 1.2 기존 Baseline (V6 기준)
| 지표 | 값 | 비고 |
|------|-----|------|
| mAP50 | 0.7972 | 목표치(0.74) 초과 달성 |
| Model | YOLOv8n | 기존 사용 모델 |
| Target | Jetson Orin Nano | TensorRT 변환 예정 |

---

## 2. 평가 메트릭 (Evaluation Metrics)

### 2.1 Detection 성능 메트릭

| 메트릭 | 설명 | 중요도 |
|--------|------|--------|
| **mAP50** | IoU 50% 기준 평균 정밀도 | ⭐⭐⭐ (최우선) |
| **mAP50-95** | IoU 50~95%까지 평균 | ⭐⭐ |
| **Precision** | 예측한 것 중 실제 결함 비율 | ⭐⭐ |
| **Recall** | 실제 결함 중 탐지한 비율 | ⭐⭐⭐ (선박 안전) |
| **F1 Score** | Precision-Recall 조화평균 | ⭐⭐ |

### 2.2 클래스별 성능 (Per-Class Metrics)

기존 취약 클래스 집중 모니터링:
- **Pinhole**: 3차 시도 2.0%, 현재 54.5% → 개선 필요
- **Scratch**: V5 11.6% → V6 81.2% (데이터 보강 성과)
- **Crack**: 미세 결함, 안정적 유지 필요

### 2.3 추론 성능 메트릭 (Inference Performance)

| 메트릭 | 설명 | 중요도 |
|--------|------|--------|
| **Inference Time (ms)** | 단일 이미지 추론 시간 | ⭐⭐⭐ |
| **FPS** | 초당 프레임 처리량 | ⭐⭐⭐ |
| **Model Size (MB)** | 모델 파일 크기 | ⭐⭐ |
| **Memory Usage (MB)** | GPU 메모리 사용량 | ⭐⭐⭐ (Jetson 제약) |
| **TensorRT FPS** | TensorRT 변환 후 FPS | ⭐⭐⭐ (배포 환경) |

### 2.4 종합 평가 점수 (Weighted Score)

```
Overall Score = (mAP50 × 0.4) + (Recall × 0.3) + (FPS_normalized × 0.3)
```

**가중치 설정 이유**:
- mAP50 (40%): 전체 탐지 정확도
- Recall (30%): 선박 안전을 위해 누락 최소화 중요
- FPS (30%): 실시간 스트리밍 요구사항

---

## 3. 실험 설계

### 3.1 모델 후보

| 모델 | 파라미터 수 | 특징 |
|------|------------|------|
| **YOLOv11n** | ~2.6M | 초경량, 속도 우선 |
| **YOLOv11s** | ~9.4M | 균형형, 속도-정확도 트레이드오프 |
| **YOLOv26s** | TBD | YOLO 최신 아키텍처 |

### 3.2 공통 학습 설정 (Hyperparameters)

```yaml
# 모든 모델에 동일 적용
training:
  epochs: 100
  batch_size: 16
  imgsz: 640
  optimizer: AdamW
  lr0: 0.01
  lrf: 0.01
  momentum: 0.937
  weight_decay: 0.0005
  warmup_epochs: 3
  patience: 50  # Early stopping

data:
  train: data/processed/train
  val: data/processed/val
  classes: 7  # 결함 7종

augmentation:
  hsv_h: 0.015
  hsv_s: 0.7
  hsv_v: 0.4
  degrees: 0.0
  translate: 0.1
  scale: 0.5
  flipud: 0.0
  fliplr: 0.5
  mosaic: 1.0
  mixup: 0.0
```

### 3.3 실험 단계

```
Phase 1: 기본 학습
├── YOLOv11n 학습 (Experiment 1)
├── YOLOv11s 학습 (Experiment 2)
└── YOLOv26s 학습 (Experiment 3)

Phase 2: 성능 측정
├── Validation 데이터셋 평가
├── 클래스별 성능 분석
└── 추론 시간 측정 (GPU/CPU)

Phase 3: 최적화
├── TensorRT 변환 (.engine)
├── Jetson 환경 벤치마크
└── 메모리 프로파일링

Phase 4: 최종 선정
├── 종합 점수 계산
├── 시각화 대시보드 생성
└── 모델 선정 및 배포
```

---

## 4. MLflow 실험 관리

### 4.1 MLflow 설정

```python
import mlflow
from mlflow.tracking import MlflowClient

# MLflow 서버 설정
mlflow.set_tracking_uri("file:./mlruns")  # 로컬 또는 서버 URI
mlflow.set_experiment("safedeck-model-comparison")

# 실험 구조
"""
Experiment: safedeck-model-comparison
├── Run: yolov11n-baseline
│   ├── params: {model: yolov11n, epochs: 100, ...}
│   ├── metrics: {mAP50: 0.xx, recall: 0.xx, fps: xx}
│   └── artifacts: {model.pt, confusion_matrix.png, ...}
├── Run: yolov11s-baseline
└── Run: yolov26s-baseline
"""
```

### 4.2 로깅할 항목

**Parameters (학습 설정)**:
```python
mlflow.log_params({
    "model_name": "yolov11n",
    "epochs": 100,
    "batch_size": 16,
    "imgsz": 640,
    "optimizer": "AdamW",
    "lr0": 0.01,
    "data_version": "v1.0",
})
```

**Metrics (성능 지표)**:
```python
mlflow.log_metrics({
    # Detection metrics
    "mAP50": 0.xx,
    "mAP50-95": 0.xx,
    "precision": 0.xx,
    "recall": 0.xx,
    "f1_score": 0.xx,

    # Per-class mAP50
    "mAP50_crack": 0.xx,
    "mAP50_scratch": 0.xx,
    "mAP50_pinhole": 0.xx,
    "mAP50_peeling": 0.xx,
    "mAP50_welding_damage": 0.xx,
    "mAP50_blister": 0.xx,
    "mAP50_water_spotting": 0.xx,

    # Inference metrics
    "inference_time_ms": xx,
    "fps_gpu": xx,
    "fps_cpu": xx,
    "model_size_mb": xx,
    "memory_usage_mb": xx,

    # TensorRT metrics (Phase 3)
    "fps_tensorrt": xx,
    "fps_jetson": xx,
})
```

**Artifacts (산출물)**:
```python
mlflow.log_artifacts("runs/detect/train/")
# 포함 항목:
# - weights/best.pt
# - confusion_matrix.png
# - F1_curve.png
# - P_curve.png
# - R_curve.png
# - PR_curve.png
# - results.csv
```

### 4.3 모델 레지스트리

```python
# 최종 선정 모델 등록
mlflow.register_model(
    model_uri=f"runs:/{run_id}/model",
    name="safedeck-defect-detector"
)

# 모델 버전 관리
client = MlflowClient()
client.transition_model_version_stage(
    name="safedeck-defect-detector",
    version=1,
    stage="Production"
)
```

---

## 5. 시각화 계획

### 5.1 MLflow UI 대시보드

1. **Run Comparison View**
   - 세 모델의 mAP50 추이 비교
   - 학습 손실(Loss) 곡선 비교
   - Epoch별 메트릭 변화

2. **Parallel Coordinates Plot**
   - mAP50, Recall, FPS 동시 비교
   - 하이퍼파라미터 영향 분석

### 5.2 커스텀 시각화

```python
# 생성할 차트 목록
visualizations = [
    "model_comparison_radar.png",      # 레이더 차트 (다축 비교)
    "class_performance_heatmap.png",   # 클래스별 성능 히트맵
    "speed_accuracy_tradeoff.png",     # 속도-정확도 트레이드오프
    "inference_time_boxplot.png",      # 추론 시간 분포
    "memory_usage_bar.png",            # 메모리 사용량 비교
    "tensorrt_comparison.png",         # TensorRT 변환 전후 비교
]
```

### 5.3 레이더 차트 (종합 비교)

```
        mAP50
          ▲
          │
   Recall ●─────● Precision
         /│\
        / │ \
       /  │  \
      ●───●───● FPS
     F1  Size  Memory
```

---

## 6. 모델 선정 기준

### 6.1 필수 조건 (Must-Have)

| 조건 | 임계값 | 근거 |
|------|--------|------|
| mAP50 | ≥ 0.75 | 기존 목표치 유지 |
| Recall | ≥ 0.70 | 안전 결함 누락 최소화 |
| FPS (Jetson) | ≥ 15 | 실시간 스트리밍 요구 |
| Memory | ≤ 4GB | Jetson Orin Nano 제약 |

### 6.2 우선순위 결정 트리

```
                    ┌─ mAP50 ≥ 0.80?
                    │
           Yes ─────┼───── No
            │                │
    ┌───────┴───────┐   선정 제외
    │               │
FPS ≥ 20?      FPS ≥ 15?
    │               │
   Yes             Yes
    │               │
 ⭐ 최우선       ✅ 후보
```

### 6.3 시나리오별 추천

| 시나리오 | 추천 모델 | 근거 |
|----------|----------|------|
| 정확도 우선 | YOLOv11s/v26s | mAP 최대화 |
| 속도 우선 | YOLOv11n | FPS 최대화 |
| 균형 (추천) | 종합점수 1위 | 가중치 적용 |

---

## 7. 실행 계획

### 7.1 스크립트 구조

```
AI/kyr/
├── src/
│   ├── training/
│   │   ├── train_yolov11n.py
│   │   ├── train_yolov11s.py
│   │   ├── train_yolov26s.py
│   │   └── train_config.yaml
│   ├── evaluation/
│   │   ├── evaluate_model.py
│   │   ├── benchmark_inference.py
│   │   └── compare_models.py
│   └── visualization/
│       ├── plot_comparison.py
│       └── generate_report.py
├── experiments/
│   └── mlruns/              # MLflow 실험 기록
└── docs/
    └── MODEL_COMPARISON_STRATEGY.md
```

### 7.2 실행 순서

```bash
# 1. 환경 설정
cd AI/kyr
pip install ultralytics mlflow matplotlib seaborn

# 2. MLflow 서버 시작 (선택사항)
mlflow ui --port 5000

# 3. 모델 학습 (순차 또는 병렬)
python src/training/train_yolov11n.py
python src/training/train_yolov11s.py
python src/training/train_yolov26s.py

# 4. 성능 평가
python src/evaluation/evaluate_model.py --model yolov11n
python src/evaluation/evaluate_model.py --model yolov11s
python src/evaluation/evaluate_model.py --model yolov26s

# 5. 비교 분석 및 시각화
python src/visualization/compare_models.py

# 6. 최종 리포트 생성
python src/visualization/generate_report.py
```

---

## 8. 예상 결과 및 다음 단계

### 8.1 예상 결과

| 모델 | 예상 mAP50 | 예상 FPS (Jetson) | 비고 |
|------|-----------|------------------|------|
| YOLOv11n | 0.75~0.80 | 25~35 | 속도 최우선 |
| YOLOv11s | 0.78~0.83 | 15~25 | 균형형 |
| YOLOv26s | 0.80~0.85 | 12~20 | 정확도 우선 |

### 8.2 다음 단계 (실험 후)

1. **최종 모델 선정** → TensorRT 변환
2. **Jetson 배포** → 실환경 테스트
3. **Flask API 통합** → SpringBoot 연동
4. **Prometheus/Grafana** → 모니터링 설정

---

## 9. 참고자료

- [Ultralytics YOLO Docs](https://docs.ultralytics.com/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [TensorRT for Jetson](https://developer.nvidia.com/tensorrt)
- 기존 실험 기록: [kyr/README.md](../README.md), [model_performance_history.md](../model_performance_history.md)
