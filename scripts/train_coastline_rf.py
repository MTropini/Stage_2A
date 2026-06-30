from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.coastline_dataset import load_coastline_pixel_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a Random Forest to segment water/land pixels on coastal images."
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "training" / "images",
        help="Folder containing annotated coastal RGB images.",
    )
    parser.add_argument(
        "--mask-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "training" / "masks",
        help="Folder containing binary water masks with matching stems.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=PROJECT_ROOT / "models" / "random_forest_coastline.pkl",
        help="Output path for the trained model.",
    )
    parser.add_argument("--pixels-per-class", type=int, default=20000)
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
    dataset = load_coastline_pixel_dataset(
        image_dir=args.image_dir,
        mask_dir=args.mask_dir,
        pixels_per_class=args.pixels_per_class,
        random_state=args.random_state,
    )

    if len(dataset.labels) == 0:
        print("No annotated coastline image/mask pairs found.")
        print(f"Images: {args.image_dir}")
        print(f"Masks:  {args.mask_dir}")
        print("Use matching file stems, for example olbia_01.png in both folders.")
        return 0

    class_counts = {
        "terre": int((dataset.labels == 0).sum()),
        "eau": int((dataset.labels == 1).sum()),
    }
    print(f"Loaded {len(dataset.pairs)} pair(s), {len(dataset.labels)} sampled pixels.")
    print(f"Class counts: {class_counts}")

    if min(class_counts.values()) < 2:
        print("Add at least 2 sampled pixels per class before training/evaluation.")
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
    print(classification_report(y_test, predictions, target_names=["terre", "eau"]))

    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    with args.model_path.open("wb") as file:
        pickle.dump({"model": model, "labels": {"terre": 0, "eau": 1}}, file)

    print(f"Saved model: {args.model_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
