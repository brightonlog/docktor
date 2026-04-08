# YOLOv26 선박 도장 결함 탐지 실험 기록

YOLOv26n 모델을 이용한 선박 도장 결함 탐지 모델 개선 실험

## 실험 목표

- **배포 환경**: Jetson Orin Nano에서 실시간 추론
- **모델**: YOLOv26n (End-to-End, NMS-free)
- **탐지 대상**: 5종 선박 도장 결함 (blister, crack, peeling, sagging, welding_damage)
- **목표 성능**: mAP50 > 0.85, 실시간 추론 속도 확보

## 탐지 클래스 (5종)

| YOLO ID | 영문명 | 한글명 | 원본 Category ID |
|---------|--------|--------|-----------------|
| 0 | blister | 부풀음 | 0 |
| 1 | crack | 균열 | 2 |
| 2 | peeling | 도막떨어짐 | 4 |
| 3 | sagging | 흐름 | 6 |
| 4 | welding_damage | 용접손상 | 9 |

---

## 1차 시도

### 실험 정보

- **날짜**: 2026-01-27
- **모델**: YOLOv26n
- **베이스 모델**: COCO pretrained weights
- **저장 위치**: `yolo26n.pt` (루트)

### 학습 설정

```yaml
하이퍼파라미터:
  - epochs: 40
  - batch_size: 4
  - img_size: 896  # 중간 해상도 (640과 1088 사이), gpu 이슈 때문에 1088은 할 수 없음
  - optimizer: AdamW
  - lr0: 0.001
  - patience: 20 (early stopping)

데이터셋:
  - 클래스: 5종 (원본 11개 중 선별)
  - 해상도: 896x896
  - Augmentation: YOLO 기본 설정
```

### 학습 결과

```
[학습 완료 후 업데이트 예정]

성능 지표:
  - mAP50: [TBD]
  - mAP50-95: [TBD]
  - Precision: [TBD]
  - Recall: [TBD]

클래스별 성능:
  - blister (부풀음): [TBD]
  - crack (균열): [TBD]
  - peeling (도막떨어짐): [TBD]
  - sagging (흐름): [TBD]
  - welding_damage (용접손상): [TBD]

학습 시간: [TBD]
```

### 주요 특징

1. **YOLOv26n 선택 이유**
   - NMS 제거 → End-to-End 추론 (TensorRT 변환 단순화)
   - DFL 제거 → 엣지 디바이스 호환성 향상
   - CPU 추론 43% 개선 (vs YOLOv11)
   - ProgLoss로 소형 물체(crack, pinhole) 탐지 개선

2. **Jetson Orin Nano 최적화**
   - 1088x1088 해상도 (1080p 웹캠 대응)
   - FP16 정밀도 (TensorRT)
   - Batch size 1 (실시간 추론)

### 관찰 사항

- [학습 중 발견된 특이사항 기록]
- [개선이 필요한 부분]
- [예상치 못한 결과]

### 개선 방향 (2차 시도 계획)

- [ ] 하이퍼파라미터 튜닝 (learning rate, batch size 조정)
- [ ] Data Augmentation 전략 변경
- [ ] 클래스 불균형 대응 (class weights)
- [ ] 소형 객체 탐지 개선 (crack, peeling)
- [ ] [기타 개선 아이디어]

---

## 2차 시도

### 실험 정보

- **날짜**: [TBD]
- **모델**: YOLOv26n
- **베이스 모델**: [1차 시도 모델 or COCO pretrained]
- **저장 위치**: [TBD]

### 변경 사항

```yaml
[1차 시도 대비 변경된 설정]
```

### 학습 결과

```
[2차 시도 완료 후 업데이트]
```

### 1차 대비 개선도

- mAP50: [1차] → [2차] (Δ: [+/-]%)
- 클래스별 성능 변화

---

## 3차 시도

### 실험 정보

- **날짜**: [TBD]
- **모델**: YOLOv26n
- **베이스 모델**: [이전 시도 모델 or COCO pretrained]
- **저장 위치**: [TBD]

### 변경 사항

```yaml
[2차 시도 대비 변경된 설정]
```

### 학습 결과

```
[3차 시도 완료 후 업데이트]
```

---

## 종합 비교

### 성능 비교표

| 시도 | mAP50 | mAP50-95 | Precision | Recall | 학습 시간 | 주요 변경사항 |
|------|-------|----------|-----------|--------|-----------|--------------|
| 1차 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | Baseline (COCO pretrained) |
| 2차 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [변경사항] |
| 3차 | [TBD] | [TBD] | [TBD] | [TBD] | [TBD] | [변경사항] |

### 클래스별 최고 성능

| 클래스 | 최고 mAP50 | 달성 시도 | 비고 |
|--------|-----------|----------|------|
| blister (부풀음) | [TBD] | [1/2/3]차 | |
| crack (균열) | [TBD] | [1/2/3]차 | |
| peeling (도막떨어짐) | [TBD] | [1/2/3]차 | |
| sagging (흐름) | [TBD] | [1/2/3]차 | |
| welding_damage (용접손상) | [TBD] | [1/2/3]차 | |

---

## 학습된 교훈 (Lessons Learned)

### 1차 시도에서 배운 점
- [학습 과정에서 얻은 인사이트]
- [효과적이었던 접근법]
- [비효율적이었던 부분]

### 2차 시도에서 배운 점
- [TBD]

### 3차 시도에서 배운 점
- [TBD]

---

## 최종 선택 모델

- **선택된 시도**: [1/2/3]차
- **선택 이유**: [성능, 추론 속도, 안정성 등]
- **배포 모델 경로**: [TBD]
- **TensorRT 변환**: [완료/예정]

---

## 참고 자료

- YOLOv26 공식 문서: https://docs.ultralytics.com/models/yolo26/
- 학습 노트북: [src/yolo_detection/train.ipynb](src/yolo_detection/train.ipynb)
- 데이터셋 준비: [src/yolo_detection/prepare_dataset.py](src/yolo_detection/prepare_dataset.py)
- 모델 README: [src/yolo_detection/README.md](src/yolo_detection/README.md)
