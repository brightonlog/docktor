#!/usr/bin/env python3
"""
Extract and Organize KYR Dataset (Validation Data)
AI Hub에서 다운로드 받은 ZIP 파일을 압축 해제하고,
Category/Subcategory 구조로 data/processed/extracted 폴더에 정리하는 스크립트

Usage:
    python src/extract_dataset.py [--source PATH]

Options:
    --source: ZIP 파일이 있는 경로 (기본값: data/raw 또는 SafeDeck_Data)
"""

import os
import sys
import argparse
import zipfile
from pathlib import Path
from tqdm import tqdm

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config.dataset_config import CATEGORY_MAP, SUBCATEGORY_MAP

# 경로 설정 (AI/kyr 기준)
BASE_DIR = Path(__file__).parent.parent
EXTRACTED_DIR = BASE_DIR / "data" / "processed" / "extracted"
IMAGES_DIR = EXTRACTED_DIR / "images"
LABELS_DIR = EXTRACTED_DIR / "labels"

# 기본 데이터 소스 경로들
DEFAULT_RAW_DIR = BASE_DIR / "data" / "raw"
SAFEDECK_DATA_DIR = Path("C:/Users/SSAFY/Desktop/SafeDeck_Data/194.선박 도장 품질 측정 데이터/01-1.정식개방데이터/Validation")


def parse_filename(filename):
    """
    파일명에서 카테고리와 서브카테고리 추출

    Example:
        VS_양품_선수.zip -> (normal, bow)
        VS_도막_손상_도막떨어짐.zip -> (coating_damage, peeling)
        VS_도막 손상_도막떨어짐.zip -> (coating_damage, peeling)  # 공백 있는 경우
        VL_양품_선수.zip -> (normal, bow)
    """
    # 접두사 제거 (VS: Validation Source, VL: Validation Label)
    name = filename.replace("VS_", "").replace("VL_", "").replace(".zip", "")

    # 공백을 언더스코어로 변환 (일부 파일명에 공백이 있음)
    name = name.replace(" ", "_")

    # 언더스코어로 분리
    parts = name.split("_")

    if len(parts) < 2:
        print(f"Warning: Cannot parse filename: {filename}")
        return None, None

    # 카테고리 추출 (도막_손상, 도장_불량 처리)
    category_kr = parts[0]
    if len(parts) > 2 and parts[0] in ["도막", "도장"]:
        category_kr = f"{parts[0]}_{parts[1]}"
        subcategory_kr = "_".join(parts[2:])
    else:
        subcategory_kr = "_".join(parts[1:])

    # 영어로 매핑
    category_en = CATEGORY_MAP.get(category_kr)
    subcategory_en = SUBCATEGORY_MAP.get(subcategory_kr)

    # 부분 매칭 시도
    if not subcategory_en:
        for k, v in SUBCATEGORY_MAP.items():
            if k in subcategory_kr:
                subcategory_en = v
                break

    if not category_en or not subcategory_en:
        print(f"Warning: Unknown category or subcategory in {filename}")
        print(f"  Category KR: {category_kr} -> EN: {category_en}")
        print(f"  Subcategory KR: {subcategory_kr} -> EN: {subcategory_en}")
        return None, None

    return category_en, subcategory_en


