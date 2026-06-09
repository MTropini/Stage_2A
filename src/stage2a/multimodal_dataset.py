from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from stage2a.classification_dataset import LABELS
from stage2a.features import extract_image_features
from stage2a.image_io import IMAGE_EXTENSIONS


@dataclass(frozen=True)
class MultimodalDataset:
    features: np.ndarray
    labels: np.ndarray
    rgb_paths: list[Path]
    lidar_paths: list[Path]


def load_multimodal_dataset(rgb_dir: Path, lidar_dir: Path) -> MultimodalDataset:
    """Load paired RGB and LiDAR-derived images using matching file stems."""
    features = []
    labels = []
    rgb_paths = []
    lidar_paths = []

    for class_name, label in LABELS.items():
        rgb_class_dir = rgb_dir / class_name
        lidar_class_dir = lidar_dir / class_name
        lidar_by_key = _images_by_pairing_key(lidar_class_dir)

        for rgb_path in _list_images(rgb_class_dir):
            lidar_path = lidar_by_key.get(_pairing_key(rgb_path.stem))
            if lidar_path is None:
                continue

            rgb_features = extract_image_features(rgb_path)
            lidar_features = extract_image_features(lidar_path)
            features.append(np.concatenate([rgb_features, lidar_features]))
            labels.append(label)
            rgb_paths.append(rgb_path)
            lidar_paths.append(lidar_path)

    if not features:
        return MultimodalDataset(
            features=np.empty((0, 0), dtype=np.float32),
            labels=np.empty((0,), dtype=np.int64),
            rgb_paths=[],
            lidar_paths=[],
        )

    return MultimodalDataset(
        features=np.vstack(features).astype(np.float32),
        labels=np.asarray(labels, dtype=np.int64),
        rgb_paths=rgb_paths,
        lidar_paths=lidar_paths,
    )


def report_missing_pairs(rgb_dir: Path, lidar_dir: Path) -> list[str]:
    """Return human-readable messages for RGB images without LiDAR pairs."""
    messages = []

    for class_name in LABELS:
        rgb_stems = set(_images_by_pairing_key(rgb_dir / class_name))
        lidar_stems = set(_images_by_pairing_key(lidar_dir / class_name))

        for stem in sorted(rgb_stems - lidar_stems):
            messages.append(f"Missing LiDAR pair for {class_name}/{stem}")

    return messages


def _images_by_stem(folder: Path) -> dict[str, Path]:
    return {path.stem: path for path in _list_images(folder)}


def _images_by_pairing_key(folder: Path) -> dict[str, Path]:
    return {_pairing_key(path.stem): path for path in _list_images(folder)}


def _pairing_key(stem: str) -> str:
    """Normalize stems so olbia_arch_1 and olbia_arch_lidar_1 can be paired."""
    return stem.replace("_lidar_", "_")


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
