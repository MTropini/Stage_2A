from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_PATCH_SPECS = {
    "patch": 100.0,
    "large": 250.0,
    "tres_large": 500.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate square positive patch polygons around known archaeological sites."
    )
    parser.add_argument(
        "--sites",
        type=Path,
        required=True,
        help="Input vector layer containing known sites (.gpkg, .shp, .geojson).",
    )
    parser.add_argument(
        "--layer",
        default=None,
        help="Layer name inside the input GeoPackage. Optional for single-layer files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports_qgis" / "positive_patch_polygons.gpkg",
        help="Output GeoPackage containing generated patch polygons.",
    )
    parser.add_argument(
        "--output-layer",
        default="positive_patches",
        help="Output layer name.",
    )
    parser.add_argument(
        "--site-id-field",
        default=None,
        help="Existing field used as site_id. If omitted, site01, site02... are generated.",
    )
    parser.add_argument(
        "--name-field",
        default=None,
        help="Optional existing field containing the site name.",
    )
    parser.add_argument(
        "--target-crs",
        default=None,
        help="Projected CRS used for metric patch sizes, for example EPSG:2154 or EPSG:32632.",
    )
    parser.add_argument(
        "--patch-size",
        type=float,
        default=DEFAULT_PATCH_SPECS["patch"],
        help="Small patch side length in map units, normally meters.",
    )
    parser.add_argument(
        "--large-size",
        type=float,
        default=DEFAULT_PATCH_SPECS["large"],
        help="Large patch side length in map units, normally meters.",
    )
    parser.add_argument(
        "--tres-large-size",
        type=float,
        default=DEFAULT_PATCH_SPECS["tres_large"],
        help="Very large patch side length in map units, normally meters.",
    )
    parser.add_argument(
        "--source",
        default="qgis_export",
        help="Value written in the source field.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        import geopandas as gpd
        from shapely.geometry import box
    except ModuleNotFoundError:
        print("geopandas and shapely are required. Install with:")
        print("python -m pip install -r requirements.txt")
        return 1

    args = parse_args()
    sites = gpd.read_file(args.sites, layer=args.layer)

    if sites.empty:
        print(f"No site found in: {args.sites}")
        return 1

    if sites.crs is None:
        print("Input sites layer has no CRS. Define its CRS in QGIS before running this script.")
        return 1

    if sites.crs.is_geographic and args.target_crs is None:
        print(
            "Input CRS uses degrees. Provide a projected metric CRS with --target-crs, "
            "for example --target-crs EPSG:2154."
        )
        return 1

    if args.target_crs is not None:
        sites = sites.to_crs(args.target_crs)

    patch_specs = [
        ("patch", args.patch_size),
        ("large", args.large_size),
        ("tres_large", args.tres_large_size),
    ]

    output_rows = []
    for index, site in sites.reset_index(drop=True).iterrows():
        site_id = _site_id(site, index, args.site_id_field)
        site_name = _optional_value(site, args.name_field)
        center = site.geometry.centroid

        for patch_type, size in patch_specs:
            half_size = size / 2.0
            geometry = box(
                center.x - half_size,
                center.y - half_size,
                center.x + half_size,
                center.y + half_size,
            )
            output_rows.append(
                {
                    "patch_id": f"{site_id}_{patch_type}",
                    "site_id": site_id,
                    "site_name": site_name,
                    "classe": "archeologique",
                    "patch_type": patch_type,
                    "size_m": float(size),
                    "source": args.source,
                    "commentaire": "positive patch generated from site layer",
                    "geometry": geometry,
                }
            )

    output = gpd.GeoDataFrame(output_rows, geometry="geometry", crs=sites.crs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_file(args.output, layer=args.output_layer, driver="GPKG")

    print(f"Input sites: {len(sites)}")
    print(f"Generated patches: {len(output)}")
    print(f"Output: {args.output}")
    print(f"Layer: {args.output_layer}")
    print("Patch types:")
    for patch_type, size in patch_specs:
        print(f"- {patch_type}: {size:g} map units")
    return 0


def _site_id(site, index: int, site_id_field: str | None) -> str:
    if site_id_field and site_id_field in site and site[site_id_field] not in (None, ""):
        value = str(site[site_id_field]).strip()
        return _clean_identifier(value)
    return f"site{index + 1:02d}"


def _optional_value(site, field: str | None) -> str:
    if field and field in site and site[field] not in (None, ""):
        return str(site[field])
    return ""


def _clean_identifier(value: str) -> str:
    clean = []
    for char in value.lower():
        if char.isalnum():
            clean.append(char)
        elif char in {"_", "-", " "}:
            clean.append("_")
    return "".join(clean).strip("_") or "site"


if __name__ == "__main__":
    raise SystemExit(main())

