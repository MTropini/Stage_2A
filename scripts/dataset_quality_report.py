from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a per-site dataset quality report from the combined audit."
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "dataset_audit.csv",
        help="Combined dataset audit CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "dataset_quality_by_site.csv",
        help="Per-site quality CSV report.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "dataset_quality_report.md",
        help="Human-readable Markdown report.",
    )
    parser.add_argument(
        "--min-patches",
        type=int,
        default=4,
        help="Recommended minimum number of archaeological patch samples per site.",
    )
    parser.add_argument(
        "--min-negatives",
        type=int,
        default=8,
        help="Recommended minimum number of negative samples per site.",
    )
    parser.add_argument(
        "--min-large",
        type=int,
        default=1,
        help="Recommended minimum number of large archaeological samples per site.",
    )
    parser.add_argument(
        "--exclude-patch-type",
        action="append",
        default=["tres_large"],
        help="Patch type to exclude from training-oriented counts. Can be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = _read_rows(args.audit_csv)
    if not rows:
        print(f"No rows found in: {args.audit_csv}")
        return 1

    excluded_types = set(args.exclude_patch_type or [])
    report_rows = _build_site_report(rows, excluded_types, args)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(report_rows, args.output_csv)
    _write_markdown(rows, report_rows, excluded_types, args.output_md, args)
    _print_summary(rows, report_rows, excluded_types, args.output_csv, args.output_md)
    return 0


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _build_site_report(
    rows: list[dict[str, str]], excluded_types: set[str], args: argparse.Namespace
) -> list[dict[str, str]]:
    sites = sorted({row["site_id"] for row in rows})
    report_rows = []

    for site_id in sites:
        site_rows = [row for row in rows if row["site_id"] == site_id]
        usable = [
            row
            for row in site_rows
            if row["status"] == "ok" and row["patch_type"] not in excluded_types
        ]
        unusable = [row for row in site_rows if row["status"] != "ok"]

        positives = [row for row in usable if row["label"] == "archeologique"]
        negatives = [row for row in usable if row["label"] == "non_archeologique"]
        patches = [row for row in positives if row["patch_type"] == "patch"]
        large = [row for row in positives if row["patch_type"] == "large"]

        missing_patches = max(args.min_patches - len(patches), 0)
        missing_negatives = max(args.min_negatives - len(negatives), 0)
        missing_large = max(args.min_large - len(large), 0)

        recommendations = []
        if missing_patches:
            recommendations.append(f"add_{missing_patches}_archaeological_patch")
        if missing_large:
            recommendations.append(f"add_{missing_large}_large_patch")
        if missing_negatives:
            recommendations.append(f"add_{missing_negatives}_negative")
        if unusable:
            recommendations.append(f"fix_{len(unusable)}_file_issue")
        if not recommendations:
            recommendations.append("ok")

        report_rows.append(
            {
                "site_id": site_id,
                "usable_total": str(len(usable)),
                "archeologique_total": str(len(positives)),
                "non_archeologique_total": str(len(negatives)),
                "patch_count": str(len(patches)),
                "large_count": str(len(large)),
                "negative_count": str(len(negatives)),
                "unusable_count": str(len(unusable)),
                "missing_patch_count": str(missing_patches),
                "missing_large_count": str(missing_large),
                "missing_negative_count": str(missing_negatives),
                "recommendations": ";".join(recommendations),
                "source_breakdown": _source_breakdown(usable),
                "file_issues": _file_issues(unusable),
            }
        )

    return report_rows


def _source_breakdown(rows: list[dict[str, str]]) -> str:
    counts = Counter(row.get("dataset_source", "unknown") for row in rows)
    return ";".join(f"{source}:{count}" for source, count in sorted(counts.items()))


def _file_issues(rows: list[dict[str, str]]) -> str:
    return ";".join(
        f"{row['patch_id']}={row['status']}" for row in sorted(rows, key=lambda item: item["patch_id"])
    )


def _write_csv(report_rows: list[dict[str, str]], output_path: Path) -> None:
    fieldnames = [
        "site_id",
        "usable_total",
        "archeologique_total",
        "non_archeologique_total",
        "patch_count",
        "large_count",
        "negative_count",
        "unusable_count",
        "missing_patch_count",
        "missing_large_count",
        "missing_negative_count",
        "recommendations",
        "source_breakdown",
        "file_issues",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)


def _write_markdown(
    rows: list[dict[str, str]],
    report_rows: list[dict[str, str]],
    excluded_types: set[str],
    output_path: Path,
    args: argparse.Namespace,
) -> None:
    usable_training = [
        row
        for row in rows
        if row["status"] == "ok" and row["patch_type"] not in excluded_types
    ]
    unusable = [row for row in rows if row["status"] != "ok"]
    labels = Counter(row["label"] for row in usable_training)
    patch_types = Counter(row["patch_type"] for row in usable_training)
    sources = Counter(row.get("dataset_source", "unknown") for row in usable_training)

    needs_work = [
        row
        for row in report_rows
        if row["recommendations"] != "ok"
    ]

    lines = [
        "# Dataset quality report",
        "",
        "## Global summary",
        "",
        f"- Sites: {len(report_rows)}",
        f"- Training-usable samples: {len(usable_training)}",
        f"- Unusable samples: {len(unusable)}",
        f"- Excluded patch types: {', '.join(sorted(excluded_types)) or 'none'}",
        f"- Target per site: {args.min_patches} archaeological patches, "
        f"{args.min_large} large patch, {args.min_negatives} negatives",
        "",
        "## Counts",
        "",
        f"- Labels: {_counter_text(labels)}",
        f"- Patch types: {_counter_text(patch_types)}",
        f"- Sources: {_counter_text(sources)}",
        "",
        "## Sites needing action",
        "",
    ]

    if needs_work:
        lines.extend(
            [
                "| Site | Usable | Patch | Large | Negative | Unusable | Recommendation |",
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in needs_work:
            lines.append(
                "| {site_id} | {usable_total} | {patch_count} | {large_count} | "
                "{negative_count} | {unusable_count} | {recommendations} |".format(**row)
            )
    else:
        lines.append("All sites meet the current thresholds.")

    lines.extend(["", "## Per-site detail", ""])
    lines.extend(
        [
            "| Site | Arch. total | Neg. total | Patch | Large | Sources | File issues |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in report_rows:
        lines.append(
            "| {site_id} | {archeologique_total} | {non_archeologique_total} | "
            "{patch_count} | {large_count} | {source_breakdown} | {file_issues} |".format(
                **row
            )
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _counter_text(counter: Counter[str]) -> str:
    return ", ".join(f"{key}={value}" for key, value in sorted(counter.items()))


def _print_summary(
    rows: list[dict[str, str]],
    report_rows: list[dict[str, str]],
    excluded_types: set[str],
    output_csv: Path,
    output_md: Path,
) -> None:
    usable = [
        row
        for row in rows
        if row["status"] == "ok" and row["patch_type"] not in excluded_types
    ]
    needs_work = [row for row in report_rows if row["recommendations"] != "ok"]

    print(f"Training-usable samples: {len(usable)}")
    print(f"Sites: {len(report_rows)}")
    print(f"Sites needing action: {len(needs_work)}")
    for row in needs_work:
        print(f"- {row['site_id']}: {row['recommendations']}")
    print(f"CSV report: {output_csv}")
    print(f"Markdown report: {output_md}")


if __name__ == "__main__":
    raise SystemExit(main())
