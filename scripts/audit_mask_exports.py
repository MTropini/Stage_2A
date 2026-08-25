from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.image_io import IMAGE_EXTENSIONS


@dataclass(frozen=True)
class MaskAudit:
    source: str
    modality: str
    image_id: str
    image_path: Path | None
    mask_path: Path
    image_size: tuple[int, int] | None
    mask_size: tuple[int, int]
    status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit QGIS mask exports before converting them to YOLO labels."
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        type=Path,
        default=[
            PROJECT_ROOT / "data" / "exports_qgis",
            PROJECT_ROOT / "data" / "exports_qgis_auto",
        ],
        help="Export roots containing rgb/lidar and rgb_masque/lidar_masque folders.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "mask_export_audit.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audits: list[MaskAudit] = []
    for source_root in args.sources:
        audits.extend(_audit_source(source_root, "rgb", "rgb_masque"))
        audits.extend(_audit_source(source_root, "lidar", "lidar_masque"))

    if not audits:
        print("No mask images found.")
        return 1

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(audits, args.output_csv)
    _print_summary(audits, args.output_csv)
    return 0


def _audit_source(source_root: Path, image_folder: str, mask_folder: str) -> list[MaskAudit]:
    clean_dir = source_root / image_folder
    mask_dir = source_root / mask_folder
    clean_by_id = {_image_id(path): path for path in _list_images(clean_dir)}
    audits = []

    for mask_path in _list_images(mask_dir):
        image_id = _mask_id(mask_path)
        image_path = clean_by_id.get(image_id)
        image_size = _image_size(image_path) if image_path else None
        mask_size = _image_size(mask_path)
        audits.append(
            MaskAudit(
                source=source_root.name,
                modality=image_folder,
                image_id=image_id,
                image_path=image_path,
                mask_path=mask_path,
                image_size=image_size,
                mask_size=mask_size,
                status=_status(image_path, image_size, mask_size),
            )
        )

    return audits


def _list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _image_id(path: Path) -> str:
    return path.stem


def _mask_id(path: Path) -> str:
    stem = path.stem
    return stem[: -len("_masque")] if stem.endswith("_masque") else stem


def _image_size(path: Path | None) -> tuple[int, int] | None:
    if path is None:
        return None
    with Image.open(path) as image:
        return image.size


def _status(
    image_path: Path | None,
    image_size: tuple[int, int] | None,
    mask_size: tuple[int, int],
) -> str:
    if image_path is None:
        return "missing_clean_image"
    if image_size != mask_size:
        return "size_mismatch"
    return "ok"


def _write_csv(audits: list[MaskAudit], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source",
                "modality",
                "image_id",
                "image_path",
                "mask_path",
                "image_width",
                "image_height",
                "mask_width",
                "mask_height",
                "status",
            ],
        )
        writer.writeheader()
        for audit in audits:
            writer.writerow(
                {
                    "source": audit.source,
                    "modality": audit.modality,
                    "image_id": audit.image_id,
                    "image_path": str(audit.image_path) if audit.image_path else "",
                    "mask_path": str(audit.mask_path),
                    "image_width": audit.image_size[0] if audit.image_size else "",
                    "image_height": audit.image_size[1] if audit.image_size else "",
                    "mask_width": audit.mask_size[0],
                    "mask_height": audit.mask_size[1],
                    "status": audit.status,
                }
            )


def _print_summary(audits: list[MaskAudit], output_csv: Path) -> None:
    print(f"Mask files audited: {len(audits)}")
    for source in sorted({audit.source for audit in audits}):
        source_audits = [audit for audit in audits if audit.source == source]
        print(f"- {source}: {len(source_audits)}")
        for modality in sorted({audit.modality for audit in source_audits}):
            modality_audits = [audit for audit in source_audits if audit.modality == modality]
            ok_count = sum(audit.status == "ok" for audit in modality_audits)
            print(f"  - {modality}: {ok_count}/{len(modality_audits)} ok")

    bad = [audit for audit in audits if audit.status != "ok"]
    print(f"Problems: {len(bad)}")
    for audit in bad[:30]:
        print(
            f"- {audit.source}/{audit.modality}/{audit.image_id}: "
            f"{audit.status} ({audit.mask_path.name})"
        )
    if len(bad) > 30:
        print(f"... and {len(bad) - 30} more")
    print(f"Report saved: {output_csv}")


if __name__ == "__main__":
    raise SystemExit(main())
