# core.py
import os
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import rasterize

def analyze_grid_structure(shp_path):
    """
    shapefileのグリッド構造を分析して詳細な情報を返す
    
    Args:
        shp_path: 入力シェープファイルのパス
        precision: 数値の丸め桁数
        
    Returns:
        dict: グリッド情報を含む辞書
            - 'ncols': 推奨列数
            - 'nrows': 推奨行数
            - 'cell_size_x': セル幅（X方向）
            - 'cell_size_y': セル高さ（Y方向）
            - 'extent': 範囲 (minx, miny, maxx, maxy)
            - 'cell_size_stats': セルサイズの統計情報
                - 'min_x', 'max_x', 'mean_x', 'median_x', 'std_x'
                - 'min_y', 'max_y', 'mean_y', 'median_y', 'std_y'
    """
    # シェープファイル読み込み
    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise RuntimeError("シェープファイルにフィーチャが含まれていません")
    
    # 全体のバウンディングボックスを取得
    minx, miny, maxx, maxy = gdf.total_bounds
    
    # 各フィーチャのバウンディングボックスを取得
    bounds_list = [geom.bounds for geom in gdf.geometry]
    minxs, minys, maxxs, maxys = zip(*bounds_list)
    
    # 各フィーチャの幅と高さを計算
    widths = np.array([mx - mnx for mnx, mx in zip(minxs, maxxs)])
    heights = np.array([my - mny for mny, my in zip(minys, maxys)])
    
    # セルサイズの統計を計算
    def calc_stats(arr):
        return {
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
            'mean': float(np.mean(arr)),
            'median': float(np.median(arr)),
            'std': float(np.std(arr))
        }
    
    cell_size_stats = {
        'x': calc_stats(widths),
        'y': calc_stats(heights)
    }
    
    # セルサイズを計算（平均値を使用）
    cell_size_x = cell_size_stats['x']['mean']
    cell_size_y = cell_size_stats['y']['mean']
    
    # グリッド数を計算
    ncols = max(1, int(round((maxx - minx) / cell_size_x)))
    nrows = max(1, int(round((maxy - miny) / cell_size_y)))
    
    # 結果を辞書に格納
    result = {
        'ncols': ncols,
        'nrows': nrows,
        'cell_size_x': cell_size_x,
        'cell_size_y': cell_size_y,
        'extent': (minx, miny, maxx, maxy),
        'cell_size_stats': cell_size_stats
    }
    
    # 結果を表示
    print("\n=== グリッド情報 ===")
    print(f"推奨グリッド数: {ncols} (列) x {nrows} (行)")
    print(f"推奨セルサイズ: dx={cell_size_x:.12f}, dy={cell_size_y:.12f}")
    print(f"範囲: minx={minx:.12f}, miny={miny:.12f}, maxx={maxx:.12f}, maxy={maxy:.12f}")
    
    print("\n=== セルサイズ統計 (X方向) ===")
    print(f"最小: {cell_size_stats['x']['min']:.12f}")
    print(f"最大: {cell_size_stats['x']['max']:.12f}")
    print(f"平均: {cell_size_stats['x']['mean']:.12f}")
    print(f"中央値: {cell_size_stats['x']['median']:.12f}")
    print(f"標準偏差: {cell_size_stats['x']['std']:.12f}")
    
    print("\n=== セルサイズ統計 (Y方向) ===")
    print(f"最小: {cell_size_stats['y']['min']:.12f}")
    print(f"最大: {cell_size_stats['y']['max']:.12f}")
    print(f"平均: {cell_size_stats['y']['mean']:.12f}")
    print(f"中央値: {cell_size_stats['y']['median']:.12f}")
    print(f"標準偏差: {cell_size_stats['y']['std']:.12f}")
    
    return result



def shp_to_ascii(shp_path, field, nodata, output_path, bounds=None):
    """
    ShapefileをESRI ASCII Grid形式(.asc)に変換
    グリッド数は入力シェープファイルのフィーチャに基づいて自動設定される

    Parameters:
        shp_path: 入力シェープファイルパス
        field: 属性フィールド名
        nodata: NoData値
        output_path: 出力ファイルパス (.asc)
        bounds: (minx, miny, maxx, maxy) を指定すると範囲を上書き
    """
    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise RuntimeError("シェープファイルにフィーチャが含まれていません")
    
    # boundsが渡されれば上書き、なければシェープの範囲を使用
    if bounds:
        minx, miny, maxx, maxy = bounds
    else:
        minx, miny, maxx, maxy = gdf.total_bounds
    
    # 各フィーチャのバウンディングボックスを取得
    bounds_list = [geom.bounds for geom in gdf.geometry]
    minxs, minys, maxxs, maxys = zip(*bounds_list)
    
    # グリッドのセル数を計算（各フィーチャのグリッド数を考慮）
    ncols = max(1, int(round((maxx - minx) / min(maxx - minx, min(maxxs) - min(minxs)))))
    nrows = max(1, int(round((maxy - miny) / min(maxy - miny, min(maxys) - min(minys)))))
    
    # セルサイズを計算（範囲を正確にカバーするように調整）
    dx = (maxx - minx) / ncols
    dy = (maxy - miny) / nrows
    
    # グリッドの実際の範囲（シェープの範囲と完全に一致）
    grid_width = ncols * dx
    grid_height = nrows * dy
    
    # グリッドの中心をシェープの中心に合わせる
    shape_center_x = (minx + maxx) / 2
    shape_center_y = (miny + maxy) / 2
    
    # グリッドの範囲を再計算
    grid_minx = shape_center_x - grid_width / 2
    grid_maxx = shape_center_x + grid_width / 2
    grid_miny = shape_center_y - grid_height / 2
    grid_maxy = shape_center_y + grid_height / 2
    
    print(f"セル数: {ncols} x {nrows}")
    print(f"セルサイズ: dx={dx:.12f}, dy={dy:.12f}")
    print(f"シェープ範囲: minx={minx:.12f}, miny={miny:.12f}, maxx={maxx:.12f}, maxy={maxy:.12f}")
    print(f"グリッド範囲: minx={grid_minx:.12f}, miny={grid_miny:.12f}, maxx={grid_maxx:.12f}, maxy={grid_maxy:.12f}")
    
    if ncols <= 0 or nrows <= 0:
        raise ValueError("計算されたncolsまたはnrowsが0以下です。セルサイズと範囲を確認してください")
    
    # グリッドの範囲を使用して変換行列を作成
    transform = from_bounds(grid_minx, grid_miny, grid_maxx, grid_maxy, ncols, nrows)
    shapes = ((geom, float(val)) for geom, val in zip(gdf.geometry, gdf[field]))
    raster = rasterize(
        shapes,
        out_shape=(nrows, ncols),
        fill=nodata,
        transform=transform,
        dtype='float32'
    )

    # NoData以外の値を小数点以下3桁に丸める
    raster[raster != nodata] = np.round(raster[raster != nodata], 3)
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    # .ascファイルを手動で書き出す
    header = (
        f"ncols        {ncols}\n"
        f"nrows        {nrows}\n"
        f"xllcorner    {grid_minx}\n"
        f"yllcorner    {grid_miny}\n"
        f"cellsize     {dx}\n"
        f"NODATA_value {nodata}\n"
    )

    with open(output_path, 'w') as f:
        f.write(header)
        np.savetxt(f, raster, fmt='%10.3f')
    
    # 実際のグリッド数を返す
    return ncols, nrows, dx, dy

