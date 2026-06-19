from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.image_io import IMAGE_EXTENSIONS


SITE_PATTERN = re.compile(r"^(site\d+)")


@dataclass(frozen=True)
class SampleAudit:
    patch_id: str
    site_id: str
    patch_type: str
    label: str
    rgb_path: Path
    lidar_path: Path | None
    rgb_size: tuple[int, int]
    lidar_size: tuple[int, int] | None
    has_rgb_world_file: bool
    has_lidar_world_file: bool
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit QGIS RGB/LiDAR exports before training models."
    )
    parser.add_argument(
        "--rgb-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports_qgis" / "rgb",
        help="Folder containing RGB patches exported from QGIS.",
    )
    parser.add_argument(
        "--lidar-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports_qgis" / "lidar",
        help="Folder containing LiDAR patches exported from QGIS.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports_qgis" / "dataset_audit.csv",
        help="CSV report written by the audit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rgb_paths = _list_images(args.rgb_dir)
    lidar_by_key = {_pairing_key(path.stem): path for path in _list_images(args.lidar_dir)}

    if not rgb_paths:
        print(f"No RGB images found in: {args.rgb_dir}")
        return 1

    audits = []
    for rgb_path in rgb_paths:
        patch_id = rgb_path.stem
        pair_key = _pairing_key(patch_id)
        lidar_path = lidar_by_key.get(pair_key)
        rgb_size = _image_size(rgb_path)
        lidar_size = _image_size(lidar_path) if lidar_path is not None else None

        audits.append(
            SampleAudit(
                patch_id=patch_id,
                site_id=_site_id(patch_id),
                patch_type=_patch_type(patch_id),
                label=_label_from_patch_id(patch_id),
                rgb_path=rgb_path,
                lidar_path=lidar_path,
                rgb_size=rgb_size,
                lidar_size=lidar_size,
                has_rgb_world_file=_has_world_file(rgb_path),
                has_lidar_world_file=_has_world_file(lidar_path) if lidar_path else False,
                status=_status(rgb_path, lidar_path, rgb_size, lidar_size),
            )
        )

    _write_report(audits, args.report_path)
    _print_summary(audits, args.rgb_dir, args.lidar_dir, args.report_path)
    return 0


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _pairing_key(stem: str) -> str:
    if stem.endswith("_lidar"):
        stem = stem[: -len("_lidar")]
    return stem.replace("_lidar_", "_")


def _site_id(patch_id: str) -> str:
    match = SITE_PATTERN.match(patch_id)
    return match.group(1) if match else "unknown"


def _label_from_patch_id(patch_id: str) -> str:
    return "non_archeologique" if "_neg" in patch_id else "archeologique"


def _patch_type(patch_id: str) -> str:
    if "_neg" in patch_id:
        return "neg"
    if "tres_large" in patch_id:
        return "tres_large"
    if patch_id.endswith("_large"):
        return "large"
    if "_patch" in patch_id:
        return "patch"
    return "unknown"


def _image_size(path: Path | None) -> tuple[int, int] | None:
    if path is None:
        return None
    with Image.open(path) as image:
        return image.size


def _has_world_file(path: Path | None) -> bool:
    if path is None:
        return False

    world_extensions = {
        ".png": ".pgw",
        ".jpg": ".jgw",
        ".jpeg": ".jgw",
        ".tif": ".tfw",
        ".tiff": ".tfw",
    }
    world_suffix = world_extensions.get(path.suffix.lower())
    return path.with_suffix(world_suffix).exists() if world_suffix else False


def _status(
    rgb_path: Path,
    lidar_path: Path | None,
    rgb_size: tuple[int, int],
    lidar_size: tuple[int, int] | None,
) -> str:
    problems = []

    if lidar_path is None:
        problems.append("missing_lidar")
    elif rgb_size != lidar_size:
        problems.append("size_mismatch")

    if not _has_world_file(rgb_path):
        problems.append("missing_rgb_world_file")

    if lidar_path is not None and not _has_world_file(lidar_path):
        problems.append("missing_lidar_world_file")

    if " " in rgb_path.stem:
        problems.append("space_in_name")

    if not re.fullmatch(r"[A-Za-z0-9_]+", rgb_path.stem):
        problems.append("non_standard_name")

    return "ok" if not problems else ";".join(problems)


def _write_report(audits: list[SampleAudit], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "patch_id",
                "site_id",
                "patch_type",
                "label",
                "rgb_path",
                "lidar_path",
                "rgb_width",
                "rgb_height",
                "lidar_width",
                "lidar_height",
                "has_rgb_world_file",
                "has_lidar_world_file",
                "status",
            ],
        )
        writer.writeheader()
        for audit in audits:
            writer.writerow(
                {
                    "patch_id": audit.patch_id,
                    "site_id": audit.site_id,
                    "patch_type": audit.patch_type,
                    "label": audit.label,
                    "rgb_path": str(audit.rgb_path),
                    "lidar_path": str(audit.lidar_path) if audit.lidar_path else "",
                    "rgb_width": audit.rgb_size[0],
                    "rgb_height": audit.rgb_size[1],
                    "lidar_width": audit.lidar_size[0] if audit.lidar_size else "",
                    "lidar_height": audit.lidar_size[1] if audit.lidar_size else "",
                    "has_rgb_world_file": audit.has_rgb_world_file,
                    "has_lidar_world_file": audit.has_lidar_world_file,
                    "status": audit.status,
                }
            )


def _print_summary(
    audits: list[SampleAudit],
    rgb_dir: Path,
    lidar_dir: Path,
    report_path: Path,
) -> None:
    print(f"RGB folder: {rgb_dir}")
    print(f"LiDAR folder: {lidar_dir}")
    print(f"Audited RGB samples: {len(audits)}")

    for label in sorted({audit.label for audit in audits}):
        count = sum(audit.label == label for audit in audits)
        print(f"- {label}: {count}")

    sites = sorted({audit.site_id for audit in audits})
    known_sites = [site for site in sites if site != "unknown"]
    print(f"Sites detected: {len(known_sites)}")
    for site in sites:
        site_audits = [audit for audit in audits if audit.site_id == site]
        positives = sum(audit.label == "archeologique" for audit in site_audits)
        negatives = sum(audit.label == "non_archeologique" for audit in site_audits)
        print(f"- {site}: {positives} archeologique, {negatives} non_archeologique")

    print("Patch types:")
    for patch_type in sorted({audit.patch_type for audit in audits}):
        type_audits = [audit for audit in audits if audit.patch_type == patch_type]
        positives = sum(audit.label == "archeologique" for audit in type_audits)
        negatives = sum(audit.label == "non_archeologique" for audit in type_audits)
        print(
            f"- {patch_type}: {len(type_audits)} total, "
            f"{positives} archeologique, {negatives} non_archeologique"
        )

    bad = [audit for audit in audits if audit.status != "ok"]
    print(f"Problems: {len(bad)}")
    for audit in bad[:20]:
        print(f"- {audit.patch_id}: {audit.status}")
    if len(bad) > 20:
        print(f"... and {len(bad) - 20} more")

    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    raise SystemExit(main())
