"""
============================================================
auto_inspection_system_api.py — 백엔드 API 연동 모듈
============================================================
- auto_inspection_system.py의 검사 결과(results)를 읽어서
  S3 업로드 + Spring Boot callback까지 처리
- auto_inspection_system.py 자체는 수정하지 않음
- api.py와 동일한 S3 경로 구조 및 payload 형식 사용

사용법:
    from auto_inspection_system_api import report_inspection

    # 검사 완료 후 호출
    report_inspection(
        results=inspection_system.results,
        roi_config=camera_controller.roi_config,
        inspect_id="abc123",
        ship_id=42,
        corp_id=1,
        callback_url="http://i14e201.p.ssafy.io:8080/api/inspects/abc123/callback"
    )
"""

import cv2
import io
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # dotenv 없으면 환경변수는 직접 설정해야 함

# --- 설정 (api.py와 동일) ---
S3_BUCKET = "docktor-bucket"

# YOLO class_id(0-4) → DB category_id(1-10) 매핑
# 학습 모델: blister(0), crack(1), peeling(2), sagging(3), welding_damage(4)
# DB: 1~10 (coating_separation~other_damage)
# blister는 DB에 없어 other_damage(10)으로 매핑
# PatchCore anomaly(-1)도 other_damage(10)
_YOLO_TO_CATEGORY_ID = {
    0: 10,  # blister → other_damage
    1: 2,   # crack
    2: 4,   # peeling
    3: 6,   # sagging
    4: 9,   # welding_damage
}

# S3 클라이언트는 실제 사용 시에만 초기화 (테스트 실행 시 boto3 불필요)
_s3_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )
    return _s3_client


# ============================================================
# S3 업로드
# ============================================================

def upload_to_s3(img_array, s3_path):
    """numpy 이미지 배열을 S3에 업로드 → URL 반환 (api.py와 동일 패턴)"""
    try:
        _, buffer = cv2.imencode(".jpg", img_array)
        io_buf = io.BytesIO(buffer)
        _get_s3_client().upload_fileobj(io_buf, S3_BUCKET, s3_path)
        return f"https://{S3_BUCKET}.s3.ap-northeast-2.amazonaws.com/{s3_path}"
    except Exception as e:
        print(f"❌ S3 Upload Error: {e}")
        return ""


# ============================================================
# 좌표 변환 (auto_inspection_system.py ROIConfig.bbox_to_real_coordinates와 동일 로직)
# ============================================================

def _bbox_to_real_coordinates(bbox, zone_id, roi_width_px, roi_height_px, real_width_cm, real_height_cm):
    """
    bbox 중앙 좌표 → 실제 cm 좌표로 변환

    Args:
        bbox: [x1, y1, x2, y2] ROI 내 픽셀 좌표
        zone_id: Zone 번호 (각 zone은 30cm 간격)
    Returns:
        (absolute_x_cm, absolute_y_cm)
    """
    px_to_cm_x = real_width_cm / roi_width_px
    px_to_cm_y = real_height_cm / roi_height_px

    center_x_px = (bbox[0] + bbox[2]) / 2
    center_y_px = (bbox[1] + bbox[3]) / 2

    absolute_x_cm = center_x_px * px_to_cm_x + (zone_id * 30.0)
    absolute_y_cm = center_y_px * px_to_cm_y

    return absolute_x_cm, absolute_y_cm


def _extract_roi_info(roi_config):
    """roi_config 객체에서 좌표 변환에 필요한 값 추출"""
    return {
        "roi_width_px": roi_config.x_end - roi_config.x_start,
        "roi_height_px": roi_config.y_end - roi_config.y_start,
        "real_width_cm": roi_config.real_width_cm,
        "real_height_cm": roi_config.real_height_cm,
    }


# ============================================================
# 결함 항목 처리
# ============================================================

