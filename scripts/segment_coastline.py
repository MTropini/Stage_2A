from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.coastline import (
    save_binary_mask,
    save_coastline_overlay,
    save_water_score,
    segment_coastline_rgb,
)
from stage2a.image_io import IMAGE_EXTENSIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Segment water/land and extract a first coastline from RGB images."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "raw",
        help="Folder containing coastal images.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "processed",
        help="Folder where masks and overlays are saved.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Optional water threshold between 0 and 1. If omitted, Otsu is used.",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert water/land if the automatic mask is reversed.",
    )
    parser.add_argument(
        "--keep-all-water",
        action="store_true",
        help="Keep every detected water area instead of only water connected to the image border.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_paths = _list_images(args.input_dir)

    if not image_paths:
        print(f"No supported coastline images found in: {args.input_dir}")
        print("Add .jpg, .png, .tif, .tiff, .bmp, or .webp files, then rerun this script.")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for image_path in image_paths:
        image = Image.open(image_path)
        result = segment_coastline_rgb(
            image,
            threshold=args.threshold,
            invert=args.invert,
            keep_border_water=not args.keep_all_water,
        )

        stem = image_path.stem
        score_path = args.output_dir / f"{stem}_water_score.png"
        water_path = args.output_dir / f"{stem}_water_mask.png"
        coast_path = args.output_dir / f"{stem}_coastline_mask.png"
        overlay_path = args.output_dir / f"{stem}_coastline_overlay.png"

        save_water_score(result.water_score, str(score_path))
        save_binary_mask(result.water_mask, str(water_path))
        save_binary_mask(result.coastline_mask, str(coast_path))
        save_coastline_overlay(image, result.coastline_mask, str(overlay_path))

        print(f"{image_path.name}: threshold={result.threshold:.3f}")
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
