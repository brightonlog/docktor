import cv2
import numpy as np
import json
from flask import Flask, render_template_string, Response, request, jsonify
import time
from adafruit_pca9685 import PCA9685
import board
import busio

"""
스캔 테스트 (Flask 웹 UI)
- 노란 마커 (시작/끝) + 빨간 소화기 (결함 대신) 검출
- 위치 % 계산
- 웹에서 조작 가능 (API 제공)
- DC 모터로 후진하면서 스캔
"""

app = Flask(__name__)

# ============================================================
# 모터 설정
# ============================================================

class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 600

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))

        if throttle < 0:      # 전진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle > 0:    # 후진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:                 # 정지
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0

# I2C 및 모터 초기화
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c)
    pca.frequency = 600
    motor_hat = PWMThrottleHat(pca, channel=0)
    MOTOR_ENABLED = True
    print("[MOTOR] Motor initialized successfully")
except Exception as e:
    MOTOR_ENABLED = False
    motor_hat = None
    print(f"[MOTOR] Motor initialization failed: {e}")

# 모터 속도 설정
MOTOR_SPEED = -0.3  # 후진 속도 (음수 = 후진)

# ============================================================
# 설정
# ============================================================

# 카메라 초기화
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# HSV 범위 로드
try:
    with open('calibration_data.json', 'r') as f:
        calib_data = json.load(f)
        YELLOW_HSV = calib_data['yellow_marker']
except:
    YELLOW_HSV = {"h_min": 20, "h_max": 35, "s_min": 100, "s_max": 255, "v_min": 100, "v_max": 255}

# 빨간색 HSV 범위 (일반적인 값)
RED_HSV_LOW = {"h_min": 0, "h_max": 10, "s_min": 100, "s_max": 255, "v_min": 100, "v_max": 255}
RED_HSV_HIGH = {"h_min": 170, "h_max": 179, "s_min": 100, "s_max": 255, "v_min": 100, "v_max": 255}

# 스캔 상태
scan_state = {
    "mode": "setup",  # setup, scanning, completed
    "frame_count": 0,
    "start_marker_frame": None,
    "end_marker_frame": None,
    "red_object_frame": None,
    "red_object_x": None,
    "result_percent": None,
    "start_marker_detected": False,
    "end_marker_detected": False,
}

# 프레임 중앙 기준 (허용 범위)
CENTER_X = 320
CENTER_TOLERANCE = 80  # 중앙에서 ±80px 이내면 중앙으로 인정

# ============================================================
# 색상 검출 함수
# ============================================================

def detect_yellow_marker(frame):
    """노란색 마커 검출"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([YELLOW_HSV["h_min"], YELLOW_HSV["s_min"], YELLOW_HSV["v_min"]])
    upper = np.array([YELLOW_HSV["h_max"], YELLOW_HSV["s_max"], YELLOW_HSV["v_max"]])
    mask = cv2.inRange(hsv, lower, upper)

    # 노이즈 제거
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    markers = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 500:
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + w // 2
            cy = y + h // 2
            markers.append({"x": x, "y": y, "w": w, "h": h, "cx": cx, "cy": cy, "area": area})

    return markers

def detect_red_object(frame):
    """빨간색 객체 검출 (소화기 등)"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 빨간색은 H가 0 근처와 180 근처 두 영역
    lower1 = np.array([RED_HSV_LOW["h_min"], RED_HSV_LOW["s_min"], RED_HSV_LOW["v_min"]])
    upper1 = np.array([RED_HSV_LOW["h_max"], RED_HSV_LOW["s_max"], RED_HSV_LOW["v_max"]])
    lower2 = np.array([RED_HSV_HIGH["h_min"], RED_HSV_HIGH["s_min"], RED_HSV_HIGH["v_min"]])
    upper2 = np.array([RED_HSV_HIGH["h_max"], RED_HSV_HIGH["s_max"], RED_HSV_HIGH["v_max"]])

    mask1 = cv2.inRange(hsv, lower1, upper1)
    mask2 = cv2.inRange(hsv, lower2, upper2)
    mask = cv2.bitwise_or(mask1, mask2)

    # 노이즈 제거
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    objects = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1000:  # 소화기는 좀 더 큰 영역
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + w // 2
            cy = y + h // 2
            objects.append({"x": x, "y": y, "w": w, "h": h, "cx": cx, "cy": cy, "area": area})

    return objects

