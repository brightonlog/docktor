"""
학습 환경 및 데이터셋 체크 스크립트
학습 시작 전에 이 스크립트를 실행하여 문제를 미리 파악하세요.
"""

import sys
import torch
import yaml
from pathlib import Path


def check_gpu():
    """GPU 확인"""
    print("=" * 70)
    print("1. GPU 체크")
    print("=" * 70)

    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU 개수: {torch.cuda.device_count()}")
        print(f"현재 GPU: {torch.cuda.current_device()}")
        print(f"GPU 이름: {torch.cuda.get_device_name(0)}")

        # GPU 메모리 확인
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        allocated = torch.cuda.memory_allocated(0) / 1024**3
        reserved = torch.cuda.memory_reserved(0) / 1024**3

        print(f"\nGPU 메모리:")
        print(f"  Total: {total_memory:.2f} GB")
        print(f"  Allocated: {allocated:.2f} GB")
        print(f"  Reserved: {reserved:.2f} GB")
        print(f"  Available: {total_memory - reserved:.2f} GB")

        if total_memory < 4:
            print("  [WARNING]  경고: GPU 메모리가 4GB 미만입니다. 배치 사이즈를 줄여야 할 수 있습니다.")
    else:
        print("[ERROR] CUDA를 사용할 수 없습니다. CPU 모드로 학습됩니다.")

    print()


def check_data():
    """데이터셋 확인"""
    print("=" * 70)
    print("2. 데이터셋 체크")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent.parent
    data_yaml = base_dir / 'data' / 'yolo_dataset' / 'data.yaml'

    if not data_yaml.exists():
        print(f"[ERROR] data.yaml을 찾을 수 없습니다: {data_yaml}")
        print("   먼저 prepare_dataset.py를 실행하세요.")
        return False

    print(f"[OK] data.yaml 발견: {data_yaml}")

    # YAML 내용 읽기
    with open(data_yaml, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print(f"\n데이터셋 구성:")
    print(f"  클래스 수: {config.get('nc', 'N/A')}")
    print(f"  클래스 이름: {config.get('names', 'N/A')}")

    # 경로 확인
    train_images_rel = config.get('train', 'train/images')
    val_images_rel = config.get('val', 'val/images')

    # train/images에서 train 폴더 경로 추출
    train_folder = train_images_rel.split('/')[0] if '/' in train_images_rel else train_images_rel.replace('\\', '/').split('/')[0]
    val_folder = val_images_rel.split('/')[0] if '/' in val_images_rel else val_images_rel.replace('\\', '/').split('/')[0]

    train_path = data_yaml.parent / train_folder
    val_path = data_yaml.parent / val_folder

    print(f"\n경로 확인:")

    # Train 데이터
    if train_path.exists():
        train_images = train_path / 'images'
        train_labels = train_path / 'labels'

        if train_images.exists() and train_labels.exists():
            num_train_images = len(list(train_images.glob('*.jpg'))) + len(list(train_images.glob('*.png')))
            num_train_labels = len(list(train_labels.glob('*.txt')))

            print(f"  [OK] Train 이미지: {num_train_images}개")
            print(f"  [OK] Train 라벨: {num_train_labels}개")

            if num_train_images != num_train_labels:
                print(f"     [WARNING]  경고: 이미지와 라벨 수가 다릅니다!")

            if num_train_images == 0:
                print(f"     [ERROR] 에러: Train 이미지가 없습니다!")
                return False
        else:
            print(f"  [ERROR] Train 폴더 구조가 잘못되었습니다.")
            return False
    else:
        print(f"  [ERROR] Train 경로를 찾을 수 없습니다: {train_path}")
        return False

    # Val 데이터
    if val_path.exists():
        val_images = val_path / 'images'
        val_labels = val_path / 'labels'

        if val_images.exists() and val_labels.exists():
            num_val_images = len(list(val_images.glob('*.jpg'))) + len(list(val_images.glob('*.png')))
            num_val_labels = len(list(val_labels.glob('*.txt')))

            print(f"  [OK] Val 이미지: {num_val_images}개")
            print(f"  [OK] Val 라벨: {num_val_labels}개")

            if num_val_images != num_val_labels:
                print(f"     [WARNING]  경고: 이미지와 라벨 수가 다릅니다!")

            if num_val_images == 0:
                print(f"     [ERROR] 에러: Val 이미지가 없습니다!")
                return False
        else:
            print(f"  [ERROR] Val 폴더 구조가 잘못되었습니다.")
            return False
    else:
        print(f"  [ERROR] Val 경로를 찾을 수 없습니다: {val_path}")
        return False

    print()
    return True


def check_model():
    """모델 파일 확인"""
    print("=" * 70)
    print("3. 모델 파일 체크")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent.parent
    model_path = base_dir / 'yolo26n.pt'

    if model_path.exists():
        print(f"[OK] 모델 파일 발견: {model_path}")
        size_mb = model_path.stat().st_size / 1024 / 1024
        print(f"   파일 크기: {size_mb:.2f} MB")
    else:
        print(f"[WARNING]  모델 파일을 찾을 수 없습니다: {model_path}")
        print("   yolov8n.pt를 기본값으로 사용합니다.")

    print()


def check_directories():
    """출력 디렉토리 확인"""
    print("=" * 70)
    print("4. 출력 디렉토리 체크")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent.parent

    dirs_to_check = [
        base_dir / 'experiments',
        base_dir / 'experiments' / 'yolo_runs',
        base_dir / 'experiments' / 'mlruns',
    ]

    for directory in dirs_to_check:
        if directory.exists():
            print(f"[OK] {directory.relative_to(base_dir)}")
        else:
            print(f"[WARNING]  {directory.relative_to(base_dir)} - 자동 생성됩니다.")
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   → 생성 완료")

    print()


def check_dependencies():
    """패키지 확인"""
    print("=" * 70)
    print("5. 패키지 의존성 체크")
    print("=" * 70)

    packages = {
        'torch': 'PyTorch',
        'ultralytics': 'Ultralytics YOLO',
        'mlflow': 'MLflow',
        'yaml': 'PyYAML',
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
    }

    missing = []

    for module, name in packages.items():
        try:
            __import__(module)
            print(f"[OK] {name}")
        except ImportError:
            print(f"[ERROR] {name} - 설치되지 않음")
            missing.append(name)

    if missing:
        print(f"\n[WARNING]  누락된 패키지: {', '.join(missing)}")
        print("   pip install -r requirements.txt를 실행하세요.")

    print()


def main():
    """전체 체크 실행"""
    print("\n[CHECK] 학습 환경 진단 시작...\n")

    check_gpu()
    data_ok = check_data()
    check_model()
    check_directories()
    check_dependencies()

    print("=" * 70)
    print("진단 완료")
    print("=" * 70)

    if not data_ok:
        print("[ERROR] 데이터셋에 문제가 있습니다. 먼저 해결하세요.")
        return False
    else:
        print("[OK] 모든 체크를 통과했습니다. 학습을 시작할 수 있습니다!")
        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
