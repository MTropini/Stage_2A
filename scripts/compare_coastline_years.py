from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from stage2a.coastline_change import (
    compare_coastlines,
    find_coastline_masks,
    load_coastline_points,
    write_change_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare detected coastline masks across years."
    )
    parser.add_argument(
        "--mask-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "coastline" / "processed",
        help="Folder containing coastline mask images.",
    )
    parser.add_argument(
        "--pattern",
        default="*_coastline_mask.png",
        help="Glob pattern used to find coastline masks recursively.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "coastline"
        / "change"
        / "coastline_change_summary.csv",
        help="Output CSV containing distance metrics between consecutive years.",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=10000,
        help="Maximum coastline pixels sampled per year for distance computation.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=2048,
        help="Chunk size used for nearest-distance computation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mask_paths = find_coastline_masks(args.mask_dir, args.pattern)
    if len(mask_paths) < 2:
        print(f"Need at least 2 coastline masks in: {args.mask_dir}")
        print(f"Pattern: {args.pattern}")
        print("Expected names include a year, for example 2013_coastline_mask.png.")
        return 0

    coastlines = [
        load_coastline_points(path, max_points=args.max_points) for path in mask_paths
    ]
    coastlines = sorted(coastlines, key=lambda item: (item.sector, item.year))

    changes = []
    sectors = sorted({coastline.sector for coastline in coastlines})
    for sector in sectors:
        sector_coastlines = [
            coastline for coastline in coastlines if coastline.sector == sector
        ]
        if len(sector_coastlines) < 2:
            continue

        for coastline_a, coastline_b in zip(
            sector_coastlines[:-1], sector_coastlines[1:]
        ):
            change = compare_coastlines(
                coastline_a,
                coastline_b,
                chunk_size=args.chunk_size,
            )
            changes.append(change)
            print(
                f"{sector} {change.year_from} -> {change.year_to}: "
                f"mean={change.symmetric_mean:.3f} {change.unit}, "
                f"p95={max(change.from_to_p95, change.to_from_p95):.3f} {change.unit}"
            )

    if not changes:
        print("No comparable sectors found. Need at least 2 years per sector.")
        return 0

    write_change_summary(changes, args.output_csv)
    print(f"Saved summary: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
