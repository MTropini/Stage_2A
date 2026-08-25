from __future__ import annotations

import argparse
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a YOLO detector for archaeological site bounding boxes."
    )
    parser.add_argument(
        "--data-yaml",
        type=Path,
        default=PROJECT_ROOT / "data" / "yolo_sites" / "data.yaml",
        help="YOLO data.yaml file.",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.yaml",
        help="Initial YOLO model. Use yolov8n.yaml for offline smoke tests or yolov8n.pt for pretrained training.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=80,
        help="Training epochs. Keep modest while the dataset is small.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=640,
        help="Training image size.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Batch size. Use 2 or 4 on CPU/small GPU.",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=20,
        help="Early stopping patience.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Training device, e.g. cpu, 0, or cuda:0.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=PROJECT_ROOT / "models" / "yolo_sites",
        help="Directory where YOLO run outputs are saved.",
    )
    parser.add_argument(
        "--name",
        default="yolov8n_rgb_sites",
        help="YOLO run name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate dataset paths and print the training command summary.",
    )
    parser.add_argument(
        "--pretrained",
        action="store_true",
        help="Use pretrained weights when supported by the selected model.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_root = args.data_yaml.parent
    _validate_dataset(dataset_root)
    _print_plan(args)

    if args.dry_run:
        print("Dry run complete. No training started.")
        return 0

    config_dir = args.project / "ultralytics_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
    os.environ.setdefault("MPLCONFIGDIR", str(args.project / "matplotlib_config"))

    try:
        from ultralytics import YOLO
    except ModuleNotFoundError:
        print("The ultralytics package is required for YOLO training.")
        print("Install it with:")
        print("python -m pip install ultralytics")
        return 1

    model = YOLO(args.model)
    results = model.train(
        data=str(args.data_yaml),
        epochs=args.epochs,
        imgsz=args.image_size,
        batch=args.batch_size,
        patience=args.patience,
        device=args.device,
        project=str(args.project),
        name=args.name,
        exist_ok=True,
        pretrained=args.pretrained,
        plots=True,
        seed=42,
    )
    print(results)
    print(f"Training output: {args.project / args.name}")
    return 0


def _validate_dataset(dataset_root: Path) -> None:
    missing = []
    for split in ["train", "val", "test"]:
        image_dir = dataset_root / "images" / split
        label_dir = dataset_root / "labels" / split
        if not image_dir.exists():
            missing.append(str(image_dir))
        if not label_dir.exists():
            missing.append(str(label_dir))

    if missing:
        raise FileNotFoundError("Missing YOLO directories:\n" + "\n".join(missing))

    for split in ["train", "val", "test"]:
        image_dir = dataset_root / "images" / split
        label_dir = dataset_root / "labels" / split
        image_stems = {path.stem for path in image_dir.iterdir() if path.is_file()}
        label_stems = {path.stem for path in label_dir.glob("*.txt")}
        missing_labels = sorted(image_stems - label_stems)
        missing_images = sorted(label_stems - image_stems)

        if missing_labels or missing_images:
            message = [f"Mismatch in split {split}."]
            if missing_labels:
                message.append(f"Images without labels: {missing_labels[:10]}")
            if missing_images:
                message.append(f"Labels without images: {missing_images[:10]}")
            raise ValueError("\n".join(message))

        if not image_stems:
            raise ValueError(f"No images found in split {split}: {image_dir}")


def _print_plan(args: argparse.Namespace) -> None:
    dataset_root = args.data_yaml.parent
    print("YOLO training plan")
    print(f"- data: {args.data_yaml}")
    print(f"- model: {args.model}")
    print(f"- epochs: {args.epochs}")
    print(f"- image_size: {args.image_size}")
    print(f"- batch_size: {args.batch_size}")
    print(f"- patience: {args.patience}")
    print(f"- device: {args.device}")
    for split in ["train", "val", "test"]:
        image_count = len(list((dataset_root / "images" / split).iterdir()))
        label_count = len(list((dataset_root / "labels" / split).glob("*.txt")))
        print(f"- {split}: {image_count} images, {label_count} labels")


if __name__ == "__main__":
    raise SystemExit(main())
