"""
============================================================
Visualization Utilities for Inspection Results
============================================================
검사 결과 시각화 도구
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple


# 색상 정의 (BGR 형식)
COLORS = {
    'normal': (0, 255, 0),      # 초록색
    'anomaly': (0, 255, 255),   # 노란색
    'defect': (0, 0, 255),      # 빨간색
    'white': (255, 255, 255),   # 흰색
    'black': (0, 0, 0),         # 검은색
}


def draw_bbox(image: np.ndarray, bbox: List[float], label: str,
              color: Tuple[int, int, int], thickness: int = 3) -> np.ndarray:
    """
    이미지에 Bounding Box 그리기

    Args:
        image: 원본 이미지
        bbox: [x1, y1, x2, y2] 좌표
        label: 라벨 텍스트
        color: BGR 색상
        thickness: 선 두께

    Returns:
        bbox가 그려진 이미지
    """
    x1, y1, x2, y2 = map(int, bbox)

    # BBox 그리기
    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

    # 라벨 배경 그리기
    label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    y1_label = max(y1, label_size[1] + 10)

    cv2.rectangle(image,
                  (x1, y1_label - label_size[1] - 10),
                  (x1 + label_size[0], y1_label + baseline),
                  color, -1)

    # 라벨 텍스트 그리기
    cv2.putText(image, label, (x1, y1_label - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS['white'], 2)

    return image


def draw_frame_border(image: np.ndarray, color: Tuple[int, int, int],
                      thickness: int = 10) -> np.ndarray:
    """
    이미지 전체에 테두리 그리기

    Args:
        image: 원본 이미지
        color: BGR 색상
        thickness: 테두리 두께

    Returns:
        테두리가 그려진 이미지
    """
    h, w = image.shape[:2]
    cv2.rectangle(image, (0, 0), (w-1, h-1), color, thickness)
    return image


def draw_header_text(image: np.ndarray, text: str,
                     color: Tuple[int, int, int] = COLORS['anomaly']) -> np.ndarray:
    """
    이미지 상단 중앙에 텍스트 그리기

    Args:
        image: 원본 이미지
        text: 텍스트 내용
        color: 텍스트 색상

    Returns:
        텍스트가 그려진 이미지
    """
    h, w = image.shape[:2]

    # 텍스트 크기 측정
    font_scale = 1.5
    thickness = 3
    text_size, baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, font_scale, thickness)

    # 중앙 위치 계산
    text_x = (w - text_size[0]) // 2
    text_y = 50

    # 배경 사각형 그리기 (반투명)
    overlay = image.copy()
    cv2.rectangle(overlay,
                  (text_x - 10, text_y - text_size[1] - 10),
                  (text_x + text_size[0] + 10, text_y + 10),
                  COLORS['black'], -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)

    # 텍스트 그리기
    cv2.putText(image, text, (text_x, text_y),
                cv2.FONT_HERSHEY_DUPLEX, font_scale, color, thickness)

    return image


def draw_zone_info(image: np.ndarray, zone_id: int, zone_type: str) -> np.ndarray:
    """
    Zone 정보 그리기 (좌측 상단)

    Args:
        image: 원본 이미지
        zone_id: Zone 번호
        zone_type: Zone 타입

    Returns:
        Zone 정보가 그려진 이미지
    """
    text = f"Zone {zone_id} - {zone_type.upper()}"

    font_scale = 0.8
    thickness = 2
    text_size, baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

    # 배경 사각형
    cv2.rectangle(image, (10, 10), (20 + text_size[0], 20 + text_size[1]),
                  COLORS['black'], -1)

    # 텍스트
    cv2.putText(image, text, (15, 15 + text_size[1]),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, COLORS['white'], thickness)

    return image


def visualize_normal(image: np.ndarray, zone_id: int) -> np.ndarray:
    """
    Normal Zone 시각화
    - 초록색 테두리
    - Zone 정보

    Args:
        image: 원본 이미지
        zone_id: Zone 번호

    Returns:
        시각화된 이미지
    """
    result = image.copy()

    # 초록색 테두리
    result = draw_frame_border(result, COLORS['normal'], thickness=15)

    # Zone 정보
    result = draw_zone_info(result, zone_id, 'NORMAL')

    # NORMAL 텍스트
    result = draw_header_text(result, 'NORMAL', COLORS['normal'])

    return result


def visualize_anomaly(image: np.ndarray, zone_id: int,
                      detections: List[Dict]) -> np.ndarray:
    """
    Anomaly Zone 시각화
    - 노란색 테두리
    - "ANOMALY DETECTION" 텍스트
    - Zone 정보

    Args:
        image: 원본 이미지
        zone_id: Zone 번호
        detections: 탐지 결과 리스트

    Returns:
        시각화된 이미지
    """
    result = image.copy()

    # 노란색 테두리
    result = draw_frame_border(result, COLORS['anomaly'], thickness=15)

    # Zone 정보
    result = draw_zone_info(result, zone_id, 'ANOMALY')

    # ANOMALY DETECTION 텍스트
    result = draw_header_text(result, 'ANOMALY DETECTION', COLORS['anomaly'])

    # 탐지 정보 표시
    if detections:
        h, w = result.shape[:2]
        y_offset = h - 50

        for det in detections:
            if 'score' in det:
                text = f"Anomaly Score: {det['score']:.4f}"
                cv2.putText(result, text, (20, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS['anomaly'], 2)
                y_offset -= 30

    return result


def visualize_defect(image: np.ndarray, zone_id: int,
                     detections: List[Dict]) -> np.ndarray:
    """
    Defect Zone 시각화
    - 각 결함마다 빨간색 BBox
    - 결함 클래스명 표시
    - Zone 정보

    Args:
        image: 원본 이미지
        zone_id: Zone 번호
        detections: YOLO 탐지 결과 리스트

    Returns:
        시각화된 이미지
    """
    result = image.copy()

    # Zone 정보
    result = draw_zone_info(result, zone_id, 'DEFECT')

    if not detections:
        # 결함이 탐지되지 않은 경우
        result = draw_frame_border(result, COLORS['normal'], thickness=15)
        result = draw_header_text(result, 'NO DEFECT', COLORS['normal'])
    else:
        # 결함 탐지된 경우
        for det in detections:
            class_name = det.get('class_name', 'Unknown')
            confidence = det.get('confidence', 0.0)
            bbox = det.get('bbox', None)

            if bbox:
                label = f"{class_name} {confidence:.2f}"
                result = draw_bbox(result, bbox, label, COLORS['defect'], thickness=3)

        # DEFECT DETECTED 텍스트
        result = draw_header_text(result, 'DEFECT DETECTED', COLORS['defect'])

    return result


def visualize_inspection_result(image: np.ndarray, zone_id: int, zone_type: str,
                                detections: List[Dict], is_defective: bool) -> np.ndarray:
    """
    검사 결과 시각화 (통합 함수)

    Args:
        image: 원본 이미지
        zone_id: Zone 번호
        zone_type: Zone 타입 ('normal', 'anomaly', 'defect')
        detections: 탐지 결과 리스트
        is_defective: 결함 여부

    Returns:
        시각화된 이미지
    """
    if zone_type == 'normal':
        return visualize_normal(image, zone_id)

    elif zone_type == 'anomaly':
        # 이제 anomaly zone도 YOLO를 사용하므로 defect 시각화 사용
        return visualize_defect(image, zone_id, detections)

    elif zone_type == 'defect':
        return visualize_defect(image, zone_id, detections)

    else:
        # 알 수 없는 타입
        return image


def create_thumbnail(image: np.ndarray, max_size: int = 320) -> np.ndarray:
    """
    썸네일 이미지 생성 (웹 UI용)

    Args:
        image: 원본 이미지
        max_size: 최대 크기 (픽셀)

    Returns:
        리사이즈된 이미지
    """
    h, w = image.shape[:2]

    if max(h, w) <= max_size:
        return image

    if h > w:
        new_h = max_size
        new_w = int(w * (max_size / h))
    else:
        new_w = max_size
        new_h = int(h * (max_size / w))

    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def add_timestamp(image: np.ndarray, timestamp: str) -> np.ndarray:
    """
    이미지에 타임스탬프 추가 (우측 하단)

    Args:
        image: 원본 이미지
        timestamp: 타임스탬프 문자열

    Returns:
        타임스탬프가 추가된 이미지
    """
    h, w = image.shape[:2]

    font_scale = 0.6
    thickness = 2
    text_size, baseline = cv2.getTextSize(timestamp, cv2.FONT_HERSHEY_SIMPLEX,
                                          font_scale, thickness)

    text_x = w - text_size[0] - 20
    text_y = h - 20

    # 배경
    cv2.rectangle(image,
                  (text_x - 5, text_y - text_size[1] - 5),
                  (w - 15, h - 15),
                  COLORS['black'], -1)

    # 텍스트
    cv2.putText(image, timestamp, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, COLORS['white'], thickness)

    return image
