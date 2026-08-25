from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SVG visualizations from the tuned RGB+LiDAR error report."
    )
    parser.add_argument(
        "--report-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "fusion_error_report_tuned.csv",
        help="Detailed prediction report CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "combined" / "figures",
        help="Directory where SVG figures are written.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="Decision threshold shown on probability plots.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = _read_rows(args.report_csv)
    if not rows:
        print(f"No rows found in: {args.report_csv}")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    confusion_path = args.output_dir / "confusion_matrix.svg"
    histogram_path = args.output_dir / "probability_histogram.svg"
    site_errors_path = args.output_dir / "errors_by_site.svg"
    patch_errors_path = args.output_dir / "errors_by_patch_type.svg"
    summary_path = args.output_dir / "visualization_summary.md"

    _write_confusion_matrix(rows, confusion_path)
    _write_probability_histogram(rows, histogram_path, args.threshold)
    _write_errors_by_site(rows, site_errors_path)
    _write_errors_by_patch_type(rows, patch_errors_path)
    _write_summary(
        rows=rows,
        output_path=summary_path,
        confusion_path=confusion_path,
        histogram_path=histogram_path,
        site_errors_path=site_errors_path,
        patch_errors_path=patch_errors_path,
    )

    print(f"Rows: {len(rows)}")
    print(f"Correct: {sum(row['error_type'] == 'correct' for row in rows)}")
    print(f"False negatives: {sum(row['error_type'] == 'false_negative' for row in rows)}")
    print(f"False positives: {sum(row['error_type'] == 'false_positive' for row in rows)}")
    print(f"Confusion matrix: {confusion_path}")
    print(f"Probability histogram: {histogram_path}")
    print(f"Errors by site: {site_errors_path}")
    print(f"Errors by patch type: {patch_errors_path}")
    print(f"Summary: {summary_path}")
    return 0


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _write_confusion_matrix(rows: list[dict[str, str]], output_path: Path) -> None:
    labels = ["non_archeologique", "archeologique"]
    matrix = {
        true_label: {
            predicted_label: sum(
                row["true_label"] == true_label
                and row["predicted_label"] == predicted_label
                for row in rows
            )
            for predicted_label in labels
        }
        for true_label in labels
    }

    total = len(rows)
    max_value = max(max(values.values()) for values in matrix.values())
    cell = 130
    left = 190
    top = 100
    width = 520
    height = 430
    parts = [_svg_header(width, height)]
    parts.append(_text(260, 38, "Confusion matrix", 24, "middle", weight="700"))
    parts.append(_text(60, 245, "True label", 15, "middle", rotate=-90, weight="700"))
    parts.append(_text(320, 76, "Predicted label", 15, "middle", weight="700"))

    for col, predicted_label in enumerate(labels):
        parts.append(_text(left + col * cell + cell / 2, top - 18, predicted_label, 13, "middle"))
    for row_index, true_label in enumerate(labels):
        parts.append(_text(left - 18, top + row_index * cell + cell / 2, true_label, 13, "end"))

    for row_index, true_label in enumerate(labels):
        for col, predicted_label in enumerate(labels):
            value = matrix[true_label][predicted_label]
            intensity = 0.15 + 0.75 * (value / max_value if max_value else 0)
            fill = _blue(intensity)
            x = left + col * cell
            y = top + row_index * cell
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" stroke="#ffffff" stroke-width="3"/>')
            parts.append(_text(x + cell / 2, y + 54, str(value), 32, "middle", weight="700", fill="#ffffff"))
            parts.append(_text(x + cell / 2, y + 84, f"{value / total:.1%}", 15, "middle", fill="#ffffff"))

    accuracy = sum(row["true_label"] == row["predicted_label"] for row in rows) / total
    parts.append(_text(320, 385, f"Accuracy: {accuracy:.3f}", 16, "middle", weight="700"))
    parts.append("</svg>")
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _write_probability_histogram(
    rows: list[dict[str, str]], output_path: Path, threshold: float
) -> None:
    bins = [i / 10 for i in range(11)]
    arch_counts = [0] * 10
    non_arch_counts = [0] * 10

    for row in rows:
        probability = float(row["probability_archeologique"])
        index = min(int(probability * 10), 9)
        if row["true_label"] == "archeologique":
            arch_counts[index] += 1
        else:
            non_arch_counts[index] += 1

    width = 760
    height = 460
    left = 70
    top = 70
    chart_width = 620
    chart_height = 280
    max_count = max(arch_counts + non_arch_counts + [1])
    bar_width = chart_width / 10
    parts = [_svg_header(width, height)]
    parts.append(_text(width / 2, 38, "Probability histogram", 24, "middle", weight="700"))
    parts.append(_text(width / 2, 430, "P(archeologique)", 14, "middle", weight="700"))
    parts.append(_text(22, top + chart_height / 2, "Count", 14, "middle", rotate=-90, weight="700"))
    _axes(parts, left, top, chart_width, chart_height)

    for index in range(10):
        x = left + index * bar_width
        non_height = chart_height * non_arch_counts[index] / max_count
        arch_height = chart_height * arch_counts[index] / max_count
        parts.append(
            f'<rect x="{x + 5}" y="{top + chart_height - non_height}" '
            f'width="{bar_width / 2 - 6}" height="{non_height}" fill="#377eb8" opacity="0.82"/>'
        )
        parts.append(
            f'<rect x="{x + bar_width / 2 + 2}" y="{top + chart_height - arch_height}" '
            f'width="{bar_width / 2 - 6}" height="{arch_height}" fill="#e41a1c" opacity="0.82"/>'
        )
        parts.append(_text(x + bar_width / 2, top + chart_height + 22, f"{bins[index]:.1f}", 11, "middle"))

    threshold_x = left + threshold * chart_width
    parts.append(f'<line x1="{threshold_x}" y1="{top}" x2="{threshold_x}" y2="{top + chart_height}" stroke="#111827" stroke-width="2" stroke-dasharray="6 5"/>')
    parts.append(_text(threshold_x + 5, top + 18, f"threshold {threshold:.2f}", 12, "start", weight="700"))
    parts.append(_legend(510, 78, [("non_archeologique", "#377eb8"), ("archeologique", "#e41a1c")]))
    parts.append("</svg>")
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _write_errors_by_site(rows: list[dict[str, str]], output_path: Path) -> None:
    sites = sorted({row["site_id"] for row in rows})
    false_negatives = [
        sum(row["site_id"] == site and row["error_type"] == "false_negative" for row in rows)
        for site in sites
    ]
    false_positives = [
        sum(row["site_id"] == site and row["error_type"] == "false_positive" for row in rows)
        for site in sites
    ]
    _write_grouped_bar_chart(
        output_path=output_path,
        title="Errors by site",
        labels=sites,
        series=[
            ("False negatives", false_negatives, "#e41a1c"),
            ("False positives", false_positives, "#ff9f1c"),
        ],
        y_label="Errors",
    )


def _write_errors_by_patch_type(rows: list[dict[str, str]], output_path: Path) -> None:
    patch_types = sorted({row["patch_type"] for row in rows})
    false_negatives = [
        sum(row["patch_type"] == patch_type and row["error_type"] == "false_negative" for row in rows)
        for patch_type in patch_types
    ]
    false_positives = [
        sum(row["patch_type"] == patch_type and row["error_type"] == "false_positive" for row in rows)
        for patch_type in patch_types
    ]
    _write_grouped_bar_chart(
        output_path=output_path,
        title="Errors by patch type",
        labels=patch_types,
        series=[
            ("False negatives", false_negatives, "#e41a1c"),
            ("False positives", false_positives, "#ff9f1c"),
        ],
        y_label="Errors",
    )


def _write_grouped_bar_chart(
    output_path: Path,
    title: str,
    labels: list[str],
    series: list[tuple[str, list[int], str]],
    y_label: str,
) -> None:
    width = max(760, 90 + len(labels) * 46)
    height = 480
    left = 70
    top = 70
    chart_width = width - 130
    chart_height = 300
    max_value = max([value for _, values, _ in series for value in values] + [1])
    group_width = chart_width / len(labels)
    bar_width = min(18, group_width / (len(series) + 1))

    parts = [_svg_header(width, height)]
    parts.append(_text(width / 2, 38, title, 24, "middle", weight="700"))
    parts.append(_text(width / 2, 455, "Site" if "site" in title else "Patch type", 14, "middle", weight="700"))
    parts.append(_text(22, top + chart_height / 2, y_label, 14, "middle", rotate=-90, weight="700"))
    _axes(parts, left, top, chart_width, chart_height)

    for label_index, label in enumerate(labels):
        group_x = left + label_index * group_width
        for series_index, (_, values, color) in enumerate(series):
            value = values[label_index]
            bar_height = chart_height * value / max_value
            x = group_x + group_width / 2 - (len(series) * bar_width) / 2 + series_index * bar_width
            y = top + chart_height - bar_height
            parts.append(f'<rect x="{x}" y="{y}" width="{bar_width - 2}" height="{bar_height}" fill="{color}" opacity="0.88"/>')
            if value:
                parts.append(_text(x + bar_width / 2 - 1, y - 5, str(value), 10, "middle"))
        parts.append(_text(group_x + group_width / 2, top + chart_height + 20, label, 10, "middle", rotate=-35))

    parts.append(_legend(width - 235, 78, [(name, color) for name, _, color in series]))
    parts.append("</svg>")
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _write_summary(
    rows: list[dict[str, str]],
    output_path: Path,
    confusion_path: Path,
    histogram_path: Path,
    site_errors_path: Path,
    patch_errors_path: Path,
) -> None:
    counts = Counter(row["error_type"] for row in rows)
    site_errors = defaultdict(Counter)
    for row in rows:
        if row["error_type"] != "correct":
            site_errors[row["site_id"]][row["error_type"]] += 1

    lines = [
        "# Fusion Result Visualizations",
        "",
        f"- Samples: {len(rows)}",
        f"- Correct: {counts['correct']}",
        f"- False negatives: {counts['false_negative']}",
        f"- False positives: {counts['false_positive']}",
        "",
        "## Figures",
        "",
        f"- [Confusion matrix]({confusion_path.name})",
        f"- [Probability histogram]({histogram_path.name})",
        f"- [Errors by site]({site_errors_path.name})",
        f"- [Errors by patch type]({patch_errors_path.name})",
        "",
        "## Sites With Most Errors",
        "",
        "| Site | False negatives | False positives | Total errors |",
        "|---|---:|---:|---:|",
    ]

    sorted_sites = sorted(
        site_errors.items(),
        key=lambda item: item[1]["false_negative"] + item[1]["false_positive"],
        reverse=True,
    )
    for site, counter in sorted_sites:
        false_negative = counter["false_negative"]
        false_positive = counter["false_positive"]
        lines.append(
            f"| {site} | {false_negative} | {false_positive} | "
            f"{false_negative + false_positive} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _svg_header(width: float, height: float) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>'
        '<style>text{font-family:Arial, Helvetica, sans-serif; fill:#111827;}</style>'
    )


def _text(
    x: float,
    y: float,
    text: str,
    size: int,
    anchor: str,
    *,
    fill: str = "#111827",
    weight: str = "400",
    rotate: float | None = None,
) -> str:
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{fill}"{transform}>{_escape(text)}</text>'
    )


