# 🚗 Jetson Orin Nano Car 자동 주행 검사 시스템

## 📋 개요

캘리브레이션 데이터를 기반으로 180cm 보드지를 30cm씩 6구역으로 나눠 자동 주행하며 객체 탐지를 수행하는 시스템입니다.

### 주요 기능
- ✅ 캘리브레이션 기반 정확한 30cm 주행
- ✅ ROI 크롭으로 보드지 영역(30cm x 85cm)만 표시
- ✅ 실시간 Flask 웹 모니터링
- ✅ 자동 촬영 및 YOLO 결함 탐지
- ✅ 결과 자동 저장 (이미지 + JSON)

---
# 🚀 초간단 사용 가이드

## 환경이 바뀔 때마다 (거리, 각도 등)

### ✅ 올바른 방법 (자동)

```bash
# 1단계: ROI 조정 (웹 브라우저)
python web_roi_config.py
# → http://<Jetson IP>:5005 접속
# → 버튼으로 ROI 조정
# → [설정 저장] 클릭
# → roi_config.txt에 자동 저장됨

# 2단계: 검사 시스템 실행 (파일 수정 불필요!)
python auto_inspection_system.py
# → roi_config.txt를 자동으로 읽어옴
# → http://<Jetson IP>:5004 접속
```

**끝!** 파일 수정 필요 없음! 👍

---

## 🎯 상황별 사용법

### 상황 1: 처음 사용할 때
```bash
1. python web_roi_config.py
   → ROI 조정 후 저장

2. python auto_inspection_system.py
   → 자동으로 ROI 적용됨
```

### 상황 2: 거리가 바뀌었을 때 (예: 100cm → 80cm)
```bash
1. python web_roi_config.py
   → ROI 재조정 후 저장

2. python auto_inspection_system.py
   → 새로운 ROI가 자동으로 적용됨
```

### 상황 3: 다른 장소에서 시연할 때
```bash
1. python web_roi_config.py
   → 새 환경에 맞게 ROI 조정
   → 저장

2. python auto_inspection_system.py
   → 자동으로 적용
```

---

## 📁 파일 구조

```
scripts/
├── web_roi_config.py           # ROI 조정 도구
├── auto_inspection_system.py   # 검사 시스템
└── roi_config.txt              # ROI 설정 (자동 생성)
    ↑
    이 파일만 있으면 자동으로 적용됨!
```

-

## 🔍 확인 방법

**auto_inspection_system.py 실행 시 터미널에 표시:**

```
[ROI] Loading config from: /path/to/roi_config.txt
[ROI] Loaded: (180, 80) -> (460, 400)
[ROI] Size: 280 x 320 pixels
```

이 메시지가 뜨면 자동으로 적용된 것입니다! ✅

---

## ⚠️ 주의사항

1. **web_roi_config.py와 auto_inspection_system.py는 같은 폴더에 있어야 합니다**
   - roi_config.txt도 같은 폴더에 자동 생성됨

2. **roi_config.txt가 없으면?**
   - 기본값 (160, 60) -> (480, 420) 사용
   - 경고 메시지 표시

3. **거리가 바뀌면 반드시 ROI 재조정!**
   - 안 하면 보드지가 화면에 제대로 안 잡힘

---

## 📝 요약

**Q: 거리가 달라질 때도 쓸 수 있어?**
→ **YES!** 거리가 바뀔 때마다 ROI만 재조정하면 됩니다.

**Q: 그때마다 파일 수정해야 해?**
→ **NO!** roi_config.txt가 자동으로 적용됩니다.


## 🎯 시스템 구성

### 하드웨어 사양
- **보드지 크기**: 180cm x 85cm
- **검사 구역**: 30cm씩 6구역
- **오린카 높이**: 14cm
- **웹캠 높이**: 10cm (고정)
- **오린카 길이**: 28cm
- **보드지 거리**: 약 100cm (±10cm)

### 캘리브레이션 결과 (적용됨)
```
출력 25% / 시간 2.7초 → 약 30cm 주행
평균 속도: 11.04 cm/s
```

---

## 🚀 설치 및 실행

### 1. 필요한 파일
```
project/
├── scripts/
│   ├── auto_inspection_system.py  # 메인 시스템
│   ├── roi_config_tool.py         # ROI 설정 도구
│   └── visualization_utils.py     # 시각화 유틸
├── models/
│   └── yolo/
│       └── best_fixed.engine          # YOLO 모델
└── inspection_results/             # 결과 저장 (자동 생성)
```

### 2. ROI 설정 (최초 1회)

**목적**: 웹캠 화면에서 보드지 30cm x 85cm 영역만 보이도록 조정

```bash
# ROI 설정 도구 실행
python roi_config_tool.py
```

**조정 방법**:
1. 오린카를 보드지 앞 1미터에 위치
2. 키보드로 ROI 조정:
   - `w/s`: 위아래 이동
   - `a/d`: 좌우 이동
   - `i/k`: 높이 조정
   - `j/l`: 폭 조정
   - `c`: 크롭 화면 미리보기
   - `r`: 초기값 리셋
   - `q`: 저장 및 종료

