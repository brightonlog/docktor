import cv2
import numpy as np
import json
from flask import Flask, render_template_string, Response, request, jsonify

"""
노란색 스티커 HSV 범위 캘리브레이션 (Flask 웹 UI)
- 브라우저에서 실시간으로 HSV 범위를 조절하며 확인
- http://[Jetson_IP]:5000 접속
"""

app = Flask(__name__)

# 카메라 초기화
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 노란색 기본 HSV 범위
hsv_values = {
    "h_min": 20,
    "h_max": 35,
    "s_min": 100,
    "s_max": 255,
    "v_min": 100,
    "v_max": 255
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>HSV Calibration - Yellow Marker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
        }
        h1 {
            color: #eee;
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
        .video-container h3 {
            margin-bottom: 10px;
            color: #ffd700;
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
        .slider-group {
            margin-bottom: 15px;
        }
        .slider-group label {
            display: block;
            margin-bottom: 5px;
            color: #ffd700;
        }
        .slider-row {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        input[type="range"] {
            flex: 1;
            height: 8px;
            -webkit-appearance: none;
            background: #0f3460;
            border-radius: 4px;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            background: #ffd700;
            border-radius: 50%;
            cursor: pointer;
        }
        .value-display {
            width: 40px;
            text-align: right;
            font-weight: bold;
        }
        .btn {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        .btn-save {
            background: #ffd700;
            color: #1a1a2e;
        }
        .btn-save:hover {
            background: #ffed4a;
        }
        .btn-reset {
            background: #e94560;
            color: white;
        }
        .btn-reset:hover {
            background: #ff6b6b;
        }
        .status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            display: none;
        }
        .status.success {
            display: block;
            background: #27ae60;
        }
        .status.error {
            display: block;
            background: #e74c3c;
        }
        .hsv-info {
            background: #0f3460;
            padding: 10px;
            border-radius: 5px;
            margin-top: 15px;
            font-family: monospace;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <h1>Yellow Marker HSV Calibration</h1>

    <div class="container">
        <div class="video-container">
            <h3>Original + Detection</h3>
            <img src="/video_feed" width="640" height="480">
        </div>

        <div class="video-container">
            <h3>Mask</h3>
            <img src="/mask_feed" width="640" height="480">
        </div>

        <div class="controls">
            <h3 style="color: #ffd700; margin-top: 0;">HSV Range</h3>

            <div class="slider-group">
                <label>H Min (Hue)</label>
                <div class="slider-row">
                    <input type="range" id="h_min" min="0" max="179" value="{{ h_min }}" oninput="updateHSV()">
                    <span class="value-display" id="h_min_val">{{ h_min }}</span>
                </div>
            </div>

            <div class="slider-group">
                <label>H Max (Hue)</label>
                <div class="slider-row">
                    <input type="range" id="h_max" min="0" max="179" value="{{ h_max }}" oninput="updateHSV()">
                    <span class="value-display" id="h_max_val">{{ h_max }}</span>
                </div>
            </div>

            <div class="slider-group">
                <label>S Min (Saturation)</label>
                <div class="slider-row">
                    <input type="range" id="s_min" min="0" max="255" value="{{ s_min }}" oninput="updateHSV()">
                    <span class="value-display" id="s_min_val">{{ s_min }}</span>
                </div>
            </div>

            <div class="slider-group">
                <label>S Max (Saturation)</label>
                <div class="slider-row">
                    <input type="range" id="s_max" min="0" max="255" value="{{ s_max }}" oninput="updateHSV()">
                    <span class="value-display" id="s_max_val">{{ s_max }}</span>
                </div>
            </div>

            <div class="slider-group">
                <label>V Min (Value)</label>
                <div class="slider-row">
                    <input type="range" id="v_min" min="0" max="255" value="{{ v_min }}" oninput="updateHSV()">
                    <span class="value-display" id="v_min_val">{{ v_min }}</span>
                </div>
            </div>

            <div class="slider-group">
                <label>V Max (Value)</label>
                <div class="slider-row">
                    <input type="range" id="v_max" min="0" max="255" value="{{ v_max }}" oninput="updateHSV()">
                    <span class="value-display" id="v_max_val">{{ v_max }}</span>
                </div>
            </div>

            <button class="btn btn-save" onclick="saveHSV()">Save to JSON</button>
            <button class="btn btn-reset" onclick="resetHSV()">Reset to Default</button>

            <div id="status" class="status"></div>

            <div class="hsv-info">
                <strong>Current Range:</strong><br>
                H: [<span id="info_h_min">{{ h_min }}</span> - <span id="info_h_max">{{ h_max }}</span>]<br>
                S: [<span id="info_s_min">{{ s_min }}</span> - <span id="info_s_max">{{ s_max }}</span>]<br>
                V: [<span id="info_v_min">{{ v_min }}</span> - <span id="info_v_max">{{ v_max }}</span>]
            </div>
        </div>
    </div>

    <script>
        function updateHSV() {
            const params = ['h_min', 'h_max', 's_min', 's_max', 'v_min', 'v_max'];
            const data = {};

            params.forEach(p => {
                const val = document.getElementById(p).value;
                data[p] = parseInt(val);
                document.getElementById(p + '_val').textContent = val;
                document.getElementById('info_' + p).textContent = val;
            });

            fetch('/update_hsv', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        }

        function saveHSV() {
            fetch('/save_hsv', {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    const status = document.getElementById('status');
                    if (data.success) {
                        status.className = 'status success';
                        status.textContent = 'Saved to calibration_data.json';
                    } else {
                        status.className = 'status error';
                        status.textContent = 'Save failed!';
                    }
                    setTimeout(() => { status.style.display = 'none'; }, 3000);
                });
        }

        function resetHSV() {
            const defaults = {h_min: 20, h_max: 35, s_min: 100, s_max: 255, v_min: 100, v_max: 255};
            Object.keys(defaults).forEach(p => {
                document.getElementById(p).value = defaults[p];
            });
            updateHSV();
        }
    </script>
</body>
</html>
"""

def generate_frames():
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # BGR -> HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # HSV 범위로 마스크 생성
        lower = np.array([hsv_values["h_min"], hsv_values["s_min"], hsv_values["v_min"]])
        upper = np.array([hsv_values["h_max"], hsv_values["s_max"], hsv_values["v_max"]])
        mask = cv2.inRange(hsv, lower, upper)

        # 노이즈 제거
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 컨투어 검출 및 표시
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:
                x, y, w, h = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # 중심점 계산
                cx, cy = x + w // 2, y + h // 2
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(frame, f"({cx}, {cy})", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 프레임 인코딩
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def generate_mask():
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # BGR -> HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # HSV 범위로 마스크 생성
        lower = np.array([hsv_values["h_min"], hsv_values["s_min"], hsv_values["v_min"]])
        upper = np.array([hsv_values["h_max"], hsv_values["s_max"], hsv_values["v_max"]])
        mask = cv2.inRange(hsv, lower, upper)

        # 노이즈 제거
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 마스크를 3채널로 변환 (표시용)
        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        ret, buffer = cv2.imencode('.jpg', mask_colored)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, **hsv_values)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/mask_feed')
def mask_feed():
    return Response(generate_mask(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/update_hsv', methods=['POST'])
def update_hsv():
    global hsv_values
    data = request.get_json()
    hsv_values.update(data)
    return jsonify({"success": True})

@app.route('/save_hsv', methods=['POST'])
def save_hsv():
    try:
        save_data = {
            "yellow_marker": hsv_values.copy()
        }
        with open('calibration_data.json', 'w') as f:
            json.dump(save_data, f, indent=4)
        print(f"HSV 저장 완료: {hsv_values}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"저장 실패: {e}")
        return jsonify({"success": False})

if __name__ == "__main__":
    print("=" * 60)
    print("  Yellow Marker HSV Calibration Server")
    print("=" * 60)
    print("http://[Jetson_IP]:5000 에 접속하세요")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, threaded=True)
