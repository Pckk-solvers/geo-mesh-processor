#!/usr/bin/env python3
import argparse
import os
import geopandas as gpd
import pandas as pd
import contextlib

# 各種解析関数を定義（英語説明 / 日本語説明）

def analyze_crs(gdf):
    # Coordinate Reference System
    # 座標参照系
    print("=== CRS / 座標参照系 ===")
    print(f"CRS: {gdf.crs}  /  座標参照系: {gdf.crs}")


def analyze_geometry_types(gdf):
    # Geometry types count
    # ジオメトリ種類のカウント
    print("=== Geometry Types / ジオメトリ種類 ===")
    geom_types = gdf.geom_type.value_counts()
    for geom, count in geom_types.items():
        print(f"{geom}: {count} features  /  ジオメトリ '{geom}' のフィーチャ数: {count}")


def analyze_extent(gdf):
    # Spatial extent
    # 空間範囲
    print("=== Extent / 空間範囲 ===")
    minx, miny, maxx, maxy = gdf.total_bounds
    print(f"Extent: xmin={minx}, ymin={miny}, xmax={maxx}, ymax={maxy}  /  空間範囲: xmin={minx}, ymin={miny}, xmax={maxx}, ymax={maxy}")


def analyze_feature_cells(gdf):
    # Feature bounding boxes and sizes
    # フィーチャごとのバウンディングボックスとサイズ
    print("=== Feature Cells / フィーチャセル情報 ===")
    bounds = gdf.geometry.bounds
    for idx, row in bounds.iterrows():
        minx, miny, maxx, maxy = row['minx'], row['miny'], row['maxx'], row['maxy']
        width = maxx - minx
        height = maxy - miny
        corners = [(minx, miny), (minx, maxy), (maxx, maxy), (maxx, miny)]
        print(f"Feature {idx}: Width(幅)={width}, Height(高さ)={height}")
        print(f"Corners(コーナー座標): {corners}")


def analyze_fields(gdf):
    # Attribute fields and types
    # 属性フィールドと型
    print("=== Fields / フィールド一覧 ===")
    for name, dtype in gdf.dtypes.items():
        if name != gdf.geometry.name:
            print(f"- {name}: {dtype}")


def analyze_attribute_distribution(gdf):
    # Attribute distribution statistics
    # 属性分布統計
    print("=== Attribute Distribution / 属性分布 ===")
    for name, dtype in gdf.dtypes.items():
        if name == gdf.geometry.name:
            continue
        print(f"-- Field '{name}' / フィールド '{name}' ===")
        if pd.api.types.is_numeric_dtype(dtype):
            series = gdf[name].dropna()
            stats = series.describe()
            print(stats.to_string().replace('\n', '\n') + f" / 数値型の統計量")
        else:
            unique_vals = gdf[name].dropna().unique()
            print(f"Unique values ({len(unique_vals)}): {list(unique_vals)[:10]}{'...' if len(unique_vals) > 10 else ''} / ユニーク値数: {len(unique_vals)} 件")


def analyze_missing_invalid(gdf):
    # Missing or invalid geometries count
    # 無効または欠損ジオメトリの数
    print("=== Missing/Invalid Geometries / 無効ジオメトリ ===")
    invalid = gdf[gdf.geometry.is_empty | gdf.geometry.isna()]
    count = len(invalid)
    print(f"Count(数): {count}")


def analyze_duplicates(gdf):
    # Duplicate geometries count
    # 重複ジオメトリの数
    print("=== Duplicate Geometries / 重複ジオメトリ ===")
    dup_count = gdf.duplicated(subset=[gdf.geometry.name]).sum()
    print(f"Count(数): {dup_count}")


def analyze_vertex_counts(gdf):
    # Vertex count statistics
    # 頂点数統計
    print("=== Vertex Counts / 頂点数 ===")
    def count_coords(geom):
        if geom is None or geom.is_empty:
            return 0
        if geom.geom_type == 'Point':
            return 1
        if geom.geom_type.startswith('Multi'):
            return sum(count_coords(part) for part in geom.geoms)
        try:
            return len(geom.exterior.coords)
        except Exception:
            return 0
    counts = gdf.geometry.apply(count_coords)
    stats = counts.describe()
    print(stats.to_string() + f" / 頂点数統計")


def analyze_resolution_consistency(bounds, dx, dy):
    # Resolution consistency check
    # 解像度整合性チェック
    print("=== Resolution Consistency / 解像度チェック ===")
    minx, miny, maxx, maxy = bounds
    if dx and dy:
        cols = (maxx - minx) / dx
        rows = (maxy - miny) / dy
        print(f"Columns(列数) (width/dx): {cols} {'(integer)' if cols.is_integer() else '(non-integer)'}")
        print(f"Rows(行数) (height/dy): {rows} {'(integer)' if rows.is_integer() else '(non-integer)'}")


def estimate_performance(shp_path, gdf):
    # File size and memory usage estimate
    # ファイルサイズ・メモリ使用量推定
    print("=== Performance Estimate / パフォーマンス見積もり ===")
    exts = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
    total_size = sum(os.path.getsize(shp_path.replace('.shp', ext)) for ext in exts if os.path.exists(shp_path.replace('.shp', ext)))
    mem_usage = gdf.memory_usage(deep=True).sum()
    print(f"Shapefile size: {total_size/1024:.2f} KB  /  シェープファイルサイズ: {total_size/1024:.2f} KB")
    print(f"Memory usage: {mem_usage/1024:.2f} KB  /  メモリ使用量: {mem_usage/1024:.2f} KB")


def main():
    parser = argparse.ArgumentParser(description="Analyze a shapefile before rasterization and output results to a text file.\nシェープファイルをラスタ化前に解析し、結果をテキストファイルに出力します。")
    parser.add_argument(
        "shapefile",
        nargs='?',
        default=r'input\sample_polygon_WGS84_1\sample_polygon_WGS84.shp',
        help="Input shapefile path (default: %(default)s)\n入力シェープファイルのパス(デフォルト: %(default)s)"
    )
    parser.add_argument("--dx", type=float, help="Cell width DX in map units\nセル幅 DX" )
    parser.add_argument("--dy", type=float, help="Cell height DY in map units\nセル高さ DY" )
    parser.add_argument(
        "-o", "--output",
        default="analysis.txt",
        help="Output text file path (default: %(default)s)\n出力テキストファイルのパス(デフォルト: %(default)s)"
    )
    args = parser.parse_args()

    shp = args.shapefile
    if not os.path.exists(shp):
        print(f"Error: '{shp}' not found.\nエラー: ファイルが見つかりません: {shp}")
        exit(1)

    gdf = gpd.read_file(shp)
    bounds = gdf.total_bounds

    with open(args.output, 'w', encoding='utf-8') as f, contextlib.redirect_stdout(f):
        analyze_crs(gdf)
        analyze_geometry_types(gdf)
        analyze_extent(gdf)
        analyze_feature_cells(gdf)
        analyze_fields(gdf)
        analyze_attribute_distribution(gdf)
        analyze_missing_invalid(gdf)
        analyze_duplicates(gdf)
        analyze_vertex_counts(gdf)
        analyze_resolution_consistency(bounds, args.dx, args.dy)
        estimate_performance(shp, gdf)

    print(f"Analysis complete. Results written to {args.output}\n解析完了。結果は {args.output} に書き出されました。")

if __name__ == "__main__":
    main()
