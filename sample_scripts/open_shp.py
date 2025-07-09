#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shapefile の geometry と I/J フィールドから
1セルあたりの幅 (xres) と高さ (yres) を計算するスクリプト
"""

import geopandas as gpd

# 入力シェープファイルのパス
INPUT_SHP = r"sample_polygon\sample_polygon.shp"  # 適宜書き換えてください

# 読み込み
gdf = gpd.read_file(INPUT_SHP)
if not {"I", "J"}.issubset(gdf.columns):
    raise KeyError("I フィールドまたは J フィールドが見つかりません")

# 1) 列数・行数（セル数）を I/J フィールドのユニーク数から取得
ncols = int(gdf["I"].nunique())
nrows = int(gdf["J"].nunique())

# 2) 全体のバウンディングボックスを取得
xmin, ymin, xmax, ymax = gdf.total_bounds

# 3) 解像度（セル幅・セル高さ）を計算
xres = (xmax - xmin) / ncols
yres = (ymax - ymin) / nrows

# 結果を出力
print(f"列数 (ncols): {ncols}")
print(f"行数 (nrows): {nrows}")
print(f"セル幅 (xres): {xres}")
print(f"セル高さ (yres): {yres}")
