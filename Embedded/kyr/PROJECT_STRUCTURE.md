# 📁 Project Structure

Orin Car Inspection System의 폴더 구조 및 파일 설명입니다.

---

## 🌳 폴더 트리

```
kyr/
├── 📖 README.md                                # 프로젝트 메인 README
├── 📁 PROJECT_STRUCTURE.md                     # 이 파일 (폴더 구조 설명)
│
├── 🚗 inspection/                              # 검사 시스템 메인 폴더
│   ├── orincar_inspection_system.py           # 자동 검사 시스템 (모터 제어)
│   ├── orincar_inspection_manual.py           # 수동 검사 시스템 (손으로 실습)
│   ├── run_inspection.sh                      # 자동 모드 실행 스크립트
│   ├── run_manual_inspection.sh               # 수동 모드 실행 스크립트
│   └── config.json                            # 검사 시스템 설정 파일
│
├── 🤖 models/                                  # AI 모델 폴더
│   ├── yolo/                                  # YOLO 결함 탐지 모델
│   │   ├── best_fixed.pt                      # PyTorch 모델
│   │   ├── best_fixed.engine                  # TensorRT 엔진 (최적화)
│   │   ├── best_fixed.onnx                    # ONNX 모델
│   │   └── best_fixed.torchscript             # TorchScript 모델
│   │
│   └── anomaly_detection/                     # Anomaly Detection 모델
│       ├── best_model.pt                      # Autoencoder 모델
│       └── ANOMALY_DETECTION_GUIDE.md         # 구현 가이드
│
├── 📖 docs/                                    # 문서 폴더
│   ├── QUICK_START.md                         # 빠른 시작 가이드 ⭐
│   ├── MANUAL_MODE_GUIDE.md                   # 수동 모드 가이드
│   ├── INSPECTION_SYSTEM_README.md            # 자동 모드 상세 매뉴얼
│   ├── README_INSPECTION.md                   # 간단 요약
│   └── detection_pipeline.md                  # AI 탐지 파이프라인 설명
│
├── 🛠️ utils/                                   # 유틸리티 도구
│   ├── flask_detection_server.py              # 실시간 YOLO 탐지 웹 서버
│   ├── convert_to_tensorrt.py                 # PyTorch → TensorRT 변환
│   └── gpu_exporter.py                        # GPU 메트릭 Exporter (Prometheus)
│
├── 📏 calibration/                             # 캘리브레이션 도구
│   ├── calibration.py                         # 모터 속도 캘리브레이션
│   └── calibration_steering.py                # 조향 캘리브레이션
│
├── ⚡ benchmark/                               # 벤치마크 도구
│   └── pytorch_vs_tensorrt.py                 # PyTorch vs TensorRT 성능 비교
│
├── 📊 monitoring/                              # 모니터링 시스템
│   ├── docker-compose.yml                     # Grafana + Prometheus 구성
│   ├── prometheus.yml                         # Prometheus 설정
│   └── grafana/                               # Grafana 대시보드 및 설정
│       ├── dashboards/                        # 대시보드 JSON 파일
│       └── provisioning/                      # Provisioning 설정
│
├── 🎨 templates/                               # Flask 템플릿
│   └── index.html                             # 웹 UI HTML 템플릿
│
└── 📁 inspection_results/                      # 검사 결과 저장 (자동 생성)
    ├── inspection_results_<timestamp>.json    # 검사 결과 JSON
    ├── manual_inspection_<timestamp>.json     # 수동 검사 결과 JSON
    └── zone_*.jpg                             # Zone별 촬영 이미지
```

---

## 📂 폴더별 상세 설명

### 🚗 inspection/ - 검사 시스템 메인

검사 시스템의 핵심 코드가 위치한 폴더입니다.

| 파일 | 포트 | 설명 |
|------|------|------|
| **orincar_inspection_system.py** | 5002 | 자동 검사 시스템 (모터 자동 제어) |
| **orincar_inspection_manual.py** | 5003 | 수동 검사 시스템 (손으로 밀면서 실습) |
| run_inspection.sh | - | 자동 모드 실행 스크립트 |
| run_manual_inspection.sh | - | 수동 모드 실행 스크립트 |
| config.json | - | 검사 설정 (참고용) |

#### 실행 방법

```bash
# 자동 모드 (모터 제어)
cd inspection
./run_inspection.sh

# 수동 모드 (손으로 실습) - 추천!
cd inspection
./run_manual_inspection.sh
```

---

### 🤖 models/ - AI 모델

YOLO 결함 탐지 및 Anomaly Detection 모델이 저장된 폴더입니다.

#### models/yolo/

YOLO 모델의 여러 포맷이 저장되어 있습니다.

