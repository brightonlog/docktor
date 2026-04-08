#!/usr/bin/env python3
"""
Data Augmentation for Ship Coating Defect Detection
Conservative augmentations to preserve small defects
"""

import numpy as np
import cv2
from typing import Dict, Tuple, Optional

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False


def get_train_augmentation(image_size: Tuple[int, int] = (1024, 1024),
                          use_albumentations: bool = True) -> Optional[object]:
    """
    Get training augmentation pipeline
    Conservative augmentations to preserve small defects

    Args:
        image_size: Target image size (width, height)
        use_albumentations: Whether to use albumentations library

    Returns:
        Augmentation pipeline or None
    """
    if not use_albumentations or not ALBUMENTATIONS_AVAILABLE:
        return None

    return A.Compose([
        # Geometric augmentations (conservative)
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        A.ShiftScaleRotate(
            shift_limit=0.05,
            scale_limit=0.1,
            rotate_limit=15,
            border_mode=cv2.BORDER_CONSTANT,
            value=0,
            p=0.5
        ),

        # Color augmentations
        A.OneOf([
            A.ColorJitter(
                brightness=0.2,
                contrast=0.2,
                saturation=0.2,
                hue=0.1,
                p=1.0
            ),
            A.HueSaturationValue(
                hue_shift_limit=10,
                sat_shift_limit=20,
                val_shift_limit=20,
                p=1.0
            ),
        ], p=0.5),

        # Blur and noise (light)
        A.OneOf([
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
            A.MotionBlur(blur_limit=3, p=1.0),
            A.GaussNoise(var_limit=(5.0, 15.0), p=1.0),
        ], p=0.3),

        # Lighting
        A.RandomBrightnessContrast(
            brightness_limit=0.2,
            contrast_limit=0.2,
            p=0.4
        ),

        # CLAHE for local contrast enhancement
        A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.3),

    ], bbox_params=A.BboxParams(
        format='coco',
        label_fields=['category_ids'],
        min_area=50,
        min_visibility=0.3
    ))


def get_val_augmentation(image_size: Tuple[int, int] = (1024, 1024),
                        use_albumentations: bool = True) -> Optional[object]:
    """
    Get validation augmentation pipeline (no augmentation, just formatting)

    Args:
        image_size: Target image size (width, height)
        use_albumentations: Whether to use albumentations library

    Returns:
        Augmentation pipeline or None
    """
    if not use_albumentations or not ALBUMENTATIONS_AVAILABLE:
        return None

    return A.Compose([
        # No augmentations for validation
    ], bbox_params=A.BboxParams(
        format='coco',
        label_fields=['category_ids']
    ))


class SimpleAugmentation:
    """
    Simple augmentation without external dependencies
    Fallback when albumentations is not available
    """

    def __init__(self, is_train: bool = True):
        self.is_train = is_train

    def horizontal_flip(self, image: np.ndarray, bboxes: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Horizontal flip"""
        h, w = image.shape[:2]
        image = cv2.flip(image, 1)

        if len(bboxes) > 0:
            bboxes[:, 0] = w - bboxes[:, 0] - bboxes[:, 2]

        return image, bboxes

    def vertical_flip(self, image: np.ndarray, bboxes: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Vertical flip"""
        h, w = image.shape[:2]
        image = cv2.flip(image, 0)

        if len(bboxes) > 0:
            bboxes[:, 1] = h - bboxes[:, 1] - bboxes[:, 3]

        return image, bboxes

    def adjust_brightness(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Adjust brightness"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    def adjust_contrast(self, image: np.ndarray, factor: float) -> np.ndarray:
        """Adjust contrast"""
        mean = image.mean()
        return np.clip((image - mean) * factor + mean, 0, 255).astype(np.uint8)

    def __call__(self, image: np.ndarray, bboxes: Optional[np.ndarray] = None) -> Dict:
        """
        Apply augmentation

        Args:
            image: Image (H, W, C)
            bboxes: Bounding boxes (N, 4) in [x, y, w, h] format

        Returns:
            Dict with 'image' and 'bboxes'
        """
        if bboxes is None:
            bboxes = np.array([])

        if not self.is_train:
            return {'image': image, 'bboxes': bboxes}

        # Random horizontal flip
        if np.random.rand() < 0.5:
            image, bboxes = self.horizontal_flip(image, bboxes)

        # Random vertical flip
        if np.random.rand() < 0.5:
            image, bboxes = self.vertical_flip(image, bboxes)

        # Random brightness
        if np.random.rand() < 0.3:
            factor = np.random.uniform(0.8, 1.2)
            image = self.adjust_brightness(image, factor)

        # Random contrast
        if np.random.rand() < 0.3:
            factor = np.random.uniform(0.8, 1.2)
            image = self.adjust_contrast(image, factor)

        return {'image': image, 'bboxes': bboxes}
