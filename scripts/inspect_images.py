from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.image_io import describe_image, list_image_paths, load_image
from stage2a.preprocessing import percentile_contrast, simple_threshold, to_float01, to_grayscale
from stage2a.visualization import save_inspection_figure


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and preprocess images stored in data/raw."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Folder containing input images.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Folder where inspection figures are saved.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold applied after grayscale contrast normalization.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_paths = list_image_paths(args.input_dir)

    if not image_paths:
        print(f"No supported images found in: {args.input_dir}")
        print("Add .jpg, .png, .tif, .tiff, .bmp, or .webp files, then rerun this script.")
        return 0

    print(f"Found {len(image_paths)} image(s) in {args.input_dir}")

    for image_path in image_paths:
        info = describe_image(image_path)
        print(
            f"- {info.path.name}: {info.width}x{info.height}, "
            f"mode={info.mode}, shape={info.shape}, dtype={info.dtype}, "
            f"range=[{info.min_value:.3f}, {info.max_value:.3f}]"
        )

        _, image = load_image(image_path)
        grayscale = to_grayscale(image)
        contrast = percentile_contrast(to_float01(grayscale))
        mask = simple_threshold(contrast, threshold=args.threshold)

        output_path = args.output_dir / f"{image_path.stem}_inspection.png"
        save_inspection_figure(
            original=image,
            grayscale=grayscale,
            contrast=contrast,
            mask=mask,
            output_path=output_path,
        )
        print(f"  saved: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

