# 🚗 Orin Car Inspection System

Jetson Orin Nano 기반의 180cm 보드 결함 검사 시스템입니다.

---

## 🎯 프로젝트 개요

### 핵심 기능

- **6개 Zone 순차 검사**: 180cm 보드를 30cm씩 나눠 검사
- **2단계 하이브리드 탐지**: YOLO (결함) + Anomaly Detection (이상)
- **2가지 모드**: 자동 모드 (모터 제어) + 수동 모드 (손으로 실습)
- **웹 UI**: 실시간 진행 상황 모니터링

### 시스템 구성

```
180cm Board
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ Zone 0  │ Zone 1  │ Zone 2  │ Zone 3  │ Zone 4  │ Zone 5  │
│ Normal  │ Normal  │ Anomaly │ Defect  │ Defect  │ Defect  │
│  30cm   │  30cm   │  30cm   │  30cm   │  30cm   │  30cm   │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

---

## 🚀 빠른 시작

### 🖐️ 수동 모드 (추천!)

**캘리브레이션 없이 바로 실습 가능!**

```bash
cd inspection
./run_manual_inspection.sh
```

웹 브라우저: `http://<Jetson IP>:5003`

📖 **상세 가이드**: [docs/MANUAL_MODE_GUIDE.md](docs/MANUAL_MODE_GUIDE.md)

---

### 🚗 자동 모드

**실제 검사용 (캘리브레이션 필요)**

1. **캘리브레이션**:
   ```bash
   cd calibration
   python3 calibration.py
   # http://<IP>:5001 접속하여 속도 측정
   ```

2. **속도 적용**:
   ```python
   # inspection/orincar_inspection_system.py에서
   speed_cm_per_sec: float = 30.0  # 측정값으로 변경
   ```

3. **검사 시작**:
   ```bash
   cd inspection
   ./run_inspection.sh
   # http://<IP>:5002 접속
   ```

📖 **상세 가이드**: [docs/INSPECTION_SYSTEM_README.md](docs/INSPECTION_SYSTEM_README.md)

---

## 📁 프로젝트 구조

```
kyr/
├── 🚗 inspection/              # 검사 시스템 메인
│   ├── orincar_inspection_system.py    (자동 모드)
│   └── orincar_inspection_manual.py    (수동 모드)
│
├── 🤖 models/                  # AI 모델
│   ├── yolo/                  (결함 탐지)
│   └── anomaly_detection/     (이상 탐지)
│
├── 📖 docs/                    # 문서
│   ├── QUICK_START.md         (빠른 시작) ⭐
│   ├── MANUAL_MODE_GUIDE.md   (수동 모드 가이드)
│   └── INSPECTION_SYSTEM_README.md  (자동 모드 매뉴얼)
│
├── 🛠️ utils/                   # 유틸리티
│   ├── flask_detection_server.py  (실시간 탐지)
│   └── convert_to_tensorrt.py     (모델 변환)
│
├── 📏 calibration/             # 캘리브레이션
├── ⚡ benchmark/               # 성능 벤치마크
├── 📊 monitoring/              # Grafana + Prometheus
└── 📁 inspection_results/      # 결과 저장 (자동 생성)
```

📖 **전체 구조 보기**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## 🌐 서비스 포트