| 파일 | 포맷 | 용도 |
|------|------|------|
| best_fixed.pt | PyTorch | 기본 모델 (개발/테스트) |
| best_fixed.engine | TensorRT | 최적화 모델 (프로덕션) ⭐ |
| best_fixed.onnx | ONNX | 범용 포맷 |
| best_fixed.torchscript | TorchScript | PyTorch 최적화 |

**우선순위**: `.engine` > `.pt` > `.onnx`

시스템은 TensorRT 엔진을 우선 사용하며, 없을 경우 PyTorch 모델을 사용합니다.

#### models/anomaly_detection/

Autoencoder 기반 이상 탐지 모델입니다.

| 파일 | 설명 |
|------|------|
| best_model.pt | Autoencoder 모델 |
| ANOMALY_DETECTION_GUIDE.md | 구현 가이드 📖 |

**주의**: 현재 코드에서 Anomaly Detection은 placeholder로 구현되어 있습니다.
실제 추론 로직은 가이드를 참고하여 구현해야 합니다.

---

### 📖 docs/ - 문서

모든 문서가 한 곳에 모여 있습니다.

| 문서 | 내용 | 추천 |
|------|------|------|
| **QUICK_START.md** | 빠른 시작 가이드 | ⭐⭐⭐ 여기부터! |
| **MANUAL_MODE_GUIDE.md** | 수동 모드 상세 설명 | ⭐⭐ 실습용 |
| INSPECTION_SYSTEM_README.md | 자동 모드 전체 매뉴얼 | ⭐⭐ 실제 검사용 |
| README_INSPECTION.md | 간단 요약 | ⭐ 빠른 참조 |
| detection_pipeline.md | AI 탐지 파이프라인 설명 | 참고 |

#### 읽는 순서

1. **[QUICK_START.md](docs/QUICK_START.md)** - 전체 개요 및 빠른 시작
2. **[MANUAL_MODE_GUIDE.md](docs/MANUAL_MODE_GUIDE.md)** - 손으로 실습하기
3. **[INSPECTION_SYSTEM_README.md](docs/INSPECTION_SYSTEM_README.md)** - 자동 모드 사용법

---

### 🛠️ utils/ - 유틸리티 도구

검사 시스템 외 보조 도구들입니다.

| 도구 | 포트 | 용도 |
|------|------|------|
| flask_detection_server.py | 5000 | 실시간 YOLO 탐지 스트리밍 웹 서버 |
| convert_to_tensorrt.py | - | PyTorch 모델을 TensorRT로 변환 |
| gpu_exporter.py | 9101 | GPU 메트릭을 Prometheus로 Export |

#### 실행 예시

```bash
# 실시간 탐지 웹 서버
cd utils
python3 flask_detection_server.py
# http://<IP>:5000 접속

# TensorRT 변환
cd utils
python3 convert_to_tensorrt.py

# GPU 모니터링
cd utils
python3 gpu_exporter.py
```

---

### 📏 calibration/ - 캘리브레이션

모터 속도 및 조향 캘리브레이션 도구입니다.

| 도구 | 포트 | 용도 |
|------|------|------|
| calibration.py | 5001 | 모터 속도 측정 및 캘리브레이션 |
| calibration_steering.py | - | 조향 캘리브레이션 |

#### 사용법

```bash
cd calibration
python3 calibration.py
# http://<IP>:5001 접속
```

**자동 모드 사용 전 필수!**

---

### ⚡ benchmark/ - 벤치마크

모델 성능 비교 도구입니다.

| 도구 | 용도 |
|------|------|
| pytorch_vs_tensorrt.py | PyTorch vs TensorRT 추론 속도 비교 |

#### 실행

```bash
cd benchmark
python3 pytorch_vs_tensorrt.py
```

---

### 📊 monitoring/ - 모니터링

Grafana + Prometheus 기반 모니터링 시스템입니다.

| 파일/폴더 | 설명 |
|-----------|------|
| docker-compose.yml | Grafana + Prometheus Docker 구성 |
| prometheus.yml | Prometheus 설정 (타겟, 스크래핑 간격 등) |
| grafana/dashboards/ | Grafana 대시보드 JSON |
| grafana/provisioning/ | Datasource 및 Dashboard Provisioning |

#### 실행

```bash
cd monitoring
docker-compose up -d

# Grafana: http://<IP>:3000
# Prometheus: http://<IP>:9090
```

---

### 🎨 templates/ - Flask 템플릿

Flask 웹 서버의 HTML 템플릿입니다.

| 파일 | 용도 |
|------|------|
| index.html | 실시간 탐지 웹 UI (flask_detection_server.py용) |

---

### 📁 inspection_results/ - 결과 저장

검사 결과가 자동으로 저장되는 폴더입니다. (자동 생성됨)