def _build_defect_item(detection, img, zone_id, s3_base_dir, idx, roi_info):
    """
    단일 결함 → S3 크롭 업로드 + payload 항목 생성

    Args:
        detection: {class_id, class_name, confidence, bbox}
        img: imread로 읽은 이미지 (vis_frame)
        zone_id: zone 번호
        s3_base_dir: S3 기본 경로
        idx: 해당 zone 내 결함 순번 (0-based)
        roi_info: 좌표 변환 정보
    """
    bbox = detection.get("bbox")
    h, w = img.shape[:2]

    if bbox is not None:
        # YOLO 탐지 — bbox로 크롭
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        crop = img[y1:y2, x1:x2]
    else:
        # PatchCore anomaly — bbox 없음 → 이미지 영역 전체 사용
        x1, y1, x2, y2 = 0, 0, w, h
        crop = img

    # 크롭 S3 업로드
    s3_path = f"{s3_base_dir}/defects/zone_{zone_id:02d}_defect_{idx + 1}_crop.jpg"
    cropped_url = upload_to_s3(crop, s3_path)

    # x_cord, y_cord 계산 (bbox가 None이면 이미지 중앙 기준)
    coord_bbox = bbox if bbox is not None else [0, 0, w, h]
    x_cm, y_cm = _bbox_to_real_coordinates(
        coord_bbox, zone_id,
        roi_info["roi_width_px"], roi_info["roi_height_px"],
        roi_info["real_width_cm"], roi_info["real_height_cm"],
    )

    return {
        "category_id": _YOLO_TO_CATEGORY_ID.get(detection.get("class_id"), 10),
        "confidence": detection.get("confidence"),
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "x_cord": round(x_cm),
        "y_cord": round(y_cm),
        "cropped_image_url": cropped_url,
    }


# ============================================================
# 메인 진입점
# ============================================================

def report_inspection(results, roi_config, inspect_id, ship_id, corp_id, callback_url):
    """
    검사 결과를 백엔드로 보고

    Args:
        results: List[DetectionResult] — inspection_system.results
        roi_config: ROIConfig 객체 — camera_controller.roi_config
        inspect_id: 검사 ID (백엔드/MQTT에서 전달)
        ship_id: 선박 ID
        corp_id: 업체 ID
        callback_url: Spring Boot 보고 URL
    """
    print(f"\n📡 [API] 백엔드 보고 시작 (inspect_id={inspect_id})")

    s3_base_dir = f"corp_{corp_id}/ships/{ship_id}/inspects/{inspect_id}"
    roi_info = _extract_roi_info(roi_config)

    all_defects = []
    first_original_url = None

    for result in results:
        zone_id = result.zone_id
        image_path = result.image_path

        # vis_frame 읽기
        img = cv2.imread(image_path)
        if img is None:
            print(f"⚠️  [Zone {zone_id}] 이미지 읽기 실패: {image_path}")
            continue

        # S3 original 업로드
        original_s3_path = f"{s3_base_dir}/original/zone_{zone_id:02d}.jpg"
        original_url = upload_to_s3(img, original_s3_path)

        if first_original_url is None:
            first_original_url = original_url

        print(f"  ✅ [Zone {zone_id}] original 업로드 완료")

        # 결함이 있으면 각 결함별 크롭 처리
        if result.is_defective and result.detections:
            for idx, det in enumerate(result.detections):
                defect_item = _build_defect_item(
                    det, img, zone_id, s3_base_dir, idx, roi_info
                )
                all_defects.append(defect_item)
                print(f"    🔴 결함 {idx + 1}: {det.get('class_name')} (conf={det.get('confidence', 0):.2f})")

    # --- Payload (api.py와 동일 구조) ---
    payload = {
        "inspect_id": inspect_id,
        "status": "completed",
        "image_url": first_original_url,
        "defects": all_defects,
    }

    # --- 디버그: payload 터미널 출력 + JSON 파일 저장 ---
    import json
    from pathlib import Path

    print(f"\n📋 [API] Payload (inspect_id={inspect_id}):")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    debug_dir = Path(__file__).parent / "debug_payloads"
    debug_dir.mkdir(exist_ok=True)
    debug_file = debug_dir / f"payload_{inspect_id}.json"
    with open(debug_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"💾 [API] Payload 저장: {debug_file}")

    # --- Spring Boot Callback ---
    try:
        import requests
        resp = requests.post(callback_url, json=payload, timeout=10)
        print(f"\n✅ [API] Spring Boot 보고 완료: {resp.status_code}")
        print(f"   총 결함 수: {len(all_defects)}")
        if resp.status_code >= 400:
            print(f"   ⚠️  Response body: {resp.text}")
        return True
    except Exception as e:
        print(f"\n❌ [API] Callback 실패: {e}")
        return False


# ============================================================
# 테스트 실행 (__main__)
# ============================================================

