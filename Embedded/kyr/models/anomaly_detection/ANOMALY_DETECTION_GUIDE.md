# Anomaly Detection 구현 가이드

Autoencoder 기반 이상 탐지 모델의 추론 로직을 구현하는 가이드입니다.

## 📋 목차

- [개요](#개요)
- [현재 상태](#현재-상태)
- [구현 방법](#구현-방법)
- [예제 코드](#예제-코드)
- [테스트](#테스트)

---

## 🎯 개요

### Autoencoder 기반 이상 탐지

1. **학습**: 정상(Normal) 이미지만 사용하여 Autoencoder 학습
2. **추론**:
   - 입력 이미지를 Autoencoder에 통과
   - Reconstruction Error 계산
   - Threshold 기반 이상 판단

### 동작 원리

```
입력 이미지 → Encoder → Latent → Decoder → 재구성 이미지
              ↓                              ↓
              압축                          복원
                                             ↓
                        Reconstruction Error 계산
                                             ↓
                        Threshold 비교 → 이상 판단
```

---

## 📊 현재 상태

`orincar_inspection_system.py`의 `AnomalyDetector` 클래스는 **placeholder**로 구현되어 있습니다.

```python
class AnomalyDetector:
    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float, bool]:
        # TODO: 실제 Autoencoder 추론 로직 구현
        # Placeholder: 랜덤하게 이상 판단
        reconstruction_error = np.random.random()
        is_anomaly = reconstruction_error > self.threshold
        ...
```

**실제 추론 로직을 구현해야 합니다!**

---

## 🔧 구현 방법

### Step 1: 모델 아키텍처 확인

먼저 `best_model.pt` 모델의 구조를 확인합니다.

```python
import torch

model = torch.load('anomaly_detection/best_model.pt')
print(model)  # 모델 구조 출력
```

### Step 2: 이미지 전처리 함수 작성

Autoencoder 입력에 맞게 이미지를 전처리합니다.

```python
import cv2
import numpy as np
import torch
from torchvision import transforms

def preprocess_image(frame: np.ndarray, input_size=(128, 128)) -> torch.Tensor:
    """
    이미지 전처리
    Args:
        frame: OpenCV 이미지 (BGR, H x W x 3)
        input_size: 모델 입력 크기 (width, height)
    Returns:
        torch.Tensor: (1, 3, H, W) 형태의 텐서
    """
    # BGR → RGB
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 리사이즈
    image = cv2.resize(image, input_size)

    # 정규화 (0-255 → 0-1)
    image = image.astype(np.float32) / 255.0

    # Transpose (H, W, C) → (C, H, W)
    image = np.transpose(image, (2, 0, 1))

    # Numpy → Tensor
    tensor = torch.from_numpy(image)

    # Batch dimension 추가 (C, H, W) → (1, C, H, W)
    tensor = tensor.unsqueeze(0)

    return tensor
```

### Step 3: Reconstruction Error 계산

```python
def calculate_reconstruction_error(original: torch.Tensor,
                                   reconstructed: torch.Tensor,
                                   method='mse') -> float:
    """
    Reconstruction Error 계산
    Args:
        original: 원본 이미지 텐서
        reconstructed: 재구성된 이미지 텐서
        method: 'mse' 또는 'mae'
    Returns:
        float: Reconstruction error 값
    """
    if method == 'mse':
        # Mean Squared Error
        error = torch.mean((original - reconstructed) ** 2)
    elif method == 'mae':
        # Mean Absolute Error
        error = torch.mean(torch.abs(original - reconstructed))
    else:
        raise ValueError(f"Unknown method: {method}")

    return error.item()
```

### Step 4: Bounding Box 생성 (선택 사항)

이상 영역에 BBox를 생성할 수 있습니다.

```python
def generate_anomaly_bbox(error_map: np.ndarray,
                          threshold: float) -> List[List[int]]:
    """
    에러 맵에서 이상 영역의 BBox 생성
    Args:
        error_map: Reconstruction error map (H x W)
        threshold: 이상 판단 임계값
    Returns:
        List[List[int]]: [[x1, y1, x2, y2], ...] BBox 리스트
    """
    # Threshold 적용
    anomaly_mask = (error_map > threshold).astype(np.uint8) * 255

    # Contour 찾기
    contours, _ = cv2.findContours(anomaly_mask,
                                   cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 10 and h > 10:  # 최소 크기 필터링
            bboxes.append([x, y, x + w, y + h])

    return bboxes
```

---

## 💻 예제 코드

### 완전한 AnomalyDetector 구현 예시

```python
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from typing import Dict, List, Tuple

class AnomalyDetector:
    """Autoencoder 기반 이상 탐지"""

    def __init__(self, model_path: str, threshold: float = 0.7):
        self.model_path = model_path
        self.threshold = threshold
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.input_size = (128, 128)  # 모델에 맞게 조정
        self.load_model()

    def load_model(self):
        """모델 로드"""
        try:
            print(f"[ANOMALY] Loading model: {self.model_path}")
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()
            print("[ANOMALY] Model loaded successfully")
        except Exception as e:
            print(f"[ERROR] Anomaly model load failed: {e}")
            self.model = None

    def preprocess(self, frame: np.ndarray) -> torch.Tensor:
        """이미지 전처리"""
        # BGR → RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 리사이즈
        image = cv2.resize(image, self.input_size)

        # 정규화 (0-255 → 0-1)
        image = image.astype(np.float32) / 255.0

        # Transpose (H, W, C) → (C, H, W)
        image = np.transpose(image, (2, 0, 1))

        # Numpy → Tensor
        tensor = torch.from_numpy(image).unsqueeze(0)  # (1, C, H, W)

        return tensor.to(self.device)

    def calculate_error(self, original: torch.Tensor,
                       reconstructed: torch.Tensor) -> float:
        """Reconstruction Error 계산"""
        # MSE (Mean Squared Error)
        error = torch.mean((original - reconstructed) ** 2)
        return error.item()

    def detect(self, frame: np.ndarray) -> Tuple[List[Dict], float, bool]:
        """
        이상 탐지
        Returns: (detections, inference_time_ms, is_defective)
        """
        if self.model is None:
            print("[WARN] Anomaly model not available, skipping detection")
            return [], 0.0, False

        try:
            import time
            start_time = time.time()

            # 1. 이미지 전처리
            input_tensor = self.preprocess(frame)

            # 2. 추론 (no gradient)
            with torch.no_grad():
                reconstructed = self.model(input_tensor)

            # 3. Reconstruction Error 계산
            reconstruction_error = self.calculate_error(input_tensor, reconstructed)

            # 4. 이상 판단
            is_anomaly = reconstruction_error > self.threshold

            inference_time = (time.time() - start_time) * 1000

            # 5. 결과 생성
            detections = []
            if is_anomaly:
                detections.append({
                    'type': 'anomaly',
                    'score': float(reconstruction_error),
                    'threshold': self.threshold,
                    'description': f'Anomaly detected (error: {reconstruction_error:.4f})'
                })

            print(f"[ANOMALY] Error: {reconstruction_error:.4f}, "
                  f"Threshold: {self.threshold}, "
                  f"Is Anomaly: {is_anomaly}")

            return detections, inference_time, is_anomaly

        except Exception as e:
            print(f"[ERROR] Anomaly detection failed: {e}")
            import traceback
            traceback.print_exc()
            return [], 0.0, False
```

---

## 🧪 테스트

### 1. 단독 테스트 스크립트

`test_anomaly_detection.py` 파일을 생성하여 테스트합니다.

```python
#!/usr/bin/env python3
import cv2
import sys
from anomaly_detection_impl import AnomalyDetector  # 위에서 구현한 클래스

def test_anomaly_detection(image_path: str):
    """이상 탐지 테스트"""

    # 모델 로드
    detector = AnomalyDetector(
        model_path='anomaly_detection/best_model.pt',
        threshold=0.7
    )

    # 이미지 로드
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Failed to load image: {image_path}")
        return

    print(f"Image loaded: {frame.shape}")

    # 탐지 수행
    detections, inference_time, is_anomaly = detector.detect(frame)

    # 결과 출력
    print(f"\n{'='*60}")
    print(f"Inference Time: {inference_time:.2f} ms")
    print(f"Is Anomaly: {is_anomaly}")
    print(f"Detections: {len(detections)}")

    for i, det in enumerate(detections):
        print(f"\nDetection {i+1}:")
        for key, value in det.items():
            print(f"  {key}: {value}")

    print(f"{'='*60}\n")

    # 결과 시각화
    result_image = frame.copy()
    if is_anomaly:
        cv2.putText(result_image, "ANOMALY DETECTED", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if detections:
            score = detections[0]['score']
            cv2.putText(result_image, f"Score: {score:.4f}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    else:
        cv2.putText(result_image, "NORMAL", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # 저장
    output_path = image_path.replace('.jpg', '_result.jpg')
    cv2.imwrite(output_path, result_image)
    print(f"Result saved: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 test_anomaly_detection.py <image_path>")
        sys.exit(1)

    test_anomaly_detection(sys.argv[1])
```

### 2. 실행

```bash
# 정상 이미지 테스트
python3 test_anomaly_detection.py normal_sample.jpg

# 이상 이미지 테스트
python3 test_anomaly_detection.py anomaly_sample.jpg
```

### 3. Threshold 조정

여러 테스트 이미지로 실험하여 최적의 threshold를 찾습니다.

```python
# Threshold 스윕 테스트
thresholds = [0.3, 0.5, 0.7, 0.9]

for threshold in thresholds:
    detector = AnomalyDetector(
        model_path='anomaly_detection/best_model.pt',
        threshold=threshold
    )
    # 테스트 수행
    ...
```

---

## 📝 체크리스트

완전한 구현을 위해 다음 사항들을 확인하세요:

- [ ] 모델 아키텍처 확인 및 이해
- [ ] 입력 크기 (input_size) 확인 및 설정
- [ ] 전처리 방식 확인 (정규화, 색상 공간 등)
- [ ] Reconstruction Error 계산 방식 선택 (MSE, MAE, SSIM 등)
- [ ] Threshold 값 실험 및 최적화
- [ ] 다양한 이미지로 테스트
- [ ] `orincar_inspection_system.py`에 통합
- [ ] 실제 검사 환경에서 성능 확인

---

## 🔄 시스템 통합

구현이 완료되면 `orincar_inspection_system.py`의 `AnomalyDetector` 클래스를 교체합니다.

1. 위 예제 코드를 복사
2. `orincar_inspection_system.py`의 `AnomalyDetector` 클래스 교체
3. 테스트 실행

또는 별도 파일로 분리:

```python
# anomaly_detector_impl.py 파일 생성
# ... (위 예제 코드)

# orincar_inspection_system.py에서 import
from anomaly_detector_impl import AnomalyDetector
```

---

## 💡 팁

1. **GPU 사용 확인**
   ```python
   print(f"Device: {self.device}")
   print(f"CUDA available: {torch.cuda.is_available()}")
   ```

2. **추론 시간 최적화**
   - TensorRT로 변환
   - Half precision (FP16) 사용
   - Batch 처리

3. **Error Map 시각화**
   ```python
   error_map = torch.abs(original - reconstructed)
   error_map_np = error_map[0, 0].cpu().numpy()  # 첫 번째 채널
   cv2.imwrite('error_map.jpg', error_map_np * 255)
   ```

4. **Threshold 자동 조정**
   - 정상 이미지들의 error 분포 분석
   - Mean + K * Std 방식 사용

---

## 📚 참고 자료

- PyTorch Autoencoder Tutorial: https://pytorch.org/tutorials/
- Anomaly Detection Papers: https://paperswithcode.com/task/anomaly-detection
- OpenCV Documentation: https://docs.opencv.org/

---

**구현 완료 후 반드시 실제 환경에서 테스트하세요! 🧪**
