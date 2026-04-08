#!/usr/bin/env python3
"""
ONNX 모델을 TensorRT로 변환 (FP16)

Usage:
    python convert_to_tensorrt.py
"""

import sys
from pathlib import Path

def convert_onnx_to_tensorrt(onnx_path, engine_path):
    """
    ONNX → TensorRT FP16 변환

    Args:
        onnx_path: ONNX 모델 경로
        engine_path: TensorRT 엔진 저장 경로
    """
    try:
        import tensorrt as trt
    except ImportError:
        print("\n❌ TensorRT not installed!")
        print("  Jetson: TensorRT is pre-installed")
        print("  Ubuntu/PC: pip install nvidia-tensorrt")
        return False

    print("="*60)
    print(f"Converting ONNX to TensorRT (FP16)")
    print("="*60)

    # TensorRT 로거
    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

    # Builder 생성
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, TRT_LOGGER)

    # ONNX 파싱
    print(f"\n[1/4] Parsing ONNX model: {onnx_path}")
    with open(onnx_path, 'rb') as f:
        if not parser.parse(f.read()):
            print("Failed to parse ONNX file")
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            return False

    print("  ✓ ONNX parsed successfully")

    # Builder config
    config = builder.create_builder_config()

    # 메모리 제한 (젯슨 오린 나노: 8GB)
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 2 << 30)  # 2GB

    # FP16 설정
    print(f"\n[2/4] Setting precision: FP16")
    if not builder.platform_has_fast_fp16:
        print("  ⚠ Warning: FP16 not supported on this platform")
    else:
        config.set_flag(trt.BuilderFlag.FP16)
        print("  ✓ FP16 enabled")

    # Engine 빌드
    print(f"\n[3/4] Building TensorRT engine (this may take a few minutes)...")
    serialized_engine = builder.build_serialized_network(network, config)

    if serialized_engine is None:
        print("  ❌ Failed to build engine")
        return False

    print("  ✓ Engine built successfully")

    # Engine 저장
    print(f"\n[4/4] Saving engine to: {engine_path}")
    engine_path.parent.mkdir(parents=True, exist_ok=True)

    with open(engine_path, 'wb') as f:
        f.write(serialized_engine)

    # 파일 크기
    file_size_mb = engine_path.stat().st_size / (1024 ** 2)
    print(f"  ✓ Engine saved ({file_size_mb:.2f} MB)")

    print("\n" + "="*60)
    print("Conversion Complete!")
    print("="*60)

    # 크기 비교
    onnx_size_mb = onnx_path.stat().st_size / (1024 ** 2)
    reduction = (1 - file_size_mb / onnx_size_mb) * 100

    print(f"\n  Model Size:")
    print(f"    ONNX:       {onnx_size_mb:.2f} MB")
    print(f"    TensorRT:   {file_size_mb:.2f} MB")
    print(f"    Reduction:  {reduction:.1f}%")
    print("="*60)

    return True

def main():
    # 현재 디렉토리
    model_dir = Path(__file__).parent

    # ONNX 및 Engine 경로
    onnx_path = model_dir / "efficientnet_b0_v2.onnx"
    engine_path = model_dir / "efficientnet_b0_v2_fp16.engine"

    if not onnx_path.exists():
        print(f"❌ ONNX model not found: {onnx_path}")
        sys.exit(1)

    # 변환 실행
    success = convert_onnx_to_tensorrt(
        onnx_path=onnx_path,
        engine_path=engine_path
    )

    if not success:
        print("\n❌ Conversion failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
