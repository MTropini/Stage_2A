from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def extract_image_features(path: Path, thumbnail_size: int = 16) -> np.ndarray:
    """Extract simple image-level features for classical ML baselines."""
    image = Image.open(path).convert("RGB")
    rgb = np.asarray(image, dtype=np.float32) / 255.0
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0

    color_features = _channel_statistics(rgb)
    gray_features = _array_statistics(gray)
    texture_features = _gradient_statistics(gray)
    thumbnail_features = _thumbnail(gray, thumbnail_size)

    return np.concatenate(
        [color_features, gray_features, texture_features, thumbnail_features]
    ).astype(np.float32)


def _channel_statistics(rgb: np.ndarray) -> np.ndarray:
    features = []
    for channel_index in range(3):
        features.extend(_array_statistics(rgb[..., channel_index]))
    return np.asarray(features, dtype=np.float32)


def _array_statistics(values: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            float(np.mean(values)),
            float(np.std(values)),
            float(np.min(values)),
            float(np.percentile(values, 10)),
            float(np.percentile(values, 25)),
            float(np.percentile(values, 50)),
            float(np.percentile(values, 75)),
            float(np.percentile(values, 90)),
            float(np.max(values)),
        ],
        dtype=np.float32,
    )


def _gradient_statistics(gray: np.ndarray) -> np.ndarray:
    gradient_y, gradient_x = np.gradient(gray)
    magnitude = np.sqrt(gradient_x**2 + gradient_y**2)
    return _array_statistics(magnitude)


def _thumbnail(gray: np.ndarray, thumbnail_size: int) -> np.ndarray:
    image = Image.fromarray(np.clip(gray * 255, 0, 255).astype(np.uint8))
    image = image.resize((thumbnail_size, thumbnail_size), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32).reshape(-1) / 255.0

