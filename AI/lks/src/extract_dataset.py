#!/usr/bin/env python3
"""
Extract ship coating dataset with English directory structure
"""
import os
import sys
import json
import zipfile
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config.dataset_config import CATEGORY_MAP, SUBCATEGORY_MAP

def parse_filename(filename):
    """
    Parse Korean filename to get category and subcategory

    Example: VS_양품_선수.zip -> (normal, bow)
             VS_도막_손상_도막떨어짐.zip -> (coating_damage, peeling)
             VS_도막 손상_도막떨어짐.zip -> (coating_damage, peeling)  # 공백 포함
             VL_양품_선수.zip -> (normal, bow)
    """
    # Remove VS_ or VL_ prefix and .zip extension
    name = filename.replace("VS_", "").replace("VL_", "").replace(".zip", "")

    # 공백을 언더스코어로 변환 (Windows 다운로드 파일명 호환)
    name = name.replace(" ", "_")

    # Split by underscore
    parts = name.split("_")

    if len(parts) < 2:
        print(f"Warning: Cannot parse filename: {filename}")
        return None, None

    # First part(s) are category
    category_kr = parts[0]
    if len(parts) > 2 and parts[0] in ["도막", "도장"]:
        category_kr = f"{parts[0]}_{parts[1]}"
        subcategory_kr = "_".join(parts[2:])
    else:
        subcategory_kr = "_".join(parts[1:])

    # Map to English
    category_en = CATEGORY_MAP.get(category_kr)
    subcategory_en = SUBCATEGORY_MAP.get(subcategory_kr)

    if not category_en or not subcategory_en:
        print(f"Warning: Unknown category or subcategory in {filename}")
        print(f"  Category KR: {category_kr} -> EN: {category_en}")
        print(f"  Subcategory KR: {subcategory_kr} -> EN: {subcategory_en}")
        return None, None

    return category_en, subcategory_en

def normalize_extensions(target_dir, data_type="images"):
    """
    Normalize file extensions to lowercase (.JPG -> .jpg)
    and update JSON file_name fields if data_type is labels

    Args:
        target_dir: Directory to normalize
        data_type: 'images' or 'labels'
    """
    rename_count = 0

    if data_type == "images":
        # Rename .JPG to .jpg
        for jpg_file in Path(target_dir).glob("*.JPG"):
            new_name = jpg_file.with_suffix(".jpg")
            jpg_file.rename(new_name)
            rename_count += 1

    elif data_type == "labels":
        # Update JSON file_name fields
        for json_file in Path(target_dir).glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                modified = False
                if 'images' in data:
                    for img in data['images']:
                        if 'file_name' in img and img['file_name'].endswith('.JPG'):
                            img['file_name'] = img['file_name'].replace('.JPG', '.jpg')
                            modified = True

                if modified:
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    rename_count += 1
            except:
                pass

    if rename_count > 0:
        print(f"  [OK] Normalized {rename_count} file extensions")

def extract_with_structure(zip_path, output_base, data_type="images"):
    """
    Extract ZIP file to organized English directory structure

    Args:
        zip_path: Path to ZIP file
        output_base: Base output directory
        data_type: 'images' or 'labels'
    """
    filename = os.path.basename(zip_path)
    category, subcategory = parse_filename(filename)

    if not category or not subcategory:
        print(f"Skipping {filename} due to parsing error")
        return False

    # Create target directory
    if data_type == "images":
        target_dir = os.path.join(output_base, "01.images", category, subcategory)
    else:
        target_dir = os.path.join(output_base, "02.labels", category, subcategory)

    os.makedirs(target_dir, exist_ok=True)

    print(f"\nExtracting: {filename}")
    print(f"  -> {target_dir}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all files
            zip_ref.extractall(target_dir)

        # Normalize file extensions
        normalize_extensions(target_dir, data_type)

        # Count extracted files
        file_count = len([f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))])
        print(f"  [OK] Extracted {file_count} files")
        return True

    except zipfile.BadZipFile:
        print(f"  [FAIL] Error: Corrupted ZIP file")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False

