import cv2
import numpy as np

def print_camera_properties(cap):
    """현재 카메라의 모든 설정값 출력"""
    print("\n=== 현재 카메라 설정값 ===")
    properties = {
        'CAP_PROP_BRIGHTNESS': cv2.CAP_PROP_BRIGHTNESS,
        'CAP_PROP_CONTRAST': cv2.CAP_PROP_CONTRAST,
        'CAP_PROP_SATURATION': cv2.CAP_PROP_SATURATION,
        'CAP_PROP_HUE': cv2.CAP_PROP_HUE,
        'CAP_PROP_EXPOSURE': cv2.CAP_PROP_EXPOSURE,
        'CAP_PROP_AUTO_EXPOSURE': cv2.CAP_PROP_AUTO_EXPOSURE,
        'CAP_PROP_GAIN': cv2.CAP_PROP_GAIN,
        'CAP_PROP_AUTO_WB': cv2.CAP_PROP_AUTO_WB,
        'CAP_PROP_WB_TEMPERATURE': cv2.CAP_PROP_WB_TEMPERATURE,
        'CAP_PROP_AUTOFOCUS': cv2.CAP_PROP_AUTOFOCUS,
        'CAP_PROP_FOCUS': cv2.CAP_PROP_FOCUS,
        'CAP_PROP_SHARPNESS': cv2.CAP_PROP_SHARPNESS,
    }

    for name, prop in properties.items():
        value = cap.get(prop)
        print(f"{name}: {value}")

def create_trackbar_window():
    """카메라 설정을 실시간으로 조정할 수 있는 트랙바 생성"""
    cv2.namedWindow('Camera Settings')

    # 트랙바 생성 (0-100 범위, 기본값 50)
    cv2.createTrackbar('Brightness', 'Camera Settings', 50, 100, lambda x: None)
    cv2.createTrackbar('Contrast', 'Camera Settings', 50, 100, lambda x: None)
    cv2.createTrackbar('Saturation', 'Camera Settings', 50, 100, lambda x: None)
    cv2.createTrackbar('Exposure', 'Camera Settings', 50, 100, lambda x: None)
    cv2.createTrackbar('Gain', 'Camera Settings', 50, 100, lambda x: None)
    cv2.createTrackbar('Sharpness', 'Camera Settings', 50, 100, lambda x: None)
    cv2.createTrackbar('WB Temp', 'Camera Settings', 50, 100, lambda x: None)

    # Auto 설정 토글 (0 = OFF, 1 = ON)
    cv2.createTrackbar('Auto Exposure', 'Camera Settings', 1, 1, lambda x: None)
    cv2.createTrackbar('Auto WB', 'Camera Settings', 1, 1, lambda x: None)
    cv2.createTrackbar('Auto Focus', 'Camera Settings', 0, 1, lambda x: None)

def apply_settings(cap):
    """트랙바 값을 읽어서 카메라에 적용"""
    # 값 읽기 (0-100을 -50~50 범위로 변환)
    brightness = cv2.getTrackbarPos('Brightness', 'Camera Settings') - 50
    contrast = cv2.getTrackbarPos('Contrast', 'Camera Settings') - 50
    saturation = cv2.getTrackbarPos('Saturation', 'Camera Settings') - 50
    exposure = cv2.getTrackbarPos('Exposure', 'Camera Settings') - 50
    gain = cv2.getTrackbarPos('Gain', 'Camera Settings')
    sharpness = cv2.getTrackbarPos('Sharpness', 'Camera Settings')
    wb_temp = cv2.getTrackbarPos('WB Temp', 'Camera Settings') * 100  # 0-10000 범위

    auto_exposure = cv2.getTrackbarPos('Auto Exposure', 'Camera Settings')
    auto_wb = cv2.getTrackbarPos('Auto WB', 'Camera Settings')
    auto_focus = cv2.getTrackbarPos('Auto Focus', 'Camera Settings')

    # 설정 적용
    cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
    cap.set(cv2.CAP_PROP_CONTRAST, contrast)
    cap.set(cv2.CAP_PROP_SATURATION, saturation)
    cap.set(cv2.CAP_PROP_SHARPNESS, sharpness)
    cap.set(cv2.CAP_PROP_GAIN, gain)

    # Auto Exposure 설정
    # 0.75 = 자동 모드, 0.25 = 수동 모드 (카메라에 따라 다를 수 있음)
    if auto_exposure:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
    else:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, exposure)

    # Auto White Balance 설정
    cap.set(cv2.CAP_PROP_AUTO_WB, auto_wb)
    if not auto_wb:
        cap.set(cv2.CAP_PROP_WB_TEMPERATURE, wb_temp)

    # Auto Focus 설정 (고정 초점 카메라는 지원 안 될 수 있음)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, auto_focus)

def main():
    # 카메라 초기화
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 현재 설정 출력
    print_camera_properties(cap)

    # 트랙바 윈도우 생성
    create_trackbar_window()
    cv2.namedWindow('Camera Feed')

    print("\n=== 사용 방법 ===")
    print("트랙바를 조정하여 실시간으로 카메라 설정을 변경할 수 있습니다.")
    print("'s' 키: 현재 설정값 출력")
    print("'r' 키: 기본값으로 리셋")
    print("'q' 키: 종료")
    print("================\n")

    while True:
        # 설정 적용
        apply_settings(cap)

        # 프레임 읽기
        ret, frame = cap.read()
        if not ret:
            print("카메라에서 프레임을 읽을 수 없습니다.")
            break

        # 프레임 표시
        cv2.imshow('Camera Feed', frame)

        # 키 입력 처리
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('s'):
            print_camera_properties(cap)
        elif key == ord('r'):
            # 트랙바를 기본값(50)으로 리셋
            cv2.setTrackbarPos('Brightness', 'Camera Settings', 50)
            cv2.setTrackbarPos('Contrast', 'Camera Settings', 50)
            cv2.setTrackbarPos('Saturation', 'Camera Settings', 50)
            cv2.setTrackbarPos('Exposure', 'Camera Settings', 50)
            cv2.setTrackbarPos('Gain', 'Camera Settings', 50)
            cv2.setTrackbarPos('Sharpness', 'Camera Settings', 50)
            cv2.setTrackbarPos('WB Temp', 'Camera Settings', 50)
            cv2.setTrackbarPos('Auto Exposure', 'Camera Settings', 1)
            cv2.setTrackbarPos('Auto WB', 'Camera Settings', 1)
            cv2.setTrackbarPos('Auto Focus', 'Camera Settings', 0)
            print("설정을 기본값으로 리셋했습니다.")

    # 리소스 해제
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
