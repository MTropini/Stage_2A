from __future__ import annotations

import argparse
import shutil
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


WORLD_FILE_SUFFIXES = (".pgw", ".wld", ".pngw", ".jgw", ".tfw")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Segment coastline orthophotos organized by year folders."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "orthophoto",
        help="Root folder containing one subfolder per year.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "processed_orthophoto",
        help="Root folder where yearly outputs are saved.",
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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute outputs even when they already exist.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_paths = _list_images(args.input_root)
    if not image_paths:
        print(f"No supported orthophotos found in: {args.input_root}")
        return 0

    for image_path in image_paths:
        year = image_path.parent.name
        output_dir = args.output_root / year
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = image_path.stem
        score_path = output_dir / f"{stem}_water_score.png"
        water_path = output_dir / f"{stem}_water_mask.png"
        coast_path = output_dir / f"{stem}_coastline_mask.png"
        overlay_path = output_dir / f"{stem}_coastline_overlay.png"

        if not args.overwrite and coast_path.exists() and overlay_path.exists():
            print(f"{year}/{image_path.name}: skipped existing outputs")
            continue

        image = Image.open(image_path)
        result = segment_coastline_rgb(
            image,
            threshold=args.threshold,
            invert=args.invert,
            keep_border_water=not args.keep_all_water,
        )

        save_water_score(result.water_score, str(score_path))
        save_binary_mask(result.water_mask, str(water_path))
        save_binary_mask(result.coastline_mask, str(coast_path))
        save_coastline_overlay(image, result.coastline_mask, str(overlay_path))
        _copy_world_file(image_path, coast_path)

        print(f"{year}/{image_path.name}: threshold={result.threshold:.3f}")
        print(f"  saved: {coast_path}")
        print(f"  saved: {overlay_path}")

    return 0


def _list_images(root: Path) -> list[Path]:
    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _copy_world_file(source_image: Path, target_image: Path) -> None:
    for suffix in WORLD_FILE_SUFFIXES:
        source_world = source_image.with_suffix(suffix)
        if source_world.exists():
            target_world = target_image.with_suffix(suffix)
            shutil.copyfile(source_world, target_world)
            return


if __name__ == "__main__":
    raise SystemExit(main())
