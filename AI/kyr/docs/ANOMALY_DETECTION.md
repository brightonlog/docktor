# Anomaly Detection Module

선박 도장 결함 이상탐지를 위한 **SSIM Autoencoder** 기반 비지도 학습 모듈입니다.

## 개요

### 왜 Autoencoder를 선택하게 되었을까?

이상 탐지를 하기 위해서는 다른 모델들도 사용할 수 있었습니다. 가령, 이미지의 국소 특징을 기억해서 미세결함(핀홀이나 스크래치)를 잘 탐지하는  patch core나, 학생-교사 모델이 서로 비교하며 찾기 때문에 속도가 무척 빠른 EfficientAD도 있었습니다. 다만,
Docktor 프로젝트는 이상 탐지가 되면 유저에게 직접 결함 종류를 선택하게끔 하는 로직이었습니다. 따라서 PatchCore나 EfficientAD는 저희가 계획한 탐지 과정에 비해 메모리를 너무 많이 차지하여 경량화를 해야하는 등의 단점이 있었습니다. 따라서 구조도 단순하고, 구현도 비교적 간단한 Autoencoder 방식이 비교적 간단한 이상 탐지 기능에 적합하다 생각하여
 선택하게 되었습니다.


| 기존 방식 (Supervised) | Autoencoder (Unsupervised) |
|----------------------|---------------------------|
| 모든 결함에 라벨링 필요 | **정상 이미지만 필요** |
| 새로운 결함 유형 대응 어려움 | 미지의 결함도 탐지 가능 |
| 데이터 수집 비용 높음 | 정상 이미지만 수집하면 됨 |

### 동작 원리

```
정상 이미지 학습
    ↓
Autoencoder가 "정상 패턴"을 학습
    ↓
테스트 시: 정상 이미지 → 잘 복원됨 (낮은 오차)
          비정상 이미지 → 복원 실패 (높은 오차)
    ↓
복원 오차(Anomaly Score)로 이상 판정
```

### 2-Step Hybrid Pipeline에서의 역할

```
이미지 입력
    ↓
[1단계] YOLOv11 ─→ 5대 결함 탐지
    │               (sagging, crack, blister,
    │                welding_damage, peeling)
    │
    ↓ (YOLO 통과)
[2단계] Autoencoder ─→ "뭔가 이상함" 탐지
    │
    ↓
사용자에게 표시 ─→ 사용자가 직접 분류
    │
    ├─→ pinhole 또는 coating_separation 선택
    │       ↓
    │   [Active Learning] YOLO 모델 재학습 데이터로 추가
    │
    └─→ 그 외 선택
            ↓
        백엔드에 other_damage(클래스 10번)로 저장
```

**사용자 분류 후 처리 로직:**

| 사용자 선택 | 처리 방식 | 설명 |
|------------|----------|------|
| `pinhole` (5) | YOLO 재학습 | 미세 결함 → 향후 YOLO가 직접 탐지 |
| `coating_separation` (1) | YOLO 재학습 | 도막 분리 → 향후 YOLO가 직접 탐지 |
| 그 외 결함 | other_damage (10) | 기타 결함으로 백엔드 저장 |

---

## 설치

### 필수 패키지

```bash
pip install torch torchvision
pip install numpy pillow
pip install pyyaml  # 설정 파일
```

### 선택 패키지

```bash
pip install opencv-python  # 실시간 카메라 추론
pip install matplotlib     # 시각화
pip install mlflow         # 실험 추적
```

---

## 프로젝트 구조

```
src/anomaly_detection/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── autoencoder.py     # SSIM Autoencoder 모델
├── train.py               # 학습 스크립트
├── inference.py           # 추론 스크립트
└── config.yaml            # 설정 파일

models/anomaly_detection/
├── best_model.pt          # 학습된 모델 (생성됨)
└── checkpoint_epoch_*.pt  # 체크포인트 (생성됨)
```

---

## 빠른 시작

### 1. 데이터 준비

정상(양품) 이미지를 한 폴더에 모읍니다:

```
data/processed/train/images/normal/
├── image001.jpg
├── image002.jpg
└── ...
```

> 현재 확보된 양품 이미지: **8,276장**

### 2. 학습

```bash
# 기본 학습
python src/anomaly_detection/train.py \
    --data-dir data/processed/train/images/normal \
    --epochs 100 \
    --batch-size 32

# 설정 파일 사용
python src/anomaly_detection/train.py \
    --config src/anomaly_detection/config.yaml

# 경량 모델 (Jetson용)
python src/anomaly_detection/train.py \
    --model-type lightweight \
    --latent-dim 128
```

### 3. 추론

```bash
# 단일 이미지
python src/anomaly_detection/inference.py \
    --model models/anomaly_detection/best_model.pt \
    --image test.jpg

# 배치 처리
python src/anomaly_detection/inference.py \
    --model models/anomaly_detection/best_model.pt \
    --dir test_images/ \
    --visualize

# 실시간 카메라 (Jetson)
python src/anomaly_detection/inference.py \
    --model models/anomaly_detection/best_model.pt \
    --camera
```

---

## 모델 아키텍처

### Standard Autoencoder

```
Input (256×256×3)
    ↓
Encoder:
    Conv2d(3→32, 4×4, stride=2) + BN + LeakyReLU   → 128×128×32
    Conv2d(32→64, 4×4, stride=2) + BN + LeakyReLU  → 64×64×64
    Conv2d(64→128, 4×4, stride=2) + BN + LeakyReLU → 32×32×128
    Conv2d(128→256, 4×4, stride=2) + BN + LeakyReLU → 16×16×256 (Latent)
    ↓
Decoder:
    ConvT(256→128, 4×4, stride=2) + BN + ReLU → 32×32×128
    ConvT(128→64, 4×4, stride=2) + BN + ReLU  → 64×64×64
    ConvT(64→32, 4×4, stride=2) + BN + ReLU   → 128×128×32
    ConvT(32→3, 4×4, stride=2) + Sigmoid      → 256×256×3
    ↓
Output (256×256×3)
```

