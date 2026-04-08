# EDA (Exploratory Data Analysis)

선박 도장 품질 측정 데이터셋 탐색적 데이터 분석 모듈

---

## 📁 스크립트 구성

### 1. `statistical_analysis.py`
**목적:** 데이터셋 전체 통계 분석 및 YOLO 학습 전략 수립

**주요 기능:**
- 클래스별 분포 분석 (클래스 불균형 확인)
- 이미지 크기 및 해상도 분석
- 바운딩박스 크기/종횡비 통계
- 작은 객체 비율 분석 (small object detection 전략)
- 클래스 weight 계산 (불균형 학습용)
- 바운딩박스 clustering (anchor box 최적화)
- 이미지-라벨 매칭 검증

**출력 결과:**
```
results/eda/YYYY-MM-DD/statistical/
├── charts/
│   ├── class_distribution.png          # 클래스 분포
│   ├── bbox_size_distribution.png      # bbox 크기 분포
│   ├── class_imbalance.png             # 클래스 불균형 분석
│   ├── small_object_ratio.png          # 작은 객체 비율
│   └── bbox_clustering.png             # bbox clustering 결과
└── analysis_report.txt                 # 상세 통계 리포트
```

**실행:**
```bash
cd AI/lks
python src/eda/statistical_analysis.py
```

---

### 2. `visualize_samples.py`
**목적:** 라벨링 품질 검증 및 데이터 시각화

**주요 기능:**
- 각 클래스별 랜덤 샘플 추출 (기본 5장)
- 바운딩박스/세그멘테이션 시각화
- 라벨링 오류 탐지 (bbox 크기 이상, 누락 등)
- 클래스별 대표 샘플 저장

**출력 결과:**
```
results/eda/YYYY-MM-DD/samples/
├── coating_damage/
│   ├── peeling_sample_001.png
│   ├── scratch_sample_001.png
│   └── welding_damage_sample_001.png
├── painting_defect/
│   ├── crack_sample_001.png
│   ├── blister_sample_001.png
│   └── ...
└── normal/
    ├── bow_sample_001.png
    ├── deck_sample_001.png
    └── outer_plate_sample_001.png
```

**실행:**
```bash
cd AI/lks
python src/eda/visualize_samples.py

# 샘플 개수 지정
python src/eda/visualize_samples.py --samples 10
```

---

### 3. `anomaly_analysis.py`
**목적:** 이상 탐지(Anomaly Detection) 모델 학습 전략 수립

**주요 기능:**
- 정상 데이터 통계 분석 (Normal 클래스)
- 정상 vs 비정상 feature 분리도 분석
- 부위별 정상 패턴 분석 (bow, deck, outer_plate)
- 결함 타입별 다양성 분석
- 정상 데이터 variation 측정
- 이상 탐지 알고리즘 추천

**출력 결과:**
```
results/eda/YYYY-MM-DD/anomaly/
├── charts/
│   ├── normal_distribution.png         # 정상 데이터 분포
│   ├── normal_vs_defect.png            # 정상 vs 결함 비교
│   ├── defect_diversity.png            # 결함 다양성
│   └── location_pattern.png            # 부위별 패턴
├── normal_stats.txt                    # 정상 데이터 통계
└── anomaly_strategy.txt                # 이상 탐지 전략 리포트
```

**실행:**
```bash
cd AI/lks
python src/eda/anomaly_analysis.py
```

---

## 📊 결과 저장 구조

```
results/eda/
├── 2026-01-24/                 # 날짜별 분석 결과
│   ├── statistical/
│   ├── samples/
│   └── anomaly/
├── 2026-01-25/
└── latest/                     # 최신 결과 (자동 복사)
    ├── statistical/
    ├── samples/
    └── anomaly/
```

---

## 🚀 전체 분석 실행

모든 분석을 한 번에 실행:

```bash
cd AI/lks

# 1. 통계 분석
python src/eda/statistical_analysis.py

# 2. 샘플 시각화
python src/eda/visualize_samples.py

# 3. 이상 탐지 분석
python src/eda/anomaly_analysis.py
```

---

## 📝 분석 결과 확인

```bash
# 최신 결과 확인
ls results/eda/latest/

# 특정 날짜 결과 확인
ls results/eda/2026-01-24/

# 분석 리포트 읽기
cat results/eda/latest/statistical/analysis_report.txt
cat results/eda/latest/anomaly/anomaly_strategy.txt
```

---

## ⚙️ 설정

모든 스크립트는 상대 경로를 사용하므로 **반드시 `AI/lks` 디렉토리에서 실행**하세요.

```bash
# 올바른 실행 위치
cd /path/to/S14P11E201/AI/lks
python src/eda/statistical_analysis.py  # ✅

# 잘못된 실행 위치
cd /path/to/S14P11E201/AI/lks/src/eda
python statistical_analysis.py           # ❌
```

---

## 📌 참고사항

- 데이터셋 경로: `data/extracted/`
- 설정 파일: `src/config/dataset_config.py`
- 분석 결과는 Git에 포함되지 않음 (`.gitignore`에 `results/` 추가됨)
