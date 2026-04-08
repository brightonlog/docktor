"""
클래스별 폴더 정리 스크립트
- images/train, images/val 내 파일들을 클래스별 폴더로 이동
- labels/train, labels/val 내 파일들도 동일하게 이동
"""

import os
import shutil
from collections import defaultdict

base_path = r'C:\Users\SSAFY\Desktop\S14P11E201\AI\kyr'

# 클래스 코드 -> 클래스 이름 매핑
class_map = {
    '201': 'WaterSpotting',
    '202': 'Sagging',
    '203': 'Peeling',
    '204': 'Pinhole',
    '205': 'Crack',
    '206': 'Blistering',
    '207': 'Inclusion',
    '301': 'WeldingDamage',
    '302': 'Scratch',
    '303': 'Corrosion'
}


def organize_by_class(split='train'):
    """이미지와 라벨을 클래스별 폴더로 이동"""
    img_dir = os.path.join(base_path, 'images', split)
    lbl_dir = os.path.join(base_path, 'labels', split)

    # 클래스별 폴더 생성 (images와 labels 모두)
    for class_name in class_map.values():
        os.makedirs(os.path.join(img_dir, class_name), exist_ok=True)
        os.makedirs(os.path.join(lbl_dir, class_name), exist_ok=True)

    # 이미지 파일 목록 (폴더 제외, 파일만)
    img_files = [f for f in os.listdir(img_dir)
                 if f.endswith(('.jpg', '.jpeg', '.png')) and os.path.isfile(os.path.join(img_dir, f))]

    stats = defaultdict(int)
    unknown_files = []

    print(f"\n[{split.upper()}] 총 {len(img_files)}개 파일 처리 중...")

    for f in img_files:
        # 파일명에서 클래스 코드 추출 (예: 204_13_xxx.jpg -> 204)
        code = f.split('_')[0]
        class_name = class_map.get(code)

        if class_name is None:
            unknown_files.append(f)
            continue

        # 이미지 이동
        src_img = os.path.join(img_dir, f)
        dst_img = os.path.join(img_dir, class_name, f)
        shutil.move(src_img, dst_img)

        # 라벨 이동
        lbl_name = os.path.splitext(f)[0] + '.txt'
        src_lbl = os.path.join(lbl_dir, lbl_name)
        dst_lbl = os.path.join(lbl_dir, class_name, lbl_name)
        if os.path.exists(src_lbl):
            shutil.move(src_lbl, dst_lbl)

        stats[class_name] += 1

    # 결과 출력
    print(f"\n=== {split.upper()} 데이터 이동 완료 ===")
    for cls, count in sorted(stats.items()):
        print(f"  {cls}: {count}장")
    print(f"  ---------------------")
    print(f"  총: {sum(stats.values())}장")

    if unknown_files:
        print(f"\n  [경고] 알 수 없는 클래스 코드: {len(unknown_files)}개")
        for f in unknown_files[:5]:  # 처음 5개만 출력
            print(f"    - {f}")
        if len(unknown_files) > 5:
            print(f"    ... 외 {len(unknown_files) - 5}개")


if __name__ == '__main__':
    print("=" * 50)
    print("  클래스별 폴더 정리 스크립트")
    print("=" * 50)
    print(f"\n기준 경로: {base_path}")
    print(f"클래스 수: {len(class_map)}개")

    organize_by_class('train')
    organize_by_class('val')

    print("\n" + "=" * 50)
    print("  완료!")
    print("=" * 50)
