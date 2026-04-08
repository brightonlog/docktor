#!/bin/bash
###############################################################################
# YOLOv8 Training Script with MLOps
# 선박 도장 결함 탐지 모델 학습
###############################################################################

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}YOLOv8 Training with MLOps${NC}"
echo -e "${BLUE}========================================${NC}"

# Default values
MODEL="yolov8n"
EPOCHS=100
BATCH=16
DEVICE=0
DATA_YAML="data/yolo_dataset/data.yaml"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --epochs)
      EPOCHS="$2"
      shift 2
      ;;
    --batch)
      BATCH="$2"
      shift 2
      ;;
    --device)
      DEVICE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}Configuration:${NC}"
echo "  Model: $MODEL"
echo "  Epochs: $EPOCHS"
echo "  Batch: $BATCH"
echo "  Device: $DEVICE"
echo ""

echo -e "${BLUE}Note: Running in file-based mode (no MLOps UI)${NC}"
echo "  - MLflow logs: mlruns/"
echo "  - Training results: runs/detect/train/"
echo ""

# Step 1: Check dataset
echo -e "${BLUE}[1/2] Checking dataset...${NC}"
if [ ! -f "$DATA_YAML" ]; then
    echo -e "${RED}Error: $DATA_YAML not found${NC}"
    echo "Please run prepare_yolo_dataset.py first:"
    echo "  python src/training/prepare_yolo_dataset.py"
    exit 1
fi
echo -e "${GREEN}✓ Dataset ready${NC}"
echo ""

# Step 2: Start training
echo -e "${BLUE}[2/2] Starting training...${NC}"
echo ""

python src/training/train_yolov8.py \
    --model "$MODEL" \
    --data "$DATA_YAML" \
    --epochs "$EPOCHS" \
    --batch "$BATCH" \
    --device "$DEVICE"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Training Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Training artifacts saved to:"
echo "  - Model weights: runs/detect/train/weights/best.pt"
echo "  - Training curves: runs/detect/train/*.png"
echo "  - MLflow logs: mlruns/"
echo ""
echo "Next steps:"
echo "  1. View training results:"
echo "     - Check plots: ls runs/detect/train/*.png"
echo "     - Check metrics: cat runs/detect/train/results.csv"
echo "  2. Evaluate model:"
echo "     python src/training/evaluate.py --model runs/detect/train/weights/best.pt"
echo ""
