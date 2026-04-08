"""
TensorRT Export Script for Jetson Orin Nano Deployment
Converts trained YOLO model to TensorRT engine for optimized inference
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    from ultralytics import YOLO
except ImportError:
    print("Error: ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)


class TensorRTExporter:
    """TensorRT 모델 변환기"""

    # Jetson Orin Nano 최적화 설정
    JETSON_ORIN_NANO_CONFIG = {
        'imgsz': 1088,          # 1080p에 가까운 32의 배수
        'half': True,           # FP16 사용 (Jetson에서 더 빠름)
        'int8': False,          # INT8 양자화 (선택적)
        'dynamic': False,       # 동적 배치 비활성화 (더 빠른 추론)
        'simplify': True,       # ONNX 모델 단순화
        'workspace': 4,         # GPU 메모리 워크스페이스 (GB)
        'batch': 1,             # 배치 크기 (실시간 추론용)
    }

    def __init__(self, model_path: str, output_dir: str = None):
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir) if output_dir else self.model_path.parent

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        self.model = YOLO(str(self.model_path))

    def export_onnx(self, **kwargs) -> Path:
        """ONNX 형식으로 내보내기"""
        config = {**self.JETSON_ORIN_NANO_CONFIG, **kwargs}

        print("=" * 60)
        print("Exporting to ONNX format")
        print("=" * 60)

        onnx_path = self.model.export(
            format='onnx',
            imgsz=config['imgsz'],
            half=config['half'],
            dynamic=config['dynamic'],
            simplify=config['simplify'],
        )

        print(f"ONNX model saved to: {onnx_path}")
        return Path(onnx_path)

    def export_tensorrt(self, **kwargs) -> Path:
        """
        TensorRT 엔진으로 내보내기
        Note: Jetson 디바이스에서 실행해야 최적화됨
        """
        config = {**self.JETSON_ORIN_NANO_CONFIG, **kwargs}

        print("=" * 60)
        print("Exporting to TensorRT format")
        print("=" * 60)
        print(f"Image size: {config['imgsz']}")
        print(f"FP16 (half): {config['half']}")
        print(f"INT8: {config['int8']}")
        print(f"Workspace: {config['workspace']}GB")
        print("=" * 60)

        try:
            engine_path = self.model.export(
                format='engine',
                imgsz=config['imgsz'],
                half=config['half'],
                int8=config['int8'],
                dynamic=config['dynamic'],
                simplify=config['simplify'],
                workspace=config['workspace'],
                batch=config['batch'],
            )

            print(f"\nTensorRT engine saved to: {engine_path}")
            return Path(engine_path)

        except Exception as e:
            print(f"\nWarning: TensorRT export failed: {e}")
            print("This is expected if not running on a device with TensorRT installed.")
            print("Export ONNX first, then convert to TensorRT on Jetson device.")
            return None

    def export_all(self, **kwargs) -> dict:
        """모든 형식으로 내보내기"""
        results = {}

        # ONNX
        try:
            results['onnx'] = self.export_onnx(**kwargs)
        except Exception as e:
            print(f"ONNX export failed: {e}")
            results['onnx'] = None

        # TensorRT
        try:
            results['tensorrt'] = self.export_tensorrt(**kwargs)
        except Exception as e:
            print(f"TensorRT export failed: {e}")
            results['tensorrt'] = None

        return results


def create_jetson_inference_script(output_dir: Path):
    """Jetson에서 사용할 추론 스크립트 생성"""

    script_content = '''#!/usr/bin/env python3
"""
Jetson Orin Nano Inference Script
Run this script on the Jetson device with TensorRT engine
"""

import cv2
import time
import numpy as np
from pathlib import Path

try:
    from ultralytics import YOLO
except ImportError:
    print("Install ultralytics: pip install ultralytics")
    exit(1)


CLASS_NAMES = ['blister', 'crack', 'peeling', 'sagging', 'welding_damage']
CLASS_COLORS = [
    (0, 255, 255),   # blister - cyan
    (255, 0, 0),     # crack - red
    (128, 128, 128), # peeling - gray
    (255, 165, 0),   # sagging - orange
    (0, 165, 255),   # welding_damage - sky blue
]


def run_inference(
    model_path: str,
    source: int = 0,  # 0 for webcam
    conf_threshold: float = 0.5,
    show_fps: bool = True
):
    """
    실시간 추론 실행

    Args:
        model_path: TensorRT 엔진 또는 ONNX 모델 경로
        source: 비디오 소스 (0=웹캠, 또는 비디오 파일 경로)
        conf_threshold: 신뢰도 임계값
        show_fps: FPS 표시 여부
    """
    print(f"Loading model: {model_path}")
    model = YOLO(model_path)

    # 웹캠 설정 (1080p)
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print("Starting inference... Press 'q' to quit")

    fps_list = []

    while True:
        start_time = time.time()

        ret, frame = cap.read()
        if not ret:
            break

        # 추론
        results = model(frame, conf=conf_threshold, verbose=False)

        # 결과 시각화
        annotated_frame = frame.copy()

        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # 바운딩 박스 좌표
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])

                    # 클래스 이름과 색상
                    cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}"
                    color = CLASS_COLORS[cls_id] if cls_id < len(CLASS_COLORS) else (0, 255, 0)

                    # 바운딩 박스 그리기
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)

                    # 레이블 그리기
                    label = f"{cls_name}: {conf:.2f}"
                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(
                        annotated_frame,
                        (x1, y1 - label_size[1] - 10),
                        (x1 + label_size[0], y1),
                        color, -1
                    )
                    cv2.putText(
                        annotated_frame, label,
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
                    )

        # FPS 계산 및 표시
        fps = 1.0 / (time.time() - start_time)
        fps_list.append(fps)
        if len(fps_list) > 30:
            fps_list.pop(0)
        avg_fps = sum(fps_list) / len(fps_list)

        if show_fps:
            cv2.putText(
                annotated_frame,
                f"FPS: {avg_fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
            )

        # 화면 표시
        cv2.imshow("Ship Defect Detection", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    print(f"Average FPS: {sum(fps_list)/len(fps_list):.1f}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Jetson Orin Nano Inference')
    parser.add_argument('--model', type=str, required=True, help='Model path (.engine or .onnx)')
    parser.add_argument('--source', type=str, default='0', help='Video source (0 for webcam)')
    parser.add_argument('--conf', type=float, default=0.5, help='Confidence threshold')
    parser.add_argument('--no-fps', action='store_true', help='Hide FPS display')

    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source

    run_inference(
        model_path=args.model,
        source=source,
        conf_threshold=args.conf,
        show_fps=not args.no_fps
    )
'''

    script_path = output_dir / 'jetson_inference.py'
    with open(script_path, 'w') as f:
        f.write(script_content)

    print(f"Created Jetson inference script: {script_path}")
    return script_path


def main():
    parser = argparse.ArgumentParser(
        description='Export YOLO model to TensorRT for Jetson Orin Nano'
    )
    parser.add_argument(
        '--model', type=str, required=True,
        help='Path to trained YOLO model (.pt file)'
    )
    parser.add_argument(
        '--output', type=str, default=None,
        help='Output directory (default: same as model)'
    )
    parser.add_argument(
        '--imgsz', type=int, default=1088,
        help='Image size (default: 1088 for 1080p)'
    )
    parser.add_argument(
        '--fp16', action='store_true', default=True,
        help='Use FP16 precision (default: True)'
    )
    parser.add_argument(
        '--int8', action='store_true',
        help='Use INT8 quantization'
    )
    parser.add_argument(
        '--onnx-only', action='store_true',
        help='Export ONNX only (for later TensorRT conversion on Jetson)'
    )

    args = parser.parse_args()

    exporter = TensorRTExporter(args.model, args.output)

    export_kwargs = {
        'imgsz': args.imgsz,
        'half': args.fp16,
        'int8': args.int8,
    }

    if args.onnx_only:
        exporter.export_onnx(**export_kwargs)
    else:
        exporter.export_all(**export_kwargs)

    # Jetson 추론 스크립트 생성
    output_dir = Path(args.output) if args.output else Path(args.model).parent
    create_jetson_inference_script(output_dir)

    print("\n" + "=" * 60)
    print("Export completed!")
    print("=" * 60)
    print("\nNext steps for Jetson Orin Nano deployment:")
    print("1. Copy the .onnx file to Jetson device")
    print("2. On Jetson, convert ONNX to TensorRT:")
    print("   python export_tensorrt.py --model model.onnx")
    print("3. Run inference:")
    print("   python jetson_inference.py --model model.engine")
    print("=" * 60)


if __name__ == '__main__':
    main()
