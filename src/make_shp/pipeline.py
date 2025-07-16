#!/usr/bin/env python3
import os
import argparse
from src.make_shp.generate_mesh import main as generate_main
from src.make_shp.add_elevation   import main as elevation_main

def pipeline(domain_shp, basin_shp, num_cells_x, num_cells_y, points_path, out_dir, zcol=None, nodata=None):
    # 1) メッシュ生成
    print("=== メッシュ生成 ===")
    generate_main(domain_shp, basin_shp, num_cells_x, num_cells_y, out_dir)

    # 2) 標高付与
    basin_mesh  = os.path.join(out_dir, "basin_mesh.shp")
    domain_mesh = os.path.join(out_dir, "domain_mesh.shp")
    print("=== 標高付与 ===")
    elevation_main(basin_mesh, domain_mesh, points_path, out_dir, zcol, nodata)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="計算領域→メッシュ生成→標高付与 を一括実行"
    )
    ap.add_argument("--domain",    required=True, help="計算領域ポリゴン (.shp)")
    ap.add_argument("--basin",     required=True, help="流域界ポリゴン     (.shp)")
    ap.add_argument("--cells_x",   type=int, required=True, help="X方向セル数")
    ap.add_argument("--cells_y",   type=int, required=True, help="Y方向セル数")
    ap.add_argument("--points",    required=True, help="点群データ (CSV/SHP)")
    ap.add_argument("--zcol",      default=None, help="Z 列名")
    ap.add_argument("--outdir",    default="./outputs", help="出力フォルダ")
    ap.add_argument("--nodata",    type=float, default=None, help="NODATA値 (デフォルト: -9999)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    pipeline(
        args.domain, args.basin,
        args.cells_x, args.cells_y,
        args.points, args.outdir, args.zcol, args.nodata
    )