| 모델 | 파라미터 수 | Latent Dim | 용도 |
|------|-----------|------------|------|
| Standard | ~2.5M | 256 | 고품질 복원 |
| Lightweight | ~0.5M | 128 | Jetson 최적화 |

### Loss Function

**Combined Loss = α × MSE + (1-α) × SSIM_Loss**

- **MSE**: 픽셀 단위 차이 측정
- **SSIM**: 구조적 유사도 (인간 시각 시스템 모방)
- **α**: 두 손실의 비율 (기본값: 0.5)

---

## 이상 점수 계산

### Anomaly Score

```python
# 복원 오차 계산
reconstructed = model(input_image)
diff = (input_image - reconstructed) ** 2
anomaly_score = diff.mean()  # 이미지 전체 평균

# 판정
is_anomaly = anomaly_score > threshold
```

### Anomaly Map (히트맵)

```python
# 픽셀별 이상 정도
anomaly_map = diff.mean(dim=1)  # 채널 평균
# 시각화: 빨간색 = 이상 부위
```

---

## 임계값(Threshold) 설정

### 자동 보정 (권장)

```python
from src.anomaly_detection.inference import AnomalyDetector

detector = AnomalyDetector('models/best_model.pt')

# 정상 이미지로 임계값 자동 보정
# 99th percentile = 정상 이미지의 99%가 정상으로 분류됨
threshold = detector.calibrate_threshold(
    normal_images=['img1.jpg', 'img2.jpg', ...],
    percentile=99.0
)
```

### 수동 설정

1. 정상 이미지로 점수 분포 확인
2. 적절한 임계값 선택 (보통 mean + 3*std)

```python
detector.set_threshold(0.015)
```

---

## API 사용법

### Python API

```python
from src.anomaly_detection.inference import AnomalyDetector

# 초기화
detector = AnomalyDetector(
    model_path='models/anomaly_detection/best_model.pt',
    threshold=0.01,
    input_size=256
)

# 단일 이미지 추론
result = detector.predict('test.jpg', return_map=True)

print(f"이상 점수: {result.anomaly_score}")
print(f"이상 여부: {result.is_anomaly}")
print(f"추론 시간: {result.inference_time_ms}ms")

# 히트맵 시각화
if result.is_anomaly:
    detector.visualize_result('test.jpg', result, save_path='result.png')
```

### 배치 처리

```python
image_paths = ['img1.jpg', 'img2.jpg', 'img3.jpg']
results = detector.predict_batch(image_paths)

anomalies = [r for r in results if r.is_anomaly]
print(f"이상 이미지: {len(anomalies)}개")
```

---

## Jetson Orin Nano 배포

### 최적화 팁

1. **경량 모델 사용**
   ```bash
   python train.py --model-type lightweight --latent-dim 128
   ```

2. **TensorRT 변환** (추후 지원)
   ```python
   # TODO: TensorRT 변환 스크립트
   ```

3. **배치 크기 조절**
   - 학습: batch_size=16 (메모리 제한)
   - 추론: batch_size=1 (실시간)

### 예상 성능

| 환경 | FPS | 메모리 |
|------|-----|--------|
| RTX 3080 | ~200 | 2GB |
| Jetson Orin Nano (Standard) | ~30 | 3GB |
| Jetson Orin Nano (Lightweight) | ~50 | 1.5GB |

---

## MLflow 실험 추적

```bash
# MLflow UI 실행
mlflow ui --backend-store-uri file:./experiments/mlruns

# 브라우저에서 http://localhost:5000 접속
```

### 추적되는 항목

- **Parameters**: epochs, batch_size, learning_rate, latent_dim, ...
- **Metrics**: train_loss, val_loss, train_mse, val_mse, train_ssim, val_ssim
- **Artifacts**: best_model.pt, training_curves.png

---

## 트러블슈팅

### 1. 복원 품질이 낮음

- **원인**: 학습 부족 또는 모델 용량 부족
- **해결**:
  - epochs 증가 (100 → 200)
  - latent_dim 증가 (256 → 512)
  - 데이터 증강 활성화

### 2. 정상 이미지도 이상으로 판정

- **원인**: 임계값이 너무 낮음
- **해결**:
  ```python
  detector.calibrate_threshold(normal_images, percentile=99.5)
  ```

### 3. 이상 이미지를 놓침

- **원인**: 임계값이 너무 높음 또는 이상 패턴이 정상과 유사
- **해결**:
  - 임계값 낮춤
  - 더 많은 정상 이미지로 학습
  - SSIM 비중 증가 (alpha=0.3)

### 4. Jetson에서 메모리 부족

- **해결**:
  - `--model-type lightweight` 사용
  - `--input-size 128` (품질 저하 주의)
  - batch_size 감소

---

## 다음 단계

- [ ] TensorRT 변환 스크립트 추가
- [ ] ONNX 내보내기 지원
- [ ] 점진적 학습 (Incremental Learning) 구현
- [ ] 웹 API (FastAPI) 래퍼 작성
- [ ] Gradio 데모 인터페이스

---

## 참고 자료

- [Autoencoder 기반 이상탐지 논문](https://arxiv.org/abs/1903.08550)
- [SSIM Loss 논문](https://arxiv.org/abs/2006.13846)
- [MVTec AD 벤치마크](https://www.mvtec.com/company/research/datasets/mvtec-ad)
