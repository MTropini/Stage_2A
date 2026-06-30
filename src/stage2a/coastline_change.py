from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


WORLD_FILE_SUFFIXES = (".pgw", ".wld", ".pngw", ".jgw", ".tfw")
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


@dataclass(frozen=True)
class CoastlinePoints:
    year: int
    sector: str
    path: Path
    points: np.ndarray
    unit: str


@dataclass(frozen=True)
class CoastlineChange:
    sector: str
    year_from: int
    year_to: int
    path_from: Path
    path_to: Path
    unit: str
    points_from: int
    points_to: int
    from_to_mean: float
    from_to_median: float
    from_to_p95: float
    from_to_max: float
    to_from_mean: float
    to_from_median: float
    to_from_p95: float
    to_from_max: float
    symmetric_mean: float


def find_coastline_masks(mask_dir: Path, pattern: str) -> list[Path]:
    if not mask_dir.exists():
        return []

    return sorted(
        path
        for path in mask_dir.rglob(pattern)
        if path.is_file() and extract_year(path) is not None
    )


def extract_year(path: Path) -> int | None:
    for part in (path.stem, *path.parts):
        match = YEAR_PATTERN.search(part)
        if match is not None:
            return int(match.group(0))

    return None


def extract_sector(path: Path) -> str:
    stem = path.stem
    for suffix in (
        "_coastline_mask",
        "_rf_coastline_mask",
        "_water_mask",
        "_water_score",
    ):
        stem = stem.replace(suffix, "")
    return stem


def load_coastline_points(mask_path: Path, max_points: int = 50000) -> CoastlinePoints:
    year = extract_year(mask_path)
    if year is None:
        raise ValueError(f"No year found in coastline mask name: {mask_path.name}")

    mask = np.asarray(Image.open(mask_path).convert("L"), dtype=np.uint8) >= 128
    rows, cols = np.nonzero(mask)
    if len(rows) == 0:
        raise ValueError(f"No coastline pixels found in: {mask_path}")

    coords = np.column_stack([cols.astype(np.float64), rows.astype(np.float64)])
    world = read_world_file(mask_path)
    unit = "pixels"
    if world is not None:
        coords = pixel_to_map_coordinates(coords, world)
        unit = "map_units"

    if len(coords) > max_points:
        indices = np.linspace(0, len(coords) - 1, max_points).astype(np.int64)
        coords = coords[indices]

    return CoastlinePoints(
        year=year,
        sector=extract_sector(mask_path),
        path=mask_path,
        points=coords,
        unit=unit,
    )


def compare_coastlines(
    coastline_a: CoastlinePoints,
    coastline_b: CoastlinePoints,
    chunk_size: int = 2048,
) -> CoastlineChange:
    if coastline_a.unit != coastline_b.unit:
        raise ValueError(
            f"Cannot compare different coordinate units: "
            f"{coastline_a.unit} vs {coastline_b.unit}"
        )

    distances_ab = nearest_distances(coastline_a.points, coastline_b.points, chunk_size)
    distances_ba = nearest_distances(coastline_b.points, coastline_a.points, chunk_size)

    return CoastlineChange(
        sector=coastline_a.sector,
        year_from=coastline_a.year,
        year_to=coastline_b.year,
        path_from=coastline_a.path,
        path_to=coastline_b.path,
        unit=coastline_a.unit,
        points_from=len(coastline_a.points),
        points_to=len(coastline_b.points),
        from_to_mean=float(np.mean(distances_ab)),
        from_to_median=float(np.median(distances_ab)),
        from_to_p95=float(np.percentile(distances_ab, 95)),
        from_to_max=float(np.max(distances_ab)),
        to_from_mean=float(np.mean(distances_ba)),
        to_from_median=float(np.median(distances_ba)),
        to_from_p95=float(np.percentile(distances_ba, 95)),
        to_from_max=float(np.max(distances_ba)),
        symmetric_mean=float((np.mean(distances_ab) + np.mean(distances_ba)) / 2.0),
    )


def nearest_distances(
    source_points: np.ndarray,
    target_points: np.ndarray,
    chunk_size: int,
) -> np.ndarray:
    try:
        from sklearn.neighbors import NearestNeighbors
    except ModuleNotFoundError:
        return _nearest_distances_numpy(source_points, target_points, chunk_size)

    neighbors = NearestNeighbors(n_neighbors=1, algorithm="kd_tree")
    neighbors.fit(target_points)
    distances, _ = neighbors.kneighbors(source_points, return_distance=True)
    return distances.reshape(-1)


def _nearest_distances_numpy(
    source_points: np.ndarray,
    target_points: np.ndarray,
    chunk_size: int,
) -> np.ndarray:
    distances = np.empty(len(source_points), dtype=np.float64)

    for start in range(0, len(source_points), chunk_size):
        stop = min(start + chunk_size, len(source_points))
        chunk = source_points[start:stop]
        delta = chunk[:, None, :] - target_points[None, :, :]
        squared = np.sum(delta * delta, axis=2)
        distances[start:stop] = np.sqrt(np.min(squared, axis=1))

    return distances


def read_world_file(image_path: Path) -> tuple[float, float, float, float, float, float] | None:
    candidates = [image_path.with_suffix(suffix) for suffix in WORLD_FILE_SUFFIXES]
    for candidate in candidates:
        if not candidate.exists():
            continue

        values = [float(line.strip().replace(",", ".")) for line in candidate.read_text().splitlines() if line.strip()]
        if len(values) != 6:
            raise ValueError(f"World file must contain 6 values: {candidate}")
        return tuple(values)  # type: ignore[return-value]

    return None


def pixel_to_map_coordinates(
    pixel_coords: np.ndarray,
    world: tuple[float, float, float, float, float, float],
) -> np.ndarray:
    pixel_size_x, rotation_y, rotation_x, pixel_size_y, top_left_x, top_left_y = world
    cols = pixel_coords[:, 0]
    rows = pixel_coords[:, 1]

    x = pixel_size_x * cols + rotation_x * rows + top_left_x
    y = rotation_y * cols + pixel_size_y * rows + top_left_y
    return np.column_stack([x, y])


def write_change_summary(changes: list[CoastlineChange], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "year_from",
        "year_to",
        "sector",
        "unit",
        "points_from",
        "points_to",
        "from_to_mean",
        "from_to_median",
        "from_to_p95",
        "from_to_max",
        "to_from_mean",
        "to_from_median",
        "to_from_p95",
        "to_from_max",
        "symmetric_mean",
        "path_from",
        "path_to",
    ]

    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for change in changes:
            writer.writerow(
                {
                    "year_from": change.year_from,
                    "year_to": change.year_to,
                    "sector": change.sector,
                    "unit": change.unit,
                    "points_from": change.points_from,
                    "points_to": change.points_to,
                    "from_to_mean": f"{change.from_to_mean:.3f}",
                    "from_to_median": f"{change.from_to_median:.3f}",
                    "from_to_p95": f"{change.from_to_p95:.3f}",
                    "from_to_max": f"{change.from_to_max:.3f}",
                    "to_from_mean": f"{change.to_from_mean:.3f}",
                    "to_from_median": f"{change.to_from_median:.3f}",
                    "to_from_p95": f"{change.to_from_p95:.3f}",
                    "to_from_max": f"{change.to_from_max:.3f}",
                    "symmetric_mean": f"{change.symmetric_mean:.3f}",
                    "path_from": str(change.path_from),
                    "path_to": str(change.path_to),
                }
            )
