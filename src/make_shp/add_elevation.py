# add_elevation.py
#!/usr/bin/env python3
"""
流域メッシュに平均標高を算出して付与し、
計算領域メッシュへ転記 (流域外は NoData)
"""
import argparse
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

NODATA = -9999

def detect_columns(df):
    # 小文字に統一して列名を取得
    cols = {c.lower(): c for c in df.columns}
    
    # x, y列を取得
    x_col = cols.get("x")
    y_col = cols.get("y")
    if x_col is None or y_col is None:
        raise ValueError("CSV に 'x' / 'y' 列が見つかりません")

    # x, y 以外の最初の列を z 列として使用
    z_col = next((c for c in df.columns if c.lower() not in ("x", "y")), None)
    if z_col is None:
        raise ValueError("Z 列が見つかりません")
    print(f"X 列: {x_col}, Y 列: {y_col}, Z 列: {z_col}")
        
    return x_col, y_col, z_col

def load_points(path, target_crs):
    # 1. SHPファイルの場合
    if path.lower().endswith(".shp"):
        return gpd.read_file(path).to_crs(target_crs)

    # 2. CSVファイルの場合
    df = pd.read_csv(path)
    x_col, y_col, z_col = detect_columns(df)
    
    # 3. GeoDataFrameの作成（ターゲットのCRSを直接使用）
    geom = [Point(xy) for xy in zip(df[x_col], df[y_col])]
    gdf = gpd.GeoDataFrame(
        df[[z_col]].rename(columns={z_col: "elev"}),
        geometry=geom,
        crs=target_crs  # ターゲットのCRSを直接使用
    )
    
    print(f"点群の平均標高: {gdf['elev'].mean():.6f}")
    print(f"点群の座標系: {gdf.crs}")
    print(f"点群の範囲: {gdf.total_bounds}")
    
    return gdf

def main(basin_shp, domain_shp, points_path, out_dir):
    # 1. ベースとなるポリゴンデータの読み込み
    basin = gpd.read_file(basin_shp)
    print(f"ベースのCRS: {basin.crs}")
    
    # 2. ドメインデータの読み込みと座標系の統一
    domain = gpd.read_file(domain_shp).to_crs(basin.crs)
    
    # 3. 点群データの読み込みと座標系の設定
    points = load_points(points_path, basin.crs)
    
    # 4. 座標系が正しく設定されているか確認
    print(f"点群データのCRS: {points.crs}")
    print(f"点群データの範囲: {points.total_bounds}")
    print(f"流域ポリゴンの範囲: {basin.total_bounds}")

    # 空間結合 + 平均標高算出
    joined = gpd.sjoin(points, basin, predicate="within", how="left")
    
    # デバッグ用に結合結果を表示
    print("結合結果の先頭5行:")
    print(joined.head())
    
    # グループ化する前に、結合に使用するインデックスを確認
    print("\nbasinのインデックス:", basin.index.tolist()[:10])
    print("joinedのindex_rightのユニーク値:", joined["index_right"].unique()[:10])
    
    # 平均標高を計算
    mean_elev = joined.groupby("index_right")["elev"].mean()
    print("\n平均標高の計算結果:")
    print(mean_elev.head())
    
    # 元のbasinのインデックスに合わせて再インデックス
    basin["elev"] = basin.index.map(mean_elev).fillna(NODATA)
    
    # 空間結合でdomainとbasinをマッチング
    domain = gpd.sjoin(domain, basin[["elev", "geometry"]], how="left", predicate="within")
    
    domain = domain[["elev", "geometry"]].dissolve(by=domain.index).reset_index()
    domain["elev"] = domain["elev"].fillna(NODATA)
    

    # 出力フォルダを作成
    import os
    os.makedirs(out_dir, exist_ok=True)

    # デバッグ用に標高の統計情報を表示
    print("\n最終的な標高の統計:")
    print("流域メッシュの標高統計:")
    print(basin["elev"].describe())
    print("\n計算領域メッシュの標高統計:")
    print(domain["elev"].describe())

    basin.to_file(f"{out_dir}/basin_mesh_elev.shp")
    domain.to_file(f"{out_dir}/domain_mesh_elev.shp")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="標高付与")
    ap.add_argument("--basin_mesh",  required=True, help="流域メッシュ (.shp)")
    ap.add_argument("--domain_mesh", required=True, help="計算領域メッシュ (.shp)")
    ap.add_argument("--points",      required=True, help="点群 CSV/SHP (.csv/.txt/.shp)")
    ap.add_argument("--outdir",      default="./outputs", help="出力フォルダ")
    args = ap.parse_args()
    main(args.basin_mesh, args.domain_mesh, args.points, args.outdir)
    
# python src/make_shp/add_elevation.py --basin_mesh output2\basin_mesh.shp --domain_mesh output2\domain_mesh.shp --points input\SHP→ASC変換作業_サンプルデータ\標高点群.csv --outdir ./output3
