# AI Detection Pipeline

이미지를 입력받아 **우선순위대로 AI 검사를 수행**하는 핵심 파이프라인입니다.

## 처리 순서

```
이미지 입력
    ↓
1. YOLO 결함 탐지 (Defect Detection)
    ↓
   결함 발견?
    ├─ YES → [결과: DEFECT] → 종료
    └─ NO  → 2단계로
    ↓
2. Anomaly Detection
    ↓
   이상 발견?
    ├─ YES → [결과: ANOMALY]
    └─ NO  → [결과: NORMAL]
    ↓
결과 저장 (JSON + 시각화 이미지)
```

## 디렉토리 구조

```
kyr/pipeline/
├── ai_pipeline.py       # 메인 파이프라인 스크립트
├── run_pipeline.sh      # 실행 스크립트
└── README.md            # 이 파일
```

## 사용법

### 1. 단일 이미지 처리

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/pipeline
./run_pipeline.sh <image_path>
```

**예시:**
```bash
./run_pipeline.sh ~/test_image.jpg
```

### 2. 폴더 내 모든 이미지 일괄 처리

```bash
./run_pipeline.sh <directory_path>
```

**예시:**
```bash
./run_pipeline.sh ~/test_images/
```

### 3. 커스텀 설정

```bash
./run_pipeline.sh <input> --yolo-conf 0.6 --anomaly-threshold 0.8
```

**전체 옵션:**
- `--yolo-model PATH`: YOLO 모델 경로
- `--anomaly-model PATH`: Anomaly 모델 경로
- `--yolo-conf FLOAT`: YOLO 신뢰도 임계값 (기본: 0.5)
- `--anomaly-threshold FLOAT`: Anomaly 임계값 (기본: 0.7)
- `--output-dir PATH`: 출력 디렉토리 (기본: ../pipeline_results)

### 4. Python 직접 실행

```bash
python3 ai_pipeline.py <input> [options]
```

## 출력 결과

처리된 결과는 `pipeline_results/session_YYYYMMDD_HHMMSS/` 폴더에 저장됩니다.

### 출력 파일

1. **시각화된 이미지** (`*_result.jpg`)
   - 결함 바운딩 박스 표시
   - 상태별 색상 테두리 (빨강/노랑/초록)
   - 최종 판정 텍스트

2. **결과 JSON** (`results.json`)
   ```json
   {
     "session_dir": "session_20260127_183000",
     "timestamp": "2026-01-27T18:30:15.123456",
     "summary": {
       "total_images": 10,
       "defect_count": 3,
       "anomaly_count": 2,
       "normal_count": 5,
       "avg_yolo_inference_ms": 45.2,
       "avg_anomaly_inference_ms": 12.5
     },
     "results": [
       {
         "image_name": "test1.jpg",
         "timestamp": "2026-01-27T18:30:10.123456",
         "yolo_detections": [...],
         "yolo_inference_ms": 45.2,
         "has_defect": true,
         "anomaly_score": 0.0,
         "anomaly_inference_ms": 0.0,
         "has_anomaly": false,
         "final_status": "defect",
         "output_image_path": "..."
       },
       ...
     ]
   }
   ```

## 결과 상태 분류

| 상태 | 설명 | 시각화 색상 |
|------|------|-------------|
| **DEFECT** | YOLO에서 결함 탐지됨 | 빨간색 테두리 |
| **ANOMALY** | YOLO에서는 정상, Anomaly Detection에서 이상 탐지 | 노란색 테두리 |
| **NORMAL** | 모든 검사 통과 | 초록색 테두리 |

## 테스트 예시

```bash
# 1. 테스트 이미지 폴더 생성
mkdir -p ~/test_images

# 2. 이미지 복사 (예시)
cp /path/to/your/images/*.jpg ~/test_images/

# 3. 파이프라인 실행
cd /home/ssafy/S14P11E201/Embedded/kyr/pipeline
./run_pipeline.sh ~/test_images/

# 4. 결과 확인
ls -la ../pipeline_results/session_*/
```

## 주요 특징

✅ **단순하고 독립적**: 웹 서버나 모터 제어 없이 AI 검사만 수행
✅ **우선순위 처리**: YOLO → Anomaly Detection 순서로 효율적 처리
✅ **배치 처리 지원**: 폴더 내 모든 이미지를 한 번에 처리
✅ **상세한 로그**: 각 단계별 추론 시간 및 결과 출력
✅ **JSON 결과**: 프로그래밍 방식으로 결과 활용 가능
✅ **시각화**: 결함 위치 및 판정 결과를 이미지에 표시

## 모델 경로

기본 모델 경로:
- YOLO: `../models/yolo/best_fixed.pt` (또는 `.engine`)
- Anomaly: `../models/anomaly_detection/best_model.pt`

모델이 없는 경우 placeholder 모드로 동작합니다.

## 문제 해결

### 모델이 없다는 에러
```bash
# YOLO 모델 확인
ls -la ../models/yolo/best_fixed.pt

# Anomaly 모델 확인
ls -la ../models/anomaly_detection/best_model.pt
```

### 권한 에러
```bash
chmod +x run_pipeline.sh
```

### Python 모듈 에러
```bash
pip3 install ultralytics opencv-python numpy torch
```

## 라이센스

Internal use only.
