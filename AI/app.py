from flask import Flask, request, jsonify
from ultralytics import YOLO
import os
import tempfile
import time

app = Flask(__name__)

model = YOLO("best.pt")

CLASS_NAMES = {
    0: "WaterSpotting", 1: "Sagging", 2: "Peeling", 3: "Pinhole",
    4: "Crack", 5: "Blistering", 6: "Inclusion",
    7: "WeldingDamage", 8: "Scratch", 9: "Corrosion"
}

@app.route('/api/v1/detect', methods=['POST'])
def detect():
    try:
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "No image provided"}), 400

        image_file = request.files['image']
        conf_threshold = float(request.form.get('confidence_threshold', 0.5))

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
            image_file.save(temp.name)
            temp_path = temp.name

        start_time = time.time()
        results = model.predict(temp_path, conf=conf_threshold)
        inference_time = int((time.time() - start_time) * 1000)

        detections = []
        result = results[0]
        img_h, img_w = result.orig_shape

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])

            detections.append({
                "class": CLASS_NAMES.get(cls_id, "Unknown"),
                "class_id": cls_id,
                "confidence": round(conf, 4),
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "bbox_normalized": [
                    round(x1 / img_w, 4), round(y1 / img_h, 4),
                    round(x2 / img_w, 4), round(y2 / img_h, 4)
                ]
            })

        os.remove(temp_path)

        return jsonify({
            "success": True,
            "data": {
                "detections": detections,
                "image_info": {"width": img_w, "height": img_h, "filename": image_file.filename},
                "inference_time_ms": inference_time,
                "model_version": "yolo11n_v6",
                "total_detections": len(detections)
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)