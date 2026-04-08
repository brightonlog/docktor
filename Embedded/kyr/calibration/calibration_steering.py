import time
import json
from flask import Flask, render_template_string, Response, request, jsonify
from adafruit_servokit import ServoKit
from adafruit_pca9685 import PCA9685
import busio
import board

"""
오린카 조향 캘리브레이션 (Flask 웹 UI)
- 바퀴가 휘어서 직진이 안될 때 사용
- 브라우저에서 실시간으로 조향 각도를 조절하며 직진 각도 찾기
- 테스트 주행 기능으로 직진 확인 가능
- http://[Jetson_IP]:5002 접속
"""

app = Flask(__name__)

# DC 모터 제어 클래스
class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 600

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))

        if throttle < 0:  # 전진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle > 0:  # 후진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:  # 정지
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0

# I2C 및 모터 초기화
i2c_bus = busio.I2C(board.SCL, board.SDA)
kit = ServoKit(channels=16, i2c=i2c_bus, address=0x60)

# DC 모터 초기화 (PCA9685 사용)
pca = PCA9685(i2c_bus)
pca.frequency = 600
motor_hat = PWMThrottleHat(pca, channel=0)

# 조향 설정값 (기본 중앙값: 120도)
steering_config = {
    "center_angle": 120,  # 직진 각도
    "left_limit": 90,     # 최대 좌회전
    "right_limit": 150,   # 최대 우회전
    "current_angle": 120,
    "test_speed": 30,     # 테스트 주행 속도 (0-100%)
    "test_duration": 2    # 테스트 주행 시간 (초)
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Orin Car Steering Calibration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #ffd700;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #aaa;
            font-size: 14px;
            margin-bottom: 30px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: #16213e;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .steering-visual {
            margin: 30px 0;
            position: relative;
        }
        .steering-wheel {
            width: 200px;
            height: 200px;
            margin: 0 auto;
            border: 8px solid #ffd700;
            border-radius: 50%;
            position: relative;
            background: #0f3460;
        }
        .steering-indicator {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 6px;
            height: 90px;
            background: #e94560;
            transform-origin: bottom center;
            transform: translate(-50%, -100%) rotate(0deg);
            transition: transform 0.2s;
            border-radius: 3px;
        }
        .angle-display {
            font-size: 48px;
            font-weight: bold;
            color: #ffd700;
            margin: 20px 0;
        }
        .slider-container {
            margin: 30px 0;
        }
        input[type="range"] {
            width: 100%;
            height: 12px;
            -webkit-appearance: none;
            background: linear-gradient(to right, #e94560 0%, #ffd700 50%, #27ae60 100%);
            border-radius: 6px;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 30px;
            height: 30px;
            background: white;
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }
        .range-labels {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 12px;
            color: #aaa;
        }
        .btn {
            padding: 15px 30px;
            margin: 10px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.1s;
        }
        .btn:active {
            transform: scale(0.95);
        }
        .btn-save {
            background: #27ae60;
            color: white;
        }
        .btn-save:hover {
            background: #2ecc71;
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4);
        }
        .btn-reset {
            background: #e94560;
            color: white;
        }
        .btn-reset:hover {
            background: #ff6b6b;
            box-shadow: 0 4px 15px rgba(233, 69, 96, 0.4);
        }
        .btn-quick {
            background: #3498db;
            color: white;
            padding: 10px 20px;
            font-size: 14px;
        }
        .btn-quick:hover {
            background: #5dade2;
        }
        .btn-test-drive {
            background: #ff6b35;
            color: white;
            padding: 18px 40px;
            font-size: 18px;
            margin: 20px 0;
        }
        .btn-test-drive:hover {
            background: #ff8c61;
            box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
        }
        .btn-test-drive:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .quick-controls {
            margin: 20px 0;
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .test-drive-section {
            background: #0f3460;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid #ff6b35;
        }
        .test-drive-section h3 {
            color: #ff6b35;
            margin-top: 0;
        }
        .speed-control {
            margin: 15px 0;
        }
        .speed-control label {
            display: block;
            margin-bottom: 5px;
            color: #ff6b35;
            font-weight: bold;
        }
        .info-box {
            background: #0f3460;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-family: monospace;
            font-size: 14px;
            text-align: left;
        }
        .info-box strong {
            color: #ffd700;
        }
        .status {
            margin-top: 15px;
            padding: 12px;
            border-radius: 8px;
            display: none;
            font-weight: bold;
        }
        .status.success {
            display: block;
            background: #27ae60;
        }
        .status.error {
            display: block;
            background: #e74c3c;
        }
        .direction-indicator {
            margin: 15px 0;
            font-size: 18px;
            font-weight: bold;
        }
        .direction-left { color: #e94560; }
        .direction-center { color: #ffd700; }
        .direction-right { color: #27ae60; }
    </style>
</head>
<body>
    <h1>🏎️ Orin Car Steering Calibration</h1>
    <p class="subtitle">바퀴 직진 각도를 찾아 저장하세요</p>

    <div class="container">
        <div class="steering-visual">
            <div class="steering-wheel">
                <div class="steering-indicator" id="indicator"></div>
            </div>
        </div>

        <div class="angle-display" id="angleDisplay">{{ current_angle }}°</div>

        <div class="direction-indicator" id="direction">
            <span class="direction-center">⬆️ CENTER</span>
        </div>

        <div class="slider-container">
            <input type="range" id="angleSlider"
                   min="{{ left_limit }}"
                   max="{{ right_limit }}"
                   value="{{ current_angle }}"
                   oninput="updateAngle(this.value)">
            <div class="range-labels">
                <span>⬅️ LEFT ({{ left_limit }}°)</span>
                <span>CENTER</span>
                <span>RIGHT ({{ right_limit }}°) ➡️</span>
            </div>
        </div>

        <div class="quick-controls">
            <button class="btn btn-quick" onclick="adjustAngle(-5)">⬅️ -5°</button>
            <button class="btn btn-quick" onclick="adjustAngle(-1)">⬅️ -1°</button>
            <button class="btn btn-quick" onclick="setCenter()">🎯 CENTER</button>
            <button class="btn btn-quick" onclick="adjustAngle(1)">+1° ➡️</button>
            <button class="btn btn-quick" onclick="adjustAngle(5)">+5° ➡️</button>
        </div>

        <div class="test-drive-section">
            <h3>🚗 테스트 주행</h3>
            <div class="speed-control">
                <label>주행 속도 (0-100%): </label>
                <input type="range" id="testSpeed" min="10" max="60" value="{{ test_speed }}"
                       oninput="document.getElementById('speedValue').textContent = this.value">
                <span id="speedValue" style="color: #ff6b35; font-weight: bold; margin-left: 10px;">{{ test_speed }}</span>%
            </div>
            <div class="speed-control">
                <label>주행 시간 (초): </label>
                <input type="range" id="testDuration" min="0.5" max="5" step="0.5" value="{{ test_duration }}"
                       oninput="document.getElementById('durationValue').textContent = this.value">
                <span id="durationValue" style="color: #ff6b35; font-weight: bold; margin-left: 10px;">{{ test_duration }}</span>초
            </div>
            <button class="btn btn-test-drive" id="testDriveBtn" onclick="testDrive()">
                🚗 테스트 주행 시작
            </button>
            <div style="font-size: 12px; color: #aaa; margin-top: 10px;">
                💡 조향 각도를 조정한 후 이 버튼으로 직진 여부를 확인하세요
            </div>
        </div>

        <div>
            <button class="btn btn-save" onclick="saveSteering()">✅ 현재 각도를 직진으로 저장</button>
            <button class="btn btn-reset" onclick="resetSteering()">🔄 기본값으로 리셋</button>
        </div>

        <div id="status" class="status"></div>

        <div class="info-box">
            <strong>📝 사용 방법:</strong><br>
            1. 슬라이더나 버튼으로 각도 조정<br>
            2. 오린카를 직진 주행시켜 테스트<br>
            3. 완벽한 직진 각도를 찾으면 저장<br>
            4. 저장된 값은 steering_config.json에 보관됨<br><br>
            <strong>📊 현재 설정:</strong><br>
            직진 각도: <span id="info_center">{{ center_angle }}</span>°<br>
            좌회전 한계: {{ left_limit }}°<br>
            우회전 한계: {{ right_limit }}°
        </div>
    </div>

    <script>
        const centerAngle = {{ center_angle }};
        const leftLimit = {{ left_limit }};
        const rightLimit = {{ right_limit }};

        function updateAngle(angle) {
            angle = parseInt(angle);
            document.getElementById('angleDisplay').textContent = angle + '°';

            // 방향 표시 업데이트
            const direction = document.getElementById('direction');
            if (angle < centerAngle - 2) {
                direction.innerHTML = '<span class="direction-left">⬅️ LEFT</span>';
            } else if (angle > centerAngle + 2) {
                direction.innerHTML = '<span class="direction-right">RIGHT ➡️</span>';
            } else {
                direction.innerHTML = '<span class="direction-center">⬆️ CENTER</span>';
            }

            // 핸들 비주얼 회전 (-90도 ~ +90도 범위로 매핑)
            const rotation = ((angle - centerAngle) / (rightLimit - leftLimit)) * 180;
            document.getElementById('indicator').style.transform =
                `translate(-50%, -100%) rotate(${rotation}deg)`;

            // 서버에 각도 전송
            fetch('/update_angle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({angle: angle})
            });
        }

        function adjustAngle(delta) {
            const slider = document.getElementById('angleSlider');
            let newAngle = parseInt(slider.value) + delta;
            newAngle = Math.max(leftLimit, Math.min(rightLimit, newAngle));
            slider.value = newAngle;
            updateAngle(newAngle);
        }

        function setCenter() {
            const slider = document.getElementById('angleSlider');
            slider.value = centerAngle;
            updateAngle(centerAngle);
        }

        function saveSteering() {
            const currentAngle = parseInt(document.getElementById('angleSlider').value);

            fetch('/save_steering', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({center_angle: currentAngle})
            })
            .then(res => res.json())
            .then(data => {
                const status = document.getElementById('status');
                if (data.success) {
                    status.className = 'status success';
                    status.textContent = `✅ 직진 각도 ${currentAngle}°로 저장 완료!`;
                    document.getElementById('info_center').textContent = currentAngle;
                } else {
                    status.className = 'status error';
                    status.textContent = '❌ 저장 실패!';
                }
                setTimeout(() => { status.style.display = 'none'; }, 3000);
            });
        }

        function resetSteering() {
            if (confirm('기본값 (120°)으로 리셋하시겠습니까?')) {
                fetch('/reset_steering', {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    }
                });
            }
        }

        function testDrive() {
            const speed = parseInt(document.getElementById('testSpeed').value);
            const duration = parseFloat(document.getElementById('testDuration').value);
            const btn = document.getElementById('testDriveBtn');
            const status = document.getElementById('status');

            // 버튼 비활성화
            btn.disabled = true;
            btn.textContent = `🚗 주행 중... (${duration}초)`;

            fetch('/test_drive', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({speed: speed, duration: duration})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    status.className = 'status success';
                    status.textContent = '✅ 테스트 주행 완료! 직진했나요?';
                } else {
                    status.className = 'status error';
                    status.textContent = '❌ 주행 실패: ' + (data.error || '알 수 없는 오류');
                }
                setTimeout(() => { status.style.display = 'none'; }, 3000);

                // 버튼 다시 활성화
                btn.disabled = false;
                btn.textContent = '🚗 테스트 주행 시작';
            })
            .catch(error => {
                console.error('Error:', error);
                status.className = 'status error';
                status.textContent = '❌ 통신 오류';
                btn.disabled = false;
                btn.textContent = '🚗 테스트 주행 시작';
            });
        }

        // 초기 각도 설정
        updateAngle({{ current_angle }});
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, **steering_config)

