#!/usr/bin/env python3
"""
メッシュ生成スクリプト（標準メッシュからの抽出機能付き）

このスクリプトは、計算領域と流域界のメッシュを生成します。
標準メッシュが指定された場合は、事前に領域を抽出してから処理を行います。
"""

import argparse
import os

from src.make_shp.generate_mesh import main as generate_main
from src.make_shp.extract_standard_mesh import extract_cells


def generate_mesh(domain_shp: str,
                 basin_shp: str,
                 cells: int,
                 out_dir: str,
                 standard_mesh: str | None = None,
                 mesh_id: str | None = None) -> None:
    """計算領域と流域界のメッシュを生成します。

    パラメータ
    ----------
    domain_shp : str
        計算領域ポリゴンのシェープファイルパス
    basin_shp : str
        流域界ポリゴンのシェープファイルパス
    cells : int
        X,Y方向のセル数
    out_dir : str
        出力ディレクトリのパス
    standard_mesh : str | None, optional
        標準メッシュのシェープファイルパス（オプション）
    mesh_id : str | None, optional
        標準メッシュのIDカラム名（standard_mesh指定時必須）
    """

    # --- 0) 標準メッシュ抽出 ---
    if standard_mesh:
        extracted = os.path.join(out_dir, "domain_standard_mesh.shp")
        print(f"Extracting standard mesh cells intersecting domain → {extracted}")
        extract_cells(standard_mesh, domain_shp, extracted, mesh_id)
        domain_shp = extracted
    x_cells = cells
    y_cells = cells

    # --- 1) メッシュ生成 ---
    print("=== メッシュ生成 ===")
    generate_main(domain_shp, basin_shp, x_cells, y_cells, out_dir)
    domain_out = os.path.join(out_dir, "domain_mesh.shp")
    print(f"計算領域メッシュを生成中: {x_cells}x{y_cells} グリッド...")
    print(f"計算領域メッシュを保存しました: {domain_out}")

def main() -> None:
    ap = argparse.ArgumentParser(description="標準メッシュ抽出を含むメッシュ生成")
    ap.add_argument("--domain", required=True, help="計算領域ポリゴン (.shp)")
    ap.add_argument("--basin", required=True, help="流域界ポリゴン (.shp)")
    ap.add_argument("--cells", type=int, required=True, help="セル数")
    ap.add_argument("--outdir", default="./outputs", help="出力フォルダ")
    ap.add_argument("--standard-mesh", default=None, help="標準地域メッシュ (.shp)")
    ap.add_argument("--mesh-id", default=None, help="標準メッシュのID列名")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    generate_mesh(
        args.domain,
        args.basin,
        args.cells,
        args.outdir,
        args.standard_mesh,
        args.mesh_id,
    )


if __name__ == "__main__":
    main()
