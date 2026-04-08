# API 연동 흐름 — 함수별 설명

## 전체 그림

```
Spring Boot (백엔드)
      │
      │ MQTT 메시지 발행  (또는 HTTP POST /move)
      ▼
┌─────────────┐     HTTP POST      ┌──────────────────────┐
│   api.py    │ ─────────────────► │ auto_inspection_     │
│  (port 5000)│ ◄─────────────────  │ system.py (port 5004)│
│  MQTT 수신  │   polling + 결과   │  카메라 / 모델 / 검사  │
└─────────────┘                    └──────────────────────┘
      │
      │ S3 업로드 + callback POST
      ▼
┌─────────────────────┐
│ auto_inspection_    │
│ system_api.py       │  ← S3, Spring Boot callback 로직
│ (모듈, 프로세스 아님)│
└─────────────────────┘
      │
      ▼
Spring Boot (백엔드) ← 검사 결과 수신
```

---

## 단계 1 — 트리거: 백엔드가 검사를 요청

Spring Boot에서 MQTT 메시지를 발행하거나, 누군가 HTTP로 직접 호출합니다.

### MQTT 경로
```
Spring Boot → MQTT Broker (i14e201.p.ssafy.io:8082)
  → topic: robot/orin_01/move
  → payload: { inspect_id, ship_id, corp_id, callback_url }
```

### HTTP 경로 (테스트용)
```bash
curl -X POST http://localhost:5000/move
  -d '{ "inspect_id": "test_001", "ship_id": 42, "corp_id": 1,
        "callback_url": "http://백엔드/..." }'
```

---

## 단계 2 — api.py: 명령 수신

**파일:** `api.py`

### 진입점: on_message() 또는 move_robot()

```
MQTT 메시지 도착
      │
      ▼
on_message()              ← MQTT로 받은 경우
  or
move_robot()              ← HTTP POST /move로 받은 경우
      │
      ├─ is_busy 확인 (다른 검사 진행 중이면 무시)
      ├─ is_busy = True
      │
      ▼
threading.Thread(target=execute_and_report).start()
                          ← 별도 스레드로 실행 (바로 응답 반환)
```

**핵심:** `on_message`와 `move_robot` 둘 다 결국 `execute_and_report()`를 스레드로 실행합니다.

---

## 단계 3 — api.py: execute_and_report() — 검사 트리거 및 대기

**파일:** `api.py` → `execute_and_report()`

이 함수가 전체 흐름의 중심입니다.

```
execute_and_report(inspect_id, ship_id, corp_id, callback_url)
      │
      ├─ [Step 1] POST http://localhost:5004/api/start_auto
      │            → auto_inspection_system.py에 "검사 시작" 신호
      │
      ├─ [Step 2] 루프: GET http://localhost:5004/api/status
      │            → completed_zones == total_zones 이고 is_active == False 이면 종료
      │            → 2초마다 반복
      │
      ├─ [Step 3] inspection_results.json 파일 읽기
      │            → status의 image_path에서 session 폴더 경로 추출
      │            → 해당 폴더의 inspection_results.json 파싱
      │            → 여기에 bbox, class_id 등 full 정보가 있음
      │
      ├─ [Step 4] GET http://localhost:5004/api/roi_config
      │            → ROI 좌표 변환에 필요한 정보 가져오기
      │
      └─ [Step 5] report_inspection() 호출
                   → S3 업로드 + Spring Boot 보고 (단계 5번)
```

**왜 inspection_results.json을 읽는가?**
`/api/status`에서 반환되는 `zone_results`에는 `class_name`과 `confidence`만 있습니다.
`bbox`와 `class_id`는 포함되지 않아서, S3 크롭 업로드와 좌표 변환을 할 수 없습니다.
`inspection_results.json`은 `save_results()`에서 `asdict(DetectionResult)`로 저장되어서 모든 정보가 있습니다.

---

## 단계 4 — auto_inspection_system.py: 실제 검사 수행

**파일:** `auto_inspection_system.py`

`api.py`가 POST /api/start_auto를 보내면, 여기서 실제 검사가 돌기 시작합니다.

```
api_start_auto()                    ← Flask 라우트 핸들러
      │
      ├─ AutoInspectionSystem 생성
      ├─ start_session()            ← session 폴더 생성
      │
      └─ threading.Thread(run_auto_inspection).start()
                │
                ▼
        run_auto_inspection()       ← zone 0~5 루프
                │
                ├─ inspect_current_zone()     ← 각 zone마다 반복
                │       │
                │       ├─ camera.capture_frame(crop_roi=True)  ← ROI 크롭된 프레임
                │       │
                │       ├─ [Stage 1] yolo_detector.detect()     ← YOLO 탐지
                │       │       → detections: [{class_id, class_name, confidence, bbox}]
                │       │
                │       ├─ [Stage 2] patchcore_detector.detect() ← YOLO 음성이면 실행
                │       │       → detections: [{class_id: -1, class_name: "anomaly", bbox: None}]
                │       │
                │       ├─ _visualize_detections()              ← 결과 시각화 (테두리 등)
                │       │
                │       └─ camera.save_image(vis_frame)         ← 이미지 파일 저장
                │               → zone_00_detection.jpg 등
                │
                ├─ move_to_next_zone()        ← 모터로 30cm 주행
                │
                └─ finish_session()
                        │
                        └─ save_results()     ← inspection_results.json 저장
                                │
                                ▼
                        {
                          "results": [
                            {
                              "zone_id": 0,
                              "detections": [
                                { "class_id": 4, "class_name": "Crack",
                                  "confidence": 0.95, "bbox": [50, 80, 200, 250] }
                              ],
                              "image_path": "/path/to/zone_00_detection.jpg",
                              "is_defective": true
                            },
                            ...
                          ]
                        }
```