def extract_zip_file(zip_path, target_dir):
    """ZIP 파일을 지정된 디렉토리에 압축 해제"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            for file in tqdm(file_list, desc=f"  Extracting {zip_path.name}", leave=False):
                try:
                    # 한글 파일명 인코딩 처리
                    try:
                        decoded_name = file.encode('cp437').decode('euc-kr')
                    except:
                        try:
                            decoded_name = file.encode('cp437').decode('utf-8')
                        except:
                            decoded_name = file

                    # 파일명 정리 (경로 구분자 통일, 선행 슬래시 제거)
                    decoded_name = decoded_name.replace('\\', '/')
                    decoded_name = decoded_name.lstrip('/')

                    # 파일명만 추출 (하위 폴더 구조 무시)
                    filename_only = os.path.basename(decoded_name)
                    if not filename_only:
                        continue  # 디렉토리 엔트리 건너뛰기

                    # 파일 추출
                    data = zip_ref.read(file)
                    target_path = target_dir / filename_only

                    if not file.endswith('/'):
                        with open(target_path, 'wb') as f:
                            f.write(data)
                except Exception as e:
                    print(f"    Error extracting {file}: {e}")
                    continue
        return True
    except zipfile.BadZipFile:
        print(f"  Error: Corrupted ZIP file - {zip_path.name}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def find_zip_files(source_path=None):
    """ZIP 파일들을 찾아서 이미지/라벨로 분류하여 반환"""
    image_zips = []
    label_zips = []

    # 소스 경로 결정
    if source_path:
        source = Path(source_path)
        if source.exists():
            # 단일 폴더인 경우 직접 검색
            if (source / "01.원천데이터").exists():
                image_dir = source / "01.원천데이터"
                label_dir = source / "02.라벨링데이터"
            else:
                image_dir = source
                label_dir = source
        else:
            print(f"[ERROR] Source path not found: {source}")
            return [], []
    elif SAFEDECK_DATA_DIR.exists():
        # SafeDeck_Data 폴더가 있으면 사용
        image_dir = SAFEDECK_DATA_DIR / "01.원천데이터"
        label_dir = SAFEDECK_DATA_DIR / "02.라벨링데이터"
        print(f"Using SafeDeck_Data: {SAFEDECK_DATA_DIR}")
    elif DEFAULT_RAW_DIR.exists():
        # data/raw 폴더 사용
        image_dir = DEFAULT_RAW_DIR
        label_dir = DEFAULT_RAW_DIR
        print(f"Using data/raw: {DEFAULT_RAW_DIR}")
    else:
        print("[ERROR] No data source found!")
        print(f"  - SafeDeck_Data: {SAFEDECK_DATA_DIR}")
        print(f"  - data/raw: {DEFAULT_RAW_DIR}")
        return [], []

    # ZIP 파일 수집
    if image_dir.exists():
        for z in sorted(image_dir.glob("*.zip")):
            if "VS" in z.name or "Source" in z.name:
                image_zips.append(z)

    if label_dir.exists():
        for z in sorted(label_dir.glob("*.zip")):
            if "VL" in z.name or "Label" in z.name:
                label_zips.append(z)

    return image_zips, label_zips


def main():
    parser = argparse.ArgumentParser(description='Extract and organize KYR dataset')
    parser.add_argument('--source', type=str, default=None,
                        help='Path to ZIP files (default: SafeDeck_Data or data/raw)')
    args = parser.parse_args()

    print("=" * 70)
    print("KYR Dataset Extraction & Organization")
    print("=" * 70)

    # ZIP 파일 찾기
    image_zips, label_zips = find_zip_files(args.source)

    if not image_zips and not label_zips:
        print("\n[ERROR] No ZIP files found!")
        return

    print(f"\nFound ZIP files:")
    print(f"  - Image ZIPs (VS): {len(image_zips)}")
    print(f"  - Label ZIPs (VL): {len(label_zips)}")

    # 출력 디렉토리 생성
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0

    # 이미지 ZIP 처리
    if image_zips:
        print("\n" + "=" * 70)
        print("EXTRACTING IMAGES")
        print("=" * 70)

        for zip_path in image_zips:
            category, subcategory = parse_filename(zip_path.name)
            if not category or not subcategory:
                error_count += 1
                continue

            target_dir = IMAGES_DIR / category / subcategory
            target_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n{zip_path.name}")
            print(f"  -> {target_dir.relative_to(BASE_DIR)}")

            if extract_zip_file(zip_path, target_dir):
                success_count += 1
            else:
                error_count += 1

    # 라벨 ZIP 처리
    if label_zips:
        print("\n" + "=" * 70)
        print("EXTRACTING LABELS")
        print("=" * 70)

        for zip_path in label_zips:
            category, subcategory = parse_filename(zip_path.name)
            if not category or not subcategory:
                error_count += 1
                continue

            target_dir = LABELS_DIR / category / subcategory
            target_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n{zip_path.name}")
            print(f"  -> {target_dir.relative_to(BASE_DIR)}")

            if extract_zip_file(zip_path, target_dir):
                success_count += 1
            else:
                error_count += 1

    # 결과 요약
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    print(f"\nExtracted to: {EXTRACTED_DIR}")

    # 디렉토리 구조 출력
    print("\n" + "=" * 70)
    print("DIRECTORY STRUCTURE")
    print("=" * 70)

    for root, dirs, files in os.walk(EXTRACTED_DIR):
        level = root.replace(str(EXTRACTED_DIR), '').count(os.sep)
        indent = '  ' * level
        folder_name = os.path.basename(root)
        file_count = len(files)

        if level < 3:
            if file_count > 0:
                print(f'{indent}{folder_name}/ ({file_count} files)')
            else:
                print(f'{indent}{folder_name}/')


if __name__ == "__main__":
    main()
