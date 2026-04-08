from flask import Flask, request, jsonify
import requests
import time
import threading
import json
from flask_cors import CORS
import os
import paho.mqtt.client as mqtt

app = Flask(__name__)
CORS(app)

# --- 설정 정보 ---
SPRING_SERVER_URL = "http://i14e201.p.ssafy.io:8080"
ROBOT_ID = "orin_01"
MQTT_BROKER = "i14e201.p.ssafy.io"
MQTT_PORT = 1883
MQTT_TOPIC = f"robot/{ROBOT_ID}/move"

is_busy = False
status_lock = threading.Lock()

# auto_inspection_system.py Flask 서버 주소 (검사 트리거 및 결과 조회용)
INSPECTION_SERVER_URL = "http://localhost:5004"


def execute_and_report(inspect_id, ship_id, corp_id, callback_url, duration):
    """
    MQTT/HTTP 명령 수신 후 실제 검사 실행 및 백엔드 보고
    - auto_inspection_system.py(localhost:5004)에 검사 트리거
    - 완료 후 inspection_results.json에서 결과 읽기
    - auto_inspection_system_api.report_inspection()로 S3 + callback
    """
    global is_busy
    try:
        from types import SimpleNamespace
        from auto_inspection_system_api import report_inspection

        # 1. 검사 시작 트리거
        print(f"📡 [Inspect {inspect_id}] 검사 트리거...")
        start_resp = requests.post(f"{INSPECTION_SERVER_URL}/api/start_auto")
        start_result = start_resp.json()
        if not start_result.get("success"):
            print(f"❌ 검사 시작 실패: {start_result.get('message')}")
            return

        # 2. 검사 완료 대기 (polling)
        print("⏳ 검사 완료 대기...")
        while True:
            status = requests.get(f"{INSPECTION_SERVER_URL}/api/status").json()
            completed = status.get("completed_zones", 0)
            total = status.get("total_zones", 6)
            is_active = status.get("is_active", True)
            print(f"  [{completed}/{total}] {'진행 중...' if is_active else '완료'}")
            if not is_active and completed >= total:
                break
            time.sleep(2)

        print(f"✅ 검사 완료 — {completed}개 zone, 결함: {status.get('defective_zones', 0)}개")

        # 3. inspection_results.json 읽기 (full bbox/class_id 정보 포함)
        zone_results = status.get("zone_results", [])
        if not zone_results:
            print("⚠️ 검사 결과가 비어있습니다")
            return

        session_dir = os.path.dirname(zone_results[0]["image_path"])
        results_json_path = os.path.join(session_dir, "inspection_results.json")

        with open(results_json_path, "r", encoding="utf-8") as f:
            results_data = json.load(f)

        # dict → SimpleNamespace (report_inspection의 .속성 접근과 호환)
        results = [SimpleNamespace(**r) for r in results_data["results"]]

        # 4. ROI config 가져오기
        roi_resp = requests.get(f"{INSPECTION_SERVER_URL}/api/roi_config").json()
        roi_config = SimpleNamespace(**roi_resp)

        # 5. 백엔드 보고 (S3 업로드 + Spring Boot callback)
        report_inspection(
            results=results,
            roi_config=roi_config,
            inspect_id=inspect_id,
            ship_id=ship_id,
            corp_id=corp_id,
            callback_url=callback_url,
        )

    except Exception as e:
        print(f"❌ 작업 도중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
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
        inspect_id = payload.get("inspect_id")

        with status_lock:
            if is_busy:
                print(
                    f"⚠️ [MQTT] 로봇이 현재 작업 중입니다. 명령을 무시합니다. (ID: {inspect_id})"
                )
                return
            is_busy = True

        print(f"📩 MQTT 메시지 수신! (ID: {inspect_id})")
        params = {
            "inspect_id": inspect_id,
            "ship_id": payload.get("ship_id"),
            "corp_id": payload.get("corp_id", 1),
            "callback_url": payload.get("callback_url"),
            "duration": float(payload.get("duration", 2.0)),
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


@app.route("/move", methods=["POST"])
def move_robot():
    global is_busy
    data = request.get_json()
    inspect_id = data.get("inspect_id")

    with status_lock:
        if is_busy:
            return (
                jsonify(
                    {
                        "status": "rejected",
                        "reason": "Robot is currently busy with another task",
                    }
                ),
                429,
            )

        is_busy = True

    print(f"📢 HTTP: /move 요청 수신! (ID: {inspect_id})")
    params = {
        "inspect_id": inspect_id,
        "ship_id": data.get("ship_id"),
        "corp_id": data.get("corp_id", 1),
        "callback_url": data.get("callback_url"),
        "duration": float(data.get("duration", 2.0)),
    }
    threading.Thread(target=execute_and_report, kwargs=params).start()
    return jsonify({"status": "started", "inspect_id": inspect_id}), 200


if __name__ == "__main__":
    mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
    mqtt_thread.start()
    app.run(host="0.0.0.0", port=5000)
