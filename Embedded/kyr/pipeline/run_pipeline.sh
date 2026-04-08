#!/bin/bash

##############################################################
# AI Detection Pipeline - Test Runner
##############################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  AI Detection Pipeline - Test Runner"
echo "============================================================"
echo ""

# 기본 설정
YOLO_MODEL="../models/yolo/best_fixed.pt"
ANOMALY_MODEL="../models/anomaly_detection/best_model.pt"
OUTPUT_DIR="../pipeline_results"

# 사용법 출력
if [ "$1" == "-h" ] || [ "$1" == "--help" ] || [ -z "$1" ]; then
    echo "Usage: $0 <input_image_or_directory> [options]"
    echo ""
    echo "Arguments:"
    echo "  input_image_or_directory    Image file or directory containing images"
    echo ""
    echo "Options:"
    echo "  --yolo-model PATH           YOLO model path (default: $YOLO_MODEL)"
    echo "  --anomaly-model PATH        Anomaly model path (default: $ANOMALY_MODEL)"
    echo "  --yolo-conf FLOAT           YOLO confidence threshold (default: 0.5)"
    echo "  --anomaly-threshold FLOAT   Anomaly threshold (default: 0.7)"
    echo "  --output-dir PATH           Output directory (default: $OUTPUT_DIR)"
    echo ""
    echo "Examples:"
    echo "  # 단일 이미지 처리"
    echo "  $0 test_image.jpg"
    echo ""
    echo "  # 폴더 내 모든 이미지 처리"
    echo "  $0 ./test_images/"
    echo ""
    echo "  # 커스텀 설정으로 처리"
    echo "  $0 ./test_images/ --yolo-conf 0.6 --anomaly-threshold 0.8"
    echo ""
    exit 0
fi

# Python 실행
echo "[INFO] Running AI Pipeline..."
echo ""

python3 ai_pipeline.py "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ Pipeline execution completed successfully!"
    echo "============================================================"
else
    echo ""
    echo "============================================================"
    echo "❌ Pipeline execution failed with exit code: $EXIT_CODE"
    echo "============================================================"
fi

exit $EXIT_CODE
