from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from stage2a.features import extract_image_features
from stage2a.image_io import IMAGE_EXTENSIONS


LABELS = {
    "non_archeologique": 0,
    "archeologique": 1,
}


@dataclass(frozen=True)
class ClassificationDataset:
    features: np.ndarray
    labels: np.ndarray
    paths: list[Path]


def load_classification_dataset(dataset_dir: Path) -> ClassificationDataset:
    """Load labelled image folders and extract one feature vector per image."""
    features = []
    labels = []
    paths = []

    for class_name, label in LABELS.items():
        class_dir = dataset_dir / class_name
        image_paths = _list_images(class_dir)

        for image_path in image_paths:
            features.append(extract_image_features(image_path))
            labels.append(label)
            paths.append(image_path)

    if not features:
        return ClassificationDataset(
            features=np.empty((0, 0), dtype=np.float32),
            labels=np.empty((0,), dtype=np.int64),
            paths=[],
        )

    return ClassificationDataset(
        features=np.vstack(features),
        labels=np.asarray(labels, dtype=np.int64),
        paths=paths,
    )


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

