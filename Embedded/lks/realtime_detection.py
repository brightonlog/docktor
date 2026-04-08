"""
============================================================
realtime_detection.py — 클래스별 색상 bbox 실시간 탐지
============================================================
- online.py의 Flask 스트리밍 구조 동일
- results.plot() 대신 클래스별 색상 bbox로 직접 그림
- bbox 색상은 auto_inspection_system.py와 동일한 규칙
============================================================
사용법:
    python realtime_detection.py [소스] [출력너비]
      소스     : 생략시 카메라, 파일경로시 동영상
      출력너비 : 생략시 원본해상도, 숫자 지정시 비례 축소 → FPS 향상
    예시:
      python realtime_detection.py                        # 카메라 원본
      python realtime_detection.py ./first1.mp4           # 동영상 원본
      python realtime_detection.py ./first1.mp4 640       # 동영상 640px 축소
    → http://[Jetson_IP]:5000 에서 확인
============================================================
"""

import cv2
from ultralytics import YOLO
from flask import Flask, Response
import time
import sys
import os
import random
import signal
import threading

app = Flask(__name__)

# ============================================================
# best_fixed.engine (5클래스) — auto_inspection_system.py와 동일 모델
# ============================================================
CLASS_NAMES = {
    0: 'blister',
    1: 'crack',
    2: 'peeling',
    3: 'sagging',
    4: 'welding_damage',
}

# ============================================================
# class_id별 BGR 색상 — auto_inspection_system.py와 동일
# ============================================================
BBOX_COLORS = {
    0: (0, 255, 255),    # blister        — 노랑
    1: (0, 0, 255),      # crack          — 빨강
    2: (0, 255, 0),      # peeling        — 초록
    3: (255, 255, 0),    # sagging        — 청록
    4: (255, 0, 255),    # welding_damage — 자홍
}

# 미정의 class_id → 랜덤 원색 캐시
_color_cache = {}

def _get_color(class_id):
    """정의된 클래스는 고정색, 미정의는 랜덤 원색 생성후 캐싱"""
    if class_id in BBOX_COLORS:
        return BBOX_COLORS[class_id]
    if class_id not in _color_cache:
        # H(0~359) 랜덤 → 항상 최대 채도·밝기의 원색
        h = random.randint(0, 359)
        c, x = 255, int(255 * (1 - abs(h / 60 % 2 - 1)))
        rgb = [(c,x,0),(x,c,0),(0,c,x),(0,x,c),(x,0,c),(c,0,x)][h // 60]
        _color_cache[class_id] = (rgb[2], rgb[1], rgb[0])  # RGB→BGR
    return _color_cache[class_id]

# ============================================================
# 모델 + 카메라 초기화
# ============================================================
model = YOLO('./models/yolo/best.engine', task='detect')

# argv: [1]=소스(생략시 카메라), [2]=출력너비(생략시 원본)
_source = sys.argv[1] if len(sys.argv) > 1 else 0
_resize_w = int(sys.argv[2]) if len(sys.argv) > 2 else None

cap = cv2.VideoCapture(_source)
if not cap.isOpened():
    print(f"❌ 소스 열기 실패: {_source}")
    sys.exit(1)

if _source == 0:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

_orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
_orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
_native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

# 축소 지정 시 비례 계산
if _resize_w:
    _w = _resize_w
    _h = round(_orig_h * _resize_w / _orig_w)
else:
    _w, _h = _orig_w, _orig_h

# 640 기준 스케일팩터 → bbox 두께/폰트 크기 비례 조정
_scale = _w / 320
_BBOX_THICKNESS = max(2, round(2 * _scale))
_LABEL_SCALE = round(0.4 * _scale, 2)
_LABEL_THICKNESS = max(1, round(1 * _scale))
_OVL_SCALE = round(0.8 * _scale, 2)
_OVL_THICKNESS = max(2, round(2 * _scale))

# 출력 동영상 VideoWriter (동영상 소스일 때만)
if _source != 0:
    _stem, _ext = os.path.splitext(_source)
    _out_path = f"{_stem}_detected{_ext}"
    _writer = cv2.VideoWriter(_out_path, cv2.VideoWriter_fourcc(*'mp4v'), _native_fps, (_w, _h))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"📹 원본: {_orig_w}x{_orig_h}, {total_frames}프레임, {_native_fps:.1f}fps")
    if _resize_w:
        print(f"📐 축소: {_w}x{_h}")
    print(f"💾 출력 경로: {_out_path}")
else:
    _writer = None


# ============================================================
# bbox 그리기
# ============================================================

def draw_detections(frame, results):
    """탐지 결과를 클래스별 색상 bbox로 그리기"""
    boxes = results.boxes
    for i in range(len(boxes)):
        x1, y1, x2, y2 = map(int, boxes.xyxy[i])
        class_id = int(boxes.cls[i])
        class_name = CLASS_NAMES.get(class_id, results.names.get(class_id, 'unknown'))
        color = _get_color(class_id)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, _BBOX_THICKNESS)

        # 라벨 위치: 위에 공간 없으면 박스 안 아래로
        label_h = round(12 * _scale)
        if y1 - label_h < 0:
            label_y = y1 + label_h + 2
        else:
            label_y = y1 - 3
        cv2.putText(frame, class_name, (x1 + 2, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, _LABEL_SCALE, color, _LABEL_THICKNESS)

    return frame


# ============================================================
# MJPEG 스트리밍
# ============================================================

def generate_frames():
    fps_start_time = time.time()
    fps_counter = 0
    fps = 0

    while True:
        success, frame = cap.read()
        if not success:
            break

        if _resize_w:
            frame = cv2.resize(frame, (_w, _h))

        results = model.predict(
            source=frame,
            conf=0.25,
            iou=0.45,
            verbose=False,
            device=0
        )[0]

        frame = draw_detections(frame, results)

        # FPS 계산 (10프레임마다 갱신)
        fps_counter += 1
        if fps_counter % 10 == 0:
            fps_end_time = time.time()
            fps = 10 / (fps_end_time - fps_start_time)
            fps_start_time = time.time()
            fps += 10

        cv2.putText(frame, f"FPS: {fps:.1f} | Defects: {len(results.boxes)}",
                    (10, round(30 * _scale)), cv2.FONT_HERSHEY_SIMPLEX, _OVL_SCALE, (0, 255, 0), _OVL_THICKNESS)

        if _writer is not None:
            _writer.write(frame)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    if _writer is not None:
        _writer.release()
        print(f"✅ 출력 동영상 저장 완료: {_out_path}")

    # 동영상 끝 → 서버 자동 종료
    threading.Thread(target=lambda: (time.sleep(0.5), os.kill(os.getpid(), signal.SIGINT)), daemon=True).start()


# ============================================================
# Flask 라우트
# ============================================================

@app.route('/')
def index():
    return f"<h1>Docktor Real-time Detection</h1><img src='/video_feed' width='{_w}'>"


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    source_label = f"동영상: {_source}" if _source != 0 else "카메라 (device 0)"
    print("=" * 60)
    print("  SafeDeck 실시간 탐지 (클래스별 색상 bbox)")
    print(f"  소스: {source_label}")
    print("  http://[Jetson_IP]:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, threaded=True)
