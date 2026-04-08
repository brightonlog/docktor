"""
SSIM Autoencoder for Anomaly Detection

선박 도장 결함 이상탐지를 위한 Convolutional Autoencoder
- 정상 이미지만으로 학습 (Unsupervised Learning)
- 복원 오차(MSE + SSIM)를 이용해 이상 점수 계산
- Jetson Orin Nano 최적화를 위한 경량 설계
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class SSIMLoss(nn.Module):
    """
    Structural Similarity Index (SSIM) Loss

    SSIM은 인간의 시각 시스템을 모방하여 이미지의 구조적 유사도를 측정합니다.
    - Luminance (밝기)
    - Contrast (대비)
    - Structure (구조)
    """

    def __init__(self, window_size: int = 11, channel: int = 3):
        super().__init__()
        self.window_size = window_size
        self.channel = channel
        self.window = self._create_window(window_size, channel)

    def _create_window(self, window_size: int, channel: int) -> torch.Tensor:
        """가우시안 윈도우 생성"""
        def gaussian(window_size: int, sigma: float) -> torch.Tensor:
            gauss = torch.Tensor([
                torch.exp(torch.tensor(-(x - window_size // 2) ** 2 / float(2 * sigma ** 2)))
                for x in range(window_size)
            ])
            return gauss / gauss.sum()

        _1D_window = gaussian(window_size, 1.5).unsqueeze(1)
        _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
        window = _2D_window.expand(channel, 1, window_size, window_size).contiguous()
        return window

    def forward(self, img1: torch.Tensor, img2: torch.Tensor) -> torch.Tensor:
        """
        SSIM Loss 계산

        Args:
            img1: 원본 이미지 [B, C, H, W]
            img2: 복원 이미지 [B, C, H, W]

        Returns:
            1 - SSIM (Loss로 사용하기 위해 1에서 뺌)
        """
        channel = img1.size(1)

        if self.window.device != img1.device:
            self.window = self.window.to(img1.device)

        if channel != self.channel:
            self.window = self._create_window(self.window_size, channel).to(img1.device)
            self.channel = channel

        mu1 = F.conv2d(img1, self.window, padding=self.window_size // 2, groups=channel)
        mu2 = F.conv2d(img2, self.window, padding=self.window_size // 2, groups=channel)

        mu1_sq = mu1.pow(2)
        mu2_sq = mu2.pow(2)
        mu1_mu2 = mu1 * mu2

        sigma1_sq = F.conv2d(img1 * img1, self.window, padding=self.window_size // 2, groups=channel) - mu1_sq
        sigma2_sq = F.conv2d(img2 * img2, self.window, padding=self.window_size // 2, groups=channel) - mu2_sq
        sigma12 = F.conv2d(img1 * img2, self.window, padding=self.window_size // 2, groups=channel) - mu1_mu2

        C1 = 0.01 ** 2
        C2 = 0.03 ** 2

        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

        return 1 - ssim_map.mean()


class CombinedLoss(nn.Module):
    """
    MSE + SSIM Combined Loss

    MSE: 픽셀 레벨의 차이를 측정
    SSIM: 구조적 유사도를 측정
    """

    def __init__(self, alpha: float = 0.5):
        """
        Args:
            alpha: MSE와 SSIM의 비율 (0.5 = 동일 비중)
                   Loss = alpha * MSE + (1 - alpha) * SSIM_Loss
        """
        super().__init__()
        self.alpha = alpha
        self.mse = nn.MSELoss()
        self.ssim = SSIMLoss()

    def forward(self, output: torch.Tensor, target: torch.Tensor) -> Tuple[torch.Tensor, dict]:
        """
        Combined Loss 계산

        Returns:
            total_loss: 총 손실
            loss_dict: 개별 손실값 딕셔너리
        """
        mse_loss = self.mse(output, target)
        ssim_loss = self.ssim(output, target)
        total_loss = self.alpha * mse_loss + (1 - self.alpha) * ssim_loss

        return total_loss, {
            "mse": mse_loss.item(),
            "ssim": ssim_loss.item(),
            "total": total_loss.item()
        }


class Encoder(nn.Module):
    """
    Convolutional Encoder

    이미지를 점진적으로 압축하여 잠재 공간(Latent Space)으로 변환
    256x256x3 -> 16x16x256 (Latent)
    """

    def __init__(self, in_channels: int = 3, latent_dim: int = 256):
        super().__init__()

        # 256x256 -> 128x128
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(0.2, inplace=True)
        )

        # 128x128 -> 64x64
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2, inplace=True)
        )

        # 64x64 -> 32x32
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True)
        )

        # 32x32 -> 16x16
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, latent_dim, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(latent_dim),
            nn.LeakyReLU(0.2, inplace=True)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        return x


class Decoder(nn.Module):
    """
    Convolutional Decoder

    잠재 공간에서 이미지를 복원
    16x16x256 -> 256x256x3
    """

    def __init__(self, out_channels: int = 3, latent_dim: int = 256):
        super().__init__()

        # 16x16 -> 32x32
        self.deconv1 = nn.Sequential(
            nn.ConvTranspose2d(latent_dim, 128, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True)
        )

        # 32x32 -> 64x64
        self.deconv2 = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )

        # 64x64 -> 128x128
        self.deconv3 = nn.Sequential(
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True)
        )

        # 128x128 -> 256x256
        self.deconv4 = nn.Sequential(
            nn.ConvTranspose2d(32, out_channels, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()  # 0-1 범위로 출력
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.deconv1(x)
        x = self.deconv2(x)
        x = self.deconv3(x)
        x = self.deconv4(x)
        return x


class SSIMAnomalyAutoencoder(nn.Module):
    """
    SSIM Anomaly Detection Autoencoder

    선박 도장 결함 탐지를 위한 메인 모델

    동작 원리:
    1. 정상 이미지만으로 학습
    2. 학습 후, 정상 이미지는 잘 복원되고 비정상 이미지는 복원이 잘 안됨
    3. 복원 오차(Anomaly Score)를 계산하여 이상 여부 판단

    Usage:
        model = SSIMAnomalyAutoencoder()

        # 학습
        reconstructed = model(input_image)
        loss = criterion(reconstructed, input_image)

        # 추론
        anomaly_score, anomaly_map = model.compute_anomaly_score(test_image)
        is_anomaly = anomaly_score > threshold
    """

    def __init__(
        self,
        in_channels: int = 3,
        latent_dim: int = 256,
        input_size: int = 256
    ):
        """
        Args:
            in_channels: 입력 채널 수 (RGB=3)
            latent_dim: 잠재 공간 차원
            input_size: 입력 이미지 크기 (정사각형 가정)
        """
        super().__init__()

        self.in_channels = in_channels
        self.latent_dim = latent_dim
        self.input_size = input_size

        self.encoder = Encoder(in_channels, latent_dim)
        self.decoder = Decoder(in_channels, latent_dim)

        # 이상 점수 계산용
        self.ssim_loss = SSIMLoss()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        순전파: 입력 이미지 복원

        Args:
            x: 입력 이미지 [B, C, H, W]

        Returns:
            복원된 이미지 [B, C, H, W]
        """
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """잠재 공간으로 인코딩"""
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """잠재 공간에서 디코딩"""
        return self.decoder(z)

    @torch.no_grad()
    def compute_anomaly_score(
        self,
        x: torch.Tensor,
        return_map: bool = True
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        이상 점수 계산

        Args:
            x: 입력 이미지 [B, C, H, W]
            return_map: 이상 맵 반환 여부

        Returns:
            anomaly_score: 이미지별 이상 점수 [B]
            anomaly_map: 픽셀별 이상 맵 [B, 1, H, W] (return_map=True일 때)
        """
        self.eval()

        # 복원
        reconstructed = self.forward(x)

        # 픽셀별 차이 (이상 맵)
        diff = (x - reconstructed).pow(2).mean(dim=1, keepdim=True)  # [B, 1, H, W]

        # 이미지별 평균 점수
        anomaly_score = diff.view(diff.size(0), -1).mean(dim=1)  # [B]

        if return_map:
            # 0-1 범위로 정규화
            anomaly_map = diff
            for i in range(diff.size(0)):
                min_val = anomaly_map[i].min()
                max_val = anomaly_map[i].max()
                if max_val > min_val:
                    anomaly_map[i] = (anomaly_map[i] - min_val) / (max_val - min_val)
            return anomaly_score, anomaly_map

        return anomaly_score, None

    def get_reconstruction_with_diff(
        self,
        x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        복원 이미지와 차이 맵을 함께 반환 (시각화용)

        Returns:
            original: 원본 이미지
            reconstructed: 복원 이미지
            diff_map: 차이 맵
        """
        with torch.no_grad():
            reconstructed = self.forward(x)
            diff_map = torch.abs(x - reconstructed).mean(dim=1, keepdim=True)
            diff_map = diff_map.repeat(1, 3, 1, 1)  # 시각화를 위해 3채널로

        return x, reconstructed, diff_map


class LightweightAutoencoder(SSIMAnomalyAutoencoder):
    """
    경량화된 Autoencoder (Jetson Orin Nano 최적화)

    파라미터 수를 줄여서 추론 속도 향상
    """

    def __init__(
        self,
        in_channels: int = 3,
        latent_dim: int = 128,  # 더 작은 잠재 공간
        input_size: int = 256
    ):
        # 부모 클래스 초기화를 건너뛰고 직접 구현
        nn.Module.__init__(self)

        self.in_channels = in_channels
        self.latent_dim = latent_dim
        self.input_size = input_size

        # 경량 인코더
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 16, 4, 2, 1),
            nn.BatchNorm2d(16),
            nn.LeakyReLU(0.2),
            nn.Conv2d(16, 32, 4, 2, 1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(0.2),
            nn.Conv2d(32, 64, 4, 2, 1),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2),
            nn.Conv2d(64, latent_dim, 4, 2, 1),
            nn.BatchNorm2d(latent_dim),
            nn.LeakyReLU(0.2),
        )

        # 경량 디코더
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(latent_dim, 64, 4, 2, 1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 4, 2, 1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 16, 4, 2, 1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.ConvTranspose2d(16, in_channels, 4, 2, 1),
            nn.Sigmoid(),
        )

        self.ssim_loss = SSIMLoss()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


