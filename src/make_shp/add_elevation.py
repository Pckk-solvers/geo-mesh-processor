#!/usr/bin/env python
"""
計算領域ポリゴンを任意セルサイズでグリッド化し
流域界ポリゴンでクリップした 2 種類のメッシュを Shapefile 出力
"""
import argparse, numpy as np, geopandas as gpd
from shapely.geometry import box

def build_grid(extent, size, crs):
    minx, miny, maxx, maxy = extent
    xs = np.arange(minx, maxx, size)
    ys = np.arange(miny, maxy, size)
    polys = [box(x, y, x + size, y + size) for x in xs for y in ys]
    return gpd.GeoDataFrame(geometry=polys, crs=crs)

def main(domain_shp, basin_shp, cell_size, out_dir):
    domain = gpd.read_file(domain_shp)
    basin  = gpd.read_file(basin_shp).to_crs(domain.crs)

    grid = build_grid(domain.total_bounds, cell_size, domain.crs)
    basin_mesh = gpd.overlay(grid, basin, how="intersection")

    # --- 出力（Shapefile は 10 文字制限注意） ---
    grid.to_file(f"{out_dir}/domain_mesh.shp")
    basin_mesh.to_file(f"{out_dir}/basin_mesh.shp")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, help="計算領域ポリゴン")
    ap.add_argument("--basin",  required=True, help="流域界ポリゴン")
    ap.add_argument("--cell",   type=float, required=True, help="セルサイズ (入力 CRS 単位)")
    ap.add_argument("--outdir", default="../outputs", help="出力フォルダ")
    args = ap.parse_args()
    main(args.domain, args.basin, args.cell, args.outdir)
