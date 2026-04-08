# Image Preprocessing Module

선박 도장 결함 탐지를 위한 이미지 전처리 모듈

## 전처리 전략

### 타겟 크기: 1024×1024

**선택 이유:**
- 작은 결함 보존 (최소 ~29 픽셀 유지)
- 메모리 효율적 (이미지당 12MB, 배치 사이즈 16-32 가능)
- 정확도/속도 균형 (풀 해상도 대비 -1~-3% mAP, 3.5배 빠른 학습)
- 프로덕션 배포에 적합

### Letterbox Resize

종횡비를 유지하면서 리사이징:
- 이미지를 타겟 크기에 맞춰 스케일링
- 남은 공간은 패딩으로 채움 (검은색 또는 평균 픽셀값)
- **결함의 형태와 기하학적 특성 보존**

## 모듈 구조

```
preprocessing/
├── __init__.py                    # 모듈 초기화
├── image_preprocessor.py          # 핵심 전처리 클래스
├── augmentation.py                # 데이터 증강
├── visualize_preprocessing.py     # 전처리 결과 시각화
└── README.md                      # 문서
```

## 사용법

### 1. 기본 전처리

```python
from preprocessing import ImagePreprocessor

# Preprocessor 생성
preprocessor = ImagePreprocessor(
    target_size=(1024, 1024),
    normalize=True,
    mean=(0.485, 0.456, 0.406),  # ImageNet mean
    std=(0.229, 0.224, 0.225)     # ImageNet std
)

# 이미지 전처리
import cv2
image = cv2.imread('image.jpg')
processed_image, metadata = preprocessor.preprocess_image(image)

# metadata에는 scale, pad, original_size 정보가 포함됨
print(f"Scale: {metadata['scale']}")
print(f"Padding: {metadata['pad']}")
```

### 2. 어노테이션 변환

```python
# 어노테이션도 함께 변환
annotation = {
    'bbox': [100, 200, 300, 400],  # [x, y, w, h]
    'segmentation': [x1, y1, x2, y2, ...],
    'category_id': 207
}

transformed_ann = preprocessor.preprocess_annotation(annotation, metadata)

# transformed_ann에는 변환된 좌표가 포함됨
```

### 3. 역변환 (추론 결과를 원본 좌표로)

```python
# 모델 예측 bbox를 원본 이미지 좌표로 변환
predicted_bbox = [50, 100, 200, 150]
original_bbox = preprocessor.inverse_transform_bbox(predicted_bbox, metadata)
```

### 4. 이미지 역정규화 (시각화용)

```python
# 정규화된 이미지를 시각화 가능한 형태로
denormalized = preprocessor.denormalize_image(processed_image)
```

### 5. 데이터 증강

```python
from preprocessing import get_train_augmentation, get_val_augmentation

# 학습용 증강 (보수적)
train_aug = get_train_augmentation(image_size=(1024, 1024))

# 검증용 (증강 없음)
val_aug = get_val_augmentation(image_size=(1024, 1024))

# Albumentations 사용 예시
if train_aug:
    augmented = train_aug(
        image=image,
        bboxes=bboxes,
        category_ids=category_ids
    )
    aug_image = augmented['image']
    aug_bboxes = augmented['bboxes']
```

### 6. 전처리 결과 시각화

```bash
# 카테고리별 3개 샘플, 1024×1024 크기로 시각화
python src/preprocessing/visualize_preprocessing.py --samples 3 --size 1024

# 더 많은 샘플
python src/preprocessing/visualize_preprocessing.py --samples 5 --size 1024

# 결과는 results/preprocessing/latest/ 에 저장됨
```

## 데이터 증강 전략

### 보수적 증강 (작은 결함 보존)

```python
# Geometric Augmentations
- HorizontalFlip (p=0.5)
- VerticalFlip (p=0.5)
- RandomRotate90 (p=0.5)
- ShiftScaleRotate (shift=0.05, scale=0.1, rotate=15°, p=0.5)

# Color Augmentations
- ColorJitter (brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1)
- HueSaturationValue
- RandomBrightnessContrast (p=0.4)

# Noise & Blur (light)
- GaussianBlur (p=0.3)
- MotionBlur (p=0.3)
- GaussNoise (p=0.3)

# Local Contrast
- CLAHE (p=0.3)
```

