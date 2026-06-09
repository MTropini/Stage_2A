from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def save_inspection_figure(
    original: np.ndarray,
    grayscale: np.ndarray,
    contrast: np.ndarray,
    mask: np.ndarray,
    output_path: Path,
) -> None:
    """Save a four-panel figure to inspect basic preprocessing steps."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    panels = [
        ("Original", _to_pil_rgb(original)),
        ("Grayscale", _to_pil_gray(grayscale)),
        ("Contrast", _to_pil_gray(contrast)),
        ("Mask", _to_pil_gray(mask.astype(np.uint8) * 255)),
    ]

    panel_width = 320
    title_height = 28
    padding = 12
    panel_height = panel_width + title_height

    canvas = Image.new(
        "RGB",
        (len(panels) * panel_width + (len(panels) + 1) * padding, panel_height + 2 * padding),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    for index, (title, image) in enumerate(panels):
        x = padding + index * (panel_width + padding)
        y = padding
        draw.text((x, y), title, fill="black", font=font)
        resized = _fit_square(image, panel_width)
        canvas.paste(resized, (x, y + title_height))

    canvas.save(output_path)


def _displayable_rgb(image: np.ndarray) -> np.ndarray:
    """Make common image arrays displayable with matplotlib."""
    if image.ndim == 2:
        return image

    if image.ndim == 3 and image.shape[2] >= 3:
        return image[..., :3]

    return np.squeeze(image)


def _to_pil_rgb(image: np.ndarray) -> Image.Image:
    image = _displayable_rgb(image)

    if image.ndim == 2:
        return _to_pil_gray(image).convert("RGB")

    if image.dtype != np.uint8:
        image = _scale_uint8(image)

    return Image.fromarray(image[..., :3]).convert("RGB")


def _to_pil_gray(image: np.ndarray) -> Image.Image:
    if image.dtype != np.uint8:
        image = _scale_uint8(image)

    return Image.fromarray(np.squeeze(image)).convert("L").convert("RGB")


def _scale_uint8(image: np.ndarray) -> np.ndarray:
    image = image.astype(np.float32)
    min_value = float(np.nanmin(image))
    max_value = float(np.nanmax(image))

    if max_value == min_value:
        return np.zeros_like(image, dtype=np.uint8)

    image = (image - min_value) / (max_value - min_value)
    return np.clip(image * 255, 0, 255).astype(np.uint8)


def _fit_square(image: Image.Image, size: int) -> Image.Image:
    image = image.copy()
    image.thumbnail((size, size), Image.Resampling.LANCZOS)

    square = Image.new("RGB", (size, size), "white")
    x = (size - image.width) // 2
    y = (size - image.height) // 2
    square.paste(image, (x, y))
    return square
