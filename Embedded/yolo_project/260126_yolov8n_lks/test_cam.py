import cv2

# 모든 인덱스를 다 찔러보는 테스트 (0~5)
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
    if cap.isOpened():
        print(f"✅ 카메라 인덱스 {i}번 인식 성공!")
        ret, frame = cap.read()
        if ret:
            print(f"   - {i}번에서 이미지 데이터 읽기 성공!")
        cap.release()
    else:
        print(f"❌ {i}번 카메라 없음")