#!/usr/bin/env python
"""
basin_mesh に平均標高を付与し
domain_mesh へ転記 (流域外セルは NoData)
"""
import argparse, pandas as pd, geopandas as gpd
from shapely.geometry import Point

NODATA = -9999

def detect_columns(df):
    cols_lower = {c.lower(): c for c in df.columns}
    x_col = cols_lower.get("x")
    y_col = cols_lower.get("y")
    if x_col is None or y_col is None:
        raise ValueError("CSV に x / y 列が見つかりません")

    # Z 列は x・y 以外の 3 番目の列を自動採用
    z_candidates = [c for c in df.columns if c not in (x_col, y_col)]
    if not z_candidates:
        raise ValueError("Z 列を自動検出できません（3 列目が必要）")
    z_col = z_candidates[0]
    return x_col, y_col, z_col

def load_points(path, crs):
    if path.lower().endswith(".shp"):
        return gpd.read_file(path).to_crs(crs)

    # CSV / TXT
    df = pd.read_csv(path)
    x_col, y_col, z_col = detect_columns(df)
    geom = [Point(xy) for xy in zip(df[x_col], df[y_col])]
    gdf  = gpd.GeoDataFrame(df[[z_col]], geometry=geom, crs=crs).rename(columns={z_col: "elev"})
    return gdf

def main(basin_mesh_shp, domain_mesh_shp, points_path, out_dir):
    basin  = gpd.read_file(basin_mesh_shp)
    domain = gpd.read_file(domain_mesh_shp).to_crs(basin.crs)
    points = load_points(points_path, basin.crs)

    # 空間結合 → ポリゴンごとの平均
    joined  = gpd.sjoin(points, basin, predicate="within", how="left")
    mean_elev = joined.groupby("index_right")["elev"].mean()
    basin["elev"] = mean_elev.reindex(basin.index).fillna(NODATA)

    # domain へ転記
    domain = domain.merge(basin[["elev"]], left_index=True, right_index=True, how="left")
    domain["elev"] = domain["elev"].fillna(NODATA)

    basin.to_file(f"{out_dir}/basin_mesh_elev.shp")
    domain.to_file(f"{out_dir}/domain_mesh_elev.shp")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--basin_mesh",  required=True, help="basin_mesh.shp")
    ap.add_argument("--domain_mesh", required=True, help="domain_mesh.shp")
    ap.add_argument("--points",      required=True, help="点群 (SHP / CSV / TXT)")
    ap.add_argument("--outdir",      default="../outputs", help="出力フォルダ")
    args = ap.parse_args()
    main(args.basin_mesh, args.domain_mesh, args.points, args.outdir)
