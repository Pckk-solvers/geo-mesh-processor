#!/usr/bin/env python3
"""Mesh generation script with optional standard mesh extraction."""

import argparse
import os

from src.make_shp.generate_mesh import main as generate_main
from src.make_shp.extract_standard_mesh import extract_cells


def generate_mesh(domain_shp: str,
                   basin_shp: str,
                   cells_x: int,
                   cells_y: int,
                   out_dir: str,
                   standard_mesh: str | None = None,
                   mesh_id: str | None = None) -> None:
    """Generate domain and basin meshes.

    Parameters
    ----------
    domain_shp : str
        Path to domain polygon shapefile.
    basin_shp : str
        Path to basin polygon shapefile.
    cells_x : int
        Number of cells in X direction.
    cells_y : int
        Number of cells in Y direction.
    out_dir : str
        Output directory for shapefiles.
    standard_mesh : str | None, optional
        Path to standard mesh shapefile used to pre-extract domain cells.
    mesh_id : str | None, optional
        ID column name of the standard mesh.
    """
    if standard_mesh:
        extracted = os.path.join(out_dir, "domain_standard_mesh.shp")
        print(f"Extracting standard mesh cells -> {extracted}")
        extract_cells(standard_mesh, domain_shp, extracted, mesh_id)
        domain_shp = extracted

    print("=== メッシュ生成 ===")
    generate_main(domain_shp, basin_shp, cells_x, cells_y, out_dir)


def main() -> None:
    ap = argparse.ArgumentParser(description="標準メッシュ抽出を含むメッシュ生成")
    ap.add_argument("--domain", required=True, help="計算領域ポリゴン (.shp)")
    ap.add_argument("--basin", required=True, help="流域界ポリゴン (.shp)")
    ap.add_argument("--cells-x", type=int, required=True, help="X方向セル数")
    ap.add_argument("--cells-y", type=int, required=True, help="Y方向セル数")
    ap.add_argument("--outdir", default="./outputs", help="出力フォルダ")
    ap.add_argument("--standard-mesh", default=None, help="標準地域メッシュ (.shp)")
    ap.add_argument("--mesh-id", default=None, help="標準メッシュのID列名")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    generate_mesh(
        args.domain,
        args.basin,
        args.cells_x,
        args.cells_y,
        args.outdir,
        args.standard_mesh,
        args.mesh_id,
    )


if __name__ == "__main__":
    main()
