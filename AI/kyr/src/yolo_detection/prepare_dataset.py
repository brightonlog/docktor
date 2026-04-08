"""
JSON (COCO-like) to YOLO format converter for ship painting defect detection
Filters only 5 target classes: sagging, crack, blister, welding_damage, peeling
"""

import json
import os
import shutil
from pathlib import Path
from tqdm import tqdm


# 5개 타겟 클래스 매핑 (원본 category_id -> YOLO class_id)
# 원본 데이터셋 ID 순서에 맞춤: blister(0), crack(2), peeling(4), sagging(6), welding_damage(9)
TARGET_CLASSES = {
    206: 0,  # blister (부풀음) - 원본 id: 0
    205: 1,  # crack (균열) - 원본 id: 2
    303: 2,  # peeling (도막떨어짐) - 원본 id: 4
    202: 3,  # sagging (흐름) - 원본 id: 6
    301: 4,  # welding_damage (용접손상) - 원본 id: 9
}

CLASS_NAMES = ['blister', 'crack', 'peeling', 'sagging', 'welding_damage']

# 클래스별 원본 폴더 매핑
CLASS_FOLDERS = {
    206: ('painting_defect', 'blister'),
    205: ('painting_defect', 'crack'),
    303: ('coating_damage', 'peeling'),
    202: ('painting_defect', 'sagging'),
    301: ('coating_damage', 'welding_damage'),
}


def convert_bbox_to_yolo(bbox, img_width, img_height):
    """
    COCO bbox [x, y, width, height] -> YOLO [x_center, y_center, width, height] (normalized)
    """
    x, y, w, h = bbox
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    w_norm = w / img_width
    h_norm = h / img_height

    # Clamp values to [0, 1]
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    w_norm = max(0, min(1, w_norm))
    h_norm = max(0, min(1, h_norm))

    return x_center, y_center, w_norm, h_norm


def process_json_label(json_path):
    """
    JSON 레이블 파일을 읽고 YOLO 형식으로 변환
    Returns: (image_info, yolo_annotations) or (None, None) if no target class
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not data.get('images') or not data.get('annotations'):
        return None, None

    image_info = data['images'][0]
    img_width = image_info['width']
    img_height = image_info['height']

    yolo_annotations = []

    for ann in data['annotations']:
        category_id = ann['category_id']

        # 타겟 클래스만 처리
        if category_id not in TARGET_CLASSES:
            continue

        yolo_class_id = TARGET_CLASSES[category_id]
        bbox = ann['bbox']

        x_center, y_center, w_norm, h_norm = convert_bbox_to_yolo(
            bbox, img_width, img_height
        )

        yolo_annotations.append(f"{yolo_class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

    if not yolo_annotations:
        return None, None

    return image_info, yolo_annotations


def prepare_yolo_dataset(
    source_base: str,
    output_base: str,
    split: str = 'train'
):
    """
    원본 데이터셋을 YOLO 형식으로 변환
    """
    source_path = Path(source_base) / split
    output_path = Path(output_base) / split

    # 출력 폴더 생성
    (output_path / 'images').mkdir(parents=True, exist_ok=True)
    (output_path / 'labels').mkdir(parents=True, exist_ok=True)

    stats = {name: 0 for name in CLASS_NAMES}
    total_images = 0

    for category_id, (main_cat, sub_cat) in CLASS_FOLDERS.items():
        label_folder = source_path / 'labels' / main_cat / sub_cat
        image_folder = source_path / 'images' / main_cat / sub_cat

        if not label_folder.exists():
            print(f"Warning: {label_folder} does not exist, skipping...")
            continue

        json_files = list(label_folder.glob('*.json'))
        print(f"\nProcessing {sub_cat}: {len(json_files)} files")

        for json_file in tqdm(json_files, desc=f"  {sub_cat}"):
            image_info, yolo_annotations = process_json_label(json_file)

            if image_info is None:
                continue

            # 이미지 파일 찾기
            image_name = image_info['file_name']
            image_src = image_folder / image_name

            if not image_src.exists():
                # 확장자 변경 시도
                for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                    alt_name = image_name.rsplit('.', 1)[0] + ext
                    alt_src = image_folder / alt_name
                    if alt_src.exists():
                        image_src = alt_src
                        image_name = alt_name
                        break

            if not image_src.exists():
                continue

            # 파일 복사 (이름 충돌 방지를 위해 prefix 추가)
            unique_prefix = f"{sub_cat}_{json_file.stem}"
            new_image_name = f"{unique_prefix}.jpg"
            new_label_name = f"{unique_prefix}.txt"

            # 이미지 복사
            shutil.copy2(image_src, output_path / 'images' / new_image_name)

            # YOLO 레이블 저장
            with open(output_path / 'labels' / new_label_name, 'w') as f:
                f.write('\n'.join(yolo_annotations))

            # 통계 업데이트
            for ann in yolo_annotations:
                class_id = int(ann.split()[0])
                stats[CLASS_NAMES[class_id]] += 1

            total_images += 1

    return total_images, stats


def create_data_yaml(output_base: str, yaml_path: str):
    """
    YOLO data.yaml 파일 생성
    """
    # CLASS_NAMES와 일치하도록 수정
    # CLASS_NAMES = ['blister', 'crack', 'peeling', 'sagging', 'welding_damage']
    yaml_content = f"""# Ship Painting Defect Detection Dataset
# 5 Classes: blister, crack, peeling, sagging, welding_damage

path: {output_base}
train: train/images
val: val/images

# Classes (TARGET_CLASSES 매핑과 일치)
names:
  0: blister
  1: crack
  2: peeling
  3: sagging
  4: welding_damage

# Number of classes
nc: 5
"""

    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    print(f"\nCreated data.yaml at {yaml_path}")


def main():
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent
    source_base = base_dir / 'data' / 'processed'
    output_base = base_dir / 'data' / 'yolo_dataset'

    print("=" * 60)
    print("Ship Painting Defect Dataset Preparation")
    print("Target Classes: sagging, crack, blister, welding_damage, peeling")
    print("=" * 60)

    # Train/Val 데이터 처리
    for split in ['train', 'val']:
        print(f"\n{'='*40}")
        print(f"Processing {split} split...")
        print(f"{'='*40}")

        total, stats = prepare_yolo_dataset(
            str(source_base),
            str(output_base),
            split
        )

        print(f"\n{split.upper()} Results:")
        print(f"  Total images: {total}")
        print("  Annotations per class:")
        for name, count in stats.items():
            print(f"    - {name}: {count}")

    # data.yaml 생성
    create_data_yaml(str(output_base), str(output_base / 'data.yaml'))

    print("\n" + "=" * 60)
    print("Dataset preparation completed!")
    print(f"Output directory: {output_base}")
    print("=" * 60)


if __name__ == '__main__':
    main()
