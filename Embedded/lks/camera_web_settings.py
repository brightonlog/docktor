from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading
import json
import os

app = Flask(__name__)

# 전역 변수
camera = None
camera_lock = threading.Lock()
camera_settings = {
    'brightness': 0,
    'contrast': 0,
    'saturation': 0,
    'exposure': -5,
    'gain': 50,
    'sharpness': 50,
    'wb_temp': 5000,
    'auto_exposure': 1,
    'auto_wb': 1,
    'auto_focus': 0,
    'width': 640,
    'height': 480,
}

def init_camera():
    """카메라 초기화"""
    global camera
    with camera_lock:
        if camera is not None:
            camera.release()
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, camera_settings['width'])
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_settings['height'])
        apply_camera_settings()
    return camera is not None and camera.isOpened()

def apply_camera_settings():
    """현재 설정을 카메라에 적용"""
    global camera
    if camera is None or not camera.isOpened():
        return False

    with camera_lock:
        try:
            camera.set(cv2.CAP_PROP_BRIGHTNESS, camera_settings['brightness'])
            camera.set(cv2.CAP_PROP_CONTRAST, camera_settings['contrast'])
            camera.set(cv2.CAP_PROP_SATURATION, camera_settings['saturation'])
            camera.set(cv2.CAP_PROP_SHARPNESS, camera_settings['sharpness'])
            camera.set(cv2.CAP_PROP_GAIN, camera_settings['gain'])

            # Auto Exposure
            if camera_settings['auto_exposure']:
                camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            else:
                camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                camera.set(cv2.CAP_PROP_EXPOSURE, camera_settings['exposure'])

            # Auto White Balance
            camera.set(cv2.CAP_PROP_AUTO_WB, camera_settings['auto_wb'])
            if not camera_settings['auto_wb']:
                camera.set(cv2.CAP_PROP_WB_TEMPERATURE, camera_settings['wb_temp'])

            # Auto Focus (고정 초점 카메라는 지원 안 될 수 있음)
            camera.set(cv2.CAP_PROP_AUTOFOCUS, camera_settings['auto_focus'])

            return True
        except Exception as e:
            print(f"설정 적용 오류: {e}")
            return False

def get_camera_properties():
    """현재 카메라 속성 읽기"""
    global camera
    if camera is None or not camera.isOpened():
        return None

    with camera_lock:
        try:
            props = {
                'brightness': camera.get(cv2.CAP_PROP_BRIGHTNESS),
                'contrast': camera.get(cv2.CAP_PROP_CONTRAST),
                'saturation': camera.get(cv2.CAP_PROP_SATURATION),
                'exposure': camera.get(cv2.CAP_PROP_EXPOSURE),
                'auto_exposure': camera.get(cv2.CAP_PROP_AUTO_EXPOSURE),
                'gain': camera.get(cv2.CAP_PROP_GAIN),
                'auto_wb': camera.get(cv2.CAP_PROP_AUTO_WB),
                'wb_temperature': camera.get(cv2.CAP_PROP_WB_TEMPERATURE),
                'autofocus': camera.get(cv2.CAP_PROP_AUTOFOCUS),
                'focus': camera.get(cv2.CAP_PROP_FOCUS),
                'sharpness': camera.get(cv2.CAP_PROP_SHARPNESS),
            }
            return props
        except Exception as e:
            print(f"속성 읽기 오류: {e}")
            return None

def generate_frames():
    """카메라 프레임을 스트리밍"""
    global camera
    while True:
        with camera_lock:
            if camera is None or not camera.isOpened():
                break
            success, frame = camera.read()
            if not success:
                break
            else:
                # 프레임을 JPEG로 인코딩
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue
                frame_bytes = buffer.tobytes()

        # multipart/x-mixed-replace 형식으로 프레임 전송
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('camera_settings.html')

@app.route('/video_feed')
def video_feed():
    """비디오 스트리밍 엔드포인트"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """설정 가져오기/업데이트"""
    global camera_settings

    if request.method == 'POST':
        # 설정 업데이트
        data = request.json
        for key in camera_settings:
            if key in data:
                camera_settings[key] = data[key]

        # 카메라에 적용
        success = apply_camera_settings()
        return jsonify({'success': success, 'settings': camera_settings})

    else:
        # 현재 설정 반환
        return jsonify(camera_settings)

@app.route('/properties')
def properties():
    """현재 카메라 속성 값 가져오기"""
    props = get_camera_properties()
    if props:
        return jsonify(props)
    else:
        return jsonify({'error': '카메라 속성을 읽을 수 없습니다'}), 500

@app.route('/reset', methods=['POST'])
def reset():
    """설정을 기본값으로 리셋"""
    global camera_settings
    camera_settings = {
        'brightness': 0,
        'contrast': 0,
        'saturation': 0,
        'exposure': -5,
        'gain': 50,
        'sharpness': 50,
        'wb_temp': 5000,
        'auto_exposure': 1,
        'auto_wb': 1,
        'auto_focus': 0,
        'width': 640,
        'height': 480,
    }
    apply_camera_settings()
    return jsonify({'success': True, 'settings': camera_settings})

if __name__ == '__main__':
    # 템플릿 디렉토리 생성
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)

    # 카메라 초기화
    if init_camera():
        print("카메라 초기화 성공!")
        print("\n웹 인터페이스 접속:")
        print("  - 로컬: http://localhost:5000")
        print("  - 원격: http://<Orin-IP>:5000")
        print("\n종료하려면 Ctrl+C를 누르세요.\n")

        # Flask 앱 실행 (모든 네트워크 인터페이스에서 접속 가능)
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    else:
        print("카메라 초기화 실패!")
