
'''
import cv2
from ultralytics import YOLO
import time

# ============================================================
# Jetson Orin Nano 실시간 카메라 탐지
# ============================================================

# 1. TensorRT 모델 로드 (Phase 2-B에서 생성한 best.engine)
model = YOLO('./best.engine')

# 2. 카메라 초기화
# CSI 카메라 사용 시
# cap = cv2.VideoCapture('nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! nvvidconv flip-method=0 ! video/x-raw, width=1280, height=720, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink', cv2.CAP_GSTREAMER)

# USB 카메라 사용 시 (일반적)
cap = cv2.VideoCapture(0)  # 0 = 기본 카메라

# 해상도 설정
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
cap.set(cv2.CAP_PROP_FPS, 30)

print("="*60)
print("  SafeDeck - 실시간 선박 결함 탐지")
print("="*60)
print(f"모델: TensorRT (FP16)")
print(f"카메라 해상도: 640x640")
print(f"종료: 'q' 키")
print("="*60)

# FPS 측정 변수
fps_counter = 0
start_time = time.time()
fps = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️  카메라 프레임을 읽을 수 없습니다.")
        break
    
    # 3. YOLO 추론 (TensorRT 가속)
    results = model.predict(
        source=frame,
        conf=0.25,        # Confidence threshold (25%)
        iou=0.45,         # NMS IoU threshold
        verbose=False,
        device=0          # GPU 사용
    )[0]
    
    # 4. 결과 시각화
    annotated_frame = results.plot()
    
    # FPS 계산
    fps_counter += 1
    if fps_counter % 10 == 0:
        end_time = time.time()
        fps = 10 / (end_time - start_time)
        start_time = time.time()
    
    # FPS 표시
    cv2.putText(
        annotated_frame, 
        f"FPS: {fps:.1f}", 
        (10, 30), 
        cv2.FONT_HERSHEY_SIMPLEX, 
        1, 
        (0, 255, 0), 
        2
    )
    
    # 탐지 결과 출력
    detections = results.boxes
    if len(detections) > 0:
        cv2.putText(
            annotated_frame,
            f"Defects: {len(detections)}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )
    
    # 5. 화면 출력
    cv2.imshow('SafeDeck - Ship Defect Detection', annotated_frame)
    
    # 'q' 키로 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 정리
cap.release()
cv2.destroyAllWindows()

print("\n✅ 실시간 탐지 종료")
print(f"평균 FPS: {fps:.1f}")

'''

'''


'''
import cv2
from ultralytics import YOLO
from flask import Flask, render_template, Response
import time

app = Flask(__name__)

# 1. 모델 로드 (TensorRT 엔진 사용)

model = YOLO('./best.engine', task='detect')

# 2. 카메라 초기화 (USB 캠: 0)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

def generate_frames():
    fps_start_time = time.time()
    fps_counter = 0
    fps = 0

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # 3. YOLOv11 추론 수행
        results = model.predict(
            source=frame,
            conf=0.5,
            iou=0.45,
            verbose=False,
            device=0  # Jetson GPU 사용
        )[0]

        # 4. 결과 시각화 (바운딩 박스 그리기)
        annotated_frame = results.plot()

        # FPS 계산 및 화면 표시
        fps_counter += 1
        if fps_counter % 10 == 0:
            fps_end_time = time.time()
            fps = 10 / (fps_end_time - fps_start_time)
            fps_start_time = time.time()
        
        cv2.putText(annotated_frame, f"FPS: {fps:.1f} | Defects: {len(results.boxes)}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # 5. 프레임을 JPEG로 인코딩하여 스트리밍 전송
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    # 간단한 HTML 페이지 반환
    return "<h1>Docktor Real-time Detection</h1><img src='/video_feed' width='640'>"

@app.route('/video_feed')
def video_feed():
    # MJPEG 스트리밍 응답
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    print("="*60)
    print("🚀 SafeDeck 웹 스트리밍 서버 시작")
    print("노트북 주소창에 'http://[Jetson_IP]:5000'을 입력하세요.")
    print("="*60)
    # 0.0.0.0으로 설정해야 외부(노트북)에서 접속 가능합니다.
    app.run(host='0.0.0.0', port=5000, threaded=True)