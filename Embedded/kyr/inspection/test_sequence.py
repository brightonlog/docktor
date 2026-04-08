# sudo -E $(which python) test_sequence.py

from adafruit_motor import motor
from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import board
import busio
import time


# ---------------------------------------------------------------------------
# PWM 모터 드라이버
# ---------------------------------------------------------------------------
class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 600

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))
        if throttle < 0:
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle > 0:
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0


# ---------------------------------------------------------------------------
# 하드웨어 초기화
# ---------------------------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 600

motor_hat = PWMThrottleHat(pca, channel=0)

kit = ServoKit(channels=16, i2c=i2c, address=0x60)

SERVO_CENTER = 105
SERVO_MIN = 35
SERVO_MAX = 175
SPEED = 0.6  # 전진 속도 (0.1 ~ 1.0)

kit.servo[0].angle = SERVO_CENTER  # 초기 중앙 정렬


# ---------------------------------------------------------------------------
# 제어 함수들  ← 이것들을 조합하여 시퀀스를 짜는 것
# ---------------------------------------------------------------------------
def forward(duration):
    """전진  (초 단위)"""
    print(f"[전진] {duration}s")
    motor_hat.set_throttle(SPEED)
    time.sleep(duration)


def backward(duration):
    """후진  (초 단위)"""
    print(f"[후진] {duration}s")
    motor_hat.set_throttle(-SPEED)
    time.sleep(duration)


def stop(duration=0):
    """정지  (duration 주면 그만큼 대기)"""
    print(f"[정지] {duration}s")
    motor_hat.set_throttle(0)
    kit.servo[0].angle = SERVO_CENTER  # 핸들도 중앙으로
    if duration > 0:
        time.sleep(duration)


def left_steering(duration):
    """왼쪽으로 핸들 돌리기 (모터는 그대로 유지, 핸들만 변경)"""
    print(f"[좌핸들] {duration}s")
    kit.servo[0].angle = SERVO_MIN
    time.sleep(duration)


def right_steering(duration):
    """오른쪽으로 핸들 돌리기 (모터는 그대로 유지, 핸들만 변경)"""
    print(f"[우핸들] {duration}s")
    kit.servo[0].angle = SERVO_MAX
    time.sleep(duration)


def center_steering(duration=0):
    """핸들 중앙으로 복귀 (모터는 그대로 유지)"""
    print(f"[중앙핸들] {duration}s")
    kit.servo[0].angle = SERVO_CENTER
    if duration > 0:
        time.sleep(duration)


# ---------------------------------------------------------------------------
# ★ 시퀀스 정의  ← 여기만 수정하면 됨
# ---------------------------------------------------------------------------
SEQUENCE = [
    # (함수,          시간(초))
    (left_steering, 3),  # 좌로 핸들 2초
    (center_steering, 3),
    (right_steering, 3),  # 우로 핸들 2초
    (center_steering, 3),
    # (backward, 1),  # 엑셀 전진 2초
    # (stop, 2),  # 정지
    # (backward, 1),  # 엑셀 전진 2초
    # (stop, 2),  # 정지
]


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------
def run_sequence(sequence):
    print("===== 시퀀스 실행 시작 =====")
    for i, (func, duration) in enumerate(sequence):
        print(f"  [{i+1}/{len(sequence)}] {func.__name__}({duration}s)")
        func(duration)
    print("===== 시퀀스 완료 =====")


try:
    run_sequence(SEQUENCE)
except KeyboardInterrupt:
    print("\n[!] Ctrl+C로 중단됨")
finally:
    motor_hat.set_throttle(0)
    kit.servo[0].angle = SERVO_CENTER
    pca.deinit()
    print("모터 정지 및 정리 완료.")
