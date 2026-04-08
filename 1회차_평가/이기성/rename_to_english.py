import os
import shutil
from pathlib import Path

# 한글-영어 매핑 테이블
TRANSLATION_MAP = {
    # 최상위 폴더
    "01.원천데이터": "01.images",
    "02.라벨링데이터": "02.labels",

    # 대분류
    "도막 손상": "coating_damage",
    "도장 불량": "painting_defect",
    "양품": "normal",

    # 도막 손상 세부
    "도막떨어짐": "peeling",
    "스크래치": "scratch",
    "용접손상": "welding_damage",

    # 도장 불량 세부
    "균열": "crack",
    "도막분리": "coating_separation",
    "부풀음": "blister",
    "워터스포팅": "water_spotting",
    "이물질포함": "foreign_material",
    "핀홀": "pinhole",
    "흐름": "sagging",

    # 양품 세부
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

def translate_path(korean_path):
    """한글 경로를 영어로 변환"""
    parts = korean_path.split(os.sep)
    translated_parts = []

    for part in parts:
        if part in TRANSLATION_MAP:
            translated_parts.append(TRANSLATION_MAP[part])
        else:
            translated_parts.append(part)

    return os.sep.join(translated_parts)

def copy_with_english_names(src_root, dst_root):
    """한글 경로를 영어로 변환하여 복사"""
    src_root = Path(src_root)
    dst_root = Path(dst_root)

    if not src_root.exists():
        print(f"Error: Source directory {src_root} does not exist!")
        return False

    # 대상 디렉토리가 이미 존재하면 삭제할지 확인
    if dst_root.exists():
        print(f"Warning: Destination {dst_root} already exists. Removing it...")
        shutil.rmtree(dst_root)

    # 모든 파일과 디렉토리를 순회
    file_count = 0
    error_count = 0

    for src_path in src_root.rglob('*'):
        if src_path.is_file():
            # 상대 경로 계산
            relative_path = src_path.relative_to(src_root)

            # 경로를 영어로 변환
            english_relative_path = translate_path(str(relative_path))

            # 대상 경로 생성
            dst_path = dst_root / english_relative_path

            # 디렉토리 생성
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # 파일 복사
                shutil.copy2(src_path, dst_path)
                file_count += 1

                if file_count % 50 == 0:
                    print(f"Copied {file_count} files...")

            except Exception as e:
                print(f"Error copying {src_path} to {dst_path}: {e}")
                error_count += 1

    print(f"\n=== Copy Complete ===")
    print(f"Total files copied: {file_count}")
    print(f"Errors: {error_count}")

    return error_count == 0

def verify_structure(root_dir):
    """디렉토리 구조 검증"""
    root = Path(root_dir)

    if not root.exists():
        print(f"Directory {root} does not exist!")
        return False

    print(f"\n=== Directory Structure: {root} ===")

    # 파일 수 카운트
    file_counts = {}

    for item in root.rglob('*'):
        if item.is_file():
            # 카테고리 경로 추출 (상위 2개 폴더)
            parts = item.relative_to(root).parts
            if len(parts) >= 3:
                category = f"{parts[0]}/{parts[1]}/{parts[2]}"
                file_counts[category] = file_counts.get(category, 0) + 1

    # 정렬하여 출력
    for category in sorted(file_counts.keys()):
        print(f"{category}: {file_counts[category]} files")

    total_files = sum(file_counts.values())
    print(f"\nTotal files: {total_files}")

    return True

def main():
    print("=" * 60)
    print("Korean to English Path Converter for Ship Coating Dataset")
    print("=" * 60)

    src_dir = "Sample"
    dst_dir = "Dataset"

    print(f"\nSource: {src_dir}")
    print(f"Destination: {dst_dir}")
    print("\nTranslation mapping:")
    for korean, english in sorted(TRANSLATION_MAP.items()):
        print(f"  {korean} -> {english}")

    print("\n" + "=" * 60)
    print("Starting file copy process...")
    print("=" * 60 + "\n")

    # 파일 복사
    success = copy_with_english_names(src_dir, dst_dir)

    if success:
        print("\n[SUCCESS] Files copied successfully!")

        # 원본과 변환된 구조 검증
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        print("\n[Original Structure]")
        verify_structure(src_dir)

        print("\n[New English Structure]")
        verify_structure(dst_dir)

        print("\n" + "=" * 60)
        print("[SUCCESS] Conversion completed successfully!")
        print(f"[SUCCESS] New dataset location: {dst_dir}")
        print("=" * 60)
    else:
        print("\n[ERROR] Some errors occurred during copying.")

if __name__ == "__main__":
    main()