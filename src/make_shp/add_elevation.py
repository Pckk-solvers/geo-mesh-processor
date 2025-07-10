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
        
    return x_col, y_col, z_col

def load_points(path, crs):
    if path.lower().endswith(".shp"):
        return gpd.read_file(path).to_crs(crs)

    df = pd.read_csv(path)
    x_col, y_col, z_col = detect_columns(df)
    geom = [Point(xy) for xy in zip(df[x_col], df[y_col])]
    gdf = gpd.GeoDataFrame(df[[z_col]].rename(columns={z_col:"elev"}),
                           geometry=geom, crs=crs)
    return gdf

def main(basin_shp, domain_shp, points_path, out_dir):
    basin  = gpd.read_file(basin_shp)
    domain = gpd.read_file(domain_shp).to_crs(basin.crs)
    points = load_points(points_path, basin.crs)

    # 空間結合 + 平均標高算出
    joined    = gpd.sjoin(points, basin, predicate="within", how="left")
    mean_elev = joined.groupby("index_right")["elev"].mean()
    basin["elev"] = mean_elev.reindex(basin.index).fillna(NODATA)

    # domain へ転記
    domain = domain.merge(basin[["elev"]], left_index=True, right_index=True, how="left")
    domain["elev"] = domain["elev"].fillna(NODATA)

    # 出力フォルダを作成
    import os
    os.makedirs(out_dir, exist_ok=True)

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
    
# python src/make_shp/add_elevation.py --basin_mesh output2\basin_mesh.shp --domain_mesh output2\domain_mesh.shp --points input\SHP→ASC変換作業_サンプルデータ\FG-GML-523846-DEM5A-20241003.csv --outdir ./output3
