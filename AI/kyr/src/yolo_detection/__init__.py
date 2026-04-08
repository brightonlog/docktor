"""
YOLOv26n Ship Painting Defect Detection Module

5종 선별 학습 클래스 (원본 11개 클래스 중 선별):
- blister (부풀음) - 원본 Category ID: 0
- crack (균열) - 원본 Category ID: 2
- peeling (도막떨어짐) - 원본 Category ID: 4
- sagging (흐름) - 원본 Category ID: 6
- welding_damage (용접손상) - 원본 Category ID: 9

YOLO 학습용 ID는 0-4로 재매핑됩니다.

Features:
- 1080p resolution training (optimized for Jetson Orin Nano webcam)
- MLflow experiment tracking
- TensorBoard logging
- Weights & Biases integration (optional)
- TensorRT export for Jetson deployment
"""

from pathlib import Path

__version__ = '1.0.0'
__author__ = 'KYR'

# 클래스 정의 (YOLO 학습용, 0-4로 재매핑)
CLASS_NAMES = ['blister', 'crack', 'peeling', 'sagging', 'welding_damage']
NUM_CLASSES = 5

# 원본 데이터셋 카테고리 ID 매핑 (11개 클래스 중 선별)
# YOLO ID: 원본 Category ID
ORIGINAL_CATEGORY_MAPPING = {
    0: 0,  # blister (부풀음)
    1: 2,  # crack (균열)
    2: 4,  # peeling (도막떨어짐)
    3: 6,  # sagging (흐름)
    4: 9,  # welding_damage (용접손상)
}

# 한글 이름 매핑
CLASS_NAMES_KR = {
    'blister': '부풀음',
    'crack': '균열',
    'peeling': '도막떨어짐',
    'sagging': '흐름',
    'welding_damage': '용접손상',
}

# 모듈 경로
MODULE_DIR = Path(__file__).parent
PROJECT_DIR = MODULE_DIR.parent.parent


def yolo_id_to_original_id(yolo_id: int) -> int:
    """
    YOLO 학습용 ID(0-4)를 원본 카테고리 ID로 변환

    Args:
        yolo_id: YOLO 모델이 예측한 클래스 ID (0-4)

    Returns:
        원본 데이터셋의 카테고리 ID (0, 2, 4, 6, 9)

    Example:
        >>> yolo_id_to_original_id(0)  # blister
        0
        >>> yolo_id_to_original_id(1)  # crack
        2
        >>> yolo_id_to_original_id(4)  # welding_damage
        9
    """
    return ORIGINAL_CATEGORY_MAPPING.get(yolo_id, yolo_id)


def original_id_to_yolo_id(original_id: int) -> int:
    """
    원본 카테고리 ID를 YOLO 학습용 ID(0-4)로 변환

    Args:
        original_id: 원본 데이터셋의 카테고리 ID (0, 2, 4, 6, 9)

    Returns:
        YOLO 학습용 클래스 ID (0-4), 매핑 없으면 -1 반환

    Example:
        >>> original_id_to_yolo_id(0)  # blister
        0
        >>> original_id_to_yolo_id(2)  # crack
        1
        >>> original_id_to_yolo_id(9)  # welding_damage
        4
    """
    # 역매핑 생성
    reverse_mapping = {v: k for k, v in ORIGINAL_CATEGORY_MAPPING.items()}
    return reverse_mapping.get(original_id, -1)


def get_class_info(yolo_id: int) -> dict:
    """
    YOLO ID로 클래스의 모든 정보 조회

    Args:
        yolo_id: YOLO 학습용 ID (0-4)

    Returns:
        클래스 정보 딕셔너리 (name_en, name_kr, original_id)

    Example:
        >>> get_class_info(1)
        {'yolo_id': 1, 'name_en': 'crack', 'name_kr': '균열', 'original_id': 2}
    """
    if 0 <= yolo_id < NUM_CLASSES:
        name_en = CLASS_NAMES[yolo_id]
        return {
            'yolo_id': yolo_id,
            'name_en': name_en,
            'name_kr': CLASS_NAMES_KR[name_en],
            'original_id': ORIGINAL_CATEGORY_MAPPING[yolo_id]
        }
    return None
