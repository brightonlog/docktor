# ============================================================
# Flask 객체 감지 서버 (Jetson Orin Nano)
# ============================================================
# best_fixed.pt 또는 best_fixed.engine을 사용한 실시간 객체 감지

from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO
import cv2
import os
import time
import threading
from datetime import datetime

app = Flask(__name__)

# 모델 로드
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, 'best_fixed.engine')

# .engine 파일이 없으면 .pt 파일 사용
if not os.path.exists(model_path):
    model_path = os.path.join(script_dir, 'best_fixed.pt')
    print(f"[INFO] TensorRT 파일이 없어 PyTorch 모델 사용: {model_path}")
else:
    print(f"[INFO] TensorRT 모델 사용: {model_path}")

model = YOLO(model_path)

# 전역 변수
camera = None
detection_stats = {
    'fps': 0,
    'inference_time': 0,
    'detections': 0,
    'last_update': datetime.now().isoformat()
}
stats_lock = threading.Lock()


def get_camera():
    """카메라를 강제로 깨우는 끝판왕 함수"""
    global camera
    if camera is None or not camera.isOpened():
        # Brio 100 같은 USB 웹캠에 최적화된 제트슨 전용 통로야
        # 640x480으로 아주 빠르게 영상을 가져오게 세팅했어
        pipeline = (
            "v4l2src device=/dev/video0 ! "
            "image/jpeg, width=640, height=480, framerate=30/1 ! "
            "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true"
        )
        
        print("[INFO] 제트슨 전용 통로로 카메라를 여는 중...")
        camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        
        # 만약 전용 통로가 실패하면, 마지막 수단으로 일반 방식으로 0번을 시도해
        if not camera.isOpened():
            print("[WARN] 전용 통로 실패, 일반 방식으로 0번 다시 시도...")
            camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    if camera.isOpened():
        print("[SUCCESS] 드디어 카메라가 눈을 떴어! 🏎️💨")
    else:
        print("[ERROR] 여전히 카메라가 잠들어 있네... 케이블을 다시 꽂아볼까?")
        
    return camera

def generate_frames():
    """프레임 생성 및 객체 감지"""
    global detection_stats

    cam = get_camera()
    prev_time = time.time()

    while True:
        success, frame = cam.read()
        if not success:
            break

        # 객체 감지
        start_time = time.time()
        results = model(frame, conf=0.5, verbose=False)
        inference_time = (time.time() - start_time) * 1000

        # 결과 그리기
        annotated_frame = results[0].plot()

        # FPS 계산
        current_time = time.time()
        fps = 1 / (current_time - prev_time)
        prev_time = current_time

        # 감지된 객체 수
        num_detections = len(results[0].boxes)

        # 통계 업데이트
        with stats_lock:
            detection_stats['fps'] = round(fps, 2)
            detection_stats['inference_time'] = round(inference_time, 2)
            detection_stats['detections'] = num_detections
            detection_stats['last_update'] = datetime.now().isoformat()

        # FPS 정보 표시
        cv2.putText(annotated_frame, f'FPS: {fps:.1f}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_frame, f'Inference: {inference_time:.1f}ms', (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_frame, f'Objects: {num_detections}', (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # JPEG 인코딩
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """비디오 스트리밍"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/stats')
def stats():
    """감지 통계 API"""
    with stats_lock:
        return jsonify(detection_stats)


@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({'status': 'ok', 'model': os.path.basename(model_path)})


if __name__ == '__main__':
    print("=" * 70)
    print("  Flask 객체 감지 서버 시작")
    print("=" * 70)
    print(f"모델: {model_path}")
    print(f"접속 주소: http://<Jetson IP>:5000")
    print(f"예시: http://192.168.0.100:5000")
    print("=" * 70)

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
