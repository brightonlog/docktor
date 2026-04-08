"""
Dataset Configuration
Central configuration for category mappings, colors, and labels
(LKS 폴더와 동일한 구조)
"""

# Korean to English mapping for directory structure
CATEGORY_MAP = {
    "양품": "normal",
    "도막손상": "coating_damage",
    "도막_손상": "coating_damage",
    "도장불량": "painting_defect",
    "도장_불량": "painting_defect"
}

SUBCATEGORY_MAP = {
    # Normal subcategories
    "선수": "bow",
    "갑판": "deck",
    "외판": "outer_plate",
    "선미": "stern",
    "선실": "cabin",
    "기관실": "engine_room",
    "엔진커버": "engine_cover",
    "탱크": "tank",
    "파이프": "pipe",
    "해치커버": "hatch_cover",

    # Coating damage subcategories
    "도막떨어짐": "peeling",
    "스크래치": "scratch",
    "용접손상": "welding_damage",

    # Painting defect subcategories
    "워터스포팅": "water_spotting",
    "이물질포함": "foreign_material",
    "핀홀": "pinhole",
    "흐름": "sagging",
    "도막분리": "coating_separation",
    "부풀음": "blister",
    "균열": "crack"
}

# Category ID to English name mapping (for YOLO labels)
CATEGORIES = {
    101: 'Normal',
    201: 'Water Spotting',
    202: 'Sagging',
    203: 'Coating Separation',
    204: 'Pinhole',
    205: 'Crack',
    206: 'Blister',
    207: 'Foreign Material',
    301: 'Welding Damage',
    302: 'Scratch',
    303: 'Peeling'
}

# Category ID to Korean name mapping
CATEGORIES_KR = {
    101: '정상',
    201: '워터스포팅',
    202: '흐름',
    203: '도막분리',
    204: '핀홀',
    205: '균열',
    206: '부풀음',
    207: '이물질포함',
    301: '용접손상',
    302: '스크래치',
    303: '도막떨어짐'
}

# Colors for visualization (RGB format)
COLORS_RGB = {
    101: (0, 255, 0),      # Normal - Green
    201: (0, 0, 255),      # Water Spotting - Blue
    202: (255, 165, 0),    # Sagging - Orange
    203: (255, 255, 0),    # Coating Separation - Yellow
    204: (255, 0, 255),    # Pinhole - Magenta
    205: (255, 0, 0),      # Crack - Red
    206: (0, 255, 255),    # Blister - Cyan
    207: (128, 0, 128),    # Foreign Material - Purple
    301: (0, 165, 255),    # Welding Damage - Sky
    302: (255, 128, 0),    # Scratch - Orange-Red
    303: (128, 128, 128)   # Peeling - Gray
}
