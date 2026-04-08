from flask import Flask, request, jsonify
import requests
import time
import threading
import boto3
import cv2
import io
import uuid
import numpy as np
import json
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

app = Flask(__name__)
CORS(app)

# --- 설정 정보 ---
SPRING_SERVER_URL = "http://i14e201.p.ssafy.io:8080"
ROBOT_ID = "orin_01"
S3_BUCKET = "docktor-bucket"
MQTT_BROKER = "i14e201.p.ssafy.io"
MQTT_PORT = 8082
MQTT_TOPIC = f"robot/{ROBOT_ID}/move"

is_busy = False
status_lock = threading.Lock()

load_dotenv()

s3_client = boto3.client('s3', 
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), 
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'), 
    region_name=os.getenv('AWS_REGION')
)

def upload_to_s3_mem(img_array, s3_path):
    try:
        _, buffer = cv2.imencode('.jpg', img_array)
        io_buf = io.BytesIO(buffer)
        s3_client.upload_fileobj(io_buf, S3_BUCKET, s3_path)
        return f"https://{S3_BUCKET}.s3.ap-northeast-2.amazonaws.com/{s3_path}"
    except Exception as e:
        print(f"❌ S3 Error: {e}")
        return None

def process_single_defect(idx, detection, original_img, s3_base_dir):
    bbox = detection['bbox']
    crop = original_img[int(bbox[1]):int(bbox[3]), int(bbox[0]):int(bbox[2])]
    s3_path = f"{s3_base_dir}/defects/defect_{idx+1}_crop.jpg"
    url = upload_to_s3_mem(crop, s3_path)
    
    return {
        "category_id": detection.get('class_id'),
        "confidence": detection.get('confidence'),
        "x1": int(bbox[0]), "y1": int(bbox[1]), 
        "x2": int(bbox[2]), "y2": int(bbox[3]),
        "x_cord": detection.get('x_cord'),
        "y_cord": detection.get('y_cord'),
        "cropped_image_url": url
    }

def execute_and_report(inspect_id, ship_id, corp_id, callback_url, duration):
    global is_busy
    try:
        print(f"📡 [Inspect {inspect_id}] 분석 데이터 처리 시작...")
        time.sleep(duration) 
        
        sample_ai_result = {
            "success": True,
            "data": {
                "detections": [
                    {"class": "Crack", "class_id": 4, "confidence": 0.95, "bbox": [100, 150, 250, 300], "x_cord": 15, "y_cord": 34},
                    {"class": "Corrosion", "class_id": 9, "confidence": 0.87, "bbox": [300, 200, 450, 350], "x_cord": 55, "y_cord": 120}
                ]
            }
        }

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cv2.putText(frame, f"Inspect ID: {inspect_id}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        s3_base_dir = f"corp_{corp_id}/ships/{ship_id}/inspects/{inspect_id}"
        original_s3_path = f"{s3_base_dir}/original/img_{inspect_id}_{uuid.uuid4().hex[:6]}.jpg"
        original_url = upload_to_s3_mem(frame, original_s3_path)
        
        detections = sample_ai_result["data"]["detections"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            defect_results = list(executor.map(
                lambda x: process_single_defect(x[0], x[1], frame, s3_base_dir), 
                enumerate(detections)
            ))

        payload = {
            "inspect_id": inspect_id,
            "status": "completed",
            "image_url": original_url,
            "defects": defect_results
        }

        resp = requests.post(callback_url, json=payload, timeout=10)
        print(f"✅ [Callback] Spring Boot 보고 완료: {resp.status_code}")

    except Exception as e:
        print(f"❌ 작업 도중 오류 발생: {e}")
    finally:
        with status_lock:
            is_busy = False
            print(f"🔓 로봇 상태 해제 (Ready)")
            
def on_connect(client, userdata, flags, rc):
    print(f"✅ MQTT 브로커 연결 성공 ({MQTT_BROKER}:{MQTT_PORT})")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global is_busy
    try:
        payload = json.loads(msg.payload.decode())
        inspect_id = payload.get('inspect_id')

        with status_lock:
            if is_busy:
                print(f"⚠️ [MQTT] 로봇이 현재 작업 중입니다. 명령을 무시합니다. (ID: {inspect_id})")
                return
            is_busy = True 
        
        print(f"📩 MQTT 메시지 수신! (ID: {inspect_id})")
        params = {
            "inspect_id": inspect_id,
            "ship_id": payload.get('ship_id'),
            "corp_id": payload.get('corp_id', 1),
            "callback_url": payload.get('callback_url'),
            "duration": float(payload.get('duration', 2.0))
        }
        threading.Thread(target=execute_and_report, kwargs=params).start()
        
    except Exception as e:
        print(f"❌ MQTT 처리 오류: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"❌ MQTT 연결 실패: {e}")

@app.route('/move', methods=['POST'])
def move_robot():
    global is_busy
    data = request.get_json()
    inspect_id = data.get('inspect_id')

    with status_lock:
        if is_busy:
            return jsonify({
                "status": "rejected", 
                "reason": "Robot is currently busy with another task"
            }), 429 

        is_busy = True

    print(f"📢 HTTP: /move 요청 수신! (ID: {inspect_id})")
    params = {
        "inspect_id": inspect_id,
        "ship_id": data.get('ship_id'),
        "corp_id": data.get('corp_id', 1),
        "callback_url": data.get('callback_url'),
        "duration": float(data.get('duration', 2.0))
    }
    threading.Thread(target=execute_and_report, kwargs=params).start()
    return jsonify({"status": "started", "inspect_id": inspect_id}), 200

if __name__ == '__main__':
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()
    app.run(host='0.0.0.0', port=5000)