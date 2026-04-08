from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import threading

app = Flask(__name__)
CORS(app)

# --- 하드웨어 초기화 (로컬 에러 방지 및 젯슨 대응) ---
pca = None
IS_JETSON = False

try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685

    # 젯슨 오린 I2C 설정
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c)
    pca.frequency = 60
    IS_JETSON = True
    print("✅ [JETSON MODE] PCA9685 하드웨어 연결 성공!")
except (ImportError, NotImplementedError) as e:
    print(f"⚠️ [LOCAL MODE] 시뮬레이션 모드로 시작합니다. (사유: {e})")

class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel

    def set_throttle(self, throttle):
        # 1. 로컬 시뮬레이션 출력
        if not self.pwm:
            print(f"🚜 [SIMULATOR] 채널 {self.channel} 모터 출력: {throttle}")
            return

        # 2. 실제 젯슨 오린 하드웨어 제어 로직
        pulse = int(0xFFFF * abs(throttle))
        try:
            if throttle < 0:      # 전진 (기존 로직 유지)
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
            print(f"🚀 [REAL] 모터 가동 중 (Throttle: {throttle})")
        except Exception as e:
            print(f"❌ 모터 제어 오류: {e}")

# 모터 객체 생성 (기존 채널 0 사용)
motor_hat = PWMThrottleHat(pca, channel=0)

def execute_move(direction, duration):
    print(f"📡 명령 수신: {direction} ({duration}초)")

    if direction == 'forward':
        motor_hat.set_throttle(-0.5)
    elif direction == 'backward':
        motor_hat.set_throttle(0.5)

    time.sleep(duration)

    motor_hat.set_throttle(0)
    print("🛑 이동 완료 및 정지")

@app.route('/move', methods=['POST'])
def move_robot():
    try:
        data = request.get_json()
        direction = data.get('direction', 'forward')
        duration = float(data.get('duration', 2.0))

        # 비동기 스레드 실행 (스프링부트 응답 지연 방지)
        thread = threading.Thread(target=execute_move, args=(direction, duration))
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"[{'Jetson' if IS_JETSON else 'Local'}] {direction} 명령 접수",
            "duration": duration
        }), 200

    except Exception as e:
        print(f"🔥 에러 발생: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    mode = "Jetson Orin" if IS_JETSON else "Local Laptop"
    return f"Robot Server is Running on {mode}!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)