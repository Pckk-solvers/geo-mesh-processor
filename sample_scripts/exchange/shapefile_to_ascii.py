#!/usr/bin/env python3
import argparse
import sys
import os
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize

def derive_cell_size(gdf, precision=8):
    """
    ポリゴンからセルサイズを自動推定（モードを使用し、浮動小数点誤差に強い）。
    precision: 値を丸める小数点以下桁数
    """
    b = gdf.geometry.bounds
    widths = b['maxx'] - b['minx']
    heights = b['maxy'] - b['miny']
    # 丸めて最頻値を取得
    w_rounded = np.round(widths.values, precision)
    h_rounded = np.round(heights.values, precision)
    uw, w_counts = np.unique(w_rounded, return_counts=True)
    uh, h_counts = np.unique(h_rounded, return_counts=True)
    dx = float(uw[np.argmax(w_counts)])
    dy = float(uh[np.argmax(h_counts)])
    print(f"Derived cell size (mode): dx={dx}, dy={dy}")
    return dx, dy

def rasterize_to_ascii(shp_path, out_asc, attribute, dx=None, dy=None, nodata=-9999):
    # 入力シェープファイル読み込み
    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise RuntimeError("Input shapefile contains no features.")

    # 解像度設定: 未指定時は自動推定
    if dx is None or dy is None:
        dx_auto, dy_auto = derive_cell_size(gdf)
        dx = dx if dx is not None else dx_auto
        dy = dy if dy is not None else dy_auto

    # バウンディングボックス取得
    minx, miny, maxx, maxy = gdf.total_bounds
    # 列数・行数計算
    ncols = int(round((maxx - minx) / dx))
    nrows = int(round((maxy - miny) / dy))
    if ncols <= 0 or nrows <= 0:
        raise ValueError("Computed ncols/nrows <= 0. Check dx/dy and extent.")

    # 変換行列作成
    transform = from_bounds(minx, miny, maxx, maxy, ncols, nrows)

    # ラスタ化シェープ生成 (geom, value)
    shapes = ((geom, float(val)) for geom, val in zip(gdf.geometry, gdf[attribute]))
    # ラスタ化実行
    raster = rasterize(
        shapes,
        out_shape=(nrows, ncols),
        fill=nodata,
        transform=transform,
        dtype='float32'
    )

    # ASCII Grid 出力
    profile = {
        'driver': 'AAIGrid',
        'height': nrows,
        'width': ncols,
        'count': 1,
        'dtype': 'float32',
        'crs': gdf.crs,
        'transform': transform,
        'nodata': nodata
    }
    with rasterio.open(out_asc, 'w', **profile) as dst:
        dst.write(raster, 1)

    print(f"ASCII Grid written to {out_asc}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert a polygon shapefile to ESRI ASCII Grid.'
    )
    parser.add_argument(
        'shapefile',
        nargs='?',
        default=r'input\sample_polygon_WGS84_1\sample_polygon_WGS84.shp',
        help='Path to input polygon shapefile (default: input\sample_polygon_WGS84\sample_polygon_WGS84.shp)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Path to output ASC file. If omitted, uses output/<入力ファイル名>.asc',
        default=None
    )
    parser.add_argument(
        '-a', '--attribute',
        default='elevation',
        help='Field name for cell values (default: elevation)'
    )
    parser.add_argument(
        '--dx',
        type=float,
        help='Cell width (optional, auto-derived if omitted)'
    )
    parser.add_argument(
        '--dy',
        type=float,
        help='Cell height (optional, auto-derived if omitted)'
    )
    parser.add_argument(
        '--nodata',
        type=float,
        default=-9999,
        help='NoData value for cells (default: -9999)'
    )
    args = parser.parse_args()

    if not os.path.exists(args.shapefile):
        print(f"Error: Shapefile '{args.shapefile}' not found.")
        sys.exit(1)
    # 入力ファイル名（拡張子なし）を取得
    base = os.path.splitext(os.path.basename(args.shapefile))[0]

    # 出力ディレクトリ＆ファイル名を決定
    out_dir = 'output'
    if args.output:
        out_asc = args.output
        out_dir = os.path.dirname(out_asc) or out_dir
    else:
        out_asc = os.path.join(out_dir, f'{base}.asc')

    # 出力ディレクトリがなければ作成
    os.makedirs(out_dir, exist_ok=True)

    rasterize_to_ascii(
        args.shapefile,
        out_asc,
        args.attribute,
        dx=args.dx,
        dy=args.dy,
        nodata=args.nodata
    )
