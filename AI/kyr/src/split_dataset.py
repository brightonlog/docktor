#!/usr/bin/env python3
"""
Split Dataset into Train/Val
추출된 데이터(data/processed/extracted)를 train/val로 분할하여
data/processed/train, data/processed/val 폴더에 저장하는 스크립트

Usage:
    python src/split_dataset.py [--ratio 0.8] [--seed 42] [--copy]

Arguments:
    --ratio: Train 데이터 비율 (기본값: 0.8 = 80% train, 20% val)
    --seed: Random seed for reproducibility (기본값: 42)
    --copy: 파일을 복사 (기본값: 이동)
"""

import os
import sys
import random
import shutil
import argparse
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

# 경로 설정 (AI/kyr 기준)
BASE_DIR = Path(__file__).parent.parent
EXTRACTED_DIR = BASE_DIR / "data" / "processed" / "extracted"
TRAIN_DIR = BASE_DIR / "data" / "processed" / "train"
VAL_DIR = BASE_DIR / "data" / "processed" / "val"


def get_image_label_pairs(images_dir, labels_dir):
    """
    이미지-라벨 쌍을 찾아서 반환

    Returns:
        dict: {(category, subcategory): [(image_path, label_path), ...]}
    """
    pairs = defaultdict(list)

    if not images_dir.exists():
        return pairs

    # 모든 카테고리/서브카테고리 순회
    for category_dir in images_dir.iterdir():
        if not category_dir.is_dir():
            continue
        category = category_dir.name

        for subcategory_dir in category_dir.iterdir():
            if not subcategory_dir.is_dir():
                continue
            subcategory = subcategory_dir.name

            # 해당 서브카테고리의 이미지 파일들
            for img_file in subcategory_dir.iterdir():
                if not img_file.is_file():
                    continue
                if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                    continue

                # 대응하는 라벨 파일 찾기
                label_path = labels_dir / category / subcategory / (img_file.stem + '.json')

                if label_path.exists():
                    pairs[(category, subcategory)].append((img_file, label_path))
                else:
                    # 라벨이 없는 이미지도 포함 (Normal 카테고리 등)
                    pairs[(category, subcategory)].append((img_file, None))

    return pairs


def split_and_move(pairs, train_ratio, seed, use_copy=False):
    """
    데이터를 train/val로 분할하여 이동/복사
    """
    random.seed(seed)

    total_train = 0
    total_val = 0

    action = shutil.copy2 if use_copy else shutil.move
    action_name = "Copying" if use_copy else "Moving"

    print(f"\n{action_name} files (train_ratio={train_ratio}, seed={seed})...")

    for (category, subcategory), file_pairs in pairs.items():
        if not file_pairs:
            continue

        # 셔플 후 분할
        random.shuffle(file_pairs)
        split_idx = int(len(file_pairs) * train_ratio)

        train_pairs = file_pairs[:split_idx]
        val_pairs = file_pairs[split_idx:]

        print(f"\n{category}/{subcategory}: {len(train_pairs)} train, {len(val_pairs)} val")

        # Train 데이터 처리
        train_img_dir = TRAIN_DIR / "images" / category / subcategory
        train_lbl_dir = TRAIN_DIR / "labels" / category / subcategory
        train_img_dir.mkdir(parents=True, exist_ok=True)
        train_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path, lbl_path in tqdm(train_pairs, desc="  Train", leave=False):
            action(img_path, train_img_dir / img_path.name)
            if lbl_path and lbl_path.exists():
                action(lbl_path, train_lbl_dir / lbl_path.name)

        total_train += len(train_pairs)

        # Val 데이터 처리
        val_img_dir = VAL_DIR / "images" / category / subcategory
        val_lbl_dir = VAL_DIR / "labels" / category / subcategory
        val_img_dir.mkdir(parents=True, exist_ok=True)
        val_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path, lbl_path in tqdm(val_pairs, desc="  Val", leave=False):
            action(img_path, val_img_dir / img_path.name)
            if lbl_path and lbl_path.exists():
                action(lbl_path, val_lbl_dir / lbl_path.name)

        total_val += len(val_pairs)

    return total_train, total_val


def print_directory_structure(base_dir, max_depth=3):
    """디렉토리 구조 출력"""
    for root, dirs, files in os.walk(base_dir):
        level = root.replace(str(base_dir), '').count(os.sep)
        if level >= max_depth:
            continue
        indent = '  ' * level
        folder_name = os.path.basename(root)
        file_count = len(files)

        if file_count > 0:
            print(f'{indent}{folder_name}/ ({file_count} files)')
        else:
            print(f'{indent}{folder_name}/')


def main():
    parser = argparse.ArgumentParser(description='Split dataset into train/val')
    parser.add_argument('--ratio', type=float, default=0.8,
                        help='Train data ratio (default: 0.8)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    parser.add_argument('--copy', action='store_true',
                        help='Copy files instead of moving')
    args = parser.parse_args()

    print("=" * 70)
    print("KYR Dataset Split (Train/Val)")
    print("=" * 70)

    # 추출된 데이터 확인
    images_dir = EXTRACTED_DIR / "images"
    labels_dir = EXTRACTED_DIR / "labels"

    if not images_dir.exists():
        print(f"\n[ERROR] Extracted images not found: {images_dir}")
        print("Please run extract_dataset.py first.")
        return

    print(f"\nSource: {EXTRACTED_DIR}")
    print(f"Train output: {TRAIN_DIR}")
    print(f"Val output: {VAL_DIR}")

    # 이미지-라벨 쌍 수집
    print("\nCollecting image-label pairs...")
    pairs = get_image_label_pairs(images_dir, labels_dir)

    total_pairs = sum(len(p) for p in pairs.values())
    print(f"Found {total_pairs} image-label pairs across {len(pairs)} subcategories")

    if total_pairs == 0:
        print("\n[ERROR] No data found to split!")
        return

    # 출력 디렉토리 초기화
    if TRAIN_DIR.exists():
        shutil.rmtree(TRAIN_DIR)
    if VAL_DIR.exists():
        shutil.rmtree(VAL_DIR)

    # 분할 및 이동/복사
    total_train, total_val = split_and_move(
        pairs,
        args.ratio,
        args.seed,
        use_copy=args.copy
    )

    # 결과 요약
    print("\n" + "=" * 70)
    print("SPLIT COMPLETE")
    print("=" * 70)
    print(f"Train: {total_train} samples ({args.ratio*100:.0f}%)")
    print(f"Val: {total_val} samples ({(1-args.ratio)*100:.0f}%)")
    print(f"Total: {total_train + total_val} samples")

    # 디렉토리 구조 출력
    print("\n" + "=" * 70)
    print("TRAIN DIRECTORY STRUCTURE")
    print("=" * 70)
    print_directory_structure(TRAIN_DIR)

    print("\n" + "=" * 70)
    print("VAL DIRECTORY STRUCTURE")
    print("=" * 70)
    print_directory_structure(VAL_DIR)

    # extracted 폴더 정리 (이동 모드인 경우)
    if not args.copy:
        print("\n" + "=" * 70)
        print("CLEANUP")
        print("=" * 70)
        # 빈 폴더 삭제
        for dirpath, dirnames, filenames in os.walk(EXTRACTED_DIR, topdown=False):
            if not dirnames and not filenames:
                os.rmdir(dirpath)
                print(f"Removed empty: {dirpath}")


if __name__ == "__main__":
    main()
