#!/usr/bin/env python3
"""
Image Preprocessor for Ship Coating Defect Detection
Letterbox resize to preserve aspect ratio and defect geometry
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional


def letterbox_resize(image: np.ndarray,
                     target_size: Tuple[int, int] = (1024, 1024),
                     fill_value: Tuple[int, int, int] = (114, 114, 114)) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Letterbox resize: resize image while preserving aspect ratio with padding

    Args:
        image: Input image (H, W, C)
        target_size: Target size (width, height)
        fill_value: Padding color (R, G, B)

    Returns:
        resized_image: Letterboxed image
        scale: Resize scale factor
        pad: Padding (pad_w, pad_h)
    """
    target_w, target_h = target_size
    h, w = image.shape[:2]

    # Calculate scale to fit image within target size
    scale = min(target_w / w, target_h / h)

    # New size after scaling
    new_w = int(w * scale)
    new_h = int(h * scale)

    # Resize image
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Create canvas with padding
    canvas = np.full((target_h, target_w, 3), fill_value, dtype=np.uint8)

    # Calculate padding
    pad_w = (target_w - new_w) // 2
    pad_h = (target_h - new_h) // 2

    # Place resized image on canvas
    canvas[pad_h:pad_h+new_h, pad_w:pad_w+new_w] = resized

    return canvas, scale, (pad_w, pad_h)


class ImagePreprocessor:
    """
    Image Preprocessor for Ship Coating Defect Detection

    Features:
    - Letterbox resize (preserves aspect ratio)
    - Bbox and segmentation coordinate transformation
    - Normalization
    """

    def __init__(self,
                 target_size: Tuple[int, int] = (1024, 1024),
                 normalize: bool = True,
                 mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
                 std: Tuple[float, float, float] = (0.229, 0.224, 0.225)):
        """
        Args:
            target_size: Target image size (width, height)
            normalize: Whether to normalize image
            mean: Normalization mean (ImageNet default)
            std: Normalization std (ImageNet default)
        """
        self.target_size = target_size
        self.normalize = normalize
        self.mean = np.array(mean, dtype=np.float32)
        self.std = np.array(std, dtype=np.float32)

    def transform_bbox(self, bbox: List[float], scale: float, pad: Tuple[int, int]) -> List[float]:
        """
        Transform bounding box coordinates after letterbox resize

        Args:
            bbox: [x, y, w, h] in original image
            scale: Resize scale factor
            pad: Padding (pad_w, pad_h)

        Returns:
            transformed_bbox: [x, y, w, h] in resized image
        """
        x, y, w, h = bbox
        pad_w, pad_h = pad

        # Apply scale and padding
        new_x = x * scale + pad_w
        new_y = y * scale + pad_h
        new_w = w * scale
        new_h = h * scale

        return [new_x, new_y, new_w, new_h]

    def transform_segmentation(self, segmentation: List[float], scale: float, pad: Tuple[int, int]) -> List[float]:
        """
        Transform segmentation polygon coordinates after letterbox resize

        Args:
            segmentation: Flat list of [x1, y1, x2, y2, ...] in original image
            scale: Resize scale factor
            pad: Padding (pad_w, pad_h)

        Returns:
            transformed_segmentation: Flat list of transformed coordinates
        """
        pad_w, pad_h = pad

        # Convert to numpy array and reshape to (N, 2)
        points = np.array(segmentation).reshape(-1, 2)

        # Apply scale and padding
        points[:, 0] = points[:, 0] * scale + pad_w
        points[:, 1] = points[:, 1] * scale + pad_h

        # Flatten back to list
        return points.flatten().tolist()

    def preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Preprocess image with letterbox resize

        Args:
            image: Input image (H, W, C) in BGR or RGB

        Returns:
            processed_image: Preprocessed image
            metadata: Dict with scale, pad, original_size
        """
        original_h, original_w = image.shape[:2]

        # Letterbox resize
        resized_image, scale, pad = letterbox_resize(image, self.target_size)

        # Convert to RGB if needed
        if len(resized_image.shape) == 3 and resized_image.shape[2] == 3:
            # Assume input is BGR (from cv2.imread)
            rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = resized_image

        # Normalize
        if self.normalize:
            normalized = rgb_image.astype(np.float32) / 255.0
            normalized = (normalized - self.mean) / self.std
            processed_image = normalized
        else:
            processed_image = rgb_image.astype(np.float32) / 255.0

        # Metadata
        metadata = {
            'scale': scale,
            'pad': pad,
            'original_size': (original_w, original_h),
            'target_size': self.target_size
        }

        return processed_image, metadata

    def preprocess_annotation(self, annotation: Dict, metadata: Dict) -> Dict:
        """
        Preprocess annotation with coordinate transformation

        Args:
            annotation: Annotation dict with bbox and/or segmentation
            metadata: Metadata from preprocess_image

        Returns:
            transformed_annotation: Annotation with transformed coordinates
        """
        scale = metadata['scale']
        pad = metadata['pad']

        transformed = annotation.copy()

        # Transform bbox if present
        if 'bbox' in annotation and annotation['bbox']:
            transformed['bbox'] = self.transform_bbox(annotation['bbox'], scale, pad)

        # Transform segmentation if present
        if 'segmentation' in annotation and annotation['segmentation']:
            transformed['segmentation'] = self.transform_segmentation(
                annotation['segmentation'], scale, pad
            )

        return transformed

    def inverse_transform_bbox(self, bbox: List[float], metadata: Dict) -> List[float]:
        """
        Inverse transform bbox from preprocessed to original coordinates

        Args:
            bbox: [x, y, w, h] in preprocessed image
            metadata: Metadata from preprocess_image

        Returns:
            original_bbox: [x, y, w, h] in original image
        """
        scale = metadata['scale']
        pad_w, pad_h = metadata['pad']

        x, y, w, h = bbox

        # Remove padding and scale
        orig_x = (x - pad_w) / scale
        orig_y = (y - pad_h) / scale
        orig_w = w / scale
        orig_h = h / scale

        return [orig_x, orig_y, orig_w, orig_h]

    def denormalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Denormalize image for visualization

        Args:
            image: Normalized image (H, W, C)

        Returns:
            denormalized_image: Image in [0, 255] range
        """
        if self.normalize:
            denormalized = image * self.std + self.mean
        else:
            denormalized = image

        denormalized = np.clip(denormalized * 255.0, 0, 255).astype(np.uint8)
        return denormalized


def create_preprocessor(config: Optional[Dict] = None) -> ImagePreprocessor:
    """
    Factory function to create preprocessor with config

    Args:
        config: Configuration dict

    Returns:
        preprocessor: ImagePreprocessor instance
    """
    if config is None:
        config = {}

    return ImagePreprocessor(
        target_size=config.get('target_size', (1024, 1024)),
        normalize=config.get('normalize', True),
        mean=config.get('mean', (0.485, 0.456, 0.406)),
        std=config.get('std', (0.229, 0.224, 0.225))
    )