| 서비스 | 포트 | 폴더 | 용도 |
|--------|------|------|------|
| 실시간 탐지 | 5000 | utils/ | YOLO 스트리밍 |
| 캘리브레이션 | 5001 | calibration/ | 모터 속도 측정 |
| 자동 검사 | 5002 | inspection/ | 자동 모드 |
| **수동 검사** | **5003** | **inspection/** | **수동 모드 ⭐** |

---

## 📚 문서

| 문서 | 내용 | 추천 |
|------|------|------|
| **[docs/QUICK_START.md](docs/QUICK_START.md)** | ⚡ 빠른 시작 가이드 | ⭐⭐⭐ |
| **[docs/MANUAL_MODE_GUIDE.md](docs/MANUAL_MODE_GUIDE.md)** | 🖐️ 수동 모드 상세 | ⭐⭐ |
| [docs/INSPECTION_SYSTEM_README.md](docs/INSPECTION_SYSTEM_README.md) | 🚗 자동 모드 매뉴얼 | ⭐⭐ |
| [docs/README_INSPECTION.md](docs/README_INSPECTION.md) | 📄 간단 요약 | ⭐ |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 📁 폴더 구조 설명 | 참고 |
| [models/anomaly_detection/ANOMALY_DETECTION_GUIDE.md](models/anomaly_detection/ANOMALY_DETECTION_GUIDE.md) | 🔍 Anomaly 구현 가이드 | 개발자용 |

---

## 🆚 모드 비교

| 항목 | 🖐️ 수동 모드 | 🚗 자동 모드 |
|------|------------|------------|
| **포트** | 5003 | 5002 |
| **모터** | ❌ 불필요 | ✅ 필수 |
| **캘리브레이션** | ❌ 불필요 | ✅ 필수 |
| **이동** | 손으로 30cm씩 | 자동 주행 |
| **용도** | 실습, 테스트 | 실제 검사 |
| **추천** | 처음 사용자 | 캘리브레이션 완료 후 |

---

## 💡 주요 기능

### 1. 2단계 하이브리드 탐지

#### YOLO (결함 탐지)
- 5개 핵심 결함 클래스 탐지
- `sagging`, `crack`, `blister`, `welding_damage`, `peeling`

#### Anomaly Detection (이상 탐지)
- Autoencoder 기반
- 미세 결함 및 미학습 이상 탐지
- `foreign_material`, `pinhole`, `scratch` 등

### 2. Zone별 맞춤 탐지

- **Normal Zone**: 탐지 생략 (정상 구간)
- **Anomaly Zone**: Autoencoder 이상 탐지
- **Defect Zone**: YOLO 결함 탐지

### 3. 웹 UI

- 실시간 진행 상황 표시
- Zone별 상태 확인
- 탐지 결과 즉시 확인
- 통계 및 요약

---

## 🛠️ 추가 도구

### 실시간 탐지 서버

```bash
cd utils
python3 flask_detection_server.py
# http://<IP>:5000
```

### 모니터링 시스템

```bash
cd monitoring
docker-compose up -d
# Grafana: http://<IP>:3000
# Prometheus: http://<IP>:9090
```

### 성능 벤치마크

```bash
cd benchmark
python3 pytorch_vs_tensorrt.py
```

---

## 📊 검사 결과

결과는 `inspection_results/` 폴더에 자동 저장됩니다.

```
inspection_results/
├── inspection_results_<timestamp>.json    # 검사 결과
├── manual_inspection_<timestamp>.json     # 수동 모드 결과
└── zone_*.jpg                            # Zone별 이미지
```

### JSON 결과 예시

```json
{
  "timestamp": "2026-01-27T15:30:00",
  "results": [
    {
      "zone_id": 3,
      "zone_type": "defect",
      "is_defective": true,
      "detections": [
        {
          "class_name": "crack",
          "confidence": 0.89
        }
      ]
    }
  ],
  "summary": {
    "total_zones": 6,
    "defective_zones": 2
  }
}
```

---

## ⚙️ 시스템 요구사항

### 하드웨어

- **SBC**: Jetson Orin Nano
- **카메라**: USB 웹캠 (예: Logitech Brio 100)
- **모터**: PCA9685 기반 PWM 제어 (자동 모드만)

### 소프트웨어

```bash
# 필수 패키지
sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv

# Python 패키지
pip3 install flask ultralytics torch torchvision numpy
pip3 install adafruit-circuitpython-pca9685  # 자동 모드만
```

---

## 🎓 학습 경로

### 초보자

1. **[docs/QUICK_START.md](docs/QUICK_START.md)** 읽기
2. **수동 모드**로 실습 (포트 5003)
3. 시스템 동작 이해

### 중급자

1. 캘리브레이션 수행
2. **자동 모드** 사용 (포트 5002)
3. 실제 검사 진행

### 고급자

1. Anomaly Detection 구현
   - [models/anomaly_detection/ANOMALY_DETECTION_GUIDE.md](models/anomaly_detection/ANOMALY_DETECTION_GUIDE.md) 참고
2. TensorRT 최적화
3. 커스터마이징

---

## ❓ FAQ

### Q1. 캘리브레이션 없이 사용할 수 있나요?

**A**: 네! **수동 모드**를 사용하세요. 손으로 오린카를 밀면서 실습할 수 있습니다.

### Q2. 모터가 작동하지 않아요.

**A**: 수동 모드를 사용하거나, PCA9685 연결을 확인하세요 (`sudo i2cdetect -y -r 1`).

### Q3. 카메라가 인식되지 않아요.

**A**: `sudo chmod 666 /dev/video0` 실행 후 USB 재연결하세요.

### Q4. Zone 타입을 변경하고 싶어요.

**A**: `inspection/orincar_inspection_system.py` 또는 `orincar_inspection_manual.py`에서 `zone_types` 배열을 수정하세요.

---

## 📞 지원

- **프로젝트 구조**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **빠른 시작**: [docs/QUICK_START.md](docs/QUICK_START.md)
- **수동 모드**: [docs/MANUAL_MODE_GUIDE.md](docs/MANUAL_MODE_GUIDE.md)
- **자동 모드**: [docs/INSPECTION_SYSTEM_README.md](docs/INSPECTION_SYSTEM_README.md)

---

## 🎉 시작하기

```bash
# 1. 프로젝트 폴더로 이동
cd /home/ssafy/S14P11E201/Embedded/kyr

# 2. 폴더 구조 확인
cat PROJECT_STRUCTURE.md

# 3. 빠른 시작 가이드 읽기
cat docs/QUICK_START.md

# 4. 수동 모드로 실습 시작!
cd inspection
./run_manual_inspection.sh
```

---

**Happy Inspecting! 🚗💨**

Made with ❤️ for Docktor Project
