from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    mode: str
    dtype: str
    shape: tuple[int, ...]
    min_value: float
    max_value: float


def list_image_paths(folder: Path) -> list[Path]:
    """Return supported image files inside a folder, sorted by name."""
    if not folder.exists():
        return []

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def load_image(path: Path) -> tuple[Image.Image, np.ndarray]:
    """Load an image with Pillow and return both PIL and NumPy versions."""
    image = Image.open(path)
    array = np.asarray(image)
    return image, array


def describe_image(path: Path) -> ImageInfo:
    image, array = load_image(path)
    return ImageInfo(
        path=path,
        width=image.width,
        height=image.height,
        mode=image.mode,
        dtype=str(array.dtype),
        shape=tuple(array.shape),
        min_value=float(np.nanmin(array)),
        max_value=float(np.nanmax(array)),
    )

