from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.classification_dataset import load_classification_dataset
from stage2a.multimodal_dataset import load_multimodal_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare RGB-only and RGB+LiDAR Random Forest baselines with stratified k-fold cross-validation."
    )
    parser.add_argument(
        "--rgb-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "classification",
    )
    parser.add_argument(
        "--lidar-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "classification_lidar",
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of stratified cross-validation folds.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import StratifiedKFold
    except ModuleNotFoundError:
        print("scikit-learn is required. Install it with:")
        print("python -m pip install -r requirements.txt")
        return 1

    args = parse_args()
    rgb_dataset = load_classification_dataset(args.rgb_dir)
    multimodal_dataset = load_multimodal_dataset(args.rgb_dir, args.lidar_dir)

    if len(rgb_dataset.labels) != len(multimodal_dataset.labels):
        print(
            "RGB and multimodal datasets do not contain the same number of samples. "
            "Check that every RGB image has a LiDAR pair."
        )
        print(f"RGB samples: {len(rgb_dataset.labels)}")
        print(f"Paired RGB/LiDAR samples: {len(multimodal_dataset.labels)}")
        return 1

    min_class_count = int(np.bincount(rgb_dataset.labels).min())
    if args.folds > min_class_count:
        print(
            f"Requested {args.folds} folds, but the smallest class has only "
            f"{min_class_count} samples. Using {min_class_count} folds instead."
        )
        args.folds = min_class_count

    splitter = StratifiedKFold(
        n_splits=args.folds,
        shuffle=True,
        random_state=42,
    )

    rgb_scores = []
    multimodal_scores = []

    for fold_index, (train_index, test_index) in enumerate(
        splitter.split(rgb_dataset.features, rgb_dataset.labels),
        start=1,
    ):
        rgb_scores.append(
            _fit_and_score(
                rgb_dataset.features,
                rgb_dataset.labels,
                train_index,
                test_index,
            )
        )
        print(
            f"Fold {fold_index} RGB only: "
            f"accuracy={rgb_scores[-1]['accuracy']:.3f}, "
            f"F1 archeologique={rgb_scores[-1]['f1']:.3f}"
        )

        multimodal_scores.append(
            _fit_and_score(
                multimodal_dataset.features,
                multimodal_dataset.labels,
                train_index,
                test_index,
            )
        )
        print(
            f"Fold {fold_index} RGB + LiDAR: "
            f"accuracy={multimodal_scores[-1]['accuracy']:.3f}, "
            f"F1 archeologique={multimodal_scores[-1]['f1']:.3f}"
        )

    print()
    _print_summary("RGB only", rgb_scores)
    _print_summary("RGB + LiDAR", multimodal_scores)
    return 0


def _fit_and_score(
    features: np.ndarray,
    labels: np.ndarray,
    train_index: np.ndarray,
    test_index: np.ndarray,
) -> dict[str, float]:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(features[train_index], labels[train_index])
    predictions = model.predict(features[test_index])

    return {
        "accuracy": accuracy_score(labels[test_index], predictions),
        "f1": f1_score(labels[test_index], predictions),
    }


def _print_summary(name: str, scores: list[dict[str, float]]) -> None:
    accuracy = np.asarray([score["accuracy"] for score in scores])
    f1 = np.asarray([score["f1"] for score in scores])

    print(
        f"{name}: "
        f"accuracy={accuracy.mean():.3f} +/- {accuracy.std():.3f}, "
        f"F1 archeologique={f1.mean():.3f} +/- {f1.std():.3f}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
