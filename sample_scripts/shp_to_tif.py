#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shapefile の "elevation" 属性をセル数と外枠から正確に合わせて
GeoTIFF にラスタ化するスクリプト（A案: from_bounds 利用）
既存の出力ファイル削除に失敗した場合はユーザーに通知します。
"""

import os
import sys
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize

# ── 設定 ──
INPUT_SHP       = r"sample_polygon\sample_polygon.shp"
ATTRIBUTE_FIELD = "elevation"
OUTPUT_TIF      = "output_elevation.tif"
NODATA_VALUE    = -9999

# ── 0) 既存の出力ファイルを削除 ──
if os.path.exists(OUTPUT_TIF):
    try:
        os.remove(OUTPUT_TIF)
    except PermissionError:
        print(f"エラー: 既存の'{OUTPUT_TIF}'を削除できませんでした。\n"
              "ファイルが開かれていないか確認してから再実行してください。")
        sys.exit(1)

# ── 1) Shapefile 読み込み ──
gdf = gpd.read_file(INPUT_SHP)
if ATTRIBUTE_FIELD not in gdf.columns:
    raise KeyError(f"属性フィールド '{ATTRIBUTE_FIELD}' が存在しません")

# ── 2) 各ポリゴンの幅・高さ（セルサイズ）を計算 ──
bounds = gdf.geometry.bounds
cell_widths  = bounds["maxx"] - bounds["minx"]
cell_heights = bounds["maxy"] - bounds["miny"]
xres = float(np.median(cell_widths))
yres = float(np.median(cell_heights))
print(f"→ 推定セル幅 xres: {xres}")
print(f"→ 推定セル高さ yres: {yres}")

# ── 3) グリッド全体の外枠 ──
xmin, ymin, xmax, ymax = gdf.total_bounds
print(f"→ グリッド外枠 xmin,ymin,xmax,ymax: {xmin}, {ymin}, {xmax}, {ymax}")

# ── 4) ポリゴンの重心からセル数を取得 ──
centroids = gdf.geometry.centroid
xs = np.round(centroids.x, 6)
ys = np.round(centroids.y, 6)
ncols = np.unique(xs).size
nrows = np.unique(ys).size
print(f"→ 列数 (ncols): {ncols}, 行数 (nrows): {nrows}")

# ── 5) from_bounds でアフィン変換を生成 ──
transform = from_bounds(xmin, ymin, xmax, ymax, ncols, nrows)

# ── 6) (geometry, value) ジェネレータ ──
shapes = (
    (geom, val)
    for geom, val in zip(gdf.geometry, gdf[ATTRIBUTE_FIELD])
)

# ── 7) データ型の自動判定 ──
dtype = "float32" if gdf[ATTRIBUTE_FIELD].dtype.kind == "f" else "int32"

# ── 8) GeoTIFF 出力 ──
with rasterio.open(
    OUTPUT_TIF, "w",
    driver="GTiff",
    height=nrows, width=ncols,
    count=1, dtype=dtype,
    crs=gdf.crs,
    transform=transform,
    nodata=NODATA_VALUE
) as dst:
    arr = rasterize(
        shapes,
        out_shape=(nrows, ncols),
        transform=transform,
        fill=NODATA_VALUE,
        dtype=dtype
    )
    dst.write(arr, 1)

print(f"→ '{OUTPUT_TIF}' を作成しました。")
