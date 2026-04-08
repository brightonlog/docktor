# YOLOv26n 선박 도장 결함 탐지

5가지 결함 클래스를 탐지하는 YOLOv26n 기반 객체 탐지 모델

## 왜 YOLOv26n인가?

**Jetson Orin Nano 배포에 최적화된 모델**

| 특징 | YOLOv26 | YOLOv11 | 장점 |
|------|---------|---------|------|
| **NMS** | ❌ 제거 | ✅ 필요 | 후처리 없이 End-to-End 추론 → TensorRT 변환 단순화 |
| **DFL** | ❌ 제거 | ✅ 사용 | 엣지 디바이스 호환성 향상 |
| **CPU 추론** | 43% 더 빠름 | 기준 | 실시간 처리에 유리 |
| **소형 물체** | ProgLoss 적용 | 기본 | crack, pinhole 같은 작은 결함 탐지 개선 |

### 선택 이유

1. **실시간 추론**: 웹캠 1080p 스트림을 Jetson에서 실시간 처리
2. **배포 단순화**: NMS 제거로 TensorRT 엔진 변환 시 파이프라인이 단순해짐
3. **작은 결함 탐지**: 선박 도장의 미세한 균열, 핀홀 탐지에 효과적
4. **경량 모델**: nano 버전으로 Jetson Orin Nano의 제한된 리소스에 적합

