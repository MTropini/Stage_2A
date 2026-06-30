from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.coastline import (
    predict_coastline_rf,
    save_binary_mask,
    save_coastline_overlay,
    save_water_score,
)
from stage2a.image_io import IMAGE_EXTENSIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict water/land masks and coastline overlays with a trained RF model."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "raw",
        help="Folder containing coastal images to segment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "processed_rf",
        help="Folder where RF masks and overlays are saved.",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=PROJECT_ROOT / "models" / "random_forest_coastline.pkl",
        help="Path to a model created by train_coastline_rf.py.",
    )
    parser.add_argument(
        "--keep-all-water",
        action="store_true",
        help="Keep every detected water area instead of only water connected to the image border.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.model_path.exists():
        print(f"Missing model: {args.model_path}")
        print("Train it first with: python scripts/train_coastline_rf.py")
        return 0

    image_paths = _list_images(args.input_dir)
    if not image_paths:
        print(f"No supported coastline images found in: {args.input_dir}")
        return 0

    with args.model_path.open("rb") as file:
        model_package = pickle.load(file)
    model = model_package["model"] if isinstance(model_package, dict) else model_package

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for image_path in image_paths:
        image = Image.open(image_path)
        result = predict_coastline_rf(
            image,
            model=model,
            keep_border_water=not args.keep_all_water,
        )

        stem = image_path.stem
        score_path = args.output_dir / f"{stem}_rf_water_score.png"
        water_path = args.output_dir / f"{stem}_rf_water_mask.png"
        coast_path = args.output_dir / f"{stem}_rf_coastline_mask.png"
        overlay_path = args.output_dir / f"{stem}_rf_coastline_overlay.png"

        save_water_score(result.water_score, str(score_path))
        save_binary_mask(result.water_mask, str(water_path))
        save_binary_mask(result.coastline_mask, str(coast_path))
        save_coastline_overlay(image, result.coastline_mask, str(overlay_path))

        print(f"{image_path.name}: saved RF coastline outputs")
        print(f"  saved: {score_path}")
        print(f"  saved: {water_path}")
        print(f"  saved: {coast_path}")
        print(f"  saved: {overlay_path}")

    return 0


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


if __name__ == "__main__":
    raise SystemExit(main())
