from ultralytics import YOLO

# 1. 학습된 모델 불러오기
model = YOLO('best_fixed.pt') 

# 2. 벤치마크 실행 (CPU, GPU, TensorRT 등 비교)
# imgsz는 실제 서비스에서 쓸 크기로 설정해줘 (예: 896)
model.benchmark(imgsz=896, device=0)