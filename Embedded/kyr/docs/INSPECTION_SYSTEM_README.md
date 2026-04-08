# Orin Car Inspection System

180cm 보드를 30cm씩 나눠서 순차적으로 탐지하는 오린카 검사 시스템입니다.

## 📋 목차

- [시스템 개요](#시스템-개요)
- [설치 방법](#설치-방법)
- [사용 방법](#사용-방법)
- [시스템 구성](#시스템-구성)
- [캘리브레이션](#캘리브레이션)
- [API 문서](#api-문서)
- [문제 해결](#문제-해결)

---

## 🎯 시스템 개요

### 검사 방식

- **총 길이**: 180cm 보드
- **영역 수**: 6개 영역 (각 30cm)
- **탐지 방식**: 2단계 하이브리드 (YOLO + Anomaly Detection)

### 6개 영역 구성

| Zone | Type | 설명 |
|------|------|------|
| Zone 0 | Normal | 정상 (결함 없음) |
| Zone 1 | Normal | 정상 (결함 없음) |
| Zone 2 | Anomaly | 이상 탐지 (Autoencoder) |
| Zone 3 | Defect | 결함 탐지 (YOLO) |
| Zone 4 | Defect | 결함 탐지 (YOLO) |
| Zone 5 | Defect | 결함 탐지 (YOLO) |

### 동작 프로세스

```
시작 → Zone 0 촬영 & 탐지 → 30cm 주행 →
       Zone 1 촬영 & 탐지 → 30cm 주행 →
       Zone 2 촬영 & 탐지 → 30cm 주행 →
       Zone 3 촬영 & 탐지 → 30cm 주행 →
       Zone 4 촬영 & 탐지 → 30cm 주행 →
       Zone 5 촬영 & 탐지 → 완료
```

---

## 📦 설치 방법

### 1. 필수 패키지 설치

```bash
# 기본 패키지
sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv

# Python 패키지
pip3 install flask ultralytics torch torchvision numpy
pip3 install adafruit-circuitpython-pca9685
```

### 2. 파일 구조 확인

```
Embedded/kyr/
├── orincar_inspection_system.py     # 메인 시스템
├── best_fixed.pt                    # YOLO 모델
├── best_fixed.engine                # (Optional) TensorRT 엔진
├── anomaly_detection/
│   └── best_model.pt                # Anomaly Detection 모델
├── inspection_results/              # 결과 저장 디렉토리 (자동 생성)
└── INSPECTION_SYSTEM_README.md      # 이 문서
```

### 3. 카메라 확인

```bash
# 카메라 장치 확인
ls -l /dev/video*

# 카메라 테스트
v4l2-ctl --list-devices
```

### 4. 모터 하드웨어 확인

```bash
# I2C 장치 확인
sudo i2cdetect -y -r 1

# PCA9685가 0x40 주소에 있어야 함
```

---

## 🚀 사용 방법

### 1. 서버 실행

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr
python3 orincar_inspection_system.py
```

서버가 실행되면 다음과 같은 메시지가 표시됩니다:

```
======================================================================
  Orin Car Inspection System - Flask Server
======================================================================
  180cm Board Defect Detection
  - 6 zones (30cm each)
  - 2-stage hybrid detection (YOLO + Anomaly)
======================================================================
  Access URL: http://<Jetson IP>:5002
  Example: http://192.168.0.100:5002
======================================================================
```

### 2. 웹 UI 접속

브라우저에서 `http://<Jetson IP>:5002` 로 접속합니다.

예: `http://192.168.0.100:5002`

### 3. 검사 시작

1. 웹 UI에서 **"▶️ Start Inspection"** 버튼 클릭
2. 오린카가 자동으로 6개 영역을 순차 검사
3. 실시간으로 진행 상황 확인
4. 검사 완료 후 결과 확인

### 4. 결과 확인

검사 완료 후 `inspection_results/` 폴더에 다음 파일들이 생성됩니다:

- `inspection_results_<timestamp>.json` - 검사 결과 JSON
- `zone_0_normal_<timestamp>.jpg` - Zone 0 이미지
- `zone_1_normal_<timestamp>.jpg` - Zone 1 이미지
- `zone_2_anomaly_<timestamp>.jpg` - Zone 2 이미지
- `zone_3_defect_<timestamp>.jpg` - Zone 3 이미지
- `zone_4_defect_<timestamp>.jpg` - Zone 4 이미지
- `zone_5_defect_<timestamp>.jpg` - Zone 5 이미지

---

## 🔧 시스템 구성

### 주요 클래스

#### 1. InspectionConfig

검사 시스템 설정 클래스

```python
config = InspectionConfig(
    total_length_cm=180,           # 총 길이
    zone_length_cm=30,             # 영역 길이
    motor_output=50,               # 모터 출력 (0-100%)
    speed_cm_per_sec=30.0,         # 속도 (cm/s) - 캘리브레이션 후 변경
    yolo_conf_threshold=0.5,       # YOLO 신뢰도 임계값
    anomaly_threshold=0.7,         # Anomaly 임계값
    zone_types=['normal', 'normal', 'anomaly', 'defect', 'defect', 'defect']
)
```

#### 2. MotorController

모터 제어 클래스

- `move_forward(output, duration_sec)`: 전진 이동
- `stop()`: 정지
- `cleanup()`: 정리

#### 3. CameraController

카메라 제어 클래스

- `capture_frame()`: 프레임 캡처
- `save_image(frame, filepath)`: 이미지 저장
- `release()`: 카메라 해제

#### 4. YOLODetector

YOLO 결함 탐지 클래스

- `detect(frame)`: 결함 탐지
- Returns: (detections, inference_time_ms, is_defective)

#### 5. AnomalyDetector

Autoencoder 기반 이상 탐지 클래스

- `detect(frame)`: 이상 탐지
- Returns: (detections, inference_time_ms, is_anomaly)

#### 6. InspectionSystem

메인 검사 시스템 클래스

- `start_inspection()`: 검사 시작
- `stop_inspection()`: 검사 중지
- `save_results()`: 결과 저장
- `cleanup()`: 정리

---

## 📏 캘리브레이션

### ⚠️ 중요: 속도 캘리브레이션 필수

현재 코드에서 **속도는 임시값(30 cm/s)**으로 설정되어 있습니다.
정확한 검사를 위해 **반드시 캘리브레이션을 수행**해야 합니다!

### 캘리브레이션 방법

#### 1. 캘리브레이션 서버 실행

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/calibration
python3 calibration.py
```

#### 2. 웹 UI 접속

`http://<Jetson IP>:5001` 접속

#### 3. 속도 측정

1. 모터 출력(예: 50%) 입력
2. 주행 시간(예: 2초) 입력
3. **"주행 시작!"** 클릭
4. 오린카가 이동한 거리를 자로 측정
5. 측정한 거리(cm) 입력
6. **"결과 저장"** 클릭

#### 4. 여러 출력값으로 반복 테스트

다양한 출력값(30%, 40%, 50%, 60%, 70%)으로 테스트하여
가장 안정적인 출력과 속도를 찾습니다.

#### 5. 결과 확인

`calibration_data.json` 파일에 결과가 저장됩니다:

```json
[
  {
    "pwm": "50",
    "time": "2",
    "distance": "60",
    "speed": "30.00"
  }
]
```

#### 6. 시스템에 적용

측정된 속도를 `orincar_inspection_system.py`에 적용합니다:

```python
# orincar_inspection_system.py 파일 수정
@dataclass
class InspectionConfig:
    motor_output: int = 50  # 캘리브레이션에서 선택한 출력값
    speed_cm_per_sec: float = 30.0  # 측정된 실제 속도로 변경!
```

### 예시

캘리브레이션 결과: 출력 50%, 2초 동안 65cm 이동

→ 속도 = 65 / 2 = **32.5 cm/s**

→ 30cm 이동 시간 = 30 / 32.5 = **0.92초**

```python
@dataclass
class InspectionConfig:
    motor_output: int = 50           # 출력 50%
    speed_cm_per_sec: float = 32.5   # 측정된 속도
    # move_duration_sec = 30 / 32.5 = 0.92초 (자동 계산)
```

---

## 📡 API 문서

### 1. POST /api/start

검사 시작

**Request:**
```bash
curl -X POST http://192.168.0.100:5002/api/start
```

**Response:**
```json
{
  "success": true,
  "message": "Inspection started successfully"
}
```

---

### 2. POST /api/stop

검사 중지

**Request:**
```bash
curl -X POST http://192.168.0.100:5002/api/stop
```

**Response:**
```json
{
  "success": true,
  "message": "Inspection stopped"
}
```

---

### 3. GET /api/status

검사 상태 조회

**Request:**
```bash
curl http://192.168.0.100:5002/api/status
```

**Response:**
```json
{
  "is_running": true,
  "current_zone": 2,
  "total_zones": 6,
  "completed_zones": 2,
  "defective_zones": 0,
  "zone_types": ["normal", "normal", "anomaly", "defect", "defect", "defect"]
}
```

---

### 4. GET /api/results

검사 결과 조회

**Request:**
```bash
curl http://192.168.0.100:5002/api/results
```

**Response:**
```json
{
  "results": [
    {
      "zone_id": 0,
      "zone_type": "normal",
      "timestamp": "2026-01-27T14:30:00",
      "detections": [],
      "image_path": "inspection_results/zone_0_normal_1738000000.jpg",
      "inference_time_ms": 0.0,
      "is_defective": false
    },
    {
      "zone_id": 3,
      "zone_type": "defect",
      "timestamp": "2026-01-27T14:31:00",
      "detections": [
        {
          "class_id": 2,
          "class_name": "crack",
          "confidence": 0.89,
          "bbox": [120, 150, 200, 250]
        }
      ],
      "image_path": "inspection_results/zone_3_defect_1738000060.jpg",
      "inference_time_ms": 45.2,
      "is_defective": true
    }
  ]
}
```

---

### 5. GET /health

헬스 체크

**Request:**
```bash
curl http://192.168.0.100:5002/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "orincar-inspection-system"
}
```

---

## 🔍 문제 해결

### 1. 카메라가 인식되지 않을 때

```bash
# 카메라 장치 확인
ls -l /dev/video*

# 권한 문제 해결
sudo chmod 666 /dev/video0

# 카메라 재연결
# USB 케이블을 다시 꽂아보세요
```

### 2. 모터가 작동하지 않을 때

```bash
# I2C 확인
sudo i2cdetect -y -r 1

# PCA9685가 0x40에 있는지 확인
# 없으면 하드웨어 연결 확인
```

### 3. YOLO 모델 로딩 실패

```bash
# 모델 파일 확인
ls -lh best_fixed.pt

# 파일이 없으면 다운로드
# 파일이 손상되었으면 다시 다운로드
```

### 4. Anomaly Detection 모델 로딩 실패

```bash
# 모델 파일 확인
ls -lh anomaly_detection/best_model.pt

# 파일이 없으면 학습된 모델 복사
```

### 5. 속도가 부정확할 때

**반드시 캘리브레이션을 수행하세요!**

1. `calibration/calibration.py` 실행
2. 여러 출력값으로 테스트
3. 안정적인 속도 측정
4. `orincar_inspection_system.py`에 적용

### 6. 영역 타입 변경하고 싶을 때

`orincar_inspection_system.py` 파일에서 수정:

```python
@dataclass
class InspectionConfig:
    zone_types: List[str] = None

    def __post_init__(self):
        if self.zone_types is None:
            self.zone_types = [
                'defect',   # Zone 0 - 변경 가능
                'defect',   # Zone 1 - 변경 가능
                'anomaly',  # Zone 2 - 변경 가능
                'defect',   # Zone 3 - 변경 가능
                'normal',   # Zone 4 - 변경 가능
                'normal'    # Zone 5 - 변경 가능
            ]
```

가능한 타입: `'normal'`, `'anomaly'`, `'defect'`

---

## 📊 결과 JSON 구조

```json
{
  "config": {
    "total_length_cm": 180,
    "zone_length_cm": 30,
    "motor_output": 50,
    "speed_cm_per_sec": 30.0,
    "yolo_conf_threshold": 0.5,
    "anomaly_threshold": 0.7,
    "zone_types": ["normal", "normal", "anomaly", "defect", "defect", "defect"]
  },
  "timestamp": "2026-01-27T14:30:00",
  "results": [
    {
      "zone_id": 0,
      "zone_type": "normal",
      "timestamp": "2026-01-27T14:30:00",
      "detections": [],
      "image_path": "inspection_results/zone_0_normal_1738000000.jpg",
      "inference_time_ms": 0.0,
      "is_defective": false
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

## 🎨 웹 UI 기능

### 메인 화면

- **Start Inspection**: 검사 시작
- **Stop**: 검사 중지
- **Refresh**: 상태 새로고침 (자동 갱신됨)

### 진행 상황

- 6개 영역 카드 표시
- 현재 검사 중인 영역 강조 (애니메이션)
- 완료된 영역은 ✅ 표시
- 대기 중인 영역은 ⏳ 표시

### 요약 통계

- Total Zones: 총 영역 수
- Completed: 완료된 영역 수
- Defective: 결함이 발견된 영역 수

---

## 🔄 다중 서버 구성

이 시스템은 다른 Flask 서버들과 함께 실행할 수 있습니다:

| 서버 | 포트 | 용도 |
|------|------|------|
| flask_detection_server.py | 5000 | 실시간 YOLO 탐지 스트리밍 |
| calibration.py | 5001 | 모터 속도 캘리브레이션 |
| **orincar_inspection_system.py** | **5002** | **통합 검사 시스템** |

모든 서버를 동시에 실행할 수 있습니다 (포트가 다르므로).

---

## 📝 TODO

- [ ] **캘리브레이션 수행** - 실제 속도 측정 필수!
- [ ] Anomaly Detection 모델 추론 로직 구현 완성
- [ ] 이미지 전처리 로직 추가 (리사이즈, 정규화 등)
- [ ] 결과 이미지에 BBox 그리기 (탐지된 객체 시각화)
- [ ] 로그 파일 저장 기능 추가
- [ ] 에러 복구 로직 강화

---

## 💡 팁

1. **캘리브레이션은 필수입니다!**
   임시 속도값(30 cm/s)으로는 정확한 위치에 멈추지 않습니다.

2. **안정적인 출력값 선택**
   너무 낮으면 느리고, 너무 높으면 정확도가 떨어집니다.
   보통 40-60% 사이가 적당합니다.

3. **카메라 위치 조정**
   30cm 영역이 정확히 프레임에 들어오도록 카메라 높이와 각도를 조정하세요.

4. **조명 확인**
   어두우면 탐지 정확도가 떨어집니다. 충분한 조명을 확보하세요.

5. **바닥 상태 확인**
   바닥이 미끄러우면 속도가 달라질 수 있습니다.
   실제 검사 환경에서 캘리브레이션하세요.

---

## 📞 지원

문제가 발생하거나 질문이 있으면 개발팀에 문의하세요.

---

**Happy Inspecting! 🚗💨**
