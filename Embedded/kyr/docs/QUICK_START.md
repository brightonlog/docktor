# 🚀 Quick Start Guide

Orin Car Inspection System 빠른 시작 가이드입니다.

---

## 🖐️ 모터 없이 손으로 실습하기 (추천!)

**캘리브레이션이나 모터 제어 없이 바로 실습하고 싶다면?**

👉 **[수동 모드 (Manual Mode)](#-수동-모드-손으로-실습)** 를 사용하세요!

---

## ⚡ 2가지 모드

### 🖐️ 수동 모드 (Manual Mode) - 실습용

손으로 오린카를 밀면서 실습할 수 있습니다.

- ✅ **모터 불필요**
- ✅ **캘리브레이션 불필요**
- ✅ **바로 실습 가능**
- 📄 **파일**: `orincar_inspection_manual.py`
- 🌐 **포트**: 5003
- 📖 **가이드**: [MANUAL_MODE_GUIDE.md](MANUAL_MODE_GUIDE.md)

### 🚗 자동 모드 (Auto Mode) - 실제 검사용

모터가 자동으로 움직이며 검사합니다.

- ⚠️ **캘리브레이션 필수**
- ⚠️ **모터 제어 필수**
- 🎯 실제 검사에 사용
- 📄 **파일**: `orincar_inspection_system.py`
- 🌐 **포트**: 5002
- 📖 **가이드**: [INSPECTION_SYSTEM_README.md](INSPECTION_SYSTEM_README.md)

---

## 🖐️ 수동 모드 (손으로 실습)

### 1️⃣ 서버 실행

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr
./run_manual_inspection.sh
```

### 2️⃣ 웹 UI 접속

`http://<Jetson IP>:5003` 접속

### 3️⃣ 검사 진행

1. **"세션 시작"** 클릭
2. **"현재 Zone 촬영"** 클릭
3. 손으로 30cm 밀기
4. **"다음 Zone"** 클릭
5. 2~4 반복 (총 6회)

📖 **상세 가이드**: [MANUAL_MODE_GUIDE.md](MANUAL_MODE_GUIDE.md)

---

## 🚗 자동 모드 (실제 검사)

### 1️⃣ 캘리브레이션 (필수!)

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/calibration
python3 calibration.py
```

- 브라우저에서 `http://<Jetson IP>:5001` 접속
- 모터 출력 50%, 주행 시간 2초로 테스트
- 자로 이동 거리 측정 후 입력
- 속도(cm/s) 계산 후 저장

### 2️⃣ 속도 설정

측정된 속도를 [orincar_inspection_system.py](orincar_inspection_system.py:41) 에 입력:

```python
@dataclass
class InspectionConfig:
    motor_output: int = 50           # 캘리브레이션 출력값
    speed_cm_per_sec: float = 30.0   # 측정된 실제 속도로 변경!
```

### 3️⃣ 검사 시작

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr
./run_inspection.sh
```

또는

```bash
python3 orincar_inspection_system.py
```

- 브라우저에서 `http://<Jetson IP>:5002` 접속
- "▶️ Start Inspection" 버튼 클릭
- 완료될 때까지 대기 (약 6-8분)

---

## 📁 생성된 파일 목록

### 🖐️ 수동 모드 (Manual Mode)

| 파일 | 설명 | 포트 |
|------|------|------|
| [orincar_inspection_manual.py](orincar_inspection_manual.py) | 🖐️ **수동 검사 시스템 (손으로 실습)** | 5003 |
| [run_manual_inspection.sh](run_manual_inspection.sh) | 수동 모드 실행 스크립트 | - |
| [MANUAL_MODE_GUIDE.md](MANUAL_MODE_GUIDE.md) | 🖐️ **수동 모드 가이드** | - |

### 🚗 자동 모드 (Auto Mode)

| 파일 | 설명 | 포트 |
|------|------|------|
| [orincar_inspection_system.py](orincar_inspection_system.py) | 🚗 자동 검사 시스템 (모터 제어) | 5002 |
| [run_inspection.sh](run_inspection.sh) | 자동 모드 실행 스크립트 | - |
| [inspection_config.json](inspection_config.json) | 설정 파일 (참고용) | - |

### 📖 문서

| 파일 | 설명 |
|------|------|
| [QUICK_START.md](QUICK_START.md) | ⚡ **이 파일 (빠른 시작)** |
| [MANUAL_MODE_GUIDE.md](MANUAL_MODE_GUIDE.md) | 🖐️ **수동 모드 상세 가이드** |
| [INSPECTION_SYSTEM_README.md](INSPECTION_SYSTEM_README.md) | 📖 자동 모드 상세 매뉴얼 |
| [anomaly_detection/ANOMALY_DETECTION_GUIDE.md](anomaly_detection/ANOMALY_DETECTION_GUIDE.md) | 🔍 Anomaly Detection 구현 가이드 |

### ⚙️ 캘리브레이션 (자동 모드용)

| 파일 | 설명 | 포트 |
|------|------|------|
| [calibration/calibration.py](calibration/calibration.py) | 모터 속도 캘리브레이션 | 5001 |

---

## 🎯 시스템 개요

### 6개 영역 구성

```
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ Zone 0  │ Zone 1  │ Zone 2  │ Zone 3  │ Zone 4  │ Zone 5  │
│ Normal  │ Normal  │ Anomaly │ Defect  │ Defect  │ Defect  │
│  30cm   │  30cm   │  30cm   │  30cm   │  30cm   │  30cm   │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
           180cm Board
```

### 동작 방식

```
주행 → 멈춤 → 촬영 → 탐지 → 저장 → (다음 영역)
```

1. 오린카가 30cm 이동
2. 정지 후 카메라 촬영
3. Zone 타입에 따라 탐지:
   - **Normal**: 탐지 안 함 (정상)
   - **Anomaly**: Autoencoder 이상 탐지
   - **Defect**: YOLO 결함 탐지
4. 결과 저장 후 다음 영역으로 이동
5. 6개 영역 완료 시 종료

---

## 📊 결과 확인

검사 완료 후 `inspection_results/` 폴더에 생성:

```
inspection_results/
├── inspection_results_1738000000.json    # 검사 결과 JSON
├── zone_0_normal_1738000000.jpg          # Zone 0 이미지
├── zone_1_normal_1738000001.jpg          # Zone 1 이미지
├── zone_2_anomaly_1738000002.jpg         # Zone 2 이미지
├── zone_3_defect_1738000003.jpg          # Zone 3 이미지
├── zone_4_defect_1738000004.jpg          # Zone 4 이미지
└── zone_5_defect_1738000005.jpg          # Zone 5 이미지
```

---

## 🔧 커스터마이징

### Zone 타입 변경

[orincar_inspection_system.py](orincar_inspection_system.py:47) 에서 수정:

```python
zone_types = [
    'normal',   # Zone 0 - 변경 가능
    'anomaly',  # Zone 1 - 변경 가능
    'defect',   # Zone 2 - 변경 가능
    'defect',   # Zone 3 - 변경 가능
    'defect',   # Zone 4 - 변경 가능
    'normal'    # Zone 5 - 변경 가능
]
```

타입: `'normal'`, `'anomaly'`, `'defect'`

### Threshold 조정

```python
@dataclass
class InspectionConfig:
    yolo_conf_threshold: float = 0.5     # YOLO 신뢰도 (0.0-1.0)
    anomaly_threshold: float = 0.7       # Anomaly 임계값 (0.0-1.0)
```

---

## 🌐 웹 UI

### 메인 화면

- **Start Inspection**: 검사 시작
- **Stop**: 검사 중지
- **Refresh**: 상태 새로고침

### 진행 상황

- 6개 Zone 카드 표시
- 현재 검사 중인 Zone 애니메이션
- 완료된 Zone은 ✅ 표시

### 통계

- Total Zones: 6
- Completed: 완료된 Zone 수
- Defective: 결함 발견된 Zone 수

---

## 🔌 API 사용법

### 검사 시작

```bash
curl -X POST http://192.168.0.100:5002/api/start
```

### 검사 중지

```bash
curl -X POST http://192.168.0.100:5002/api/stop
```

### 상태 조회

```bash
curl http://192.168.0.100:5002/api/status
```

### 결과 조회

```bash
curl http://192.168.0.100:5002/api/results
```

---

## 🆚 모드 비교표

| 항목 | 🖐️ 수동 모드 | 🚗 자동 모드 |
|------|------------|------------|
| **파일** | orincar_inspection_manual.py | orincar_inspection_system.py |
| **포트** | 5003 | 5002 |
| **모터** | ❌ 불필요 | ✅ 필수 |
| **캘리브레이션** | ❌ 불필요 | ✅ 필수 |
| **이동 방식** | 손으로 직접 | 자동 주행 |
| **촬영 방식** | 버튼 클릭 | 자동 촬영 |
| **실행** | `./run_manual_inspection.sh` | `./run_inspection.sh` |
| **추천 용도** | 실습, 테스트, 데모 | 실제 검사 |
| **장점** | 바로 시작 가능 | 빠르고 정확 |
| **단점** | 손으로 밀어야 함 | 설정 필요 |

### 🎯 어떤 모드를 선택할까?

- **🖐️ 수동 모드**: 처음 시작, 모터 고장, 빠른 테스트
- **🚗 자동 모드**: 캘리브레이션 완료 후 실제 검사

---

## ⚠️ 주의사항

### 1. (자동 모드만 해당) 캘리브레이션은 필수!

임시 속도값(30 cm/s)으로는 정확한 위치에 멈추지 않습니다.
**반드시 실제 환경에서 속도를 측정**하세요!

### 2. Anomaly Detection 구현 필요

현재 Anomaly Detection은 **placeholder**로 구현되어 있습니다.
[anomaly_detection/ANOMALY_DETECTION_GUIDE.md](anomaly_detection/ANOMALY_DETECTION_GUIDE.md)를 참고하여 실제 추론 로직을 구현하세요.

### 3. 카메라 위치 조정

30cm 영역이 정확히 프레임에 들어오도록 카메라 높이와 각도를 조정하세요.

### 4. 조명 확인

어두우면 탐지 정확도가 떨어집니다. 충분한 조명을 확보하세요.

---

## 🆘 문제 해결

### 카메라가 안 열릴 때

```bash
sudo chmod 666 /dev/video0
# USB 재연결
```

### 모터가 안 움직일 때

```bash
sudo i2cdetect -y -r 1
# PCA9685가 0x40에 있는지 확인
```

### 모델 로딩 실패

```bash
ls -lh best_fixed.pt
ls -lh anomaly_detection/best_model.pt
# 파일 존재 및 크기 확인
```

---

## 📖 더 자세한 내용은?

**[INSPECTION_SYSTEM_README.md](INSPECTION_SYSTEM_README.md)** 를 참고하세요!

- 상세 설치 방법
- 시스템 구성 설명
- API 문서
- 문제 해결 가이드
- 팁 & 트릭

---

## 🎓 다음 단계

1. ✅ 캘리브레이션 완료
2. ✅ 속도 설정
3. ✅ 첫 검사 실행
4. 📝 Anomaly Detection 구현 ([가이드 보기](anomaly_detection/ANOMALY_DETECTION_GUIDE.md))
5. 🔧 Threshold 최적화
6. 🧪 실제 환경에서 테스트

---

**Happy Inspecting! 🚗💨**

문의사항이나 문제가 있으면 개발팀에 연락하세요.
