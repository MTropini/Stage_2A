from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create preview images with YOLO bounding boxes drawn on top."
    )
    parser.add_argument(
        "--yolo-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "yolo_sites",
        help="YOLO dataset root.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "yolo_sites" / "previews",
        help="Preview output directory.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=1200,
        help="Maximum preview width/height in pixels.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    total = 0
    for split in ["train", "val", "test"]:
        total += _preview_split(args.yolo_root, args.output_dir, split, args.max_size)
    print(f"Preview images written: {total}")
    print(f"Output directory: {args.output_dir}")
    return 0


def _preview_split(yolo_root: Path, output_dir: Path, split: str, max_size: int) -> int:
    image_dir = yolo_root / "images" / split
    label_dir = yolo_root / "labels" / split
    preview_dir = output_dir / split
    preview_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for image_path in sorted(image_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        label_path = label_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            print(f"Missing label for {image_path}")
            continue
        preview = _draw_preview(image_path, label_path, max_size)
        preview.save(preview_dir / f"{image_path.stem}_preview.jpg", quality=92)
        count += 1

    print(f"- {split}: {count} previews")
    return count


def _draw_preview(image_path: Path, label_path: Path, max_size: int) -> Image.Image:
    with Image.open(image_path).convert("RGB") as image:
        original_width, original_height = image.size
        preview = ImageOps.contain(image, (max_size, max_size)).copy()

    scale_x = preview.width / original_width
    scale_y = preview.height / original_height
    draw = ImageDraw.Draw(preview)
    font = _font()

    labels = _read_labels(label_path)
    for class_index, x_center, y_center, width, height in labels:
        x1 = (x_center - width / 2) * original_width * scale_x
        y1 = (y_center - height / 2) * original_height * scale_y
        x2 = (x_center + width / 2) * original_width * scale_x
        y2 = (y_center + height / 2) * original_height * scale_y

        color = (255, 0, 0)
        draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
        label = f"class {class_index}"
        text_box = draw.textbbox((x1, y1), label, font=font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        draw.rectangle((x1, max(0, y1 - text_height - 8), x1 + text_width + 8, y1), fill=color)
        draw.text((x1 + 4, max(0, y1 - text_height - 6)), label, fill=(255, 255, 255), font=font)

    return preview


def _read_labels(label_path: Path) -> list[tuple[int, float, float, float, float]]:
    labels = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid YOLO label line in {label_path}: {line}")
        labels.append(
            (
                int(parts[0]),
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
                float(parts[4]),
            )
        )
    return labels


def _font():
    try:
        return ImageFont.truetype("arial.ttf", 22)
    except OSError:
        return ImageFont.load_default()


if __name__ == "__main__":
    raise SystemExit(main())
