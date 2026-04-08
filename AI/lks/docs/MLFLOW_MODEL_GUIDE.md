# MLflow Model Registry 사용 가이드

PatchCore Lite 모델을 MLflow에 등록하고 관리하는 방법

## 📦 MLflow에 모델이 저장되는 이유

### 기존 방식 (파일 저장)
```python
model.save('model.npz')  # 단순 파일 저장
```

**문제점:**
- 버전 관리 어려움
- 어떤 모델이 최신인지 모호
- 실험 추적 불가능
- 배포 시 모델 찾기 어려움

### MLflow 방식
```python
mlflow.pyfunc.log_model(...)  # MLflow에 등록
```

**장점:**
- ✅ **자동 버전 관리**: 모델 버전 자동 증가
- ✅ **실험 추적**: 어떤 하이퍼파라미터로 학습했는지 기록
- ✅ **스테이징 관리**: Production/Staging 환경 분리
- ✅ **쉬운 배포**: 코드 수정 없이 모델만 교체 가능
- ✅ **메타데이터**: AUROC, F1-Score 등 성능 지표 함께 저장

## 🚀 사용 방법

### 1. 모델 학습 및 등록

```bash
python AI/lks/src/training/anomaly/train_patchcore_lite.py
```

**자동으로 수행되는 작업:**
1. 모델 학습
2. 성능 평가
3. **MLflow에 자동 등록**
4. Model Registry에 버전 생성

**출력 예시:**
```
[Bonus] Registering model to MLflow Model Registry...
  ✓ Model registered to MLflow Model Registry!
  Model name: PatchCore-Lite-ShipCoating

  MLflow Run ID: abc123def456
  View in MLflow UI: http://localhost:5000
  Model Registry: http://localhost:5000/#/models/PatchCore-Lite-ShipCoating
```

### 2. MLflow UI에서 모델 확인

```bash
# MLflow UI 실행 (이미 실행 중이면 생략)
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

브라우저에서 `http://localhost:5000` 접속

#### 2.1 실험 목록
- **Experiments** 탭 → `ship-coating-anomaly-patchcore-lite`
- 모든 학습 기록 확인 가능

#### 2.2 모델 목록
- **Models** 탭 → `PatchCore-Lite-ShipCoating`
- 등록된 모든 모델 버전 확인

### 3. 모델 스테이지 관리

MLflow UI에서:

1. **Models** → `PatchCore-Lite-ShipCoating` 클릭
2. 원하는 버전 선택
3. **Stage** → `Transition to Production` 클릭

**스테이지 종류:**
- **None**: 등록만 된 상태
- **Staging**: 테스트 중인 모델
- **Production**: 실제 서비스 중인 모델
- **Archived**: 사용 종료된 모델

### 4. 모델 로드 및 추론

#### 방법 A: Production 모델 사용 (추천)

```bash
python AI/lks/src/deployment/inference_mlflow.py \
    --image path/to/image.jpg
```

항상 **Production** 스테이지의 모델을 자동으로 로드합니다.

#### 방법 B: 특정 버전 사용

```bash
python AI/lks/src/deployment/inference_mlflow.py \
    --image path/to/image.jpg \
    --version 3
```

#### 방법 C: Run ID로 로드

```bash
python AI/lks/src/deployment/inference_mlflow.py \
    --image path/to/image.jpg \
    --run-id abc123def456
```

#### 폴더 전체 처리

```bash
python AI/lks/src/deployment/inference_mlflow.py \
    --folder path/to/images/ \
    --threshold 0.005
```

## 📊 MLflow에 저장되는 정보

### 1. Parameters (하이퍼파라미터)
- `backbone`: efficientnet_b0
- `coreset_sampling_ratio`: 0.01
- `num_neighbors`: 5
- `image_size`: 224x224
- `batch_size`: 32
- 등등...

### 2. Metrics (성능 지표)
- `val_auroc`: 0.9123
- `val_f1_score`: 0.8756
- `test_auroc`: 0.9045
- `test_f1_score`: 0.8654

### 3. Artifacts (파일)
- `models/patchcore_lite_model.npz`: 실제 모델 파일
- `results/evaluation_report.json`: 평가 결과

### 4. Model (등록된 모델)
- Python 함수로 로드 가능
- 의존성 정보 포함
- Signature (입력/출력 스키마)

## 🔄 모델 버전 관리 시나리오

### 시나리오 1: 새로운 모델 학습

```bash
# 1차 학습
python train_patchcore_lite.py
# → Version 1 생성

# 하이퍼파라미터 조정 후 재학습
# train_patchcore_lite.py에서 설정 변경
python train_patchcore_lite.py
# → Version 2 생성
```

### 시나리오 2: 성능 비교

MLflow UI에서:
1. Version 1과 Version 2의 `test_auroc` 비교
2. 더 좋은 모델을 Production으로 전환

### 시나리오 3: 롤백

문제가 발생한 경우:
1. 이전 버전을 다시 Production으로 전환
2. 코드 수정 없이 모델만 교체

