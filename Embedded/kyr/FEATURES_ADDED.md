# 🎨 새로 추가된 기능

오린카 검사 시스템에 추가된 주요 기능들입니다.

---

## ✨ 추가된 기능 목록

### 1. 📹 실시간 모니터링

**기능**: 웹 UI에서 카메라 피드를 실시간으로 확인

- 검사 진행 상황을 실시간으로 모니터링
- 현재 Zone 번호 및 타입 표시
- 30 FPS 비디오 스트리밍

**구현**:
- `/video_feed` 엔드포인트 추가
- MJPEG 스트리밍 방식 사용
- HTML 템플릿에 `<img src="/video_feed">` 추가

---

### 2. 🎨 결과 이미지 시각화

**기능**: 검사 결과를 시각적으로 표현한 이미지 자동 생성

#### Normal Zone (정상)
- ✅ **초록색 테두리** (전체 이미지)
- ✅ "NORMAL" 텍스트 (상단 중앙)
- ✅ Zone 정보 (좌측 상단)

#### Anomaly Zone (이상)
- ⚠️ **노란색 테두리** (전체 이미지)
- ⚠️ "ANOMALY DETECTION" 텍스트 (상단 중앙)
- ⚠️ Anomaly Score 표시 (하단)

#### Defect Zone (결함)
- ❌ **빨간색 BBox** (각 결함마다)
- ❌ 결함 클래스명 + 신뢰도 표시
- ❌ "DEFECT DETECTED" 텍스트 (상단 중앙)

**구현 파일**: `visualization_utils.py`

---

### 3. 📁 차수별 폴더 분리 저장

**기능**: 검사 결과를 세션별로 깔끔하게 관리

#### 폴더 구조

```
inspection_results/
├── session_20260127_143000/
│   ├── zone_00_normal.jpg
│   ├── zone_01_normal.jpg
│   ├── zone_02_anomaly.jpg
│   ├── zone_03_defect.jpg
│   ├── zone_04_defect.jpg
│   ├── zone_05_defect.jpg
│   └── inspection_results.json
│
├── session_20260127_150000/
│   └── ...
│
└── session_20260127_160000/
    └── ...
```

**장점**:
- ✅ 검사 세션별로 명확하게 구분
- ✅ 타임스탬프로 정렬 가능
- ✅ 삭제 및 관리 용이
- ✅ 같은 폴더에 이미지와 JSON 결과 함께 저장

---

## 🖼️ 시각화 예시

### Normal Zone
```
┌──────────────────────────────────┐
│ Zone 0 - NORMAL                  │  ← 좌측 상단
│                                  │
│                                  │
│         NORMAL                   │  ← 상단 중앙 (초록색)
│                                  │
│                                  │
│              2026-01-27 14:30:00 │  ← 우측 하단
└──────────────────────────────────┘
  (초록색 테두리)
```

### Anomaly Zone
```
┌──────────────────────────────────┐
│ Zone 2 - ANOMALY                 │
│                                  │
│     ANOMALY DETECTION            │  ← 노란색
│                                  │
│                                  │
│  Anomaly Score: 0.8234           │  ← 하단
│              2026-01-27 14:30:00 │
└──────────────────────────────────┘
  (노란색 테두리)
```

### Defect Zone
```
┌──────────────────────────────────┐
│ Zone 3 - DEFECT                  │
│                                  │
│      DEFECT DETECTED             │  ← 빨간색
│                                  │
│      ┌──────────┐                │
│      │ crack    │                │  ← 빨간색 BBox
│      │ 0.89     │                │
│      └──────────┘                │
│              2026-01-27 14:30:00 │
└──────────────────────────────────┘
```

---

## 📊 JSON 결과 형식

