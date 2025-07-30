# add_elevation.py
#!/usr/bin/env python3
"""
流域メッシュに平均標高を算出して付与し、
計算領域メッシュへ転記 (流域外は NoData)
"""
import argparse
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from src.shp_to_asc.gui import DEFAULT_NODATA


def get_xy_columns(df):
    """
    DataFrame df から X 列と Y 列を検出して返す。
    - X 候補: 'x', 'lon', 'longitude'
    - Y 候補: 'y', 'lat', 'latitude'
    見つからなければ ValueError を投げる。
    """
    cols = df.columns.tolist()
    # 小文字マッピング
    lower_map = {c.lower(): c for c in cols}

    # X 列
    for key in ('x'):
        if key in lower_map:
            x_col = lower_map[key]
            break
    else:
        raise ValueError("X 列（x）が見つかりません")

    # Y 列
    for key in ('y'):
        if key in lower_map:
            y_col = lower_map[key]
            break
    else:
        raise ValueError("Y 列（y）が見つかりません")

    return x_col, y_col


def get_z_candidates(df, x_col, y_col):
    """
    DataFrame df の中から、X 列と Y 列を除いた残りの列名リストを返す。
    数値型の列を優先し、なければそれ以外の列も候補に含める。
    """
    # まず数値型の列を取得し、X,Y を除外
    num_cols = [
        c for c in df.select_dtypes(include='number').columns
        if c not in (x_col, y_col)
    ]
    if num_cols:
        return num_cols

    # 数値型がなければ、残り全列を候補に
    other_cols = [c for c in df.columns if c not in (x_col, y_col)]
    return other_cols



def load_points(paths, target_crs, zcol_arg=None):
    """
    複数の点群ファイル (CSV または SHP) を読み込み、
    target_crs に変換して結合した GeoDataFrame を返します。
    paths: str または str のリスト
    """
    def _load_one(path):
        # 1) SHPファイルの場合
        if path.lower().endswith(".shp"):
            return gpd.read_file(path).to_crs(target_crs)  # 単一SHP読み込み・CRS変換 :contentReference[oaicite:0]{index=0}

        # 2) CSVファイルの場合
        df = pd.read_csv(path)  # CSV読み込み :contentReference[oaicite:1]{index=1}
        x_col, y_col = get_xy_columns(df)  # X,Y列検出 :contentReference[oaicite:2]{index=2}
        z_cands = get_z_candidates(df, x_col, y_col)  # Z列候補取得 :contentReference[oaicite:3]{index=3}

        # 3) Z列の決定
        if zcol_arg:
            if zcol_arg in z_cands:
                z_col = zcol_arg
            else:
                raise ValueError(f"現在処理中ファイルの{path}には指定された 標高値列 '{zcol_arg}' が見つかりません。他の候補: {z_cands}")
        else:
            if len(z_cands) == 1:
                z_col = z_cands[0]
            else:
                raise ValueError(f"現在処理中ファイルの{path}にはZ 列候補が複数あります: {z_cands}。--zcol で指定してください")

        # 4) GeoDataFrame 作成
        geom = [Point(xy) for xy in zip(df[x_col], df[y_col])]  # ジオメトリ作成 :contentReference[oaicite:5]{index=5}
        gdf = gpd.GeoDataFrame(
            df[[z_col]].rename(columns={z_col: "elevation"}),
            geometry=geom,
            crs=target_crs
        )
        return gdf

    # 5) 複数ファイル読み込み＆結合
    if isinstance(paths, (list, tuple)):
        gdfs = [_load_one(p) for p in paths]
        combined = pd.concat(gdfs, ignore_index=True)
        return gpd.GeoDataFrame(combined, crs=target_crs)
    else:
        return _load_one(paths)

def main(basin_shp, domain_shp, points_path, out_dir, zcol=None, nodata=None):
    # Nodata値が指定されていない場合はデフォルト値を使用
    if nodata is None:
        nodata = DEFAULT_NODATA
    # 1. ベースとなるポリゴンデータの読み込み
    basin = gpd.read_file(basin_shp)
    print(f"ベースのCRS: {basin.crs}")
    
    # 2. ドメインデータの読み込みと座標系の統一
    domain = gpd.read_file(domain_shp).to_crs(basin.crs)
    
    # 3. 点群データの読み込みと座標系の設定
    points = load_points(points_path, basin.crs, zcol)
    
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
    
    # 平均標高と点数を計算
    grouped = joined.groupby("index_right")
    mean_elev = grouped["elevation"].mean()
    point_count = grouped.size()
    point_count.name = "pnt_count"
    print("\n平均標高の計算結果:")
    print(mean_elev.head())
    print("\n点群数の計算結果:")
    print(point_count.head())

    # basinに標高と点数を追加
    basin["elevation"] = basin.index.map(mean_elev).fillna(nodata)
    basin["pnt_count"] = basin.index.map(point_count).fillna(0).astype(int)
    
    # 空間結合でdomainとbasinをマッチング
    domain = gpd.sjoin(domain, basin[["elevation", "pnt_count", "geometry"]], how="left", predicate="within")
    # 流域外は nodata / 0 に置き換え
    domain['elevation'] = domain['elevation'].fillna(nodata)
    domain['pnt_count'] = domain['pnt_count'].fillna(0).astype(int)
    
    # 不要な列（index_right, geometry_right など）を削除
    domain = domain.drop(columns=['index_right', 'geometry_right', 'feature_id'], errors='ignore')
    basin = basin.drop(columns=['index_right', 'geometry_right', 'feature_id'], errors='ignore')

    # 出力フォルダを作成
    os.makedirs(out_dir, exist_ok=True)

    # デバッグ用に標高の統計情報を表示
    print("\n最終的な標高の統計:")
    print("流域メッシュの標高統計:")
    print(basin["elevation"].describe())
    print("\n流域メッシュの点群数統計:")
    print(basin["pnt_count"].describe())
    print("\n計算領域メッシュの標高統計:")
    print(domain["elevation"].describe())
    print("\n計算領域メッシュの点群数統計:")
    print(domain["pnt_count"].describe())

    basin.to_file(f"{out_dir}/basin_mesh_elev.shp")
    domain.to_file(f"{out_dir}/domain_mesh_elev.shp")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="標高付与")
    ap.add_argument("--basin_mesh",  required=True, help="流域メッシュ (.shp)")
    ap.add_argument("--domain_mesh", required=True, help="計算領域メッシュ (.shp)")
    ap.add_argument("--points",      required=True, nargs='+', help="点群 CSV (.csv)。複数ファイル指定可")
    ap.add_argument("--zcol",        default=None, help="Z 列名")
    ap.add_argument("--outdir",      default="./outputs", help="出力フォルダ")
    args = ap.parse_args()
    main(args.basin_mesh, args.domain_mesh, args.points, args.outdir, args.zcol)
    
# python src/make_shp/add_elevation.py --basin_mesh output4\basin_mesh.shp --domain_mesh output4\domain_mesh.shp --points input\SHP→ASC変換作業_サンプルデータ\標高点群.csv --outdir ./output3