if __name__ == "__main__":
    import numpy as np
    from dataclasses import dataclass
    from typing import List, Dict
    import tempfile

    # --- Mock 클래스 (auto_inspection_system.py의 DetectionResult / ROIConfig 동일 구조) ---

    @dataclass
    class MockDetectionResult:
        zone_id: int
        zone_type: str
        timestamp: str
        detections: List[Dict]
        image_path: str
        inference_time_ms: float
        is_defective: bool

    class MockROIConfig:
        def __init__(self):
            self.x_start = 160
            self.x_end = 480   # roi_width_px = 320
            self.y_start = 60
            self.y_end = 420   # roi_height_px = 360
            self.real_width_cm = 30.0
            self.real_height_cm = 85.0

    # --- Mock 이미지 생성 ---
    tmp_dir = tempfile.mkdtemp()
    mock_images = {}
    for zone in range(3):
        img = np.zeros((360, 320, 3), dtype=np.uint8)
        cv2.putText(img, f"Zone {zone} Mock Frame",
                    (30, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
        path = os.path.join(tmp_dir, f"zone_{zone:02d}.jpg")
        cv2.imwrite(path, img)
        mock_images[zone] = path

    # --- Mock 검사 결과 ---
    # Zone 0: YOLO 결함 1건 (Crack)
    # Zone 1: 정상
    # Zone 2: PatchCore anomaly 1건 (bbox=None)
    mock_results = [
        MockDetectionResult(
            zone_id=0, zone_type="detection",
            timestamp="2026-02-02T10:00:00",
            detections=[
                {"class_id": 4, "class_name": "Crack", "confidence": 0.95,
                 "bbox": [50, 80, 200, 250]},
            ],
            image_path=mock_images[0],
            inference_time_ms=120.0,
            is_defective=True,
        ),
        MockDetectionResult(
            zone_id=1, zone_type="detection",
            timestamp="2026-02-02T10:00:05",
            detections=[],
            image_path=mock_images[1],
            inference_time_ms=95.0,
            is_defective=False,
        ),
        MockDetectionResult(
            zone_id=2, zone_type="detection",
            timestamp="2026-02-02T10:00:10",
            detections=[
                {"class_id": -1, "class_name": "anomaly", "confidence": 42.5,
                 "bbox": None},
            ],
            image_path=mock_images[2],
            inference_time_ms=200.0,
            is_defective=True,
        ),
    ]

    roi_config = MockROIConfig()
    roi_info = _extract_roi_info(roi_config)

    # --- Payload 미리보기 (S3 / callback 없이 로직 확인) ---
    print("=" * 60)
    print("  auto_inspection_system_api — 테스트 실행")
    print("=" * 60)
    print(f"  Mock zones: {len(mock_results)}")
    print(f"  결함 zones: {sum(1 for r in mock_results if r.is_defective)}")
    print(f"  ROI: {roi_info['roi_width_px']}x{roi_info['roi_height_px']}px "
          f"({roi_info['real_width_cm']}x{roi_info['real_height_cm']}cm)")
    print("-" * 60)

    for result in mock_results:
        img = cv2.imread(result.image_path)
        print(f"\n[Zone {result.zone_id}] is_defective={result.is_defective}")

        if not result.is_defective or not result.detections:
            print("  → 정상 (결함 없음)")
            continue

        for idx, det in enumerate(result.detections):
            bbox = det.get("bbox")
            h, w = img.shape[:2]

            # 크롭 영역 계산
            if bbox is not None:
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            else:
                x1, y1, x2, y2 = 0, 0, w, h

            # 좌표 변환
            coord_bbox = bbox if bbox is not None else [0, 0, w, h]
            x_cm, y_cm = _bbox_to_real_coordinates(
                coord_bbox, result.zone_id,
                roi_info["roi_width_px"], roi_info["roi_height_px"],
                roi_info["real_width_cm"], roi_info["real_height_cm"],
            )

            print(f"  결함 {idx + 1}:")
            print(f"    class_name  = {det['class_name']}")
            print(f"    category_id = {det['class_id']}")
            print(f"    confidence  = {det['confidence']}")
            print(f"    bbox        = [{x1}, {y1}, {x2}, {y2}]"
                  + (" (전체 영역 — PatchCore)" if det.get("bbox") is None else ""))
            print(f"    x_cord      = {round(x_cm)}  (원본 {x_cm:.2f} cm)")
            print(f"    y_cord      = {round(y_cm)}  (원본 {y_cm:.2f} cm)")

    print("\n" + "-" * 60)
    print("✅ Payload 검증 완료")
    print("   실제 S3 업로드 + callback: report_inspection() 호출 시 실행")
    print(f"   tmp 이미지 경로: {tmp_dir}")
