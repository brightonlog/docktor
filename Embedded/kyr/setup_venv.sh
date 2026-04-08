#!/bin/bash
# ============================================================
# Jetson Orin Nano 가상환경 설정 스크립트
# ============================================================

echo "======================================================================"
echo "  🐍 Python 가상환경 설정 (Jetson Orin Nano)"
echo "======================================================================"
echo ""

# 현재 디렉토리
VENV_DIR="/home/ssafy/S14P11E201/Embedded/kyr/venv"

# 1. 가상환경 생성 (시스템 패키지 접근 허용)
echo "1️⃣ 가상환경 생성 중..."
python3 -m venv $VENV_DIR --system-site-packages

if [ $? -ne 0 ]; then
    echo "❌ 가상환경 생성 실패!"
    echo "python3-venv를 설치하세요: sudo apt-get install python3-venv"
    exit 1
fi

echo "✅ 가상환경 생성 완료"
echo ""

# 2. 가상환경 활성화
echo "2️⃣ 가상환경 활성화 중..."
source $VENV_DIR/bin/activate

# 3. pip 업그레이드
echo "3️⃣ pip 업그레이드 중..."
pip install --upgrade pip

# 4. 필수 패키지 설치
echo "4️⃣ 필수 패키지 설치 중..."
echo ""

echo "📦 Flask 및 웹 서버 패키지..."
pip install flask

echo "📦 AI/ML 패키지..."
pip install ultralytics torch torchvision numpy

echo "📦 Adafruit 모터 제어 (자동 모드용)..."
pip install adafruit-circuitpython-pca9685

echo ""
echo "✅ 모든 패키지 설치 완료"
echo ""

# 5. OpenCV 확인
echo "5️⃣ OpenCV 확인 중..."
python3 -c "import cv2; print(f'OpenCV Version: {cv2.__version__}')" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ OpenCV 정상 동작!"
else
    echo "⚠️  OpenCV를 찾을 수 없습니다."
    echo ""
    echo "시스템에 OpenCV가 설치되어 있는지 확인하세요:"
    echo "  python3 -c 'import cv2; print(cv2.__version__)'"
    echo ""
    echo "또는 수동으로 설치:"
    echo "  sudo apt-get install python3-opencv"
fi

echo ""
echo "======================================================================"
echo "  ✅ 가상환경 설정 완료!"
echo "======================================================================"
echo ""
echo "가상환경 활성화 방법:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "가상환경 비활성화:"
echo "  deactivate"
echo ""
echo "검사 시스템 실행:"
echo "  cd inspection"
echo "  ./run_manual_inspection.sh"
echo ""
echo "======================================================================"
