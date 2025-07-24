#!/usr/bin/env python3
import os
import argparse
import glob
from src.make_shp.generate_mesh import main as generate_main
from src.make_shp.add_elevation import main as elevation_main
from src.make_shp.extract_standard_mesh import extract_cells

def pipeline(domain_shp,
             basin_shp,
             num_cells_x,
             num_cells_y,
             points_path,
             out_dir,
             zcol=None,
             nodata=None,
             standard_mesh=None,
             mesh_id=None):
    """
    1) 標準地域メッシュと計算領域の重なるセルを抽出（標準メッシュを使用する場合）
    2) メッシュ生成
    3) 標高付与
    4) 中間ファイルを削除
    """
    # --- 0) 標準メッシュ抽出 ---
    if standard_mesh:
        extracted = os.path.join(out_dir, "domain_standard_mesh.shp")
        print(f"Extracting standard mesh cells intersecting domain → {extracted}")
        extract_cells(standard_mesh, domain_shp, extracted, mesh_id)
        domain_shp = extracted

    # --- 1) メッシュ生成 ---
    print("=== メッシュ生成 ===")
    generate_main(domain_shp, basin_shp, num_cells_x, num_cells_y, out_dir)

    # --- 2) 標高付与 ---
    basin_mesh  = os.path.join(out_dir, "basin_mesh.shp")
    domain_mesh = os.path.join(out_dir, "domain_mesh.shp")
    print("=== 標高付与 ===")
    elevation_main(basin_mesh, domain_mesh, points_path, out_dir, zcol, nodata)

    # 3) 中間ファイルをまとめて削除
    try:
        for basename in ("domain_mesh", "basin_mesh"):
            pattern = os.path.join(out_dir, f"{basename}.*")
            for fp in glob.glob(pattern):
                os.remove(fp)
    except Exception as e:
        print(f"[WARNING] 中間ファイルの削除中にエラーが発生しました: {e}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="計算領域→（標準地域メッシュ抽出）→メッシュ生成→標高付与 を一括実行"
    )
    ap.add_argument("--domain",        required=True, help="計算領域ポリゴン (.shp)")
    ap.add_argument("--basin",         required=True, help="流域界ポリゴン (.shp)")
    ap.add_argument("--cells_x",       type=int, required=True, help="X方向セル数")
    ap.add_argument("--cells_y",       type=int, required=True, help="Y方向セル数")
    ap.add_argument("--points",        required=True, help="点群データ (CSV/SHP)")
    ap.add_argument("--zcol",          default=None, help="Z 列名")
    ap.add_argument("--outdir",        default="./outputs", help="出力フォルダ")
    ap.add_argument("--nodata",        type=float, default=None, help="NODATA値 (デフォルト: -9999)")
    ap.add_argument("--standard-mesh", default=None, help="標準地域メッシュ (.shp) を指定すると抽出処理を実行")
    ap.add_argument("--mesh-id",       default=None, help="標準メッシュのID列名 (省略可)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    pipeline(
        args.domain,
        args.basin,
        args.cells_x,
        args.cells_y,
        args.points,
        args.outdir,
        args.zcol,
        args.nodata,
        args.standard_mesh,
        args.mesh_id
    )
