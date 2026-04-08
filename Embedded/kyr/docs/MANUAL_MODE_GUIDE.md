# 🖐️ Manual Mode Guide

모터 없이 손으로 오린카를 밀면서 실습할 수 있는 수동 모드 가이드입니다.

---

## 🎯 수동 모드란?

캘리브레이션이나 모터 제어 없이, **손으로 오린카를 직접 밀면서** 검사 시스템을 테스트할 수 있는 모드입니다.

### 자동 모드 vs 수동 모드

| 기능 | 자동 모드 | 수동 모드 |
|------|----------|----------|
| 파일 | orincar_inspection_system.py | **orincar_inspection_manual.py** |
| 포트 | 5002 | **5003** |
| 모터 제어 | ✅ 자동 주행 | ❌ 손으로 이동 |
| 캘리브레이션 | ✅ 필수 | ❌ 불필요 |
| 이동 방식 | 자동으로 30cm 이동 | 손으로 직접 밀기 |
| 촬영 방식 | 자동 촬영 | 버튼 클릭으로 촬영 |
| 사용 케이스 | 실제 검사 | **실습 및 테스트** |

---

## 🚀 빠른 시작

### 1. 서버 실행

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr
./run_manual_inspection.sh
```

또는

```bash
python3 orincar_inspection_manual.py
```

### 2. 웹 UI 접속

브라우저에서 `http://<Jetson IP>:5003` 접속

예: `http://192.168.0.100:5003`

### 3. 검사 진행

1. **"🚀 세션 시작"** 버튼 클릭
2. 오린카를 **Zone 0 위치**에 놓기
3. **"📷 현재 Zone 촬영"** 버튼 클릭 → 촬영 및 탐지
4. 결과 확인 후 오린카를 **손으로 30cm** 앞으로 밀기
5. **"➡️ 다음 Zone"** 버튼 클릭
6. **3~5번 과정을 5번 더 반복** (총 6개 Zone)
7. 완료 시 자동으로 결과 저장

---

## 📋 상세 사용 방법

### Step 1: 세션 시작

<img src="https://via.placeholder.com/800x200/667eea/ffffff?text=Session+Start" alt="세션 시작"/>

- **"세션 시작"** 버튼 클릭
- 현재 Zone이 **Zone 1**로 표시됨
- **"현재 Zone 촬영"** 버튼 활성화

### Step 2: Zone 0 촬영

<img src="https://via.placeholder.com/800x200/3b82f6/ffffff?text=Capture+Zone" alt="Zone 촬영"/>

1. 오린카를 **Zone 0 위치**에 정확히 위치
2. 카메라가 30cm 영역을 잘 담고 있는지 확인
3. **"📷 현재 Zone 촬영"** 버튼 클릭
4. 탐지 결과 대기 (1-2초)
5. 화면에 탐지 결과 표시:
   - Zone 번호 및 타입
   - 추론 시간
   - 결함 여부
   - 탐지된 객체 리스트

### Step 3: 다음 Zone으로 이동

<img src="https://via.placeholder.com/800x200/f59e0b/ffffff?text=Move+to+Next+Zone" alt="다음 Zone"/>

1. 탐지 결과 확인
2. 오린카를 **손으로 30cm 앞으로** 밀기
3. **"➡️ 다음 Zone"** 버튼 클릭
4. 알림창: "다음 Zone으로 이동합니다. 오린카를 30cm 앞으로 밀어주세요!"
5. 현재 Zone이 **Zone 2**로 변경

### Step 4: 반복

- **Zone 1 ~ Zone 5**까지 **Step 2-3 반복**
- 총 **6개 Zone** 완료

### Step 5: 완료

<img src="https://via.placeholder.com/800x200/10b981/ffffff?text=Inspection+Complete" alt="검사 완료"/>

- Zone 5 완료 후 자동으로 세션 종료
- 알림창: "✅ 모든 Zone 검사 완료!"
- 결과 파일 자동 저장:
  - `inspection_results/manual_inspection_<timestamp>.json`
  - 6개 Zone 이미지 파일

---

## 🎨 웹 UI 설명

### 1. 헤더

- **제목**: "🖐️ Orin Car Manual Inspection"
- **MANUAL MODE** 배지 표시
- 손으로 제어한다는 안내 문구

### 2. 사용 방법 카드

- 주황색 박스에 7단계 사용 방법 표시
- 실습 전 반드시 읽기!

### 3. 제어 버튼

| 버튼 | 색상 | 기능 |
|------|------|------|
| 🚀 세션 시작 | 녹색 | 새로운 검사 세션 시작 |
| 📷 현재 Zone 촬영 | 파란색 | 현재 Zone 촬영 및 탐지 |
| ➡️ 다음 Zone | 주황색 | 다음 Zone으로 이동 (촬영 후 활성화) |
| 🏁 세션 종료 | 빨간색 | 세션 강제 종료 |

### 4. 상태 표시

- 현재 Zone 번호 및 타입
- 다음 해야 할 작업 안내
- 큰 글씨로 명확하게 표시

### 5. 마지막 탐지 결과

- 촬영 직후 결과 박스 표시
- Zone 정보, 추론 시간, 결함 여부
- 탐지된 객체 리스트 (있을 경우)

### 6. Zone 진행 상황

- 6개 Zone 카드 그리드
- 현재 Zone: 애니메이션 효과 (🎯)
- 완료된 Zone: 녹색 배경 (✅)
- 대기 중 Zone: 회색 (⏳)

