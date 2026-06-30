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
class LidarAudit:
    patch_id: str
    site_id: str
    patch_type: str
    label: str
    lidar_path: Path
    lidar_size: tuple[int, int]
    has_lidar_world_file: bool
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit LiDAR-only QGIS exports before LiDAR-only model evaluation."
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
        default=PROJECT_ROOT / "data" / "exports_qgis" / "lidar_dataset_audit.csv",
        help="CSV report written by the LiDAR-only audit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lidar_paths = _list_images(args.lidar_dir)
    if not lidar_paths:
        print(f"No LiDAR images found in: {args.lidar_dir}")
        return 1

    audits = []
    for lidar_path in lidar_paths:
        patch_id = _patch_id_from_lidar_stem(lidar_path.stem)
        audits.append(
            LidarAudit(
                patch_id=patch_id,
                site_id=_site_id(patch_id),
                patch_type=_patch_type(patch_id),
                label=_label_from_patch_id(patch_id),
                lidar_path=lidar_path,
                lidar_size=_image_size(lidar_path),
                has_lidar_world_file=_has_world_file(lidar_path),
                status=_status(lidar_path, patch_id),
            )
        )

    _write_report(audits, args.report_path)
    _print_summary(audits, args.lidar_dir, args.report_path)
    return 0


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _patch_id_from_lidar_stem(stem: str) -> str:
    if stem.endswith("_lidar"):
        return stem[: -len("_lidar")]
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


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _has_world_file(path: Path) -> bool:
    world_extensions = {
        ".png": ".pgw",
        ".jpg": ".jgw",
        ".jpeg": ".jgw",
        ".tif": ".tfw",
        ".tiff": ".tfw",
    }
    world_suffix = world_extensions.get(path.suffix.lower())
    return path.with_suffix(world_suffix).exists() if world_suffix else False


def _status(path: Path, patch_id: str) -> str:
    problems = []
    if not _has_world_file(path):
        problems.append("missing_lidar_world_file")
    if " " in path.stem:
        problems.append("space_in_name")
    if not re.fullmatch(r"[A-Za-z0-9_]+", path.stem):
        problems.append("non_standard_name")
    if _site_id(patch_id) == "unknown":
        problems.append("unknown_site_id")
    if _patch_type(patch_id) == "unknown":
        problems.append("unknown_patch_type")
    return "ok" if not problems else ";".join(problems)


def _write_report(audits: list[LidarAudit], report_path: Path) -> None:
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
                    "rgb_path": "",
                    "lidar_path": str(audit.lidar_path),
                    "rgb_width": "",
                    "rgb_height": "",
                    "lidar_width": audit.lidar_size[0],
                    "lidar_height": audit.lidar_size[1],
                    "has_rgb_world_file": "",
                    "has_lidar_world_file": audit.has_lidar_world_file,
                    "status": audit.status,
                }
            )


def _print_summary(
    audits: list[LidarAudit],
    lidar_dir: Path,
    report_path: Path,
) -> None:
    print(f"LiDAR folder: {lidar_dir}")
    print(f"Audited LiDAR samples: {len(audits)}")

    for label in sorted({audit.label for audit in audits}):
        print(f"- {label}: {sum(audit.label == label for audit in audits)}")

    print(f"Sites detected: {len({audit.site_id for audit in audits if audit.site_id != 'unknown'})}")
    for site in sorted({audit.site_id for audit in audits}):
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