```json
{
  "mode": "manual",
  "session_folder": "session_20260127_143000",
  "config": {
    "total_length_cm": 180,
    "zone_length_cm": 30,
    "zone_types": ["normal", "normal", "anomaly", "defect", "defect", "defect"]
  },
  "timestamp": "2026-01-27T14:30:00",
  "results": [
    {
      "zone_id": 3,
      "zone_type": "defect",
      "timestamp": "2026-01-27T14:30:10",
      "detections": [
        {
          "class_id": 2,
          "class_name": "crack",
          "confidence": 0.89,
          "bbox": [120, 150, 200, 250]
        }
      ],
      "image_path": "session_20260127_143000/zone_03_defect.jpg",
      "inference_time_ms": 45.2,
      "is_defective": true
    }
  ],
  "summary": {
    "total_zones": 6,
    "defective_zones": 2,
    "normal_zones": 2,
    "anomaly_zones": 1,
    "defect_zones": 3
  }
}
```

---

## 🚀 사용 방법

### 1. 수동 모드 실행

```bash
cd inspection
./run_manual_inspection.sh
```

웹 브라우저: `http://<IP>:5003`

- ✅ 실시간 카메라 피드 확인
- ✅ "세션 시작" 클릭
- ✅ "현재 Zone 촬영" 클릭하여 각 Zone 검사
- ✅ 결과는 자동으로 `inspection_results/session_XXX/` 폴더에 저장

### 2. 자동 모드 실행

```bash
cd inspection
./run_inspection.sh
```

웹 브라우저: `http://<IP>:5002`

- ✅ "Start Inspection" 클릭
- ✅ 자동으로 6개 Zone 검사 진행
- ✅ 결과는 `inspection_results/session_XXX/` 폴더에 저장

---

## 🔧 시각화 함수 API

### `visualize_inspection_result()`

```python
from visualization_utils import visualize_inspection_result, add_timestamp

# 기본 사용
visualized_image = visualize_inspection_result(
    image=frame,
    zone_id=3,
    zone_type='defect',
    detections=[...],
    is_defective=True
)

# 타임스탬프 추가
visualized_image = add_timestamp(visualized_image, "2026-01-27T14:30:00")

# 저장
cv2.imwrite('result.jpg', visualized_image)
```

### 개별 함수들

```python
from visualization_utils import (
    visualize_normal,    # Normal Zone 시각화
    visualize_anomaly,   # Anomaly Zone 시각화
    visualize_defect,    # Defect Zone 시각화
    draw_bbox,           # BBox 그리기
    draw_frame_border,   # 전체 테두리 그리기
    draw_header_text,    # 상단 텍스트 그리기
)
```

---

## 💡 장점

### 1. 실시간 모니터링
- ✅ 검사 진행 상황을 즉시 확인
- ✅ 문제 발생 시 빠른 대응 가능
- ✅ 카메라 위치 조정 실시간 확인

### 2. 시각화
- ✅ 한눈에 결과 파악 가능
- ✅ 보고서 작성 용이
- ✅ 비전문가도 이해하기 쉬움
- ✅ 결함 위치 정확히 표시

### 3. 폴더 분리 저장
- ✅ 검사 이력 관리 편리
- ✅ 특정 검사 결과만 빠르게 찾기
- ✅ 백업 및 공유 용이
- ✅ 디스크 공간 관리 편리

---

## 📝 TODO

### 자동 모드 완전 업데이트 (진행 중)

자동 모드에도 동일한 기능을 완전히 적용해야 합니다:

- [x] visualization_utils import 추가
- [x] current_frame 변수 추가
- [x] session_dir 생성 로직 추가
- [ ] inspect_zone 메서드에 시각화 코드 추가
- [ ] save_results 메서드 수정
- [ ] generate_frames 메서드 추가
- [ ] Flask /video_feed 라우트 추가
- [ ] HTML 템플릿에 비디오 피드 추가

**수동으로 추가 작업 필요!**

### 추가 개선 사항

- [ ] 실시간 그래프 (탐지 결과 시계열)
- [ ] 결과 비교 기능 (세션 간 비교)
- [ ] PDF 보고서 자동 생성
- [ ] 이메일 알림 기능
- [ ] 모바일 최적화

---

## 🎉 완료!

수동 모드는 모든 기능이 완전히 구현되었습니다!

```bash
cd inspection
./run_manual_inspection.sh
```

실시간으로 검사 과정을 모니터링하고,
아름답게 시각화된 결과를 확인하세요! 🚗💨
