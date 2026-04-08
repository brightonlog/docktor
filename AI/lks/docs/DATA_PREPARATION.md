# 데이터 준비 가이드

선박 도장 품질 측정 데이터셋 다운로드 및 전처리 파이프라인

---

## 📋 목차

1. [환경 요구사항](#환경-요구사항)
2. [데이터 다운로드](#데이터-다운로드)
3. [데이터 추출](#데이터-추출)
4. [디렉토리 구조](#디렉토리-구조)
5. [트러블슈팅](#트러블슈팅)

---

## 🔧 환경 요구사항

### 공통
- Python 3.8 이상
- 최소 40GB 이상의 여유 디스크 공간
- AI Hub 계정 및 API Key

### 필수 Python 패키지
```bash
pip install opencv-python numpy tqdm
```

---

## 📥 데이터 다운로드

### 1. AI Hub 데이터셋 정보
- **데이터셋명**: 선박 도장 품질 측정 데이터
- **데이터셋 ID**: 71447
- **데이터 출처**: [AI Hub](https://www.aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&aihubDataSe=realm&dataSetSn=71447)

### 2. aihubshell 다운로드

**Linux/Mac:**
```bash
# AI Hub에서 aihubshell 다운로드
cd AI/lks/data/raw
# aihubshell 파일을 data/raw/ 디렉토리에 배치
chmod +x aihubshell
```

**Windows:**
```powershell
# AI Hub에서 aihubshell.exe 다운로드
# AI/lks/data/raw/ 디렉토리에 배치
```

### 3. 데이터 다운로드 명령어

**Linux/Mac:**
```bash
cd AI/lks/data/raw

./aihubshell -mode d \
  -datasetkey 71447 \
  -filekey 490116,490117,490118,490119,490120,490121,490122,490123,490124,490125,490126,490129,490132,490138,490139,490140,490141,490142,490143,490144,490145,490146,490147,490148,490151,490154 \
  -aihubapikey 'YOUR_API_KEY_HERE'
```

**Windows:**
```powershell
cd AI\lks\data\raw

.\aihubshell.exe -mode d -datasetkey 71447 -filekey 490116,490117,490118,490119,490120,490121,490122,490123,490124,490125,490126,490129,490132,490138,490139,490140,490141,490142,490143,490144,490145,490146,490147,490148,490151,490154 -aihubapikey 'YOUR_API_KEY_HERE'
```

> ⚠️ `YOUR_API_KEY_HERE`를 본인의 AI Hub API Key로 교체하세요.

### 4. 다운로드 결과
- **총 파일 수**: 26개 ZIP 파일
- **용량**: 약 30.7GB
- **소요 시간**: 네트워크 속도에 따라 5~20분

---

## 📦 데이터 추출

### 1. 압축 파일 병합 확인

다운로드 후 분할 압축 파일(.part0, .part1 등)이 자동으로 병합되었는지 확인:

**Linux/Mac:**
```bash
cd AI/lks/data/raw
find . -name "*.zip" -type f | wc -l
# 결과: 26 (정상)
```

**Windows (PowerShell):**
```powershell
cd AI\lks\data\raw
(Get-ChildItem -Recurse -Filter *.zip -File).Count
# 결과: 26 (정상)
```

만약 26개가 아니라면 수동 병합이 필요합니다.

### 2. 데이터 자동 추출

**Linux/Mac:**
```bash
cd AI/lks
python src/extract_dataset.py
```

**Windows:**
```powershell
cd AI\lks
python src\extract_dataset.py
```

### 3. 추출 결과

```
✓ 총 26개 ZIP 파일 추출
✓ 13,351개 이미지 추출
✓ 13,351개 라벨 파일 추출
✓ 총 36GB 데이터 생성
```

---

## 📁 디렉토리 구조

### 최종 구조
```
AI/lks/
├── data/
│   ├── raw/                                    # 원본 ZIP 파일 (30.7GB)
│   │   └── 194.선박_도장_품질_측정_데이터/
│   │       └── 01-1.정식개방데이터/Validation/
│   │           ├── 01.원천데이터/              # 이미지 ZIP 파일 (13개)
│   │           └── 02.라벨링데이터/             # 라벨 ZIP 파일 (13개)
│   │
│   └── extracted/                              # 추출된 데이터 (36GB)
│       ├── 01.images/                          # 이미지 파일
│       │   ├── coating_damage/                 # 도막 손상 (6,087개)
│       │   │   ├── peeling/                    # 도막떨어짐
│       │   │   ├── scratch/                    # 스크래치
│       │   │   └── welding_damage/             # 용접손상
│       │   │
│       │   ├── painting_defect/                # 도장 불량 (4,168개)
│       │   │   ├── blister/                    # 부풀음
│       │   │   ├── coating_separation/         # 도막분리
│       │   │   ├── crack/                      # 균열
│       │   │   ├── foreign_material/           # 이물질포함
│       │   │   ├── pinhole/                    # 핀홀
│       │   │   ├── sagging/                    # 흐름
│       │   │   └── water_spotting/             # 워터스포팅
│       │   │
│       │   └── normal/                         # 양품 (3,096개)
│       │       ├── bow/                        # 선수
│       │       ├── deck/                       # 갑판
│       │       └── outer_plate/                # 외판
│       │
│       └── 02.labels/                          # JSON 라벨 (동일 구조)
│           ├── coating_damage/
│           ├── painting_defect/
│           └── normal/
```

### 클래스 정보

| 대분류 | 소분류 | 영문명 | 이미지 수 | 클래스 ID |
|--------|--------|--------|----------|-----------|
| **양품** | 선수 | bow | 1,028 | 101 |
| | 갑판 | deck | 1,025 | 101 |
| | 외판 | outer_plate | 1,043 | 101 |
| **도막 손상** | 도막떨어짐 | peeling | 2,005 | 303 |
| | 스크래치 | scratch | 2,047 | 302 |
| | 용접손상 | welding_damage | 2,035 | 301 |
| **도장 불량** | 부풀음 | blister | 585 | 206 |
| | 도막분리 | coating_separation | 620 | 203 |
| | 균열 | crack | 580 | 205 |
| | 이물질포함 | foreign_material | 598 | 207 |
| | 핀홀 | pinhole | 591 | 204 |
| | 흐름 | sagging | 604 | 202 |
| | 워터스포팅 | water_spotting | 590 | 201 |

---

## 🔍 데이터 검증

추출이 정상적으로 완료되었는지 확인:

**Linux/Mac:**
```bash
cd AI/lks/data/extracted

# 이미지 파일 개수 확인
find 01.images -type f -name "*.JPG" | wc -l
# 예상 결과: 13,351

# 라벨 파일 개수 확인
find 02.labels -type f -name "*.json" | wc -l
# 예상 결과: 13,351
```

**Windows (PowerShell):**
```powershell
cd AI\lks\data\extracted

# 이미지 파일 개수 확인
(Get-ChildItem -Recurse -Path 01.images -Filter *.JPG -File).Count
# 예상 결과: 13,351

# 라벨 파일 개수 확인
(Get-ChildItem -Recurse -Path 02.labels -Filter *.json -File).Count
# 예상 결과: 13,351
```

---

## 🛠 트러블슈팅

### Q1. aihubshell 실행 시 "Permission denied" 에러

**Linux/Mac:**
```bash
chmod +x aihubshell
```

### Q2. Windows에서 경로 문제

Windows에서는 백슬래시(`\`) 사용:
```powershell
cd AI\lks
python src\extract_dataset.py
```

### Q3. ZIP 파일이 26개가 아닌 경우

분할 압축 파일 병합 스크립트 실행:

**Linux/Mac:**
```bash
cd AI/lks/data/raw
python merge_parts.py  # 병합 스크립트 (있는 경우)
```

병합 스크립트가 없다면 수동 병합:
```bash
cat file.zip.part* > file.zip
```

### Q4. 디스크 공간 부족

- 필요 공간: 약 70GB (원본 30GB + 추출 36GB + 여유 공간)
- 추출 후 원본 ZIP 파일 삭제 가능 (30GB 절약)

```bash
# 추출 완료 후 원본 삭제 (선택사항)
cd AI/lks/data/raw
rm -rf 194.선박_도장_품질_측정_데이터/
```

### Q5. Python 패키지 누락 에러

```bash
pip install opencv-python numpy tqdm
```

### Q6. 경로 관련 에러

스크립트는 상대 경로를 사용하므로 반드시 프로젝트 루트에서 실행:

```bash
# 잘못된 방법
cd AI/lks/src
python extract_dataset.py  # ❌

# 올바른 방법
cd AI/lks
python src/extract_dataset.py  # ✅
```

---

## 📌 참고사항

### Git 관리
- `data/raw/*`, `data/extracted/*`는 `.gitignore`에 포함됨
- 데이터 파일은 Git에 커밋되지 않음 (용량 문제)
- 각 팀원이 개별적으로 다운로드 필요

### 설정 파일 위치
- 카테고리 정보: `src/config/dataset_config.py`
- 카테고리 추가/변경 시 이 파일만 수정하면 됨

### 다음 단계
1. 데이터 분석: `python src/data_analysis.py`
2. 모델 학습: `python src/training/detection/train.py` (예정)

---

## 💡 도움이 필요하신가요?

- 이슈 발생 시 팀원에게 문의
- AI Hub 데이터 다운로드 관련: [AI Hub 고객센터](https://www.aihub.or.kr)
