#!/usr/bin/env python3
"""H-Pattern 주행 테스트 — 선박면에서 수직 오프셋을 만드는 패턴"""

import time
import signal
import sys

from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import busio
import board

# ─── 하드웨어 초기화 ─────────────────────────────────────────
i2c = busio.I2C(board.SCL, board.SDA)
kit = ServoKit(channels=16, i2c=i2c, address=0x60)  # 서보 먼저
pca = PCA9685(i2c)  # DC 모터 이후
pca.frequency = 600


def motor(val):
    """val: -1.0(전진) ~ +1.0(후진), 0=정지"""
    pulse = int(0xFFFF * abs(val))
    if val < 0:  # 전진
        pca.channels[5].duty_cycle = pulse
        pca.channels[4].duty_cycle = 0
        pca.channels[3].duty_cycle = 0xFFFF
    elif val > 0:  # 후진
        pca.channels[5].duty_cycle = pulse
        pca.channels[4].duty_cycle = 0xFFFF
        pca.channels[3].duty_cycle = 0
    else:  # 정지
        pca.channels[5].duty_cycle = 0
        pca.channels[4].duty_cycle = 0
        pca.channels[3].duty_cycle = 0


def steer(angle):
    kit.servo[0].angle = angle
    time.sleep(1)  # 서보 대기


def fwd(sec, pwm=60):
    motor(-(pwm / 100.0))
    time.sleep(sec)
    motor(0)
    time.sleep(1)  # 모터 안정화 대기


def rev(sec, pwm=60):
    motor(pwm / 100.0)
    time.sleep(sec)
    motor(0)
    time.sleep(1)


def stop():
    motor(0)
    kit.servo[0].angle = 120


# ─── Ctrl+C 비상정지 ─────────────────────────────────────────
def on_sigint(sig, frame):
    stop()
    pca.deinit()
    sys.exit(0)


signal.signal(signal.SIGINT, on_sigint)

# ─── 실행 ────────────────────────────────────────────────────
#   서보:  직진=120  좌회전=100  우회전=140
#   모터:  전진=60%  후진=60%   회전=60%
#   속도:  15cm/s × 안전계수1.15
#   회전:  R=30cm, 오프셋목표=50cm → 호=29.6cm, 중간직선=0cm
#
kit.servo[0].angle = 120
input("ENTER → 시작")

try:
    # 1. 직선 전진
    steer(120)
    rev(2, pwm=60)

    # 2. 좌회전 호
    steer(100)
    fwd(2, pwm=60)

    # 3. 직선 전진 (수직)  — 중간직선이 필요하면 주석 해제
    # steer(120)
    # fwd(X.XX, pwm=60)   # Xcm → X.XXs

    # 4. 우회전 호
    steer(140)
    fwd(2, pwm=60)

    # 5. 직선 후진
    steer(100)
    rev(2, pwm=60)

    print("[DONE]")
finally:
    stop()
    pca.deinit()
