#!/usr/bin/env python3
"""
Reorganize KYR dataset to match LKS structure (Category/Subcategory)
kyr 폴더의 images, labels 데이터를 lks 폴더와 동일한 계층 구조로 정리하는 스크립트
"""
import os
import shutil
from pathlib import Path

# 현재 스크립트 위치 기준 경로 설정 (AI/kyr/)
BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
LABELS_DIR = BASE_DIR / "labels"

# LKS 폴더와 동일한 매핑 정보 (config/dataset_config.py 및 rename_to_english.py 참조)
CATEGORY_MAP = {
    "도막손상": "coating_damage",
    "도막_손상": "coating_damage",
    "도장불량": "painting_defect",
    "도장_불량": "painting_defect",
    "양품": "normal"
}

SUBCATEGORY_MAP = {
    # Coating Damage
    "도막떨어짐": "peeling",
    "스크래치": "scratch",
    "용접손상": "welding_damage",
    
    # Painting Defect
    "균열": "crack",
    "도막분리": "coating_separation",
    "부풀음": "blister",
    "워터스포팅": "water_spotting",
    "이물질포함": "foreign_material",
    "핀홀": "pinhole",
    "흐름": "sagging",
    
    # Normal
    "갑판": "deck",
    "기관실": "engine_room",
    "선미": "stern",
    "선수": "bow",
    "선실": "cabin",
    "엔진커버": "engine_cover",
    "외판": "outer_plate",
    "탱크": "tank",
    "파이프": "pipe",
    "해치커버": "hatch_cover"
}

def parse_filename(filename):
    """
    파일명에서 카테고리와 서브카테고리 추출
    예: VS_양품_선수.jpg -> (normal, bow)
    """
    # 확장자 제거 및 접두사 제거
    name = os.path.splitext(filename)[0]
    for prefix in ["VS_", "VL_", "TS_", "TL_"]:
        name = name.replace(prefix, "")
    
    parts = name.split("_")
    if len(parts) < 2:
        return None, None

    # 카테고리 파싱
    category_kr = parts[0]
    if len(parts) > 2 and parts[0] in ["도막", "도장"]:
        category_kr = f"{parts[0]}_{parts[1]}"
        subcategory_kr = "_".join(parts[2:])
    else:
        subcategory_kr = "_".join(parts[1:])

    # 영문 매핑
    category_en = CATEGORY_MAP.get(category_kr)
    subcategory_en = SUBCATEGORY_MAP.get(subcategory_kr)
    
    # 서브카테고리 부분 일치 검색 (파일명에 추가 정보가 있는 경우 대비)
    if not subcategory_en:
        for k, v in SUBCATEGORY_MAP.items():
            if k in subcategory_kr:
                subcategory_en = v
                break

    return category_en, subcategory_en

def reorganize_directory(target_dir):
    """디렉토리 내 파일들을 카테고리별 폴더로 이동"""
    if not target_dir.exists():
        print(f"[WARNING] Directory not found: {target_dir}")
        return

    print(f"\nProcessing {target_dir}...")
    
    # 루트에 있는 파일만 대상 (이미 폴더 안에 있는 것은 건너뜀)
    files = [f for f in target_dir.iterdir() if f.is_file()]
    
    if not files:
        print(f"  No files found in root of {target_dir.name}")
        return

    success_count = 0
    skip_count = 0

    for file_path in files:
        if file_path.name.startswith("."): 
            continue
            
        category, subcategory = parse_filename(file_path.name)
        
        if category and subcategory:
            # 목표 디렉토리 생성: images/category/subcategory
            dest_dir = target_dir / category / subcategory
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(str(file_path), str(dest_dir / file_path.name))
                success_count += 1
            except Exception as e:
                print(f"  Error moving {file_path.name}: {e}")
                skip_count += 1
        else:
            skip_count += 1

    print(f"  ✓ Moved: {success_count} files")
    print(f"  - Skipped: {skip_count} files")

def main():
    print("=" * 60)
    print("KYR Dataset Reorganization (Matching LKS Structure)")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    
    # images 폴더 정리
    reorganize_directory(IMAGES_DIR)
    
    # labels 폴더 정리
    reorganize_directory(LABELS_DIR)
    
    print("\nDone.")

if __name__ == "__main__":
    main()
