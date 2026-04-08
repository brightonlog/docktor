# Orin Car Inspection System

180cm 보드를 30cm씩 나눠서 6개 영역을 순차적으로 검사하는 시스템입니다.

---

## 🚀 빠른 실행

### 🖐️ 수동 모드 (손으로 실습 - 추천!)

```bash
./run_manual_inspection.sh
# http://<IP>:5003 접속
```

**캘리브레이션 불필요! 바로 실습 가능!**

### 🚗 자동 모드 (실제 검사)

```bash
./run_inspection.sh
# http://<IP>:5002 접속
```

**⚠️ 캘리브레이션 필수!**

---

## 📚 문서

| 문서 | 내용 |
|------|------|
| **[QUICK_START.md](QUICK_START.md)** | ⚡ 빠른 시작 가이드 (여기부터!) |
| **[MANUAL_MODE_GUIDE.md](MANUAL_MODE_GUIDE.md)** | 🖐️ 수동 모드 상세 가이드 |
| **[INSPECTION_SYSTEM_README.md](INSPECTION_SYSTEM_README.md)** | 📖 자동 모드 전체 매뉴얼 |
| **[anomaly_detection/ANOMALY_DETECTION_GUIDE.md](anomaly_detection/ANOMALY_DETECTION_GUIDE.md)** | 🔍 Anomaly Detection 구현 가이드 |

---

## 🎯 시스템 구성

```
180cm Board
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│ Zone 0  │ Zone 1  │ Zone 2  │ Zone 3  │ Zone 4  │ Zone 5  │
│ Normal  │ Normal  │ Anomaly │ Defect  │ Defect  │ Defect  │
│  30cm   │  30cm   │  30cm   │  30cm   │  30cm   │  30cm   │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
```

- **Normal**: 정상 (탐지 안 함)
- **Anomaly**: Autoencoder 이상 탐지
- **Defect**: YOLO 결함 탐지

---

## 🆚 모드 비교

| 항목 | 🖐️ 수동 모드 | 🚗 자동 모드 |
|------|------------|------------|
| 포트 | 5003 | 5002 |
| 모터 | ❌ | ✅ |
| 캘리브레이션 | ❌ | ✅ |
| 이동 | 손으로 | 자동 |
| 용도 | 실습/테스트 | 실제 검사 |

---

## 📊 검사 결과

`inspection_results/` 폴더에 저장:

- JSON 결과 파일
- 6개 Zone 이미지

---

## 💡 처음 사용자

1. **[QUICK_START.md](QUICK_START.md)** 읽기
2. **수동 모드**로 실습
3. 시스템 이해 후 **자동 모드** 사용

---

## 🛠️ 서버 포트

| 서버 | 포트 | 용도 |
|------|------|------|
| 캘리브레이션 | 5001 | 모터 속도 측정 |
| 자동 검사 | 5002 | 자동 검사 시스템 |
| **수동 검사** | **5003** | **수동 검사 시스템 (추천!)** |

---

**Happy Inspecting! 🚗💨**