def _axes(parts: list[str], left: float, top: float, width: float, height: float) -> None:
    parts.append(f'<line x1="{left}" y1="{top + height}" x2="{left + width}" y2="{top + height}" stroke="#111827" stroke-width="1.5"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + height}" stroke="#111827" stroke-width="1.5"/>')
    for fraction in [0.25, 0.5, 0.75, 1.0]:
        y = top + height - fraction * height
        parts.append(f'<line x1="{left}" y1="{y}" x2="{left + width}" y2="{y}" stroke="#e5e7eb" stroke-width="1"/>')


def _legend(x: float, y: float, items: list[tuple[str, str]]) -> str:
    parts = [f'<g transform="translate({x},{y})">']
    for index, (label, color) in enumerate(items):
        item_y = index * 22
        parts.append(f'<rect x="0" y="{item_y - 11}" width="13" height="13" fill="{color}"/>')
        parts.append(_text(20, item_y, label, 12, "start"))
    parts.append("</g>")
    return "\n".join(parts)


def _blue(intensity: float) -> str:
    base = int(245 - 150 * intensity)
    green = int(250 - 125 * intensity)
    blue = int(255 - 55 * intensity)
    return f"rgb({base},{green},{blue})"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


if __name__ == "__main__":
    raise SystemExit(main())
