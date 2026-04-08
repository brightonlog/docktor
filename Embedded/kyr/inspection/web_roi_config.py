#!/usr/bin/env python3
"""
웹 기반 ROI 설정 도구 (완전 재작성)
- SSH 환경에서도 사용 가능
- 웹 브라우저로 실시간 ROI 조정
"""

import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request
import threading
from pathlib import Path

app = Flask(__name__)

# ROI 설정 (전역 변수)
roi_config = {
    'x_start': 160,
    'x_end': 480,
    'y_start': 60,
    'y_end': 420
}

show_crop = False  # 크롭 화면 보기 토글
camera = None
camera_lock = threading.Lock()

def init_camera():
    """카메라 초기화"""
    global camera
    
    pipeline = (
        "v4l2src device=/dev/video0 ! "
        "image/jpeg, width=640, height=480, framerate=30/1 ! "
        "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true"
    )
    
    print("[INFO] Initializing camera...")
    camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    
    if not camera.isOpened():
        print("[WARN] GStreamer failed, trying V4L2...")
        camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    
    if camera.isOpened():
        print("[SUCCESS] Camera initialized")
        return True
    else:
        print("[ERROR] Camera initialization failed")
        return False

def generate_frames():
    """실시간 카메라 프레임 생성"""
    global camera, roi_config, show_crop
    
    while True:
        with camera_lock:
            success, frame = camera.read()
        
        if not success:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Camera Error", (200, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            if show_crop:
                # 크롭된 화면
                x1, x2 = roi_config['x_start'], roi_config['x_end']
                y1, y2 = roi_config['y_start'], roi_config['y_end']
                
                x1, x2 = max(0, x1), min(640, x2)
                y1, y2 = max(0, y1), min(480, y2)
                
                if x2 > x1 and y2 > y1:
                    cropped = frame[y1:y2, x1:x2].copy()
                    cv2.putText(cropped, "CROPPED VIEW", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(cropped, f"Size: {x2-x1}x{y2-y1}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    frame = cropped
                else:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(frame, "Invalid ROI", (200, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # 전체 화면에 ROI 표시
                display_frame = frame.copy()
                
                x1, x2 = roi_config['x_start'], roi_config['x_end']
                y1, y2 = roi_config['y_start'], roi_config['y_end']
                
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                cv2.line(display_frame, (center_x, 0), (center_x, 480), (0, 255, 255), 1)
                cv2.line(display_frame, (0, center_y), (640, center_y), (0, 255, 255), 1)
                
                roi_width = x2 - x1
                roi_height = y2 - y1
                
                info_text = [
                    f"ROI: ({x1}, {y1}) -> ({x2}, {y2})",
                    f"Size: {roi_width} x {roi_height} px",
                    f"Target: 30cm x 85cm"
                ]
                
                for i, text in enumerate(info_text):
                    cv2.putText(display_frame, text, (10, 30 + i * 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                frame = display_frame
        
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>ROI Configuration</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
        }
        .video-container {
            text-align: center;
            background: #000;
            border-radius: 10px;
            padding: 20px;
        }
        .video-container img {
            max-width: 100%;
            border-radius: 8px;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .control-section {
            background: rgba(255, 255, 255, 0.08);
            padding: 20px;
            border-radius: 10px;
        }
        .control-section h3 {
            margin-bottom: 15px;
            color: #fbbf24;
        }
        .btn-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 10px;
        }
        .btn {
            padding: 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 1em;
            transition: all 0.3s;
            color: white;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .btn-move { background: #3b82f6; }
        .btn-size { background: #8b5cf6; }
        .btn-special { background: #10b981; }
        .btn-toggle { background: #f59e0b; }
        .btn-save { background: #ef4444; font-size: 1.2em; padding: 20px; }
        .info-box {
            background: rgba(255, 255, 255, 0.08);
            padding: 20px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 1.1em;
        }
        .info-box .label { color: #fbbf24; font-weight: bold; }
        .info-box .value { color: #fff; }
        .step { color: #34d399; font-weight: bold; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 ROI Configuration Tool</h1>
            <p>웹 브라우저로 ROI 영역을 조정하세요</p>
        </div>

        <div class="card">
            <div class="video-container">
                <img id="videoFeed" src="/video_feed" alt="Camera Feed">
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">🎮 컨트롤</h2>
            
            <div class="controls">
                <div class="control-section">
                    <h3>📍 위치 이동</h3>
                    <div class="btn-grid">
                        <div></div>
                        <button class="btn btn-move" onclick="moveROI('up')">↑ 위</button>
                        <div></div>
                        <button class="btn btn-move" onclick="moveROI('left')">← 왼쪽</button>
                        <button class="btn btn-special" onclick="resetROI()">리셋</button>
                        <button class="btn btn-move" onclick="moveROI('right')">오른쪽 →</button>
                        <div></div>
                        <button class="btn btn-move" onclick="moveROI('down')">↓ 아래</button>
                        <div></div>
                    </div>
                </div>

                <div class="control-section">
                    <h3>📏 크기 조정</h3>
                    <div class="btn-grid">
                        <div></div>
                        <button class="btn btn-size" onclick="resizeROI('h_inc')">높이 +</button>
                        <div></div>
                        <button class="btn btn-size" onclick="resizeROI('w_dec')">폭 -</button>
                        <div style="display: flex; align-items: center; justify-content: center; color: #fbbf24;">크기</div>
                        <button class="btn btn-size" onclick="resizeROI('w_inc')">폭 +</button>
                        <div></div>
                        <button class="btn btn-size" onclick="resizeROI('h_dec')">높이 -</button>
                        <div></div>
                    </div>
                </div>

                <div class="control-section">
                    <h3>⚙️ 기타</h3>
                    <button class="btn btn-toggle" onclick="toggleView()" style="width: 100%; margin-bottom: 10px;">
                        <span id="toggleText">크롭 화면 보기</span>
                    </button>
                    <button class="btn btn-save" onclick="saveConfig()" style="width: 100%;">
                        💾 설정 저장
                    </button>
                </div>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">📊 현재 ROI 설정</h2>
            <div class="info-box">
                <div class="step">Step 1: 위치/크기 버튼으로 ROI 조정</div>
                <div class="step">Step 2: "크롭 화면 보기"로 확인</div>
                <div class="step">Step 3: "설정 저장" 클릭</div>
                <div style="margin-top: 20px;">
                    <span class="label">x_start:</span> <span class="value" id="xStart">160</span><br>
                    <span class="label">x_end:</span> <span class="value" id="xEnd">480</span><br>
                    <span class="label">y_start:</span> <span class="value" id="yStart">60</span><br>
                    <span class="label">y_end:</span> <span class="value" id="yEnd">420</span><br>
                    <span class="label">크기:</span> <span class="value" id="size">320 x 360 pixels</span>
                </div>
            </div>
        </div>
    </div>

<script>
var isCropView = false;

function updateDisplay() {
    fetch('/api/get_roi')
        .then(function(res) { return res.json(); })
        .then(function(data) {
            document.getElementById('xStart').textContent = data.x_start;
            document.getElementById('xEnd').textContent = data.x_end;
            document.getElementById('yStart').textContent = data.y_start;
            document.getElementById('yEnd').textContent = data.y_end;
            
            var width = data.x_end - data.x_start;
            var height = data.y_end - data.y_start;
            document.getElementById('size').textContent = width + ' x ' + height + ' pixels';
        })
        .catch(function(err) {
            console.error('Error:', err);
        });
}

function moveROI(direction) {
    fetch('/api/adjust_roi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'move', direction: direction})
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        updateDisplay();
    })
    .catch(function(err) {
        console.error('Error:', err);
    });
}

function resizeROI(direction) {
    fetch('/api/adjust_roi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'size', direction: direction})
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        updateDisplay();
    })
    .catch(function(err) {
        console.error('Error:', err);
    });
}

function resetROI() {
    fetch('/api/adjust_roi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'reset', direction: ''})
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        updateDisplay();
    })
    .catch(function(err) {
        console.error('Error:', err);
    });
}

function toggleView() {
    isCropView = !isCropView;
    
    fetch('/api/toggle_crop', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({show_crop: isCropView})
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        var toggleText = document.getElementById('toggleText');
        toggleText.textContent = isCropView ? '전체 화면 보기' : '크롭 화면 보기';
    })
    .catch(function(err) {
        console.error('Error:', err);
    });
}

function saveConfig() {
    fetch('/api/save_roi', {method: 'POST'})
        .then(function(res) { return res.json(); })
        .then(function(data) {
            var message = '✅ ROI 설정이 저장되었습니다!\\n\\n' +
                'roi_config.txt에 저장됨\\n\\n' +
                'x_start: ' + data.x_start + '\\n' +
                'x_end: ' + data.x_end + '\\n' +
                'y_start: ' + data.y_start + '\\n' +
                'y_end: ' + data.y_end + '\\n\\n' +
                '이제 auto_inspection_system.py를 실행하면\\n' +
                '자동으로 이 ROI가 적용됩니다!';
            
            alert(message);
        })
        .catch(function(err) {
            console.error('Error:', err);
            alert('저장 중 오류 발생');
        });
}

updateDisplay();
setInterval(updateDisplay, 2000);
console.log('JavaScript loaded successfully');
</script>

</body>
</html>
'''
    return html

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/get_roi')
def get_roi():
    return jsonify(roi_config)

@app.route('/api/adjust_roi', methods=['POST'])
def adjust_roi():
    global roi_config
    
    data = request.get_json()
    action = data.get('action')
    direction = data.get('direction')
    
    step = 10
    
    if action == 'move':
        if direction == 'up':
            roi_config['y_start'] = max(0, roi_config['y_start'] - step)
            roi_config['y_end'] = max(roi_config['y_start'] + 50, roi_config['y_end'] - step)
        elif direction == 'down':
            roi_config['y_end'] = min(480, roi_config['y_end'] + step)
            roi_config['y_start'] = min(roi_config['y_end'] - 50, roi_config['y_start'] + step)
        elif direction == 'left':
            roi_config['x_start'] = max(0, roi_config['x_start'] - step)
            roi_config['x_end'] = max(roi_config['x_start'] + 50, roi_config['x_end'] - step)
        elif direction == 'right':
            roi_config['x_end'] = min(640, roi_config['x_end'] + step)
            roi_config['x_start'] = min(roi_config['x_end'] - 50, roi_config['x_start'] + step)
    
    elif action == 'size':
        if direction == 'h_inc':
            roi_config['y_end'] = min(480, roi_config['y_end'] + step)
        elif direction == 'h_dec':
            roi_config['y_end'] = max(roi_config['y_start'] + 50, roi_config['y_end'] - step)
        elif direction == 'w_inc':
            roi_config['x_end'] = min(640, roi_config['x_end'] + step)
        elif direction == 'w_dec':
            roi_config['x_end'] = max(roi_config['x_start'] + 50, roi_config['x_end'] - step)
    
    elif action == 'reset':
        roi_config['x_start'] = 160
        roi_config['x_end'] = 480
        roi_config['y_start'] = 60
        roi_config['y_end'] = 420
    
    return jsonify({'success': True, 'roi': roi_config})

@app.route('/api/toggle_crop', methods=['POST'])
def toggle_crop():
    global show_crop
    
    data = request.get_json()
    show_crop = data.get('show_crop', False)
    
    return jsonify({'success': True, 'show_crop': show_crop})

@app.route('/api/save_roi', methods=['POST'])
def save_roi():
    script_dir = Path(__file__).parent
    config_file = script_dir / 'roi_config.txt'
    
    with open(config_file, 'w') as f:
        f.write("# ROI Configuration\n")
        f.write(f"x_start = {roi_config['x_start']}\n")
        f.write(f"x_end = {roi_config['x_end']}\n")
        f.write(f"y_start = {roi_config['y_start']}\n")
        f.write(f"y_end = {roi_config['y_end']}\n")
    
    print("\n" + "=" * 70)
    print("  ROI Configuration Saved")
    print("=" * 70)
    print(f"x_start: {roi_config['x_start']}")
    print(f"x_end: {roi_config['x_end']}")
    print(f"y_start: {roi_config['y_start']}")
    print(f"y_end: {roi_config['y_end']}")
    print(f"\nSaved to: {config_file}")
    print("=" * 70)
    
    return jsonify({
        'success': True,
        'x_start': roi_config['x_start'],
        'x_end': roi_config['x_end'],
        'y_start': roi_config['y_start'],
        'y_end': roi_config['y_end']
    })

if __name__ == '__main__':
    print("=" * 70)
    print("  Web-based ROI Configuration Tool")
    print("=" * 70)
    
    if init_camera():
        print("\n  Access URL: http://<Jetson IP>:5005")
        print("  Example: http://192.168.0.100:5005")
        print("=" * 70)
        
        try:
            app.run(host='0.0.0.0', port=5005, debug=False, threaded=True)
        finally:
            if camera:
                camera.release()
                print("\n[INFO] Camera released")
    else:
        print("\n[ERROR] Cannot start - camera initialization failed")