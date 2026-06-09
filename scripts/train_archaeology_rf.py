from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.classification_dataset import LABELS, load_classification_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a Random Forest to classify archaeological vs non-archaeological image patches."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "classification",
        help="Folder containing archeologique/ and non_archeologique/ subfolders.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=PROJECT_ROOT / "models" / "random_forest_archaeology.pkl",
        help="Output path for the trained model.",
    )
    parser.add_argument("--n-estimators", type=int, default=200)
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
    dataset = load_classification_dataset(args.dataset_dir)

    if len(dataset.labels) == 0:
        print(f"No training images found in: {args.dataset_dir}")
        print("Add images to:")
        print(f"- {args.dataset_dir / 'archeologique'}")
        print(f"- {args.dataset_dir / 'non_archeologique'}")
        return 0

    class_counts = {
        class_name: int((dataset.labels == label).sum())
        for class_name, label in LABELS.items()
    }
    print(f"Loaded {len(dataset.labels)} image(s): {class_counts}")

    if min(class_counts.values()) < 2:
        print("Add at least 2 images per class before training/evaluation.")
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

