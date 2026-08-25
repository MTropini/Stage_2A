from __future__ import annotations

import argparse
import csv
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_PATTERN = re.compile(r"^(site\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a YOLO dataset by site to avoid train/val/test leakage."
    )
    parser.add_argument(
        "--yolo-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "yolo_sites",
        help="YOLO dataset root created by convert_masks_to_yolo.py.",
    )
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--class-name",
        default="site_archeologique",
        help="YOLO class name for data.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _validate_ratios(args.train_ratio, args.val_ratio, args.test_ratio)

    manifest_path = args.yolo_root / "yolo_manifest.csv"
    rows = _read_rows(manifest_path)
    if not rows:
        print(f"No rows found in: {manifest_path}")
        return 1

    rows_by_site = _group_by_site(rows)
    split_by_site = _split_sites(
        sorted(rows_by_site),
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        random_state=args.random_state,
    )

    _prepare_split_dirs(args.yolo_root)
    split_rows = []
    for site_id, split_name in split_by_site.items():
        for row in rows_by_site[site_id]:
            output_row = _copy_pair(row, split_name, args.yolo_root)
            output_row["site_id"] = site_id
            output_row["split"] = split_name
            split_rows.append(output_row)

    split_manifest = args.yolo_root / "yolo_split_manifest.csv"
    _write_split_manifest(split_rows, split_manifest)
    _write_data_yaml(args.yolo_root / "data.yaml", args.class_name)
    _print_summary(split_rows, split_by_site, args.yolo_root)
    return 0


def _validate_ratios(train_ratio: float, val_ratio: float, test_ratio: float) -> None:
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Ratios must sum to 1.0, got {total}")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _group_by_site(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    rows_by_site: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        site_id = _site_id(row["image_id"])
        rows_by_site[site_id].append(row)
    return dict(rows_by_site)


def _site_id(image_id: str) -> str:
    match = SITE_PATTERN.match(image_id)
    return match.group(1) if match else "unknown"


def _split_sites(
    site_ids: list[str],
    train_ratio: float,
    val_ratio: float,
    random_state: int,
) -> dict[str, str]:
    shuffled = list(site_ids)
    random.Random(random_state).shuffle(shuffled)
    site_count = len(shuffled)
    train_count = max(1, round(site_count * train_ratio))
    val_count = max(1, round(site_count * val_ratio))

    if train_count + val_count >= site_count:
        train_count = max(1, site_count - 2)
        val_count = 1

    train_sites = set(shuffled[:train_count])
    val_sites = set(shuffled[train_count : train_count + val_count])
    test_sites = set(shuffled[train_count + val_count :])

    return {
        site_id: (
            "train"
            if site_id in train_sites
            else "val"
            if site_id in val_sites
            else "test"
        )
        for site_id in site_ids
        if site_id in train_sites or site_id in val_sites or site_id in test_sites
    }


def _prepare_split_dirs(yolo_root: Path) -> None:
    for split_name in ["train", "val", "test"]:
        for kind in ["images", "labels"]:
            split_dir = yolo_root / kind / split_name
            if split_dir.exists():
                for path in split_dir.iterdir():
                    if path.is_file():
                        path.unlink()
            split_dir.mkdir(parents=True, exist_ok=True)


def _copy_pair(row: dict[str, str], split_name: str, yolo_root: Path) -> dict[str, str]:
    source_image = Path(row["output_image"])
    source_label = Path(row["output_label"])
    target_image = yolo_root / "images" / split_name / source_image.name
    target_label = yolo_root / "labels" / split_name / source_label.name
    shutil.copy2(source_image, target_image)
    shutil.copy2(source_label, target_label)

    return {
        **row,
        "split_image": str(target_image),
        "split_label": str(target_label),
    }


def _write_split_manifest(rows: list[dict[str, str]], output_path: Path) -> None:
    fieldnames = [
        "split",
        "site_id",
        "output_id",
        "source",
        "image_id",
        "patch_type",
        "image_path",
        "output_image",
        "output_label",
        "split_image",
        "split_label",
        "bbox_area_ratio",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_data_yaml(output_path: Path, class_name: str) -> None:
    dataset_root = output_path.parent.resolve().as_posix()
    output_path.write_text(
        "\n".join(
            [
                f"path: {dataset_root}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "",
                "names:",
                f"  0: {class_name}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _print_summary(
    rows: list[dict[str, str]],
    split_by_site: dict[str, str],
    yolo_root: Path,
) -> None:
    print("YOLO split by site complete.")
    for split_name in ["train", "val", "test"]:
        split_rows = [row for row in rows if row["split"] == split_name]
        split_sites = sorted(
            site_id for site_id, split in split_by_site.items() if split == split_name
        )
        print(f"- {split_name}: {len(split_rows)} images, {len(split_sites)} sites")
        print(f"  sites: {', '.join(split_sites)}")
    print(f"Split manifest: {yolo_root / 'yolo_split_manifest.csv'}")
    print(f"Data YAML: {yolo_root / 'data.yaml'}")


if __name__ == "__main__":
    raise SystemExit(main())
