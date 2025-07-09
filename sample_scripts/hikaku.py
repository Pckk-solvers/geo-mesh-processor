#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate_overlap.py

GeoTIFF（ラスタ）と Shapefile（ベクタ）の重なりを面積ベースで評価するスクリプト。
- Jaccard 指数: intersection_area / union_area
- ベクタ比重なり率: intersection_area / vector_area
- ラスタ比重なり率: intersection_area / raster_area
"""

import sys
import geopandas as gpd
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

def main(shp_path: str, tif_path: str):
    # 1) ベクタ読み込み & ユニオン化
    v_gdf = gpd.read_file(shp_path)
    if v_gdf.crs is None:
        raise ValueError("シェープに CRS が定義されていません")
    vector_union = v_gdf.unary_union
    vector_area = vector_union.area

    # 2) ラスタ読み込み
    with rasterio.open(tif_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        raster_crs = src.crs

    # 3) CRS を合わせる
    if raster_crs != v_gdf.crs:
        print("→ CRS が異なります。ベクタ側をラスタ CR S に変換します")
        v_gdf = v_gdf.to_crs(raster_crs)
        vector_union = v_gdf.unary_union
        vector_area = vector_union.area

    # 4) ラスタの有効ピクセル（nodata 以外）を shape 化
    mask = data != nodata
    features = shapes(data, mask=mask, transform=transform)
    geoms = []
    for geom_dict, value in features:
        geoms.append(shape(geom_dict))
    # 一気にユニオンして連続領域をまとめる
    from shapely.ops import unary_union
    raster_union = unary_union(geoms)
    raster_area = raster_union.area

    # 5) intersection / union
    inter = vector_union.intersection(raster_union)
    intersection_area = inter.area
    union = vector_union.union(raster_union)
    union_area = union.area

    # 6) メトリクス計算
    jaccard = intersection_area / union_area if union_area > 0 else 0
    overlap_vec = intersection_area / vector_area if vector_area > 0 else 0
    overlap_ras = intersection_area / raster_area if raster_area > 0 else 0

    # 7) 結果表示
    print(f"Vector area      : {vector_area:.3f}")
    print(f"Raster area      : {raster_area:.3f}")
    print(f"Intersection area: {intersection_area:.3f}")
    print(f"Union area       : {union_area:.3f}")
    print(f"Jaccard index    : {jaccard:.4f}")
    print(f"Overlap/vector   : {overlap_vec:.4f}")
    print(f"Overlap/raster   : {overlap_ras:.4f}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python evaluate_overlap.py path/to/input.shp path/to/output.tif")
        sys.exit(1)
    shp_path = sys.argv[1]
    tif_path = sys.argv[2]
    main(shp_path, tif_path)
    
# C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\sample_polygon\sample_polygon.shp
# C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\output_elevation.tif

# python  C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\hikaku.py sample_polygon\sample_polygon.shp output_elevation_offset.tif