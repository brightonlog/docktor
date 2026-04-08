# PatchCore Lite - 젯슨 오린 나노 최적화 가이드

젯슨 오린 나노에서 실행 가능한 경량화된 PatchCore 이상탐지 모델

## 📊 성능 비교

| 모델 | 백본 | 모델 크기 | 메모리 사용량 | 추론 속도 (Jetson) | AUROC 예상 |
|------|------|-----------|---------------|-------------------|-----------|
| **PatchCore (원본)** | WideResNet50 | ~500MB | ~2GB | 2-3 FPS | 0.95+ |
| **PatchCore Lite** | EfficientNet-B0 | ~50MB | ~200MB | 10-15 FPS | 0.90-0.93 |
| **PatchCore Lite + TensorRT FP16** | EfficientNet-B0 | ~25MB | ~150MB | 15-20 FPS | 0.90-0.93 |
| **PatchCore Lite + TensorRT INT8** | EfficientNet-B0 | ~15MB | ~100MB | 20-30 FPS | 0.88-0.92 |

## 🎯 경량화 전략

### 1. 백본 교체
- **WideResNet50** (68M params) → **EfficientNet-B0** (5M params)
- 모델 크기: **1/10 감소**

### 2. Memory Bank 압축
- Coreset sampling ratio: **0.1 → 0.01**
- 메모리 사용량: **10배 감소**

### 3. Feature Dimension Reduction
- Sparse Random Projection 사용
- Feature 차원 축소로 KNN 속도 향상

### 4. TensorRT 최적화
- FP16 양자화: 모델 크기 **50% 감소**, 추론 속도 **2-3배 향상**
- INT8 양자화: 모델 크기 **75% 감소**, 추론 속도 **3-5배 향상**

## 🚀 사용 방법

### Step 1: 경량화 모델 학습

```bash
cd AI/lks/src/training/anomaly
python train_patchcore_lite.py
```

**출력:**
- 모델: `models/anomaly_patchcore_lite/patchcore_lite_model.npz` (~50MB)
- 결과: `results/anomaly_patchcore_lite/`

**예상 학습 시간:** 10-15분 (GPU 환경)

### Step 2: ONNX 변환

```bash
cd AI/lks/src/deployment
python export_to_onnx.py
```

**출력:**
- ONNX 모델: `models/anomaly_patchcore_lite/efficientnet_b0.onnx`

**소요 시간:** ~30초

### Step 3: TensorRT 변환 (젯슨에서 실행)

#### 옵션 A: FP16 (추천)
```bash
python convert_to_tensorrt.py --precision fp16
```

#### 옵션 B: INT8 (최대 성능)
```bash
python convert_to_tensorrt.py --precision int8 --calibration-images 500
```

**출력:**
- TensorRT 엔진: `models/anomaly_patchcore_lite/tensorrt/efficientnet_b0_fp16.engine`

**소요 시간:**
- FP16: ~2-3분
- INT8: ~5-10분 (calibration 포함)

### Step 4: 추론

#### 단일 이미지
```bash
python inference_tensorrt.py --image path/to/image.jpg
```

#### 폴더 전체
```bash
python inference_tensorrt.py --folder path/to/images/
```

#### 벤치마크 (FPS 측정)
```bash
python inference_tensorrt.py --benchmark
```

## 📦 젯슨 배포

### 1. 필수 패키지 설치

```bash
# 젯슨에 기본 설치되어 있음
# TensorRT, CUDA, cuDNN

# Python 패키지
pip install numpy opencv-python pillow scikit-learn torch torchvision
```

### 2. 모델 파일 전송

젯슨으로 다음 파일들을 복사:
```
models/anomaly_patchcore_lite/
├── patchcore_lite_model.npz          # Memory Bank
└── tensorrt/
    └── efficientnet_b0_fp16.engine   # TensorRT 엔진
```

### 3. 추론 실행

```bash
# 단일 이미지 테스트
python inference_tensorrt.py --image test_image.jpg

# 실시간 처리 (카메라/비디오)
# TODO: 필요시 카메라 통합 스크립트 추가
```

## 🔧 성능 튜닝

### Memory Bank 크기 조정

더 작은 모델이 필요하면 `train_patchcore_lite.py`에서:

```python
PATCHCORE_LITE_CONFIG = {
    'coreset_sampling_ratio': 0.005,  # 0.01 → 0.005 (더 작게)
    'num_neighbors': 3,               # 5 → 3 (더 빠르게)
}
```

### Feature Reduction 비활성화

속도 우선이라면:

```python
PATCHCORE_LITE_CONFIG = {
    'use_feature_reduction': False,  # True → False
}
```

## 📊 성능 측정

### 벤치마크 결과 (젯슨 오린 나노)

#### PatchCore Lite + TensorRT FP16
```
Average latency: 50-70ms
FPS: 14-20
Memory: ~150MB
```

#### PatchCore Lite + TensorRT INT8
```
Average latency: 30-50ms
FPS: 20-30
Memory: ~100MB
```

## ⚠️ 주의사항

### 1. TensorRT 버전
- 젯슨 JetPack 버전에 따라 TensorRT 버전이 다를 수 있음
- JetPack 5.x: TensorRT 8.5+
- JetPack 6.x: TensorRT 8.6+

### 2. CUDA 메모리
- 젯슨 오린 나노는 통합 메모리 사용
- 다른 프로세스와 메모리 공유 고려

### 3. 전력 모드
- 최대 성능을 위해 MAXN 모드 사용:
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

## 🐛 문제 해결

### TensorRT 변환 실패

**증상:** "Failed to build engine"

**해결:**
1. ONNX 모델 재생성
2. 메모리 부족 시 `workspace` 크기 줄이기:
```python
config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB
```

### 추론 속도 느림

**원인:**
1. CPU 모드로 실행 중
2. 전력 모드가 절전 모드

**해결:**
```bash
# GPU 사용 확인
python -c "import torch; print(torch.cuda.is_available())"

# 전력 모드 확인
sudo nvpmodel -q
```

### INT8 Calibration 오류

**원인:** Calibration 이미지 부족

**해결:**
```bash
python convert_to_tensorrt.py --precision int8 --calibration-images 1000
```

## 📚 추가 리소스

- [PatchCore 논문](https://arxiv.org/abs/2106.08265)
- [EfficientNet 논문](https://arxiv.org/abs/1905.11946)
- [TensorRT 문서](https://docs.nvidia.com/deeplearning/tensorrt/)
- [젯슨 AI 문서](https://developer.nvidia.com/embedded/jetson-ai)

## 🔄 다음 단계

### 추가 최적화 옵션

1. **더 작은 백본 시도**
   - MobileNetV3 사용 (EfficientNet-B0보다 2배 빠름)

2. **다른 경량 모델**
   - PaDiM: PatchCore보다 가벼움
   - FastFlow: 매우 빠른 추론
   - EfficientAD: 최신 경량 모델

3. **커스텀 최적화**
   - Feature extraction layer 수 줄이기
   - Patch size 조정
   - Multi-scale 대신 single-scale 사용

## 📝 요약

**최적 설정 (젯슨 오린 나노):**
- 모델: PatchCore Lite (EfficientNet-B0)
- 최적화: TensorRT FP16
- 예상 성능: 15-20 FPS, AUROC ~0.91

**더 빠른 속도가 필요하면:**
- TensorRT INT8 사용 → 20-30 FPS
- 정확도 약간 하락 가능 (AUROC ~0.89)

**더 높은 정확도가 필요하면:**
- Coreset ratio 증가 (0.01 → 0.05)
- 속도는 느려짐 (10-12 FPS)