> 참고: [Ultralytics YOLOv26 공식 문서](https://docs.ultralytics.com/models/yolo26/)

## 클래스 (5종 선별 학습)

원본 데이터셋의 11개 클래스 중 실제 선박 검사에 사용되는 5개 결함만 선별하여 학습합니다.

| YOLO ID | 영문명 | 한글명 | 원본 Category ID |
|---------|--------|--------|-----------------|
| 0 | blister | 부풀음 | 0 |
| 1 | crack | 균열 | 2 |
| 2 | peeling | 도막떨어짐 | 4 |
| 3 | sagging | 흐름 | 6 |
| 4 | welding_damage | 용접손상 | 9 |

> **참고**: YOLO ID는 학습용으로 0-4로 재매핑되며, 원본 Category ID는 전체 데이터셋의 ID입니다.

## 사용법

### 1. 데이터셋 준비

```bash
python src/yolo_detection/prepare_dataset.py
```

JSON 레이블을 YOLO 형식으로 변환하고 5개 타겟 클래스만 필터링합니다.

### 2. 모델 학습

**주피터 노트북으로 학습 (권장):**

```bash
# Jupyter Lab 실행
jupyter lab

# 또는 Jupyter Notebook
jupyter notebook
```

그 다음 `src/yolo_detection/train.ipynb`를 열어서 셀을 순서대로 실행하세요.

노트북에서는:
- 각 단계를 확인하면서 학습 진행 가능
- 하이퍼파라미터를 쉽게 조정 가능
- 학습 결과를 실시간으로 시각화
- MLflow와 TensorBoard가 자동으로 통합됨

**CLI로 학습 (레거시):**

CLI 환경에서 학습이 필요한 경우 레거시 스크립트를 사용할 수 있습니다:

```bash
# 기본 학습
python src/yolo_detection/train_legacy.py

# 커스텀 설정
python src/yolo_detection/train_legacy.py --epochs 100 --batch 16
```

### 3. 학습 모니터링

**노트북에서 직접 확인:**
- `train.ipynb`의 마지막 섹션에서 학습 결과를 자동으로 시각화합니다.
- 학습 곡선, Confusion Matrix, 클래스별 성능이 노트북 안에 표시됩니다.

**별도 대시보드 실행 (선택):**

```bash
# 모든 대시보드 실행 (MLflow + TensorBoard)
python src/yolo_detection/visualization_dashboard.py --launch

# 학습 진행 상황 실시간 모니터링
python src/yolo_detection/visualization_dashboard.py --watch

# 학습 곡선 플롯
python src/yolo_detection/visualization_dashboard.py --plot experiments/yolo_runs/run_name/results.csv
```

대시보드 URL:
- MLflow: http://localhost:5000 (실험 비교, 모델 아티팩트 관리)
- TensorBoard: http://localhost:6006 (실시간 학습 곡선)

### 4. TensorRT 변환 (Jetson 배포용)

> ⚠️ **중요**: 반드시 `best_fixed.pt`를 사용하세요! (이전 best.pt 파일은 클래스 매핑이 잘못되어 있습니다. 클래스 매핑을 올바르게 수정한 best_fixed.pt를 사용해주세요.)

```bash
# ONNX + TensorRT 변환 (best_fixed.pt 사용!)
python src/yolo_detection/export_tensorrt.py --model experiments/yolo_runs/run_name/weights/best_fixed.pt

# ONNX만 변환 (Jetson에서 TensorRT 변환)
python src/yolo_detection/export_tensorrt.py --model best_fixed.pt --onnx-only
```

#### 모델 파일 정보
- `best.pt`: 원본 학습 모델 (클래스 이름 매핑 오류 있음, 사용하지 마세요)
- `best_fixed.pt`: **수정된 모델 (올바른 클래스 이름 포함)** ← 이 파일 사용!

### 5. Jetson Orin Nano에서 추론

```bash
# 웹캠 실시간 추론 (best_fixed 모델 사용)
python jetson_inference.py --model best_fixed.engine --source 0

# 비디오 파일
python jetson_inference.py --model best_fixed.engine --source video.mp4
```

## 설정

### 학습 하이퍼파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| epochs | 40 | 학습 에폭 수 (보수적 설정, early stopping 활용) |
| batch_size | 8 | 배치 크기 |
| img_size | 1088 | 이미지 크기 (1080p 최적화) |
| optimizer | AdamW | 옵티마이저 |
| lr0 | 0.001 | 초기 학습률 |
| patience | 20 | Early stopping patience |

### Jetson Orin Nano 최적화

- **해상도**: 1088x1088 (1080p 웹캠에 최적화)
- **정밀도**: FP16 (TensorRT)
- **배치**: 1 (실시간 추론)

## 문제 해결 (Troubleshooting)

### 학습이 중간에 멈추거나 MLflow에서 failed가 뜨는 경우

**1. 환경 진단 먼저 실행**
```bash
python src/yolo_detection/check_setup.py
```

이 스크립트가 GPU, 데이터셋, 모델 파일, 디렉토리, 패키지 의존성을 체크합니다.

**2. 흔한 원인과 해결법**

| 문제 | 원인 | 해결 방법 |
|------|------|-----------|
| CUDA out of memory | GPU 메모리 부족 | 노트북에서 `config.BATCH_SIZE = 4` 또는 `2`로 줄이기 |
| 학습이 첫 에폭에서 멈춤 | 데이터 로딩 문제 | `workers=2`로 줄이거나 `cache=False`로 변경 |
| data.yaml not found | 데이터셋 준비 안 됨 | `python src/yolo_detection/prepare_dataset.py` 실행 |
| MLflow connection error | 경로 문제 | `experiments/mlruns` 폴더가 있는지 확인 |
| 디스크 공간 부족 | 로그/체크포인트 저장 공간 | 최소 10GB 여유 공간 확보 |

**3. GPU 메모리별 권장 설정**

노트북의 설정 섹션(셀 3)에서 GPU 메모리에 맞게 조정하세요:

```python
# 16GB+ (RTX 4080, A100 등)
config.BATCH_SIZE = 16
config.IMG_SIZE = 1088

# 8-12GB (RTX 3060/3070) - 기본값
config.BATCH_SIZE = 8
config.IMG_SIZE = 1088

# 6GB (RTX 2060)
config.BATCH_SIZE = 4
config.IMG_SIZE = 640

# 4GB 이하
config.BATCH_SIZE = 2
config.IMG_SIZE = 480
```

**4. 에러 메시지 확인**

노트북에서 학습 중 에러가 발생하면 자세한 에러 메시지와 스택 트레이스가 출력됩니다.
MLflow UI에서도 failed 상태인 run을 클릭하면 `error_type`과 `error_message` 파라미터에서 원인을 확인할 수 있습니다.

---

## 파일 구조

```
src/yolo_detection/
├── __init__.py              # 모듈 초기화
├── prepare_dataset.py       # 데이터셋 변환
├── train.ipynb              # 학습 노트북 (주 사용) ⭐
├── train_legacy.py          # 학습 스크립트 (레거시, CLI용)
├── export_tensorrt.py       # TensorRT 변환
├── visualization_dashboard.py # 시각화 대시보드
└── README.md                # 이 파일
```

> ⭐ **권장**: 주피터 노트북(`train.ipynb`)으로 학습하면 각 단계를 확인하면서 진행할 수 있고, MLflow와 TensorBoard가 자동으로 통합됩니다.

## 시각화 도구

1. **MLflow**: 실험 추적, 하이퍼파라미터 비교, 모델 아티팩트 관리
2. **TensorBoard**: 실시간 학습 곡선, 이미지 시각화
3. **Custom Plots**: 클래스별 성능, 학습 요약 리포트
