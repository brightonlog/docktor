import time
import cv2
import numpy as np
import os
from ultralytics import YOLO

# 테스트 이미지 준비
test_img_dir = os.path.join('.', 'scratch')
test_images = [os.path.join(test_img_dir, f) for f in os.listdir(test_img_dir)[:50]
               if f.lower().endswith(('.jpg', '.png'))]

def benchmark_model(model_path, name, num_runs=50):
    """모델 추론 속도 벤치마크"""
    model = YOLO(model_path)
    
    # Warmup
    for img_path in test_images[:5]:
        model.predict(img_path, verbose=False)
    
    # 벤치마크
    times = []
    for img_path in test_images[:num_runs]:
        start = time.time()
        model.predict(img_path, verbose=False)
        times.append(time.time() - start)
    
    avg_time = np.mean(times) * 1000  # ms
    fps = 1000 / avg_time
    
    print(f"{name}:")
    print(f"  평균 추론 시간: {avg_time:.1f}ms")
    print(f"  FPS: {fps:.1f}")
    
    return avg_time, fps

print("="*50)
print("  속도 벤치마크: PyTorch vs TensorRT")
print("="*50 + "\n")

# PyTorch 모델 벤치마크
pt_time, pt_fps = benchmark_model('./best.pt', "PyTorch (FP32)")

print()

# TensorRT 모델 벤치마크 (있으면 실행)
trt_time, trt_fps = None, None
if os.path.exists("./best.engine"):
    trt_time, trt_fps = benchmark_model("./best.engine", "TensorRT (FP16)")
    
    print("\n" + "="*50)
    print(f"속도 향상: {pt_time/trt_time:.1f}x 빠름")
    print("="*50)
else:
    print("\n[TensorRT 엔진이 없습니다. Phase 2를 먼저 실행하세요.]")