def is_centered(cx):
    """객체가 프레임 중앙에 있는지 확인"""
    return abs(cx - CENTER_X) <= CENTER_TOLERANCE

# ============================================================
# 프레임 생성
# ============================================================

def generate_frames():
    global scan_state

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # 검출
        yellow_markers = detect_yellow_marker(frame)
        red_objects = detect_red_object(frame)

        # 프레임에 가이드라인 그리기 (중앙선)
        cv2.line(frame, (CENTER_X, 0), (CENTER_X, 480), (255, 255, 255), 1)
        cv2.line(frame, (CENTER_X - CENTER_TOLERANCE, 0), (CENTER_X - CENTER_TOLERANCE, 480), (100, 100, 100), 1)
        cv2.line(frame, (CENTER_X + CENTER_TOLERANCE, 0), (CENTER_X + CENTER_TOLERANCE, 480), (100, 100, 100), 1)

        # 노란 마커 표시
        for marker in yellow_markers:
            color = (0, 255, 255)  # 노란색 박스
            if is_centered(marker["cx"]):
                color = (0, 255, 0)  # 중앙이면 초록색
            cv2.rectangle(frame, (marker["x"], marker["y"]),
                         (marker["x"] + marker["w"], marker["y"] + marker["h"]), color, 2)
            cv2.circle(frame, (marker["cx"], marker["cy"]), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"MARKER ({marker['cx']})", (marker["x"], marker["y"] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 빨간 객체 표시
        for obj in red_objects:
            cv2.rectangle(frame, (obj["x"], obj["y"]),
                         (obj["x"] + obj["w"], obj["y"] + obj["h"]), (0, 0, 255), 2)
            cv2.circle(frame, (obj["cx"], obj["cy"]), 5, (255, 0, 0), -1)
            cv2.putText(frame, f"RED ({obj['cx']})", (obj["x"], obj["y"] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 스캔 모드별 처리
        if scan_state["mode"] == "setup":
            # 세팅 모드: 마커가 중앙에 오도록 안내
            cv2.putText(frame, "SETUP MODE", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(frame, "Align YELLOW marker to CENTER", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 마커가 중앙에 있으면 READY 표시
            for marker in yellow_markers:
                if is_centered(marker["cx"]):
                    cv2.putText(frame, "READY - Press START", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    break

        elif scan_state["mode"] == "scanning":
            scan_state["frame_count"] += 1

            cv2.putText(frame, f"SCANNING - Frame: {scan_state['frame_count']}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # 시작 마커 검출 (첫 번째 노란 마커)
            if not scan_state["start_marker_detected"]:
                for marker in yellow_markers:
                    if is_centered(marker["cx"]):
                        scan_state["start_marker_detected"] = True
                        scan_state["start_marker_frame"] = scan_state["frame_count"]
                        print(f"[SCAN] Start marker detected at frame {scan_state['frame_count']}")
                        break

            # 빨간 객체 검출 (시작 마커 이후에만)
            if scan_state["start_marker_detected"] and scan_state["red_object_frame"] is None:
                for obj in red_objects:
                    scan_state["red_object_frame"] = scan_state["frame_count"]
                    scan_state["red_object_x"] = obj["cx"]
                    print(f"[SCAN] Red object detected at frame {scan_state['frame_count']}, x={obj['cx']}")
                    break

            # 끝 마커 검출 (시작 마커 이후, 일정 프레임 지난 후)
            if scan_state["start_marker_detected"]:
                frames_since_start = scan_state["frame_count"] - scan_state["start_marker_frame"]
                if frames_since_start > 10:  # 시작 후 최소 10프레임 지나야 끝 마커 인식
                    for marker in yellow_markers:
                        if is_centered(marker["cx"]):
                            scan_state["end_marker_detected"] = True
                            scan_state["end_marker_frame"] = scan_state["frame_count"]
                            print(f"[SCAN] End marker detected at frame {scan_state['frame_count']}")

                            # 모터 정지
                            if MOTOR_ENABLED and motor_hat:
                                motor_hat.set_throttle(0)
                                print("[MOTOR] Stopped - scan completed")

                            # 결과 계산
                            calculate_result()
                            scan_state["mode"] = "completed"
                            break

        elif scan_state["mode"] == "completed":
            cv2.putText(frame, "SCAN COMPLETED", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if scan_state["result_percent"] is not None:
                cv2.putText(frame, f"Defect at: {scan_state['result_percent']:.1f}%", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "No defect detected", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 상태 정보 표시
        info_y = 450
        cv2.putText(frame, f"Start: {scan_state['start_marker_frame']} | Red: {scan_state['red_object_frame']} | End: {scan_state['end_marker_frame']}",
                   (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # 프레임 인코딩
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def calculate_result():
    """결과 계산: 빨간 객체 위치 %"""
    global scan_state

    if scan_state["start_marker_frame"] is None or scan_state["end_marker_frame"] is None:
        return

    total_frames = scan_state["end_marker_frame"] - scan_state["start_marker_frame"]

    if total_frames <= 0:
        return

    if scan_state["red_object_frame"] is not None:
        red_frame = scan_state["red_object_frame"] - scan_state["start_marker_frame"]
        scan_state["result_percent"] = (red_frame / total_frames) * 100
        print(f"[RESULT] Defect at {scan_state['result_percent']:.1f}% (frame {red_frame}/{total_frames})")

# ============================================================
# HTML 템플릿
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Scan Test - Defect Location</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
        }
        h1 {
            color: #ffd700;
            text-align: center;
        }
        .container {
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .video-container {
            text-align: center;
        }
        img {
            border: 2px solid #ffd700;
            border-radius: 8px;
        }
        .controls {
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            width: 300px;
        }
        .btn {
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 18px;
            font-weight: bold;
        }
        .btn-start {
            background: #27ae60;
            color: white;
        }
        .btn-start:hover {
            background: #2ecc71;
        }
        .btn-stop {
            background: #e74c3c;
            color: white;
        }
        .btn-stop:hover {
            background: #ec7063;
        }
        .btn-reset {
            background: #3498db;
            color: white;
        }
        .btn-reset:hover {
            background: #5dade2;
        }
        .status-box {
            background: #0f3460;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #1a1a2e;
        }
        .status-label {
            color: #aaa;
        }
        .status-value {
            font-weight: bold;
            color: #ffd700;
        }
        .result-box {
            background: #27ae60;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            text-align: center;
            display: none;
        }
        .result-box.show {
            display: block;
        }
        .result-percent {
            font-size: 48px;
            font-weight: bold;
        }
        .mode-indicator {
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            font-weight: bold;
        }
        .mode-setup { background: #f39c12; }
        .mode-scanning { background: #e74c3c; }
        .mode-completed { background: #27ae60; }
    </style>
</head>
<body>
    <h1>Scan Test - Defect Location</h1>

    <div class="container">
        <div class="video-container">
            <img src="/video_feed" width="640" height="480">
        </div>

        <div class="controls">
            <div id="modeIndicator" class="mode-indicator mode-setup">SETUP MODE</div>

            <button class="btn btn-start" onclick="startScan()">START SCAN</button>
            <button class="btn btn-stop" onclick="stopScan()">STOP</button>
            <button class="btn btn-reset" onclick="resetScan()">RESET</button>

            <div class="status-box">
                <h3 style="margin-top: 0; color: #ffd700;">Status</h3>
                <div class="status-item">
                    <span class="status-label">Mode</span>
                    <span class="status-value" id="statusMode">setup</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Frame Count</span>
                    <span class="status-value" id="statusFrame">0</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Start Marker</span>
                    <span class="status-value" id="statusStart">-</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Red Object</span>
                    <span class="status-value" id="statusRed">-</span>
                </div>
                <div class="status-item">
                    <span class="status-label">End Marker</span>
                    <span class="status-value" id="statusEnd">-</span>
                </div>
            </div>

            <div id="resultBox" class="result-box">
                <div>Defect Location</div>
                <div class="result-percent" id="resultPercent">0%</div>
                <div>from start marker</div>
            </div>
        </div>
    </div>

    <script>
        function startScan() {
            fetch('/api/start', {method: 'POST'})
                .then(res => res.json())
                .then(data => console.log(data));
        }

        function stopScan() {
            fetch('/api/stop', {method: 'POST'})
                .then(res => res.json())
                .then(data => console.log(data));
        }

        function resetScan() {
            fetch('/api/reset', {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    document.getElementById('resultBox').classList.remove('show');
                });
        }

        // 상태 업데이트 폴링
        setInterval(() => {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('statusMode').textContent = data.mode;
                    document.getElementById('statusFrame').textContent = data.frame_count;
                    document.getElementById('statusStart').textContent = data.start_marker_frame || '-';
                    document.getElementById('statusRed').textContent = data.red_object_frame || '-';
                    document.getElementById('statusEnd').textContent = data.end_marker_frame || '-';

                    // 모드 인디케이터 업데이트
                    const indicator = document.getElementById('modeIndicator');
                    indicator.className = 'mode-indicator mode-' + data.mode;
                    indicator.textContent = data.mode.toUpperCase() + ' MODE';

                    // 결과 표시
                    if (data.mode === 'completed' && data.result_percent !== null) {
                        document.getElementById('resultBox').classList.add('show');
                        document.getElementById('resultPercent').textContent = data.result_percent.toFixed(1) + '%';
                    }
                });
        }, 500);
    </script>
</body>
</html>
"""

# ============================================================
# API 엔드포인트
# ============================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/start', methods=['POST'])
def api_start():
    global scan_state
    scan_state["mode"] = "scanning"
    scan_state["frame_count"] = 0
    scan_state["start_marker_detected"] = False

    # 모터 후진 시작
    if MOTOR_ENABLED and motor_hat:
        motor_hat.set_throttle(MOTOR_SPEED)
        print(f"[MOTOR] Moving backward at speed {MOTOR_SPEED}")

    print("[API] Scan started")
    return jsonify({"success": True, "message": "Scan started"})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    global scan_state
    scan_state["mode"] = "setup"

    # 모터 정지
    if MOTOR_ENABLED and motor_hat:
        motor_hat.set_throttle(0)
        print("[MOTOR] Stopped")

    print("[API] Scan stopped")
    return jsonify({"success": True, "message": "Scan stopped"})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    global scan_state
    scan_state = {
        "mode": "setup",
        "frame_count": 0,
        "start_marker_frame": None,
        "end_marker_frame": None,
        "red_object_frame": None,
        "red_object_x": None,
        "result_percent": None,
        "start_marker_detected": False,
        "end_marker_detected": False,
    }

    # 모터 정지
    if MOTOR_ENABLED and motor_hat:
        motor_hat.set_throttle(0)
        print("[MOTOR] Stopped")

    print("[API] Scan reset")
    return jsonify({"success": True, "message": "Scan reset"})

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(scan_state)

@app.route('/api/result', methods=['GET'])
def api_result():
    """결과 조회 API - 프론트/백 연동용"""
    return jsonify({
        "completed": scan_state["mode"] == "completed",
        "defect_detected": scan_state["red_object_frame"] is not None,
        "defect_location_percent": scan_state["result_percent"],
        "total_frames": (scan_state["end_marker_frame"] - scan_state["start_marker_frame"]) if scan_state["end_marker_frame"] and scan_state["start_marker_frame"] else None,
        "start_frame": scan_state["start_marker_frame"],
        "end_frame": scan_state["end_marker_frame"],
        "defect_frame": scan_state["red_object_frame"]
    })

# ============================================================
# 메인
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Scan Test Server")
    print("=" * 60)
    print("http://[Jetson_IP]:5000 에 접속하세요")
    print("")
    print("API Endpoints:")
    print("  POST /api/start  - 스캔 시작")
    print("  POST /api/stop   - 스캔 중지")
    print("  POST /api/reset  - 리셋")
    print("  GET  /api/status - 상태 조회")
    print("  GET  /api/result - 결과 조회")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, threaded=True)
