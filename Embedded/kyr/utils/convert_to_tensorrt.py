# ============================================================
# Jetson Orin Nano에서 TensorRT 변환 (best_fixed.pt)
# ============================================================
# 사용법: python convert_to_tensorrt.py

import platform
import os
import torch
from ultralytics import YOLO

print("=" * 70)
print("  TensorRT 변환 (Jetson Orin Nano)")
print("=" * 70)

# 1. 환경 확인
current_platform = platform.system()
print(f"\n[1] 플랫폼 확인")
print(f"    현재 환경: {current_platform}")

if current_platform == "Windows":
    print("\n[!] 경고: Windows 환경에서는 이 스크립트를 실행하지 마세요!")
    print("    Jetson Orin Nano로 파일을 전송한 후 실행하세요.")
    raise SystemExit("Windows에서 TensorRT 변환 불가")

print(f"    [OK] Jetson/Linux 환경 확인")

# 2. CUDA 확인
print(f"\n[2] CUDA 확인")
print(f"    CUDA 사용 가능: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"    GPU: {torch.cuda.get_device_name(0)}")
    print(f"    CUDA 버전: {torch.version.cuda}")
    print(f"    [OK] GPU 사용 준비 완료")
else:
    print(f"    [!] CUDA를 사용할 수 없습니다. CPU로 변환됩니다.")

# 3. 모델 파일 확인
print(f"\n[3] 모델 파일 확인")
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, 'best_fixed.pt')

if not os.path.exists(model_path):
    print(f"    [X] 모델 파일을 찾을 수 없습니다: {model_path}")
    print(f"    best_fixed.pt 파일이 같은 디렉토리에 있는지 확인하세요.")
    raise FileNotFoundError(model_path)

pt_size = os.path.getsize(model_path) / (1024 * 1024)
print(f"    파일: {model_path}")
print(f"    크기: {pt_size:.2f} MB")
print(f"    [OK] 모델 파일 확인 완료")

# 4. TensorRT 변환 시작
print("\n" + "=" * 70)
print("TensorRT FP16 변환 시작...")
print("=" * 70)
print("변환 설정:")
print("   - 정밀도: FP16 (속도 향상, 정확도 유지)")
print("   - 입력 크기: 640x640")
print("   - 배치 크기: 1 (실시간 추론용)")

try:
    model = YOLO(model_path)

    # TensorRT 변환
    engine_path = model.export(
        format='engine',      # TensorRT 엔진
        half=True,            # FP16 정밀도
        imgsz=640,            # 입력 이미지 크기
        device=0,             # GPU 0 사용
        simplify=True,        # ONNX 그래프 단순화
        workspace=4,          # 작업 공간 4GB
        verbose=True          # 상세 로그 출력
    )

    print(f"\n" + "=" * 70)
    print("[OK] TensorRT 변환 성공!")
    print("=" * 70)
    print(f"파일 위치: {engine_path}")

    # 파일 크기 비교
    engine_size = os.path.getsize(engine_path) / (1024 * 1024)

    print(f"\n파일 크기 비교:")
    print(f"   - PyTorch (.pt):      {pt_size:.2f} MB")
    print(f"   - TensorRT (.engine): {engine_size:.2f} MB")
    print(f"   - 변화율: {(engine_size/pt_size)*100:.1f}%")

    print(f"\n다음 단계:")
    print(f"   1. 추론 속도 벤치마크")
    print(f"   2. 실시간 카메라 테스트")

except Exception as e:
    print(f"\n[X] TensorRT 변환 실패!")
    print(f"    에러: {e}")
    print(f"\n문제 해결 방법:")
    print(f"   1. CUDA 메모리 부족시: workspace 값을 2로 낮추기")
    print(f"   2. JetPack 버전 확인: sudo apt show nvidia-jetpack")
    print(f"   3. TensorRT 버전 확인: dpkg -l | grep tensorrt")
    raise

print("\n" + "=" * 70)
print("  변환 완료!")
print("=" * 70)
