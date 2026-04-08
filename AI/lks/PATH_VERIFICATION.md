# 경로 검증 결과

실행 경로: `~/Desktop/S14P11E201/AI/lks`

## ✅ 모든 경로 설정이 올바르게 수정되었습니다

### 디렉토리 구조

```
S14P11E201/AI/lks/                    ← 실행 경로 (PROJECT_ROOT)
├── src/
│   ├── config/
│   │   └── training_config.py
│   ├── training/
│   │   └── anomaly/
│   │       ├── train_patchcore_lite.py         ✓ 경로 올바름
│   │       ├── validate_patchcore_lite.py      ✓ 경로 올바름
│   │       └── train_autoencoder.py
│   └── deployment/
│       ├── export_to_onnx.py                   ✓ 경로 수정됨
│       ├── convert_to_tensorrt.py              ✓ 경로 수정됨
│       ├── inference_tensorrt.py               ✓ 경로 수정됨
│       └── inference_mlflow.py                 ✓ 경로 수정됨
├── models/
├── results/
└── docs/
```

## 📝 PROJECT_ROOT 설정

### Training 스크립트 (src/training/anomaly/)

```python
# train_patchcore_lite.py, validate_patchcore_lite.py
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
# __file__:  src/training/anomaly/train_patchcore_lite.py
# parent:    src/training/anomaly/
# parent:    src/training/
# parent:    src/
# parent:    AI/lks/  ✓ 올바름
```

### Deployment 스크립트 (src/deployment/)

```python
# export_to_onnx.py, convert_to_tensorrt.py,
# inference_tensorrt.py, inference_mlflow.py
PROJECT_ROOT = Path(__file__).parent.parent.parent  # ← 수정됨 (4 → 3)
# __file__:  src/deployment/export_to_onnx.py
# parent:    src/deployment/
# parent:    src/
# parent:    AI/lks/  ✓ 올바름
```

## 🔧 수정된 문제

### 문제
Deployment 스크립트들이 `.parent`를 4번 호출하여 잘못된 경로를 참조:
- ❌ 이전: `AI/lks/src/deployment/` → `.parent` x 4 → `AI/` (잘못됨)
- ✓ 수정: `AI/lks/src/deployment/` → `.parent` x 3 → `AI/lks/` (올바름)

### 수정 내용
```python
# 이전 (잘못됨)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# 수정 (올바름)
PROJECT_ROOT = Path(__file__).parent.parent.parent  # deployment -> src -> lks
```

## ✅ 실행 명령어 (모두 AI/lks 경로에서 실행)

```bash
# 1. 가상환경 활성화
conda activate e201

# 2. 학습
python src/training/anomaly/train_patchcore_lite.py

# 3. 검증
python src/training/anomaly/validate_patchcore_lite.py --num_samples 200 --benchmark

# 4. ONNX 변환
python src/deployment/export_to_onnx.py

# 5. TensorRT 변환 (젯슨에서)
python src/deployment/convert_to_tensorrt.py --precision fp16

# 6. 추론
python src/deployment/inference_tensorrt.py --image path/to/image.jpg

# 7. MLflow 추론
python src/deployment/inference_mlflow.py --image path/to/image.jpg
```

## 🔍 Import 검증

모든 스크립트는 다음과 같이 import를 설정:

```python
# 1. PROJECT_ROOT 설정
PROJECT_ROOT = Path(__file__).parent...parent  # 적절한 횟수

# 2. sys.path에 추가
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# 3. Import
from config.training_config import IMAGE_DIR, LABEL_DIR, ...
from training.anomaly.train_autoencoder import collect_data, AnomalyDataset
from training.anomaly.train_patchcore_lite import PatchCoreLite, PATCHCORE_LITE_CONFIG
```

## ⚠️ 주의사항

### 1. 실행 경로
**반드시 `AI/lks` 디렉토리에서 실행:**
```bash
cd ~/Desktop/S14P11E201/AI/lks
python src/training/anomaly/train_patchcore_lite.py
```

**다른 경로에서 실행하면 안 됨:**
```bash
# ❌ 잘못됨
cd ~/Desktop/S14P11E201/AI/lks/src/training/anomaly
python train_patchcore_lite.py  # 상대 import 경로 문제 발생 가능
```

### 2. 가상환경
e201 가상환경이 활성화되어 있어야 합니다:
```bash
conda activate e201
```

### 3. 필수 패키지
다음 패키지들이 설치되어 있어야 합니다:
- numpy, pandas
- torch, torchvision, timm
- scikit-learn
- mlflow
- pillow, opencv-python
- matplotlib, seaborn

## 📊 검증 완료

- ✅ PROJECT_ROOT 경로 설정: 모든 파일 정상
- ✅ sys.path 설정: 올바름
- ✅ Import 경로: config.training_config 정상 로드
- ✅ 디렉토리 구조: 올바름

## 🎯 결론

**모든 경로 문제가 해결되었습니다!**

`AI/lks` 경로에서 e201 환경을 활성화한 후 모든 스크립트를 정상적으로 실행할 수 있습니다.
