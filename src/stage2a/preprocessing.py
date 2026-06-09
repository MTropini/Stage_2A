from __future__ import annotations

import numpy as np


def to_float01(image: np.ndarray) -> np.ndarray:
    """Normalize an image array to float values between 0 and 1."""
    image = image.astype(np.float32)
    min_value = float(np.nanmin(image))
    max_value = float(np.nanmax(image))

    if max_value == min_value:
        return np.zeros_like(image, dtype=np.float32)

    return (image - min_value) / (max_value - min_value)


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert RGB/RGBA or single-band data to grayscale."""
    if image.ndim == 2:
        return image

    if image.ndim == 3 and image.shape[2] >= 3:
        rgb = image[..., :3].astype(np.float32)
        return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]

    raise ValueError(f"Unsupported image shape for grayscale conversion: {image.shape}")


def percentile_contrast(image: np.ndarray, low: float = 2, high: float = 98) -> np.ndarray:
    """Improve contrast by clipping extreme percentiles, then normalizing."""
    image = image.astype(np.float32)
    low_value, high_value = np.percentile(image, [low, high])

    if high_value == low_value:
        return np.zeros_like(image, dtype=np.float32)

    clipped = np.clip(image, low_value, high_value)
    return (clipped - low_value) / (high_value - low_value)


def simple_threshold(image: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Create a binary mask from a normalized grayscale image."""
    return image >= threshold

