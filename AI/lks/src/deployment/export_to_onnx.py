#!/usr/bin/env python3
"""
PatchCore Lite 모델을 ONNX로 변환

Backbone (EfficientNet-B0)만 ONNX로 변환하여 TensorRT 최적화 준비

Usage:
    python export_to_onnx.py
"""

import sys
from pathlib import Path
import torch
import torch.onnx
import timm
import onnx
from onnx import shape_inference

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent  # deployment -> src -> lks
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from config.training_config import PROJECT_ROOT as CONFIG_ROOT

# ============================================================================
# Configuration
# ============================================================================

EXPORT_CONFIG = {
    'backbone': 'efficientnet_b0',
    'layers': [4],
    'image_size': (224, 224),
    'batch_size': 1,  # 추론 시 배치 크기
    'opset_version': 18,  # ONNX opset version (13 → 18로 업데이트)

    # 저장 경로
    'onnx_save_path': CONFIG_ROOT / 'models' / 'anomaly_patchcore_lite' / 'efficientnet_b0.onnx',
}

# ============================================================================
# ONNX Export
# ============================================================================

def export_backbone_to_onnx(config):
    """Backbone을 ONNX로 변환"""
    print("="*60)
    print("Exporting PatchCore Lite Backbone to ONNX")
    print("="*60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # 1. Backbone 로드
    print(f"\n[1/4] Loading backbone: {config['backbone']}")
    backbone = timm.create_model(
        config['backbone'],
        pretrained=True,
        features_only=True,
        out_indices=config['layers']
    )
    backbone.to(device)
    backbone.eval()

    # 모델 정보
    total_params = sum(p.numel() for p in backbone.parameters())
    print(f"  Total parameters: {total_params:,}")
    print(f"  Model size: ~{total_params * 4 / (1024**2):.2f} MB (FP32)")

    # 2. Dummy input 생성
    print(f"\n[2/4] Creating dummy input")
    dummy_input = torch.randn(
        config['batch_size'], 3,
        config['image_size'][0], config['image_size'][1]
    ).to(device)

    print(f"  Input shape: {dummy_input.shape}")

    # 3. Forward pass 테스트
    print(f"\n[3/4] Testing forward pass")
    with torch.no_grad():
        output = backbone(dummy_input)
        print(f"  Output shape: {output[0].shape}")

    # 4. ONNX로 변환
    print(f"\n[4/4] Converting to ONNX")

    config['onnx_save_path'].parent.mkdir(parents=True, exist_ok=True)

    # Legacy ONNX exporter 사용 (Python 3.14 호환성 문제 해결)
    with torch.no_grad():
        torch.onnx.export(
            backbone,
            dummy_input,
            str(config['onnx_save_path']),
            export_params=True,
            opset_version=config['opset_version'],
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            verbose=False,
            # Legacy exporter 사용 (Python 3.14 호환성)
            dynamo=False  # 새 exporter 비활성화
        )

    print(f"  ONNX model saved to: {config['onnx_save_path']}")

    # 5. ONNX 모델 검증
    print(f"\n[5/5] Validating ONNX model")
    onnx_model = onnx.load(str(config['onnx_save_path']))
    onnx.checker.check_model(onnx_model)

    # Shape inference
    onnx_model = shape_inference.infer_shapes(onnx_model)
    onnx.save(onnx_model, str(config['onnx_save_path']))

    print("  ONNX model is valid!")

    # 파일 크기
    file_size_mb = config['onnx_save_path'].stat().st_size / (1024 ** 2)
    print(f"  ONNX file size: {file_size_mb:.2f} MB")

    # 6. ONNX Runtime으로 테스트 (선택적)
    try:
        import onnxruntime as ort
        print(f"\n[Bonus] Testing with ONNX Runtime")

        session = ort.InferenceSession(
            str(config['onnx_save_path']),
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )

        # PyTorch vs ONNX 출력 비교
        dummy_input_np = dummy_input.cpu().numpy()
        onnx_output = session.run(None, {'input': dummy_input_np})[0]
        torch_output = output[0].cpu().numpy()

        # 오차 계산
        max_diff = abs(onnx_output - torch_output).max()
        print(f"  Max difference (PyTorch vs ONNX): {max_diff:.8f}")

        if max_diff < 1e-5:
            print("  ✓ ONNX conversion successful!")
        else:
            print(f"  ⚠ Warning: Large difference detected ({max_diff:.8f})")

    except ImportError:
        print("\n  [Info] onnxruntime not installed. Skipping ONNX Runtime test.")
        print("  Install with: pip install onnxruntime-gpu")

    print("\n" + "="*60)
    print("Export Complete!")
    print("="*60)
    print(f"\n  Next step: Convert to TensorRT")
    print(f"  Run: python convert_to_tensorrt.py")
    print("="*60)

# ============================================================================
# Main
# ============================================================================

def main():
    config = EXPORT_CONFIG.copy()
    export_backbone_to_onnx(config)

if __name__ == '__main__':
    main()