3. 출력된 좌표값을 `auto_inspection_system.py`의 `ROIConfig`에 적용

### 3. 시스템 실행

```bash
# 자동 주행 검사 시스템 실행
python auto_inspection_system.py
```

**접속**:
```
http://<Jetson IP>:5004
예: http://192.168.0.100:5004
```

---

## 📱 웹 UI 사용법

### 화면 구성
1. **실시간 모니터링**: ROI 크롭된 화면 (30cm x 85cm만 표시)
2. **제어 버튼**: 자동 검사 시작/중지
3. **진행 상황**: 6개 Zone의 상태 표시
4. **통계**: 완료/결함 Zone 수

### 자동 검사 흐름
```
1. "자동 검사 시작" 버튼 클릭
   ↓
2. Zone 0 촬영 및 탐지
   ↓
3. 30cm 주행 (2.7초)
   ↓
4. Zone 1 촬영 및 탐지
   ↓
5. ... (반복)
   ↓
6. Zone 5 완료 → 결과 저장
```

**소요 시간**: 약 20~25초

---

## 📊 Zone 구성

| Zone | 위치 (cm) | 유형 | 탐지 방법 |
|------|-----------|------|-----------|
| 0 | 0-30 | Normal | 탐지 안 함 |
| 1 | 30-60 | Normal | 탐지 안 함 |
| 2 | 60-90 | Anomaly | YOLO |
| 3 | 90-120 | Defect | YOLO |
| 4 | 120-150 | Defect | YOLO |
| 5 | 150-180 | Defect | YOLO |

---

## 💾 결과 저장

### 저장 위치
```
inspection_results/
└── auto_session_20260128_153000/
    ├── zone_00_normal.jpg
    ├── zone_01_normal.jpg
    ├── zone_02_anomaly.jpg
    ├── zone_03_defect.jpg
    ├── zone_04_defect.jpg
    ├── zone_05_defect.jpg
    └── inspection_results.json
```

### JSON 결과 형식
```json
{
  "mode": "auto",
  "session_folder": "auto_session_20260128_153000",
  "timestamp": "2026-01-28T15:30:00",
  "results": [
    {
      "zone_id": 0,
      "zone_type": "normal",
      "timestamp": "2026-01-28T15:30:05",
      "detections": [],
      "inference_time_ms": 0.0,
      "is_defective": false
    },
    ...
  ],
  "summary": {
    "total_zones": 6,
    "defective_zones": 3
  }
}
```

---

## ⚙️ 설정 커스터마이징

### 모터 출력 조정
`auto_inspection_system.py`의 `InspectionConfig`:
```python
@dataclass
class InspectionConfig:
    motor_pwm: int = 25      # 출력 (%)
    motor_time: float = 2.7  # 시간 (초)
```

**조정 가이드** (캘리브레이션 결과 기준):
- **25% / 2.7초** → 30cm (추천)
- **30% / 2.1초** → 30cm (빠름)
- **40% / 1.4초** → 30cm (매우 빠름, 불안정)

### ROI 영역 조정
`ROIConfig`:
```python
@dataclass
class ROIConfig:
    x_start: int = 160   # 왼쪽 시작
    x_end: int = 480     # 오른쪽 끝
    y_start: int = 60    # 위쪽 시작
    y_end: int = 420     # 아래쪽 끝
```

### YOLO 신뢰도 임계값
```python
yolo_conf_threshold: float = 0.5  # 0.0 ~ 1.0
```

---

## 🔧 문제 해결

### 1. ROI가 보드지를 제대로 못 잡음
→ `roi_config_tool.py` 실행하여 재조정

### 2. 주행 거리가 30cm보다 짧거나 김
→ `InspectionConfig`의 `motor_pwm`, `motor_time` 조정

### 3. YOLO 모델 로드 실패
→ 모델 경로 확인: `../models/yolo/best_fixed.engine`

### 4. 카메라 오류
→ GStreamer 설치 확인, 카메라 연결 확인

---

## 📐 ROI 계산 참고

### 카메라 시야각 계산 (참고용)
```
거리: 100cm
웹캠 높이: 10cm
보드지 세로: 85cm
보드지 가로: 30cm

→ 640x480 해상도에서
  가로 30cm ≈ 320px
  세로 85cm ≈ 360px
```

**주의**: 실제 환경에 따라 다르므로 `roi_config_tool.py`로 조정 필수!

---

## 🎓 추가 기능

### 수동 모드 (비교용)
손으로 밀면서 검사하는 모드는 기존 `manual_inspection.py` 사용

### 캘리브레이션
새로운 바닥/조건에서는 `calibration_improved.py`로 재캘리브레이션

---

## 📞 문의

문제 발생 시:
1. 터미널 로그 확인
2. `inspection_results/` 폴더 확인
3. ROI 설정 재조정

---

**최종 업데이트**: 2026-01-29
**버전**: 1.0.0