### 피해야 할 증강

- 강한 RandomCrop (작은 결함 손실)
- RandomErasing (결함 정보 손실)
- 심한 왜곡 (결함 형태 변형)
- Cutout/MixUp (결함 경계 불분명)

## 전처리 파이프라인 예시

```python
import cv2
import json
from pathlib import Path
from preprocessing import ImagePreprocessor

# 1. Setup
preprocessor = ImagePreprocessor(target_size=(1024, 1024))
image_path = 'data/extracted/01.images/painting_defect/blister/sample.jpg'
label_path = 'data/extracted/02.labels/painting_defect/blister/sample.json'

# 2. Load data
image = cv2.imread(str(image_path))
with open(label_path, 'r') as f:
    data = json.load(f)

# 3. Preprocess
processed_image, metadata = preprocessor.preprocess_image(image)

# 4. Transform annotations
transformed_annotations = []
for ann in data['annotations']:
    transformed_ann = preprocessor.preprocess_annotation(ann, metadata)
    transformed_annotations.append(transformed_ann)

# 5. 학습에 사용
# model.train(processed_image, transformed_annotations)
```

## 주요 클래스 및 함수

### ImagePreprocessor

**주요 메서드:**
- `preprocess_image(image)`: 이미지 전처리
- `preprocess_annotation(annotation, metadata)`: 어노테이션 좌표 변환
- `inverse_transform_bbox(bbox, metadata)`: 역변환
- `denormalize_image(image)`: 역정규화

### letterbox_resize

```python
def letterbox_resize(
    image: np.ndarray,
    target_size: Tuple[int, int] = (1024, 1024),
    fill_value: Tuple[int, int, int] = (114, 114, 114)
) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Returns:
        resized_image: Letterboxed image
        scale: Resize scale factor
        pad: Padding (pad_w, pad_h)
    """
```

## 출력 예시

### 전처리 전후 비교

```
results/preprocessing/latest/
├── blister/
│   ├── blister_sample_001_comparison.png     # 원본 vs 전처리 (라벨 없음)
│   ├── blister_sample_001_annotated.png      # 원본 vs 전처리 (라벨 있음)
│   └── blister_sample_001_metadata.txt       # 메타데이터
├── scratch/
├── peeling/
└── ...
```

### 메타데이터 예시

```
Original size: 4032x3024
Preprocessed size: 1024x1024
Scale factor: 0.2540
Padding (w, h): (0, 128)
Number of annotations: 1
```

## 카테고리별 주의사항

### 작은 결함 (Scratch, Peeling, Crack)
- 강한 crop 피하기
- 작은 결함 모니터링
- 최소 크기 필터링 주의

### 큰 결함 (Coating Separation, Blister)
- 충분한 컨텍스트 유지
- 큰 receptive field 필요

## 성능 기대치

| 해상도 | 메모리/이미지 | 배치 크기 | 학습 속도 | 예상 mAP |
|--------|--------------|-----------|-----------|----------|
| Full (4032×3024) | 48 MB | 4-8 | 1x | 100% |
| 1536×1536 | 27 MB | 8-16 | 2x | 98-99% |
| **1024×1024** | **12 MB** | **16-32** | **3.5x** | **97-99%** |
| 768×768 | 7 MB | 32-64 | 5x | 94-96% |
| 512×512 | 3 MB | 64-128 | 8x | 88-92% |

## 다음 단계

1. 전처리 결과 확인: `results/preprocessing/latest/`
2. 데이터셋 클래스 구현 (PyTorch/TensorFlow)
3. 학습 파이프라인에 통합
4. 작은 결함 카테고리 성능 모니터링
5. 필요시 앵커 박스 조정

## 참고

- 분석 리포트: `results/eda/preprocessing_analysis_report.txt`
- 권장사항: `results/eda/preprocessing_recommendations_summary.md`
- 시각화: `results/eda/*.png`
