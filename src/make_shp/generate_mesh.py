# generate_mesh.py
#!/usr/bin/env python3
"""
計算領域ポリゴンを任意セルサイズでグリッド化し、
流域界ポリゴンでクリップした 2 種類のメッシュを Shapefile 出力
"""
import argparse
import math
import numpy as np
import geopandas as gpd
from shapely.geometry import box

def build_grid(extent, num_cells_x, num_cells_y, crs):
    minx, miny, maxx, maxy = extent
    width = maxx - minx
    height = maxy - miny
    
    # セルサイズを計算
    cell_size_x = width / num_cells_x
    cell_size_y = height / num_cells_y
    
    print(f"X方向のセルサイズ: {cell_size_x:.6f} 度")
    print(f"Y方向のセルサイズ: {cell_size_y:.6f} 度")
    print(f"X方向のセル数: {num_cells_x}, Y方向のセル数: {num_cells_y}")
    print(f"実サイズ: 横 {width:.6f} 度 x 縦 {height:.6f} 度")
    
    # グリッド生成
    xs = np.linspace(minx, maxx, num_cells_x + 1)
    ys = np.linspace(miny, maxy, num_cells_y + 1)
    
    polys = []
    for i in range(num_cells_x):
        for j in range(num_cells_y):
            poly = box(xs[i], ys[j], xs[i+1], ys[j+1])
            polys.append(poly)
    
    return gpd.GeoDataFrame(geometry=polys, crs=crs)

def main(domain_shp, basin_shp, num_cells_x, num_cells_y, out_dir):
    domain = gpd.read_file(domain_shp)
    basin_gdf = gpd.read_file(basin_shp).to_crs(domain.crs)

    # 1) 全体メッシュ生成
    grid = build_grid(domain.total_bounds, num_cells_x, num_cells_y, domain.crs)

    # 2) 流域ポリゴンを一つの形状にまとめる
    basin_union = basin_gdf.unary_union

    # 3) 各セルが流域ユニオンと交差するかでフィルタ
    mask = grid.geometry.intersects(basin_union)
    basin_mesh = grid[mask].copy()
    
    # 出力フォルダ準備
    import os
    os.makedirs(out_dir, exist_ok=True)

    # 4) Shapefile 出力
    grid.to_file(f"{out_dir}/domain_mesh.shp")       # 全体セル
    basin_mesh.to_file(f"{out_dir}/basin_mesh.shp")   # 流域内セル（正方形のみ）
    print(f"Domain CRS: {domain.crs}")
    print(f"Domain bounds: {domain.total_bounds}")
    print(f"Basin CRS: {basin_gdf.crs}")
    print(f"Basin bounds: {basin_gdf.total_bounds}")    
    print(f"Grid CRS: {grid.crs}")
    print(f"Grid bounds: {grid.total_bounds}")
    print(f"Basin mesh CRS: {basin_mesh.crs}")
    print(f"Basin mesh bounds: {basin_mesh.total_bounds}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="メッシュ生成")
    ap.add_argument("--domain", required=True, help="計算領域ポリゴン (.shp)")
    ap.add_argument("--basin", required=True, help="流域界ポリゴン (.shp)")
    ap.add_argument("--cells_x", type=int, required=True, help="X方向の分割数")
    ap.add_argument("--cells_y", type=int, required=True, help="Y方向の分割数")
    ap.add_argument("--outdir", default="./outputs", help="出力フォルダ")
    args = ap.parse_args()
    main(args.domain, args.basin, args.cells_x, args.cells_y, args.outdir)

# python src/make_shp/generate_mesh.py --domain input\SHP→ASC変換作業_サンプルデータ\計算領域_POL.shp --basin input\SHP→ASC変換作業_サンプルデータ\流域界_POL.shp --cells_x 100 --cells_y 100 --outdir ./output2
