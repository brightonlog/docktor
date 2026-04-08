FROM python:3.9-slim

# 필요한 빌드 도구 및 라이브러리 설치
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libgpiod-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 하드웨어 라이브러리 설치
# --no-cache-dir를 사용하여 이미지 용량을 줄이고 최신 버전을 가져옵니다.
RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    requests \
    adafruit-circuitpython-pca9685 \
    adafruit-circuitpython-motor \
    board \
    RPi.GPIO

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]