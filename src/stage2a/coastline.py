from __future__ import annotations

from dataclasses import dataclass
from collections import deque

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class CoastlineResult:
    water_score: np.ndarray
    water_mask: np.ndarray
    coastline_mask: np.ndarray
    threshold: float


def segment_coastline_rgb(
    image: Image.Image,
    threshold: float | None = None,
    invert: bool = False,
    keep_border_water: bool = True,
) -> CoastlineResult:
    """Segment water from land in an RGB image and extract the coastline boundary."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    score = water_index_rgb(rgb)

    if threshold is None:
        threshold = otsu_threshold(score)

    water_mask = score >= threshold
    if invert:
        water_mask = ~water_mask

    if keep_border_water:
        water_mask = border_connected_component(water_mask)

    coastline_mask = mask_boundary(water_mask)
    return CoastlineResult(
        water_score=score,
        water_mask=water_mask,
        coastline_mask=coastline_mask,
        threshold=float(threshold),
    )


def water_index_rgb(rgb: np.ndarray) -> np.ndarray:
    """Compute a simple RGB water index for images without NIR information."""
    red = rgb[..., 0]
    green = rgb[..., 1]
    blue = rgb[..., 2]
    eps = 1e-6

    blue_red = (blue - red) / (blue + red + eps)
    blue_green = (blue - green) / (blue + green + eps)
    darkness = 1.0 - np.mean(rgb, axis=2)

    score = 0.55 * blue_red + 0.25 * blue_green + 0.20 * darkness
    return normalize01(score)


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Estimate a threshold with Otsu's method on normalized values."""
    clean_values = normalize01(values).reshape(-1)
    histogram, bin_edges = np.histogram(clean_values, bins=bins, range=(0.0, 1.0))

    probabilities = histogram.astype(np.float64)
    probabilities /= probabilities.sum()

    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    cumulative_prob = np.cumsum(probabilities)
    cumulative_mean = np.cumsum(probabilities * bin_centers)
    global_mean = cumulative_mean[-1]

    numerator = (global_mean * cumulative_prob - cumulative_mean) ** 2
    denominator = cumulative_prob * (1.0 - cumulative_prob)
    variance = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator > 0,
    )

    return float(bin_centers[int(np.argmax(variance))])


def mask_boundary(mask: np.ndarray) -> np.ndarray:
    """Return pixels where a binary mask touches a different neighbouring value."""
    mask = mask.astype(bool)
    boundary = np.zeros_like(mask, dtype=bool)

    boundary[1:, :] |= mask[1:, :] != mask[:-1, :]
    boundary[:-1, :] |= mask[:-1, :] != mask[1:, :]
    boundary[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    boundary[:, :-1] |= mask[:, :-1] != mask[:, 1:]

    return boundary


def border_connected_component(mask: np.ndarray) -> np.ndarray:
    """Keep the largest mask component connected to the image border."""
    mask = mask.astype(bool)
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    largest_component = np.zeros_like(mask, dtype=bool)
    largest_size = 0

    for x in range(width):
        component = _collect_component(mask, visited, 0, x)
        if component is not None and len(component) > largest_size:
            largest_component = _component_to_mask(component, mask.shape)
            largest_size = len(component)

        component = _collect_component(mask, visited, height - 1, x)
        if component is not None and len(component) > largest_size:
            largest_component = _component_to_mask(component, mask.shape)
            largest_size = len(component)

    for y in range(height):
        component = _collect_component(mask, visited, y, 0)
        if component is not None and len(component) > largest_size:
            largest_component = _component_to_mask(component, mask.shape)
            largest_size = len(component)

        component = _collect_component(mask, visited, y, width - 1)
        if component is not None and len(component) > largest_size:
            largest_component = _component_to_mask(component, mask.shape)
            largest_size = len(component)

    if largest_size == 0:
        return mask

    return largest_component


def _collect_component(
    mask: np.ndarray,
    visited: np.ndarray,
    start_y: int,
    start_x: int,
) -> list[tuple[int, int]] | None:
    if not mask[start_y, start_x] or visited[start_y, start_x]:
        return None

    height, width = mask.shape
    queue: deque[tuple[int, int]] = deque()
    component: list[tuple[int, int]] = []
    visited[start_y, start_x] = True
    queue.append((start_y, start_x))

    while queue:
        y, x = queue.popleft()
        component.append((y, x))
        for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= next_y < height and 0 <= next_x < width:
                _push_if_mask(mask, visited, queue, next_y, next_x)

    return component


def _component_to_mask(
    component: list[tuple[int, int]],
    shape: tuple[int, int],
) -> np.ndarray:
    output = np.zeros(shape, dtype=bool)
    for y, x in component:
        output[y, x] = True
    return output


def _push_if_mask(
    mask: np.ndarray,
    visited: np.ndarray,
    queue: deque[tuple[int, int]],
    y: int,
    x: int,
) -> None:
    if mask[y, x] and not visited[y, x]:
        visited[y, x] = True
        queue.append((y, x))


def save_water_score(score: np.ndarray, output_path: str) -> None:
    Image.fromarray(to_uint8(score)).save(output_path)


def save_binary_mask(mask: np.ndarray, output_path: str) -> None:
    Image.fromarray(mask.astype(np.uint8) * 255).save(output_path)


def save_coastline_overlay(
    image: Image.Image,
    coastline_mask: np.ndarray,
    output_path: str,
    color: tuple[int, int, int] = (255, 0, 0),
) -> None:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    rgb[coastline_mask] = color
    Image.fromarray(rgb).save(output_path)


def normalize01(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32)
    min_value = float(np.nanmin(values))
    max_value = float(np.nanmax(values))

    if max_value == min_value:
        return np.zeros_like(values, dtype=np.float32)

    return (values - min_value) / (max_value - min_value)


def to_uint8(values: np.ndarray) -> np.ndarray:
    return np.clip(normalize01(values) * 255, 0, 255).astype(np.uint8)
