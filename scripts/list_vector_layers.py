from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List layers and columns in a vector file.")
    parser.add_argument("path", type=Path, help="Vector file path, for example a GeoPackage.")
    return parser.parse_args()


def main() -> int:
    try:
        import geopandas as gpd
        import pyogrio
    except ModuleNotFoundError:
        print("geopandas and pyogrio are required. Install with:")
        print("python -m pip install -r requirements.txt")
        return 1

    args = parse_args()
    layers = pyogrio.list_layers(args.path)

    print(f"File: {args.path}")
    for layer_name, geometry_type in layers:
        data = gpd.read_file(args.path, layer=layer_name, rows=1)
        print(f"- layer={layer_name}, geometry={geometry_type}")
        print(f"  crs={data.crs}")
        print(f"  columns={list(data.columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

