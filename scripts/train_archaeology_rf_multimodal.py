from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.classification_dataset import LABELS
from stage2a.multimodal_dataset import load_multimodal_dataset, report_missing_pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a Random Forest with paired orthophoto and LiDAR-derived patches."
    )
    parser.add_argument(
        "--rgb-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "classification",
        help="Folder containing RGB archeologique/ and non_archeologique/ patches.",
    )
    parser.add_argument(
        "--lidar-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "classification_lidar",
        help="Folder containing matching LiDAR-derived patches.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=PROJECT_ROOT / "models" / "random_forest_archaeology_multimodal.pkl",
        help="Output path for the trained multimodal model.",
    )
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split
    except ModuleNotFoundError:
        print("scikit-learn is required. Install it with:")
        print("python -m pip install -r requirements.txt")
        return 1

    args = parse_args()
    missing_pairs = report_missing_pairs(args.rgb_dir, args.lidar_dir)
    for message in missing_pairs:
        print(f"Warning: {message}")

    dataset = load_multimodal_dataset(args.rgb_dir, args.lidar_dir)
    if len(dataset.labels) == 0:
        print("No paired RGB/LiDAR training images found.")
        print("LiDAR files must use the same base names as RGB files.")
        print("Example:")
        print("  data/classification/archeologique/olbia_arch_1.png")
        print("  data/classification_lidar/archeologique/olbia_arch_1.png")
        return 0

    class_counts = {
        class_name: int((dataset.labels == label).sum())
        for class_name, label in LABELS.items()
    }
    print(f"Loaded {len(dataset.labels)} paired sample(s): {class_counts}")

    if min(class_counts.values()) < 2:
        print("Add at least 2 paired images per class before training/evaluation.")
        return 0

    x_train, x_test, y_train, y_test = train_test_split(
        dataset.features,
        dataset.labels,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=dataset.labels,
    )

    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        random_state=args.random_state,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    target_names = ["non_archeologique", "archeologique"]
    print(classification_report(y_test, predictions, target_names=target_names))

    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    with args.model_path.open("wb") as file:
        pickle.dump(model, file)

    print(f"Saved model: {args.model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

