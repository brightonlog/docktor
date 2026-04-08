# sudo -E $(which python) keyboard_control.py


from adafruit_motor import motor
from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import board
import busio
import time
import keyboard  # pynput 대신 keyboard 사용 (sudo 필요)

class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 600  # 주파수 설정

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))  # 16비트 듀티 사이클 계산
       
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

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 600  # PCA9685 주파수 설정

motor_hat = PWMThrottleHat(pca, channel=0)

kit = ServoKit(channels=16, i2c=i2c, address=0x60)
pan = 100  # 서보 모터 초기 위치 설정
kit.servo[0].angle = pan

def i2c_scan(i2c):
    while not i2c.try_lock():
        pass
    try:
        devices = i2c.scan()
        return devices
    finally:
        i2c.unlock()

SPEED = 0.6  # 속도 설정 (0.1 ~ 1.0, 낮을수록 느림)

def on_press(event):
    global pan
    key = event.name

    if key == 'w':
        print("Motor forward")
        motor_hat.set_throttle(SPEED)  # 전진
    elif key == 's':
        print("Motor backward")
        motor_hat.set_throttle(-SPEED)  # 후진
    elif key == 'a':
        print("Servo left")
        pan -= 10  # 서보 모터 왼쪽으로 이동
        if pan < 0:
            pan = 0
        kit.servo[0].angle = pan
        print(f"Servo angle set to: {pan}")
    elif key == 'd':
        print("Servo right")
        pan += 10  # 서보 모터 오른쪽으로 이동
        if pan > 180:
            pan = 180
        kit.servo[0].angle = pan
        print(f"Servo angle set to: {pan}")
    elif key == 'space':
        print("Motor stop (spacebar)")
        motor_hat.set_throttle(0)  # 스페이스바로 정지

def on_release(event):
    key = event.name
    if key in ['w', 's']:
        print("Motor stop")
        motor_hat.set_throttle(0)  # 모터 정지

keyboard.on_press(on_press)
keyboard.on_release(on_release)

print("키보드 제어 시작 (W/S: 전진/후진, A/D: 좌/우, SPACE: 정지, ESC: 종료)")

try:
    keyboard.wait('esc')  # ESC 누를 때까지 대기
except KeyboardInterrupt:
    pass
finally:
    motor_hat.set_throttle(0)  # 모터 정지
    kit.servo[0].angle = 100  # 서보 모터 초기 위치로 리셋
    pca.deinit()  # PCA9685 정리
    print("Program stopped and motor stopped.")