@app.route('/update_angle', methods=['POST'])
def update_angle():
    global steering_config
    data = request.get_json()
    angle = int(data['angle'])

    # 서보 모터 각도 설정
    try:
        kit.servo[0].angle = angle
        steering_config['current_angle'] = angle
        print(f"조향 각도: {angle}°")
        return jsonify({"success": True})
    except Exception as e:
        print(f"서보 제어 실패: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/save_steering', methods=['POST'])
def save_steering():
    global steering_config
    data = request.get_json()
    center_angle = int(data['center_angle'])

    steering_config['center_angle'] = center_angle
    steering_config['current_angle'] = center_angle

    try:
        with open('steering_config.json', 'w') as f:
            json.dump(steering_config, f, indent=2)
        print(f"✅ 직진 각도 저장 완료: {center_angle}°")
        return jsonify({"success": True, "center_angle": center_angle})
    except Exception as e:
        print(f"저장 실패: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/reset_steering', methods=['POST'])
def reset_steering():
    global steering_config
    steering_config['center_angle'] = 120
    steering_config['current_angle'] = 120

    try:
        kit.servo[0].angle = 120
        with open('steering_config.json', 'w') as f:
            json.dump(steering_config, f, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/test_drive', methods=['POST'])
def test_drive():
    data = request.get_json()
    speed = int(data['speed'])
    duration = float(data['duration'])

    try:
        print(f"테스트 주행 시작: 속도 {speed}%, 시간 {duration}초")

        # 전진
        throttle = -(speed / 100.0)  # 전진이므로 음수
        motor_hat.set_throttle(throttle)

        # 지정된 시간만큼 대기
        time.sleep(duration)

        # 정지
        motor_hat.set_throttle(0)

        print("테스트 주행 완료")
        return jsonify({"success": True})

    except Exception as e:
        print(f"테스트 주행 실패: {e}")
        # 오류 발생 시에도 모터 정지
        motor_hat.set_throttle(0)
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    try:
        # 기존 설정 로드
        try:
            with open('steering_config.json', 'r') as f:
                saved_config = json.load(f)
                steering_config.update(saved_config)
            print(f"✅ 저장된 조향 설정 로드: 직진 각도 {steering_config['center_angle']}°")
        except FileNotFoundError:
            print("ℹ️  새로운 조향 캘리브레이션 세션 시작")

        # 초기 각도 설정
        kit.servo[0].angle = steering_config['current_angle']

        print("=" * 60)
        print("  🏎️  Orin Car Steering Calibration Server")
        print("=" * 60)
        print(f"  http://[Jetson_IP]:5002 에 접속하세요")
        print(f"  현재 직진 각도: {steering_config['center_angle']}°")
        print("=" * 60)

        app.run(host='0.0.0.0', port=5002, threaded=True)

    except KeyboardInterrupt:
        print("\n프로그램 종료")
    finally:
        # 종료 시 모터 정지 및 조향 중앙 복귀
        motor_hat.set_throttle(0)
        kit.servo[0].angle = steering_config['center_angle']
        pca.deinit()
        print(f"🛑 모터 정지 및 조향 각도 {steering_config['center_angle']}°로 복귀")