**검사가 완료되면 api.py의 polling이 완료됨을 감지하고 다음 단계로 진행합니다.**

---

## 단계 5 — auto_inspection_system_api.py: S3 업로드 및 백엔드 보고

**파일:** `auto_inspection_system_api.py` → `report_inspection()`

api.py에서 읽은 결과와 ROI config를 받아서, S3에 이미지를 올리고 백엔드에 보고합니다.

```
report_inspection(results, roi_config, inspect_id, ship_id, corp_id, callback_url)
      │
      ├─ S3 경로 구성: corp_{corp_id}/ships/{ship_id}/inspects/{inspect_id}/
      │
      ├─ [각 zone마다 반복]
      │       │
      │       ├─ cv2.imread(image_path)        ← 저장된 vis_frame 읽기
      │       │
      │       ├─ upload_to_s3(img)             ← S3 original/ 업로드
      │       │       → original/zone_00.jpg
      │       │
      │       └─ [결함이 있으면 각 결함마다]
      │               │
      │               └─ _build_defect_item()
      │                       │
      │                       ├─ bbox != None (YOLO)
      │                       │     → img[y1:y2, x1:x2] 로 크롭
      │                       │
      │                       ├─ bbox == None (PatchCore)
      │                       │     → 이미지 전체를 크롭으로 사용
      │                       │       x1=0, y1=0, x2=width, y2=height
      │                       │
      │                       ├─ upload_to_s3(crop)   ← S3 defects/ 업로드
      │                       │       → defects/zone_00_defect_1_crop.jpg
      │                       │
      │                       └─ _bbox_to_real_coordinates()  ← 좌표 변환
      │                               → 픽셀 좌표 → cm 좌표 → int 반올림
      │                               → x_cord, y_cord
      │
      └─ payload 구성 및 callback POST
              │
              ▼
        {
          "inspect_id": "test_001",
          "status": "completed",
          "image_url": "https://S3/original/zone_00.jpg",
          "defects": [
            {
              "category_id": 4,
              "confidence": 0.95,
              "x1": 50, "y1": 80, "x2": 200, "y2": 250,
              "x_cord": 12,
              "y_cord": 39,
              "cropped_image_url": "https://S3/defects/zone_00_defect_1_crop.jpg"
            }
          ]
        }
              │
              ├─ requests.post(callback_url, json=payload)
              ▼
        Spring Boot ← 보고 완료
```

---

## S3에 저장되는 구조

```
docktor-bucket/
└── corp_1/
    └── ships/
        └── 42/
            └── inspects/
                └── test_001/
                    ├── original/
                    │   ├── zone_00.jpg    ← 각 zone의 검사 이미지
                    │   ├── zone_01.jpg
                    │   └── ...
                    └── defects/
                        ├── zone_00_defect_1_crop.jpg   ← YOLO bbox 크롭
                        └── zone_02_defect_1_crop.jpg   ← PatchCore (전체 영역)
```

---

## 좌표 변환 (_bbox_to_real_coordinates)

YOLO의 bbox는 ROI 내 픽셀 좌표입니다. 백엔드에는 실제 물리적 좌표(cm)를 보내야 합니다.

```
ROI 픽셀 좌표 (bbox)          실제 cm 좌표
┌─────────────────┐           ┌─────────────────┐
│                 │           │                 │
│   bbox 중앙 •   │  ──────►  │   x_cord, y_cord│
│   (125, 165)px  │  변환     │   (12cm, 39cm)  │
│                 │           │                 │
└─────────────────┘           └─────────────────┘
  320 x 360 px                  30cm x 85cm
  (ROI 크기)                   (실제 물리 크기)

변환 공식:
  x_cm = (bbox 중앙 x px) × (real_width_cm / roi_width_px) + (zone_id × 30cm)
  y_cm = (bbox 중앙 y px) × (real_height_cm / roi_height_px)

zone_id × 30cm: 각 zone은 30cm씩 떨어져 있으므로 offset 추가
```

---

## 각 파일의 역할 요약

| 파일 | 역할 | 프로세스 |
|------|------|----------|
| `auto_inspection_system.py` | 카메라, 모터, YOLO, PatchCore 관리. 실제 검사 수행. | port 5004 |
| `api.py` | MQTT 수신, 검사 트리거, 결과 조를 가져와서 보고 실행 | port 5000 |
| `auto_inspection_system_api.py` | S3 업로드 + Spring Boot callback 로직 (모듈) | 프로세스 아님, api.py에서 import |

---

## YOLO vs PatchCore — 결과의 차이

| | YOLO | PatchCore |
|--|------|-----------|
| 탐지 방식 | 특정 결함 클래스 분류 | 정상이 아닌 것을 감지 |
| class_id | 실제 클래스 ID (예: 4=Crack) | -1 |
| class_name | Crack, Corrosion 등 | anomaly |
| bbox | [x1, y1, x2, y2] 있음 | None |
| S3 크롭 | bbox 영역만 크롭 | 이미지 전체 사용 |
| confidence | 분류 신뢰도 (0~1) | anomaly score (raw 값) |