## 💡 Python 코드에서 사용

### 기본 사용법

```python
import mlflow.pyfunc
import pandas as pd

# MLflow 설정
mlflow.set_tracking_uri("sqlite:///mlflow.db")

# Production 모델 로드
model = mlflow.pyfunc.load_model(
    "models:/PatchCore-Lite-ShipCoating/Production"
)

# 추론
input_df = pd.DataFrame({
    'image_path': ['path/to/image1.jpg', 'path/to/image2.jpg']
})

scores = model.predict(input_df)
print(scores)  # [0.001234, 0.008765]
```

### 특정 버전 로드

```python
# Version 3 로드
model = mlflow.pyfunc.load_model(
    "models:/PatchCore-Lite-ShipCoating/3"
)
```

### Run ID로 로드

```python
# 특정 실험의 모델 로드
model = mlflow.pyfunc.load_model(
    "runs:/abc123def456/patchcore_lite_model"
)
```

## 🔍 모델 메타데이터 조회

```python
from mlflow.tracking import MlflowClient

client = MlflowClient()

# 모든 버전 조회
versions = client.search_model_versions(
    "name='PatchCore-Lite-ShipCoating'"
)

for v in versions:
    print(f"Version {v.version}: Stage={v.current_stage}")

    # Run 정보 조회
    run = client.get_run(v.run_id)
    print(f"  AUROC: {run.data.metrics['test_auroc']:.4f}")
```

## 🚢 젯슨 배포 워크플로우

### 1. 개발 환경에서 학습

```bash
# PC/서버에서
python train_patchcore_lite.py
```

### 2. 최적 모델 선택

MLflow UI에서 성능이 좋은 모델을 Production으로 설정

### 3. 젯슨으로 모델 다운로드

#### 옵션 A: MLflow UI에서 직접 다운로드
1. MLflow UI → Models → Version 선택
2. Artifacts → `patchcore_lite_model.npz` 다운로드
3. 젯슨으로 전송

#### 옵션 B: CLI로 다운로드

```bash
# 젯슨에서
mlflow artifacts download \
    --run-id abc123def456 \
    --artifact-path models/patchcore_lite_model.npz \
    --dst-path ./
```

### 4. 젯슨에서 추론

```bash
# TensorRT 최적화 적용
python inference_tensorrt.py --image test.jpg
```

또는

```bash
# MLflow 모델 직접 사용 (TensorRT 없이)
python inference_mlflow.py --image test.jpg --version 3
```

## 📈 실험 추적 팁

### 1. 실험명 규칙

학습할 때 의미있는 Run name 사용:
```python
# train_patchcore_lite.py에서
with mlflow.start_run(run_name="efficientnet_b0_coreset_001"):
    ...
```

### 2. 태그 활용

```python
mlflow.set_tags({
    "purpose": "production",
    "dataset": "ship_coating_v2",
    "optimizer": "memory_optimized"
})
```

### 3. 노트 추가

MLflow UI에서 각 Run에 노트 추가:
- "Best model so far"
- "Lower coreset ratio for speed"
- "Added feature reduction"

## ⚠️ 주의사항

### 1. Storage 관리

모델 파일이 계속 쌓이므로 주기적으로 정리:
```bash
# 오래된 버전 Archived로 전환
# MLflow UI에서 수동 또는 스크립트 작성
```

### 2. Tracking URI

**개발 환경:**
```python
mlflow.set_tracking_uri("sqlite:///mlflow.db")  # 로컬
```

**프로덕션 환경:**
```python
mlflow.set_tracking_uri("http://mlflow-server:5000")  # 원격 서버
```

### 3. 의존성

MLflow 모델은 conda 환경 정의를 포함:
- 배포 시 동일한 패키지 버전 필요
- Docker 사용 권장

## 🔧 문제 해결

### "Model not found"

**원인:** 잘못된 model name이나 version

**해결:**
```bash
mlflow models list  # 등록된 모델 확인
```

### "Run ID not found"

**원인:** MLflow DB가 다름

**해결:**
```python
# 올바른 tracking URI 설정
mlflow.set_tracking_uri("...")
```

### 모델 로드 느림

**원인:** MLflow가 매번 모델을 로드

**해결:**
```python
# 모델을 한 번만 로드하고 재사용
model = mlflow.pyfunc.load_model("...")  # 한 번만
for img in images:
    score = model.predict(...)  # 재사용
```

## 📚 추가 리소스

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [MLflow Python API](https://mlflow.org/docs/latest/python_api/index.html)

## 요약

**MLflow 사용의 핵심 이점:**

1. ✅ 모델 버전이 자동으로 관리됨
2. ✅ 실험 결과를 한눈에 비교 가능
3. ✅ Production/Staging 분리로 안전한 배포
4. ✅ 코드 수정 없이 모델만 교체 가능
5. ✅ UI에서 모든 것을 관리 가능

**기본 워크플로우:**
```
학습 → MLflow 자동 등록 → UI에서 성능 확인 →
좋은 모델을 Production으로 → 배포
```