```
inspection_results/
├── inspection_results_1738000000.json      # 자동 모드 결과
├── manual_inspection_1738000000.json       # 수동 모드 결과
├── zone_0_normal_1738000000.jpg           # Zone 0 이미지
├── zone_1_normal_1738000001.jpg           # Zone 1 이미지
├── zone_2_anomaly_1738000002.jpg          # Zone 2 이미지
├── zone_3_defect_1738000003.jpg           # Zone 3 이미지
├── zone_4_defect_1738000004.jpg           # Zone 4 이미지
└── zone_5_defect_1738000005.jpg           # Zone 5 이미지
```

---

## 🚀 빠른 시작 (폴더별)

### 1️⃣ 수동 모드로 실습 (추천!)

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/inspection
./run_manual_inspection.sh
```

웹 브라우저: `http://<IP>:5003`

### 2️⃣ 자동 모드로 검사

**먼저 캘리브레이션:**

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/calibration
python3 calibration.py
# http://<IP>:5001 접속
```

**속도 측정 후 자동 모드 실행:**

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/inspection
# orincar_inspection_system.py에서 speed_cm_per_sec 수정 후
./run_inspection.sh
```

웹 브라우저: `http://<IP>:5002`

### 3️⃣ 실시간 탐지 테스트

```bash
cd /home/ssafy/S14P11E201/Embedded/kyr/utils
python3 flask_detection_server.py
```

웹 브라우저: `http://<IP>:5000`

---

## 🌐 포트 맵

| 서비스 | 포트 | 폴더 | 파일 |
|--------|------|------|------|
| 실시간 탐지 | 5000 | utils/ | flask_detection_server.py |
| 캘리브레이션 | 5001 | calibration/ | calibration.py |
| 자동 검사 | 5002 | inspection/ | orincar_inspection_system.py |
| **수동 검사** | **5003** | **inspection/** | **orincar_inspection_manual.py** ⭐ |
| Grafana | 3000 | monitoring/ | docker-compose.yml |
| Prometheus | 9090 | monitoring/ | docker-compose.yml |
| GPU Exporter | 9101 | utils/ | gpu_exporter.py |

---

## 📝 파일 참조 규칙

폴더가 분리되어 있으므로, 코드에서 다른 폴더의 파일을 참조할 때 상대 경로를 사용합니다.

### inspection/ 폴더에서 참조

```python
# inspection/orincar_inspection_system.py

# 모델 파일 참조
yolo_model = '../models/yolo/best_fixed.pt'
anomaly_model = '../models/anomaly_detection/best_model.pt'

# 결과 저장
output_dir = '../inspection_results'
```

### utils/ 폴더에서 참조

```python
# utils/flask_detection_server.py

# 모델 파일 참조
model_path = '../models/yolo/best_fixed.pt'
```

---

## 🔄 폴더 구조 변경 이력

### 2026-01-27: 대규모 정리

#### 변경 전 (지저분)

```
kyr/
├── orincar_inspection_system.py
├── orincar_inspection_manual.py
├── best_fixed.pt
├── best_fixed.engine
├── anomaly_detection/
├── QUICK_START.md
├── flask_detection_server.py
└── ... (많은 파일들이 루트에 혼재)
```

#### 변경 후 (깔끔!)

```
kyr/
├── inspection/          # 검사 시스템
├── models/             # AI 모델
├── docs/               # 문서
├── utils/              # 유틸리티
├── calibration/        # 캘리브레이션
├── benchmark/          # 벤치마크
├── monitoring/         # 모니터링
└── templates/          # Flask 템플릿
```

#### 주요 변경사항

- ✅ 기능별로 폴더 분리
- ✅ 모델 파일 통합 관리
- ✅ 문서 한 곳에 모음
- ✅ 코드 내 경로 자동 수정
- ✅ 실행 스크립트 업데이트

---

## 💡 팁

### 1. 폴더 이동 시

현재 폴더 구조에서 파일을 이동하려면:

```bash
# 검사 시스템은 inspection/ 폴더에서 실행
cd inspection

# 캘리브레이션은 calibration/ 폴더에서 실행
cd calibration

# 문서는 docs/ 폴더에서 확인
cd docs
```

### 2. 새 모델 추가 시

```bash
# YOLO 모델 추가
cp new_model.pt models/yolo/

# Anomaly 모델 추가
cp new_anomaly_model.pt models/anomaly_detection/
```

### 3. 결과 파일 찾기

```bash
# 결과는 항상 루트의 inspection_results/ 폴더에
ls -lh ../inspection_results/
```

---

## 📞 참고

- **메인 문서**: [docs/QUICK_START.md](docs/QUICK_START.md)
- **프로젝트 README**: [README.md](README.md)
- **폴더 구조**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) (이 파일)

---

**폴더가 깔끔해졌습니다! 🎉**
