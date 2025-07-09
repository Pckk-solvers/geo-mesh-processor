#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shapefile の "elevation" 属性を ESRI ASCII Grid（.asc）形式のラスタに変換するサンプルスクリプト
セル形状は元シェープの I／J フィールドから自動計算します
"""

import geopandas as gpd
from rasterio.transform import from_origin
from rasterio.features import rasterize
import rasterio

# ── 設定 ──
INPUT_SHP       = r"sample_polygon\sample_polygon.shp"               # 入力シェープファイル
ATTRIBUTE_FIELD = "elevation"               # ラスタ化する属性フィールド名
OUTPUT_ASC      = "output_elevation.asc"    # 出力 ASCII Grid ファイル名
NODATA_VALUE    = -9999                     # 欠損値に使う数値

# ── 1. シェープを読み込む ──
gdf = gpd.read_file(INPUT_SHP)
if ATTRIBUTE_FIELD not in gdf.columns:
    raise KeyError(f"属性フィールド '{ATTRIBUTE_FIELD}' が見つかりません")

# ── 2. グリッド幅・高さ（セル数）を I／J フィールドから取得 ──
ncols = int(gdf["I"].nunique())
nrows = int(gdf["J"].nunique())

# ── 3. バウンディングボックスと解像度を計算 ──
xmin, ymin, xmax, ymax = gdf.total_bounds
xres = (xmax - xmin) / ncols
yres = (ymax - ymin) / nrows

# ── 4. ラスタ変換行列を作成 ──
transform = from_origin(xmin, ymax, xres, yres)

# ── 5. (geometry, value) のジェネレータを準備 ──
shapes = (
    (geom, val)
    for geom, val in zip(gdf.geometry, gdf[ATTRIBUTE_FIELD])
)

# ── 6. ASCII Grid を書き出し ──
# 属性値が小数なら float32、整数なら int32 に変換
dtype = "float32" if gdf[ATTRIBUTE_FIELD].dtype.kind == "f" else "int32"

with rasterio.open(
    OUTPUT_ASC, "w",
    driver="AAIGrid",
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

print(f"→ '{OUTPUT_ASC}' にラスタを書き出しました")
