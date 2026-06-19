from __future__ import annotations

import argparse
import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_AUDITS = [
    PROJECT_ROOT / "data" / "exports_qgis" / "dataset_audit.csv",
    PROJECT_ROOT / "data" / "exports_qgis_auto" / "dataset_audit.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine several dataset audit CSV files into one manifest."
    )
    parser.add_argument(
        "--audits",
        nargs="*",
        type=Path,
        default=DEFAULT_AUDITS,
        help="Audit CSV files to combine.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "dataset_audit.csv",
        help="Combined audit CSV output path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = []

    for audit_path in args.audits:
        if not audit_path.exists():
            print(f"Skipping missing audit: {audit_path}")
            continue

        source_name = audit_path.parent.name
        with audit_path.open("r", newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                row = dict(row)
                row["dataset_source"] = source_name
                row["sample_uid"] = f"{source_name}:{row['patch_id']}"
                rows.append(row)

    if not rows:
        print("No audit rows found.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["sample_uid", "dataset_source"] + [
        field for field in rows[0].keys() if field not in {"sample_uid", "dataset_source"}
    ]

    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Combined rows: {len(rows)}")
    _print_summary(rows)
    print(f"Output: {args.output}")
    return 0


def _print_summary(rows: list[dict[str, str]]) -> None:
    usable = [row for row in rows if row.get("status") == "ok"]
    print(f"Usable rows: {len(usable)}")

    for source in sorted({row["dataset_source"] for row in usable}):
        source_rows = [row for row in usable if row["dataset_source"] == source]
        print(f"- source {source}: {len(source_rows)}")

    for label in sorted({row["label"] for row in usable}):
        print(f"- {label}: {sum(row['label'] == label for row in usable)}")

    print(f"Sites: {len({row['site_id'] for row in usable})}")
    for site_id in sorted({row["site_id"] for row in usable}):
        site_rows = [row for row in usable if row["site_id"] == site_id]
        positives = sum(row["label"] == "archeologique" for row in site_rows)
        negatives = sum(row["label"] == "non_archeologique" for row in site_rows)
        print(f"- {site_id}: {positives} archeologique, {negatives} non_archeologique")


if __name__ == "__main__":
    raise SystemExit(main())

