from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from stage2a.coastline import create_coastline_pixel_features
from stage2a.image_io import IMAGE_EXTENSIONS


@dataclass(frozen=True)
class CoastlinePixelDataset:
    features: np.ndarray
    labels: np.ndarray
    pairs: list[tuple[Path, Path]]


def load_coastline_pixel_dataset(
    image_dir: Path,
    mask_dir: Path,
    pixels_per_class: int = 20000,
    random_state: int = 42,
) -> CoastlinePixelDataset:
    """Load RGB coastal images and binary water masks for pixel classification."""
    pairs = find_image_mask_pairs(image_dir, mask_dir)
    rng = np.random.default_rng(random_state)

    all_features: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []

    for image_path, mask_path in pairs:
        image = Image.open(image_path).convert("RGB")
        mask_image = Image.open(mask_path).convert("L")

        if image.size != mask_image.size:
            raise ValueError(
                f"Image/mask size mismatch for {image_path.name}: "
                f"{image.size} vs {mask_image.size}"
            )

        features = create_coastline_pixel_features(image)
        labels = (np.asarray(mask_image, dtype=np.uint8).reshape(-1) >= 128).astype(
            np.uint8
        )
        selected_indices = _sample_balanced_indices(labels, pixels_per_class, rng)

        all_features.append(features[selected_indices])
        all_labels.append(labels[selected_indices])

    if not all_features:
        return CoastlinePixelDataset(
            features=np.empty((0, 0), dtype=np.float32),
            labels=np.empty((0,), dtype=np.uint8),
            pairs=[],
        )

    return CoastlinePixelDataset(
        features=np.vstack(all_features).astype(np.float32),
        labels=np.concatenate(all_labels).astype(np.uint8),
        pairs=pairs,
    )


def find_image_mask_pairs(image_dir: Path, mask_dir: Path) -> list[tuple[Path, Path]]:
    if not image_dir.exists() or not mask_dir.exists():
        return []

    mask_by_stem = {
        path.stem: path
        for path in mask_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    }

    pairs: list[tuple[Path, Path]] = []
    for image_path in sorted(image_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        mask_path = mask_by_stem.get(image_path.stem)
        if mask_path is not None:
            pairs.append((image_path, mask_path))

    return pairs


def _sample_balanced_indices(
    labels: np.ndarray,
    pixels_per_class: int,
    rng: np.random.Generator,
) -> np.ndarray:
    selected: list[np.ndarray] = []

    for class_value in (0, 1):
        class_indices = np.flatnonzero(labels == class_value)
        if len(class_indices) == 0:
            continue

        sample_size = min(pixels_per_class, len(class_indices))
        selected.append(rng.choice(class_indices, size=sample_size, replace=False))

    if not selected:
        return np.empty((0,), dtype=np.int64)

    indices = np.concatenate(selected)
    rng.shuffle(indices)
    return indices
