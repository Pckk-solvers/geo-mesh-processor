#!/usr/bin/env python3
"""Assign elevation values to meshes."""

import argparse

from src.make_shp.add_elevation import main as elevation_main


def add_elevation(basin_mesh: str,
                  domain_mesh: str,
                  points_path,
                  out_dir: str,
                  zcol: str | None = None,
                  nodata: float | None = None) -> None:
    """Add elevation values to basin and domain meshes."""
    elevation_main(basin_mesh, domain_mesh, points_path, out_dir, zcol, nodata)


def main() -> None:
    ap = argparse.ArgumentParser(description="メッシュに標高を付与する")
    ap.add_argument("--basin-mesh", required=True, help="流域メッシュ (.shp)")
    ap.add_argument("--domain-mesh", required=True, help="計算領域メッシュ (.shp)")
    ap.add_argument("--points", required=True, nargs='+', help="点群 CSV/SHP")
    ap.add_argument("--outdir", default="./outputs", help="出力フォルダ")
    ap.add_argument("--zcol", default=None, help="Z 列名")
    ap.add_argument("--nodata", type=float, default=None, help="NODATA値")
    args = ap.parse_args()

    add_elevation(
        args.basin_mesh,
        args.domain_mesh,
        args.points,
        args.outdir,
        args.zcol,
        args.nodata,
    )


if __name__ == "__main__":
    main()
