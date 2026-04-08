import cv2
import time
import json
import os
from datetime import datetime
from flask import Flask, render_template_string, Response, request, jsonify
from adafruit_pca9685 import PCA9685
import board
import busio

app = Flask(__name__)

# 스크립트 파일과 같은 디렉토리에 데이터 저장
# os.path.dirname: 파일의 디렉토리 경로를 가져옴
# os.path.abspath(__file__): 현재 스크립트의 절대 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, 'calibration_data.json')

# --- [모터 제어 부분] ---
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
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 600
motor_hat = PWMThrottleHat(pca, channel=0)

# 캘리브레이션 결과 저장 - 하나의 리스트에 모든 테스트 세트 저장
calibration_data = []

def set_motor_speed(output):
    """
    output: 0~100 사이의 모터 출력
    throttle 값으로 변환: -1.0 (전진 최대) ~ 1.0 (후진 최대)
    """
    throttle = -(output / 100.0)  # 전진이므로 음수
    motor_hat.set_throttle(throttle)
    print(f"현재 출력 {output}% (throttle={throttle:.2f})로 주행 중...")

def stop_car():
    motor_hat.set_throttle(0)
    print("정지!")

# --------------------------------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Orin Car Speed Calibration (개선)</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; background: #1a1a2e; color: white; text-align: center; padding: 20px; }
        .controls { background: #16213e; padding: 20px; border-radius: 10px; display: inline-block; margin-top: 20px; }
        input { width: 80px; padding: 5px; border-radius: 5px; border: none; }
        .btn-drive { background: #ffd700; color: #1a1a2e; padding: 15px 30px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; margin: 5px; }
        .btn-save { background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn-view { background: #17a2b8; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .status-box { margin-top: 20px; padding: 15px; background: #0f3460; border-radius: 10px; display: inline-block; min-width: 400px; }
        .trial-input { margin: 10px 0; padding: 10px; background: #16213e; border-radius: 5px; }
        .result-box { margin-top: 20px; padding: 20px; background: #16213e; border-radius: 10px; max-width: 600px; margin-left: auto; margin-right: auto; }
        .history { background: #16213e; padding: 15px; border-radius: 10px; margin: 20px auto; max-width: 800px; text-align: left; }
        .test-set { border: 2px solid #ffd700; padding: 15px; margin: 15px 0; border-radius: 8px; background: #0f3460; }
        .trial-item { padding: 8px; margin: 5px 0; background: #16213e; border-left: 3px solid #17a2b8; }
        .avg-speed { color: #ffd700; font-size: 1.3em; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>🏎️ Orin Car Speed Calibration (개선판)</h1>
    <div class="controls">
        <label>모터 출력 (0-100%): </label>
        <input type="number" id="pwm_val" value="50" min="0" max="100"> <br><br>
        <label>주행 시간 (초): </label>
        <input type="number" id="drive_time" value="2" min="0.5" step="0.5"> <br><br>
        <button class="btn-drive" onclick="startTrialSet()">3회 연속 측정 시작!</button>
        <button class="btn-view" onclick="loadResults()">전체 결과 보기</button>
    </div>

    <div class="status-box" id="status_box" style="display:none;">
        <div id="status_text">대기 중...</div>
        <div id="trial_inputs"></div>
    </div>

    <div class="result-box" id="result_box" style="display:none;"></div>

    <div id="history" class="history" style="display:none;"></div>

    <script>
        // 현재 테스트 세트 정보
        let currentTestSet = {
            pwm: 0,
            time: 0,
            trials: []  // 각 시도의 거리를 저장
        };
        let currentTrialNum = 0;

        function startTrialSet() {
            const pwm = parseInt(document.getElementById('pwm_val').value);
            const time_sec = parseFloat(document.getElementById('drive_time').value);
            
            // 새 테스트 세트 초기화
            currentTestSet = {
                pwm: pwm,
                time: time_sec,
                trials: []
            };
            currentTrialNum = 0;

            document.getElementById('status_box').style.display = 'block';
            document.getElementById('result_box').style.display = 'none';
            document.getElementById('trial_inputs').innerHTML = '';

            // 첫 번째 시도 시작
            runNextTrial();
        }

        function runNextTrial() {
            currentTrialNum++;
            
            if(currentTrialNum > 3) {
                // 3회 완료 - 결과 계산 및 표시
                calculateAndShowResults();
                return;
            }

            const status_text = document.getElementById('status_text');
            status_text.innerHTML = `🚗 <strong>${currentTrialNum}번째 시도</strong> 주행 중...`;

            // 서버에 주행 요청
            fetch('/drive_test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    pwm: currentTestSet.pwm, 
                    time: currentTestSet.time
                })
            })
            .then(res => res.json())
            .then(data => {
                status_text.innerHTML = `🏁 <strong>${currentTrialNum}번째 시도</strong> 정지! 거리를 측정해주세요.`;
                
                // 거리 입력 프롬프트
                setTimeout(() => {
                    const dist = prompt(`${currentTrialNum}번째 시도: 몇 cm 이동했나요?`);
                    if(dist && parseFloat(dist) > 0) {
                        currentTestSet.trials.push(parseFloat(dist));
                        
                        // 입력된 거리 표시
                        const trial_div = document.getElementById('trial_inputs');
                        trial_div.innerHTML += `<div class="trial-input">✅ ${currentTrialNum}번째: ${dist} cm</div>`;
                        
                        // 다음 시도 진행
                        runNextTrial();
                    } else {
                        alert('유효한 거리를 입력해주세요.');
                        runNextTrial();
                    }
                }, 500);
            });
        }

        function calculateAndShowResults() {
            // 평균 거리 및 속도 계산
            const distances = currentTestSet.trials;
            const avgDistance = (distances.reduce((a, b) => a + b, 0) / distances.length).toFixed(2);
            const avgSpeed = (avgDistance / currentTestSet.time).toFixed(2);

            // 각 시도별 속도 계산
            const speeds = distances.map(d => (d / currentTestSet.time).toFixed(2));

            // 결과 표시
            let resultHTML = `
                <h3>📊 측정 완료!</h3>
                <p><strong>조건:</strong> 출력 ${currentTestSet.pwm}%, 시간 ${currentTestSet.time}초</p>
                <hr>
            `;

            distances.forEach((dist, idx) => {
                resultHTML += `<div class="trial-item">
                    ${idx + 1}번째 시도: ${dist} cm → 속도 ${speeds[idx]} cm/s
                </div>`;
            });

            resultHTML += `
                <div class="avg-speed">
                    평균 거리: ${avgDistance} cm<br>
                    ⭐ 평균 속도: ${avgSpeed} cm/s
                </div>
                <button class="btn-save" onclick="saveTestSet()">이 결과 저장하기</button>
            `;

            document.getElementById('result_box').innerHTML = resultHTML;
            document.getElementById('result_box').style.display = 'block';
            document.getElementById('status_box').style.display = 'none';
        }

        function saveTestSet() {
            // 서버에 전체 테스트 세트 저장
            fetch('/save_test_set', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentTestSet)
            })
            .then(res => res.json())
            .then(data => {
                alert('✅ 결과가 저장되었습니다!');
                document.getElementById('result_box').style.display = 'none';
                loadResults();
            });
        }

        function loadResults() {
            fetch('/get_results')
            .then(res => res.json())
            .then(data => {
                const historyDiv = document.getElementById('history');
                if(data.test_sets.length === 0) {
                    historyDiv.innerHTML = '<p>아직 저장된 결과가 없습니다.</p>';
                } else {
                    let html = '<h3>📚 전체 캘리브레이션 기록</h3>';
                    
                    data.test_sets.forEach((testSet, idx) => {
                        // 평균 계산
                        const avgDist = (testSet.trials.reduce((a, b) => a + b, 0) / testSet.trials.length).toFixed(2);
                        const avgSpeed = (avgDist / testSet.time).toFixed(2);
                        
                        html += `<div class="test-set">
                            <strong>테스트 세트 #${idx + 1}</strong> 
                            (${testSet.timestamp || '시간 미기록'})<br>
                            <strong>조건:</strong> 출력 ${testSet.pwm}%, 시간 ${testSet.time}초<br><br>
                        `;
                        
                        testSet.trials.forEach((dist, trialIdx) => {
                            const speed = (dist / testSet.time).toFixed(2);
                            html += `<div class="trial-item">
                                ${trialIdx + 1}번째: ${dist} cm → ${speed} cm/s
                            </div>`;
                        });
                        
                        html += `
                            <div class="avg-speed">
                                평균 거리: ${avgDist} cm | 
                                평균 속도: ${avgSpeed} cm/s
                            </div>
                        </div>`;
                    });
                    
                    historyDiv.innerHTML = html;
                }
                historyDiv.style.display = 'block';
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/drive_test', methods=['POST'])
def drive_test():
    """
    주행 테스트 실행
    - 지정된 출력과 시간으로 차량 주행
    """
    data = request.get_json()
    pwm = int(data['pwm'])
    sec = float(data['time'])

    # 1. 주행 시작
    set_motor_speed(pwm)

    # 2. 지정된 시간만큼 대기
    time.sleep(sec)

    # 3. 정지
    stop_car()

    return jsonify({"success": True})

@app.route('/save_test_set', methods=['POST'])
def save_test_set():
    """
    하나의 테스트 세트(3회 시도) 저장
    - 같은 조건(출력, 시간)의 3번 측정 결과를 하나의 세트로 저장
    """
    data = request.get_json()
    
    # 타임스탬프 추가 (기록 시간)
    test_set = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pwm': data['pwm'],
        'time': data['time'],
        'trials': data['trials']  # [거리1, 거리2, 거리3] 형태
    }
    
    # 전체 데이터 리스트에 추가
    calibration_data.append(test_set)

    # JSON 파일 하나에 모든 테스트 세트 저장
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(calibration_data, f, indent=2, ensure_ascii=False)

    print(f"✅ 테스트 세트 저장됨 (총 {len(calibration_data)}개 세트)")
    print(f"📁 저장 위치: {DATA_FILE}")
    return jsonify({"success": True, "total_sets": len(calibration_data)})

@app.route('/get_results')
def get_results():
    """
    저장된 모든 테스트 세트 반환
    """
    return jsonify({"test_sets": calibration_data})

if __name__ == "__main__":
    try:
        # 기존 캘리브레이션 데이터 로드
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                calibration_data.extend(loaded_data)
            print(f"✅ 기존 캘리브레이션 데이터 {len(calibration_data)}개 세트 로드됨")
            print(f"📁 파일 위치: {DATA_FILE}")
        except FileNotFoundError:
            print("ℹ️  새로운 캘리브레이션 세션 시작")
            print(f"📁 데이터 저장 예정 위치: {DATA_FILE}")

        app.run(host='0.0.0.0', port=5001)
    finally:
        # 프로그램 종료 시 모터 정지
        stop_car()
        pca.deinit()
        print("🛑 모터 정지 및 프로그램 종료")