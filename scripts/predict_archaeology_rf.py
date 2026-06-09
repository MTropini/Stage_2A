from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.features import extract_image_features
from stage2a.image_io import IMAGE_EXTENSIONS


CLASS_NAMES = {
    0: "non_archeologique",
    1: "archeologique",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict whether image patches are archaeological or not."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Image file or folder to classify.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=PROJECT_ROOT / "models" / "random_forest_archaeology.pkl",
        help="Path to the trained model.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.model_path.exists():
        print(f"Model not found: {args.model_path}")
        print("Train it first with: python scripts/train_archaeology_rf.py")
        return 1

    with args.model_path.open("rb") as file:
        model = pickle.load(file)

    image_paths = _resolve_image_paths(args.input)
    if not image_paths:
        print(f"No supported images found in: {args.input}")
        return 0

    for image_path in image_paths:
        features = extract_image_features(image_path).reshape(1, -1)
        prediction = int(model.predict(features)[0])
        probabilities = model.predict_proba(features)[0]

        print(
            f"{image_path.name}: {CLASS_NAMES[prediction]} "
            f"(P archeologique={probabilities[1]:.3f}, "
            f"P non_archeologique={probabilities[0]:.3f})"
        )

    return 0


def _resolve_image_paths(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
        return [path]

    if path.is_dir():
        return sorted(
            child
            for child in path.iterdir()
            if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS
        )

    return []


if __name__ == "__main__":
    raise SystemExit(main())

