"""
Anomaly Detection Module for Docktor Project

SSIM Autoencoder 기반 이상탐지 모듈
- 정상 이미지만으로 학습 (Unsupervised)
- 복원 오차(MSE + SSIM)를 이용해 이상 점수 계산
"""

from .models.autoencoder import SSIMAnomalyAutoencoder

__all__ = ["SSIMAnomalyAutoencoder"]