def find_or_create_data_dir(base_dir: Path, data_type: str = "images") -> Path:
    """
    데이터 디렉토리를 찾거나 없으면 생성

    Args:
        base_dir: AI/lks 기본 디렉토리
        data_type: 'images' 또는 'labels'

    Returns:
        데이터 디렉토리 경로
    """
    # 가능한 경로 패턴들 (공백 유무, 폴더명 변형)
    if data_type == "images":
        possible_paths = [
            "data/raw/194.선박_도장_품질_측정_데이터/01-1.정식개방데이터/Validation/01.원천데이터",
            "data/raw/194.선박_도장_품질_측정_데이터/01-1.정식개방데이터/Validation/01.원천 데이터",
            "data/raw/194.선박 도장 품질 측정 데이터/01-1.정식개방데이터/Validation/01.원천데이터",
            "data/raw/194.선박 도장 품질 측정 데이터/01-1.정식개방데이터/Validation/01.원천 데이터",
        ]
        default_path = "data/raw/194.선박_도장_품질_측정_데이터/01-1.정식개방데이터/Validation/01.원천데이터"
    else:
        possible_paths = [
            "data/raw/194.선박_도장_품질_측정_데이터/01-1.정식개방데이터/Validation/02.라벨링데이터",
            "data/raw/194.선박_도장_품질_측정_데이터/01-1.정식개방데이터/Validation/02.라벨링 데이터",
            "data/raw/194.선박 도장 품질 측정 데이터/01-1.정식개방데이터/Validation/02.라벨링데이터",
            "data/raw/194.선박 도장 품질 측정 데이터/01-1.정식개방데이터/Validation/02.라벨링 데이터",
        ]
        default_path = "data/raw/194.선박_도장_품질_측정_데이터/01-1.정식개방데이터/Validation/02.라벨링데이터"

    # 존재하는 경로 찾기
    for path in possible_paths:
        full_path = base_dir / path
        if full_path.exists():
            return full_path

    # 없으면 기본 경로 생성
    default_full_path = base_dir / default_path
    default_full_path.mkdir(parents=True, exist_ok=True)
    return default_full_path


def main():
    print("=" * 70)
    print("Ship Coating Dataset Extraction with English Structure")
    print("=" * 70)

    # Paths (relative to script location)
    base_dir = Path(__file__).parent.parent  # AI/lks directory
    raw_images_dir = find_or_create_data_dir(base_dir, "images")
    raw_labels_dir = find_or_create_data_dir(base_dir, "labels")
    output_dir = base_dir / "data/extracted"

    print(f"\nInput directory: {raw_images_dir}")
    print(f"Output directory: {output_dir}")

    # Get all ZIP files
    zip_files = sorted(raw_images_dir.glob("*.zip"))

    if not zip_files:
        print("\n" + "=" * 70)
        print("[INFO] No ZIP files found in the directory.")
        print("=" * 70)
        print("\nPlease download the dataset from AI Hub and place ZIP files in:")
        print(f"  {raw_images_dir}")
        print(f"  {raw_labels_dir}")
        print("\nDownload link: https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&dataSetSn=194")
        print("\nExpected ZIP files format:")
        print("  - VS_양품_선수.zip")
        print("  - VS_도막_손상_도막떨어짐.zip")
        print("  - VL_양품_선수.zip (labels)")
        print("  - etc.")
        print("\nDirectories have been created. Please add the data and run again.")
        return

    print(f"\nFound {len(zip_files)} ZIP files")

    # Extract images
    print("\n" + "=" * 70)
    print("EXTRACTING IMAGES (01.원천데이터)")
    print("=" * 70)

    success_count = 0
    error_count = 0

    for zip_path in zip_files:
        if extract_with_structure(str(zip_path), str(output_dir), data_type="images"):
            success_count += 1
        else:
            error_count += 1

    # Extract labels if available
    if raw_labels_dir.exists():
        label_zips = sorted(raw_labels_dir.glob("*.zip"))

        if label_zips:
            print("\n" + "=" * 70)
            print("EXTRACTING LABELS (02.라벨링데이터)")
            print("=" * 70)

            for zip_path in label_zips:
                if extract_with_structure(str(zip_path), str(output_dir), data_type="labels"):
                    success_count += 1
                else:
                    error_count += 1

    # Summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")

    # Show directory structure
    print("\n" + "=" * 70)
    print("DIRECTORY STRUCTURE")
    print("=" * 70)

    for root, dirs, files in os.walk(output_dir):
        level = root.replace(str(output_dir), '').count(os.sep)
        indent = ' ' * 2 * level
        folder_name = os.path.basename(root)
        print(f'{indent}{folder_name}/')

        if level < 3:  # Don't show files for top levels
            sub_indent = ' ' * 2 * (level + 1)
            file_count = len(files)
            if file_count > 0:
                print(f'{sub_indent}({file_count} files)')

if __name__ == "__main__":
    main()