def count_parameters(model: nn.Module) -> int:
    """모델 파라미터 수 계산"""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    # 테스트
    print("=" * 50)
    print("SSIM Anomaly Autoencoder 테스트")
    print("=" * 50)

    # 모델 생성
    model = SSIMAnomalyAutoencoder(input_size=256)
    lightweight = LightweightAutoencoder(input_size=256)

    print(f"\n[모델 파라미터]")
    print(f"Standard: {count_parameters(model):,} parameters")
    print(f"Lightweight: {count_parameters(lightweight):,} parameters")

    # 테스트 입력
    dummy_input = torch.randn(2, 3, 256, 256)

    # 순전파 테스트
    output = model(dummy_input)
    print(f"\n[순전파 테스트]")
    print(f"Input shape: {dummy_input.shape}")
    print(f"Output shape: {output.shape}")

    # 이상 점수 계산 테스트
    score, anomaly_map = model.compute_anomaly_score(dummy_input)
    print(f"\n[이상 점수 계산]")
    print(f"Anomaly scores: {score}")
    print(f"Anomaly map shape: {anomaly_map.shape}")

    # Loss 테스트
    criterion = CombinedLoss(alpha=0.5)
    loss, loss_dict = criterion(output, dummy_input)
    print(f"\n[Loss 계산]")
    print(f"MSE: {loss_dict['mse']:.4f}")
    print(f"SSIM: {loss_dict['ssim']:.4f}")
    print(f"Total: {loss_dict['total']:.4f}")

    print("\n" + "=" * 50)
    print("테스트 완료!")