### 7. 통계

- Total Zones: 6
- Completed: 완료된 Zone 수
- Defective: 결함 발견된 Zone 수

---

## 📊 결과 확인

검사 완료 후 `inspection_results/` 폴더에 파일 생성:

### 1. JSON 결과 파일

`manual_inspection_<timestamp>.json`

```json
{
  "mode": "manual",
  "config": {
    "total_length_cm": 180,
    "zone_length_cm": 30,
    "zone_types": ["normal", "normal", "anomaly", "defect", "defect", "defect"]
  },
  "timestamp": "2026-01-27T15:30:00",
  "results": [
    {
      "zone_id": 0,
      "zone_type": "normal",
      "detections": [],
      "is_defective": false
    },
    {
      "zone_id": 3,
      "zone_type": "defect",
      "detections": [
        {
          "class_name": "crack",
          "confidence": 0.89
        }
      ],
      "is_defective": true
    }
  ],
  "summary": {
    "total_zones": 6,
    "defective_zones": 2
  }
}
```

### 2. 이미지 파일

- `zone_0_normal_<timestamp>.jpg`
- `zone_1_normal_<timestamp>.jpg`
- `zone_2_anomaly_<timestamp>.jpg`
- `zone_3_defect_<timestamp>.jpg`
- `zone_4_defect_<timestamp>.jpg`
- `zone_5_defect_<timestamp>.jpg`

---

## 🔧 커스터마이징

### Zone 타입 변경

[orincar_inspection_manual.py:48](orincar_inspection_manual.py:48) 에서 수정:

```python
zone_types = [
    'defect',   # Zone 0
    'anomaly',  # Zone 1
    'normal',   # Zone 2
    'defect',   # Zone 3
    'defect',   # Zone 4
    'normal'    # Zone 5
]
```

### Threshold 조정

```python
@dataclass
class InspectionConfig:
    yolo_conf_threshold: float = 0.5
    anomaly_threshold: float = 0.7
```

---

## 💡 팁 & 요령

### 1. 30cm 거리 측정

- **자를 준비**하세요
- 바닥에 테이프로 **30cm 간격 표시**
- 또는 보드에 **6개 Zone 표시**

### 2. 카메라 위치

- 각 Zone이 **프레임에 꽉 차도록** 카메라 조정
- 너무 가까우면 일부만 보임
- 너무 멀면 디테일 손실

### 3. 조명

- **밝은 환경**에서 실습
- 그림자가 생기지 않도록 주의
- 형광등 또는 자연광 권장

### 4. 오린카 고정

- 촬영할 때 **오린카가 움직이지 않도록** 주의
- 손을 떼고 촬영 버튼 클릭

### 5. 실습 환경

```
[시작]  →  30cm  →  30cm  →  30cm  →  30cm  →  30cm  →  [종료]
Zone 0     Zone 1    Zone 2    Zone 3    Zone 4    Zone 5
```

바닥에 위와 같이 표시하면 편리합니다!

---

## 🆚 자동 모드와 비교

### 언제 수동 모드를 사용하나?

✅ **수동 모드 사용 케이스:**
- 모터가 작동하지 않을 때
- 캘리브레이션 전 시스템 테스트
- YOLO/Anomaly 모델 테스트
- 웹 UI 기능 확인
- 실습 및 데모

❌ **자동 모드 사용 케이스:**
- 실제 검사 작업
- 빠른 검사 필요
- 정확한 위치 제어 필요
- 반복적인 검사

### 전환 방법

```bash
# 수동 모드 → 자동 모드
# 1. 수동 모드 서버 종료 (Ctrl+C)
# 2. 자동 모드 실행
./run_inspection.sh

# 자동 모드 → 수동 모드
# 1. 자동 모드 서버 종료 (Ctrl+C)
# 2. 수동 모드 실행
./run_manual_inspection.sh
```

---

## 🐛 문제 해결

### 1. 카메라가 안 열릴 때

```bash
sudo chmod 666 /dev/video0
# USB 재연결
```

### 2. "다음 Zone" 버튼이 비활성화됨

- 먼저 **"현재 Zone 촬영"** 버튼을 클릭하세요
- 촬영 완료 후 자동으로 활성화됩니다

### 3. 탐지 결과가 이상함

- **카메라 위치** 확인
- **조명** 확인
- **Threshold** 조정 필요

### 4. Zone 순서가 헷갈림

- 웹 UI의 **"Zone 진행 상황"** 카드 확인
- 현재 Zone은 **애니메이션 효과**로 표시됨

---

## 📚 다음 단계

1. ✅ 수동 모드로 실습
2. ✅ 시스템 기능 파악
3. ✅ 모델 성능 테스트
4. 📏 캘리브레이션 수행
5. 🚗 자동 모드로 전환
6. 🏭 실제 검사 진행

---

## 📞 참고 문서

- [QUICK_START.md](QUICK_START.md) - 빠른 시작 가이드
- [INSPECTION_SYSTEM_README.md](INSPECTION_SYSTEM_README.md) - 전체 시스템 매뉴얼
- [anomaly_detection/ANOMALY_DETECTION_GUIDE.md](anomaly_detection/ANOMALY_DETECTION_GUIDE.md) - Anomaly Detection 구현 가이드

---

**Happy Manual Inspecting! 🖐️💨**

손으로 밀면서 즐겁게 실습하세요!
