#!/usr/bin/env python3
"""
全フィーチャ共通セル数でメッシュ生成スクリプト
ドメインポリゴン内の各フィーチャごとに同一セル数でグリッド化し、
流域ポリゴンでクリップしたドメインメッシュと流域メッシュを出力する。
"""
import argparse
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

def build_grid(extent, num_cells_x, num_cells_y, crs):
    """
    指定した範囲(extent)とセル数でグリッドを作成
    extent: (minx, miny, maxx, maxy)
    num_cells_x, num_cells_y: セル数
    crs: 投影法
    """
    minx, miny, maxx, maxy = extent
    xs = np.linspace(minx, maxx, num_cells_x + 1)
    ys = np.linspace(miny, maxy, num_cells_y + 1)
    polys = []
    for i in range(num_cells_x):
        for j in range(num_cells_y):
            polys.append(box(xs[i], ys[j], xs[i+1], ys[j+1]))
    return gpd.GeoDataFrame(geometry=polys, crs=crs)

def main(domain_shp, basin_shp, cells_x, cells_y, out_dir):
    # シェープの読み込み
    domain_gdf = gpd.read_file(domain_shp)
    basin_gdf = gpd.read_file(basin_shp).to_crs(domain_gdf.crs)
    basin_union = basin_gdf.unary_union

    all_grids = []
    basin_grids = []

    # 各フィーチャごとにグリッド生成
    for idx, row in domain_gdf.iterrows():
        nx = cells_x
        ny = cells_y

        extent = row.geometry.bounds  # (minx, miny, maxx, maxy)
        grid = build_grid(extent, nx, ny, domain_gdf.crs)
        grid['feature_id'] = row.get('id', idx)
        all_grids.append(grid)

        # 流域界でクリップ
        mask = grid.geometry.intersects(basin_union)
        basin_sub = grid[mask].copy()
        basin_sub['feature_id'] = row.get('id', idx)
        basin_grids.append(basin_sub)

    # 結合して出力
    os.makedirs(out_dir, exist_ok=True)
    domain_mesh = gpd.GeoDataFrame(pd.concat(all_grids, ignore_index=True), crs=domain_gdf.crs)
    basin_mesh = gpd.GeoDataFrame(pd.concat(basin_grids, ignore_index=True), crs=domain_gdf.crs)

    domain_out = os.path.join(out_dir, 'domain_mesh.shp')
    basin_out = os.path.join(out_dir, 'basin_mesh.shp')
    domain_mesh.to_file(domain_out)
    basin_mesh.to_file(basin_out)
    print(f"domain mesh -> {domain_out}")
    print(f"basin mesh  -> {basin_out}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='全フィーチャ共通セル数でメッシュ生成')
    parser.add_argument('--domain', required=True, help='ドメインポリゴン(.shp)')
    parser.add_argument('--basin',  required=True, help='流域ポリゴン(.shp)')
    parser.add_argument('--cells-x', type=int, required=True, help='セル数X（全フィーチャ共通）')
    parser.add_argument('--cells-y', type=int, required=True, help='セル数Y（全フィーチャ共通）')
    parser.add_argument('--outdir', default='./outputs', help='出力フォルダ')
    args = parser.parse_args()

    main(args.domain, args.basin, args.cells_x, args.cells_y, args.outdir)
