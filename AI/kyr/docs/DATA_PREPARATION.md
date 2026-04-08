# 데이터 준비 가이드 (Validation 데이터 중심)

AI Hub '선박 도장 품질 측정 데이터' 중 **Validation 데이터**만 다운로드하여 학습/검증 데이터셋으로 구축하는 가이드입니다.

---

## 📋 목차

1. [디렉토리 구조](#디렉토리-구조)
2. [데이터 다운로드](#데이터-다운로드)
3. [데이터 추출 및 정리](#데이터-추출-및-정리)
4. [Train/Val 분할](#trainval-분할)

---

## 📁 디렉토리 구조

### 작업 전 (다운로드 후)

```
AI/kyr/
├── data/
│   ├── raw/                        # 다운로드 받은 ZIP 파일 위치
│   │   ├── VS_양품_선수.zip
│   │   ├── VS_도막_손상_도막떨어짐.zip
│   │   ├── VL_양품_선수.zip
│   │   └── ...
│   └── processed/                  # 처리된 데이터
├── docs/
│   └── DATA_PREPARATION.md
└── src/
    ├── config/
    │   └── dataset_config.py       # 카테고리 매핑 설정
    ├── extract_dataset.py          # 압축 해제 스크립트
    └── split_dataset.py            # Train/Val 분할 스크립트
```

### 작업 후 (최종 구조)

```
AI/kyr/
├── data/
│   ├── raw/                        # (정리 후 삭제 가능)
│   └── processed/
│       ├── extracted/              # 압축 해제된 원본 (split 후 비워짐)
│       ├── train/                  # 학습 데이터 (80%)
│       │   ├── images/
│       │   │   ├── coating_damage/
│       │   │   │   ├── peeling/
│       │   │   │   ├── scratch/
│       │   │   │   └── welding_damage/
│       │   │   ├── painting_defect/
│       │   │   │   ├── crack/
│       │   │   │   ├── blister/
│       │   │   │   └── ...
│       │   │   └── normal/
│       │   │       ├── deck/
│       │   │       ├── bow/
│       │   │       └── ...
│       │   └── labels/
│       │       └── (동일 구조)
│       └── val/                    # 검증 데이터 (20%)
│           ├── images/
│           └── labels/
└── src/
    └── ...
```

---

## 📥 데이터 다운로드

### 1. 사전 준비

- **AI Hub 계정** 및 **API Key** 준비
- `aihubshell` 다운로드 (AI Hub 홈페이지 > 마이페이지 > 서비스 이용지원)

### 2. aihubshell 설치

`AI/kyr/data/raw` 폴더에 `aihubshell`을 배치합니다.

```bash
# 폴더가 없다면 생성
mkdir -p AI/kyr/data/raw
```

### 3. Validation 데이터 파일키 확인

전체 데이터가 아닌 Validation 데이터만 받기 위해 파일 목록을 조회합니다.

**Windows (PowerShell):**

```powershell
cd AI\kyr\data\raw
.\aihubshell.exe -mode l -datasetkey 71447 -aihubapikey 'YOUR_API_KEY'
```

출력된 목록에서 `Validation` 또는 `유효성`이 포함된 파일의 **File Key**를 확인합니다.
- `VS_` (Validation Source): 이미지 파일
- `VL_` (Validation Label): 라벨 파일

### 4. 데이터 다운로드

확인한 File Key를 사용하여 다운로드합니다.

```powershell
.\aihubshell.exe -mode d -datasetkey 71447 -filekey "확인한_FILE_KEY_목록(쉼표로구분)" -aihubapikey 'YOUR_API_KEY'
```

---

## 📦 데이터 추출 및 정리

다운로드한 ZIP 파일들을 자동으로 압축 해제하고, LKS 폴더와 동일한 계층 구조(`Category/Subcategory`)로 정리합니다.

### 1. 스크립트 실행

**Windows:**

```powershell
cd AI\kyr
python src/extract_dataset.py
```

### 2. 실행 결과

스크립트가 완료되면 `data/processed/extracted` 폴더에 다음과 같이 데이터가 정리됩니다.

```
data/processed/extracted/
├── images/
│   ├── coating_damage/
│   │   ├── peeling/
│   │   ├── scratch/
│   │   └── welding_damage/
│   ├── painting_defect/
│   │   ├── crack/
│   │   ├── blister/
│   │   ├── sagging/
│   │   ├── pinhole/
│   │   ├── water_spotting/
│   │   ├── foreign_material/
│   │   └── coating_separation/
│   └── normal/
│       ├── deck/
│       ├── bow/
│       ├── stern/
│       └── ...
└── labels/
    └── (동일 구조)
```

---

## ✂️ Train/Val 분할

추출된 데이터를 학습(Train)과 검증(Val)으로 나눕니다.

### 1. 스크립트 실행

```powershell
cd AI\kyr
python src/split_dataset.py
```

### 2. 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--ratio` | 0.8 | Train 데이터 비율 (0.8 = 80% train, 20% val) |
| `--seed` | 42 | Random seed (재현성을 위함) |
| `--copy` | False | 파일을 복사 (기본: 이동) |

**예시:**

```powershell
# 70% train, 30% val로 분할
python src/split_dataset.py --ratio 0.7

# 파일을 복사하여 원본 유지
python src/split_dataset.py --copy

# 특정 시드로 분할
python src/split_dataset.py --seed 123
```

### 3. 실행 결과

```
data/processed/
├── train/
│   ├── images/{category}/{subcategory}/
│   └── labels/{category}/{subcategory}/
└── val/
    ├── images/{category}/{subcategory}/
    └── labels/{category}/{subcategory}/
```

---

## 🎯 YOLO 학습에 사용하기

분할된 데이터를 YOLO 학습에 사용하려면:

```python
# 학습 코드에서 경로 설정
train_images = 'data/processed/train/images'
train_labels = 'data/processed/train/labels'
val_images = 'data/processed/val/images'
val_labels = 'data/processed/val/labels'
```

---

## 💡 참고사항

- 다운로드 용량이 부족할 경우 `data/raw`의 ZIP 파일은 추출 후 삭제해도 됩니다.
- `--copy` 옵션 없이 실행하면 `extracted` 폴더의 파일이 `train`/`val`로 이동됩니다.
- 카테고리 매핑 정보는 `src/config/dataset_config.py`에서 확인/수정할 수 있습니다.
