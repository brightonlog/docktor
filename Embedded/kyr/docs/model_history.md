# Auto Inspection System 개발 이력

## 2026-01-29 (Latest)

### PatchCore Lite 모델 적용
- **이상탐지 모델 경량화**: 기존 PatchCore에서 PatchCore Lite 모델로 변경
- 모델 파일: [patchcore_lite_model.npz](../models/anomaly_patchcore_lite/patchcore_lite_model.npz)
- 설정 파일: [config/](../models/anomaly_patchcore_lite/config/)
- PatchCore Lite는 경량화된 버전으로 추론 속도 개선 및 메모리 사용량 감소
- Stage 2 이상탐지 파이프라인에서 YOLO가 결함을 찾지 못할 때 PatchCore Lite 모델 사용

---

## 2026-01-29 (Earlier)

### 1. ROI 설정 및 Flask 화면 개선
- ROI config를 [roi_config.txt](../inspection/roi_config.txt)에서 동적으로 로드하도록 변경
- Flask 웹 화면을 ROI 크롭 영역에서 Full 웹캠 크기(640x480)로 확장
- Target Box(녹색 박스)를 추가하여 검사 영역(30cm x 85cm)을 시각적으로 표시
- 실제 탐지는 Target Box 내부 영역만 crop하여 수행

### 2. 2단계 하이브리드 탐지 파이프라인 구현
- Stage 1: YOLO 모델로 5가지 핵심 결함 탐지 (sagging, crack, blister, welding_damage, peeling)
- Stage 2: YOLO가 결함을 찾지 못하면 PatchCore로 미세 이상 탐지 수행
- 탐지 방법에 따라 색상 구분: YOLO 결함(빨간색), PatchCore 이상(주황색)

### 3. GPU/CPU 리소스 최적화
- GPU 메모리 부족 문제 해결을 위해 2가지 모드 구현
  - Mode 1 (권장): YOLO CPU + PatchCore GPU - 전체 검사 시간 0.8-2초
  - Mode 2: YOLO GPU + PatchCore CPU - PatchCore CPU 처리 시 47초 소요로 비효율적
- 성능 비교 결과 Mode 1이 약 100배 빠름 ([trouble_shooting_yolo_patchcore.md](trouble_shooting_yolo_patchcore.md) 참조)

### 4. Zone 이동 로직 개선
- Zone 간 이동 시 안정화 대기 시간을 0.5초 → 0.7초로 증가
- 캘리브레이션 데이터 기반 30cm 주행 (PWM 40%, 2초)

### 5. Target Box On/Off 토글 기능 추가
- 웹 UI에 "📦 Target Box: ON/OFF" 버튼 추가
- 사용자가 실시간으로 Target Box 표시를 켜고 끌 수 있음
- 탐지 기능은 Target Box 표시 여부와 관계없이 항상 ROI 영역에서 수행

### 6. 전체 Zone 탐지 모드로 변경
- 이전: zone_types를 ['normal', 'normal', 'anomaly', 'defect', 'defect', 'defect']로 구분하여 일부 zone만 탐지
- 변경: 모든 zone_types를 'detection'으로 통일하여 6개 전체 zone에서 2단계 하이브리드 탐지 수행
- 빠짐없이 전체 영역을 검사하여 검사 신뢰도 향상

---

## 주요 파일 구조

- [auto_inspection_system.py](../inspection/auto_inspection_system.py) - 메인 시스템
- [roi_config.txt](../inspection/roi_config.txt) - ROI 설정
- [detection_pipeline.md](detection_pipeline.md) - 탐지 파이프라인 설명
- [trouble_shooting_yolo_patchcore.md](trouble_shooting_yolo_patchcore.md) - 성능 최적화 문서

---

**최종 업데이트**: 2026-01-29
