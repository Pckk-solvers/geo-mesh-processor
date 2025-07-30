import logging
import os
import argparse
import geopandas as gpd
from pyproj import Geod

# ログ設定 - 本番環境ではWARNINGレベルに設定
logging.basicConfig(
    level=logging.WARNING,  # デフォルトはWARNINGレベルに設定
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def assign_dominant_values(
    base_path: str,
    land_path: str,
    source_field: str = 'landuse',
    output_field: str = 'dominant_value',
    threshold: float = 0.5,
    nodata=-9999,
    output_path: str = None
) -> None:
    """
    基準メッシュと属性メッシュを読み込み、面積割合が最大の属性値を各セルに付与します。
    処理の進行状況を表示します。
    """
    print("== メッシュ属性代表値付与処理を開始します ==")
    print(f"基準メッシュ: {base_path}")
    print(f"属性メッシュ: {land_path}")
    print(f"閾値: {threshold}, NoData値: {nodata}")

    # ファイル読み込み
    print("\n[1/5] ファイルを読み込んでいます...")
    base_gdf = gpd.read_file(base_path)
    land_gdf = gpd.read_file(land_path)
    print(f"  基準メッシュ: {len(base_gdf)} メッシュ")
    print(f"  属性メッシュ: {len(land_gdf)} ポリゴン")
    
    # ログ用の進捗表示
    logger.info(f"処理を開始: 基準メッシュ={base_path}")
    logger.info(f"属性メッシュ={land_path}, 閾値={threshold}")
    logger.info(f"読み込み完了: 基準メッシュ={len(base_gdf)}件, 属性メッシュ={len(land_gdf)}件")

    # CRSチェック
    if base_gdf.crs != land_gdf.crs:
        logger.error(f"CRS不一致: base={base_gdf.crs}, land={land_gdf.crs}")
        raise ValueError(f"CRS不一致: base={base_gdf.crs}, land={land_gdf.crs}")

    # mesh_id がなければ作成
    if 'mesh_id' not in base_gdf.columns:
        base_gdf = base_gdf.copy()
        base_gdf['mesh_id'] = base_gdf.index

    # 面積の計算 (Geod によるジオデシック面積)
    geod = Geod(ellps="WGS84")
    base_gdf['base_area'] = base_gdf.geometry.apply(lambda geom: abs(geod.geometry_area_perimeter(geom)[0]))

    # 空間オーバーレイ
    print("\n[2/5] 空間オーバーレイを実行中...")
    land_subset = land_gdf[[source_field, 'geometry']]
    inter = gpd.overlay(base_gdf, land_subset, how='intersection', keep_geom_type="Polygon")
    print(f"  オーバーレイ結果: {len(inter)} の交差領域を検出")

    if inter.empty:
        # 交差なし → nodata, coverage_ratio は 0
        print("\n[!] 警告: メッシュ間に交差が見つかりませんでした。すべての出力値がNODATAになります。")
        logger.warning("メッシュ間に交差がありません。すべての出力値がNODATAになります。")
        base_gdf['cov_area'] = 0
        base_gdf['cov_ratio'] = 0
        base_gdf[output_field] = nodata
    else:
        print("\n[3/5] 面積計算を実行中...")
        
        # 1) 面積計算
        inter['int_area'] = inter.geometry.apply(lambda g: abs(geod.geometry_area_perimeter(g)[0]))
        
        # 2) セル全体の被覆面積 & 被覆率を算出
        print("  各メッシュの被覆率を計算中...")
        coverage = (
            inter.groupby('mesh_id')['int_area']
                 .sum()
                 .reset_index(name='cov_area')
        )
        coverage = coverage.merge(
            base_gdf[['mesh_id', 'base_area']],
            on='mesh_id', how='left'
        )
        coverage['cov_ratio'] = (coverage['cov_area'] / coverage['base_area']).round(4)
        
        # 進捗表示
        cov_ratio_avg = coverage['cov_ratio'].mean() * 100
        print(f"  平均被覆率: {cov_ratio_avg:.1f}% (閾値: {threshold*100}%)")

        # Baseに coverage 情報をマージ
        base_gdf = base_gdf.merge(
            coverage[['mesh_id', 'cov_area', 'cov_ratio']],
            on='mesh_id', how='left'
        )
        base_gdf[['cov_area', 'cov_ratio']] = base_gdf[['cov_area', 'cov_ratio']].fillna(0)
        base_gdf['cov_ratio'] = base_gdf['cov_ratio'].round(4)

        # 4) landuse ごとの面積合計と割合を計算
        print("\n[4/5] 属性値ごとの面積割合を計算中...")
        grp = (
            inter.groupby(['mesh_id', source_field])['int_area']
                 .sum()
                 .reset_index(name='tot_area')
        )
        grp = grp.merge(base_gdf[['mesh_id', 'base_area']], on='mesh_id', how='left')
        grp['area_ratio'] = grp['tot_area'] / grp['base_area']
        
        # ユニークな属性値の数を表示
        unique_values = len(grp[source_field].unique())
        print(f"  検出された属性値の種類: {unique_values}種類")

        # 最大ratio選択
        grp_sorted = grp.sort_values(['mesh_id', 'area_ratio'], ascending=[True, False])
        dominant = grp_sorted.groupby('mesh_id', as_index=False).first()

        # 6) coverage_ratio を dominant にマージして閾値判定
        dominant = dominant.merge(
            coverage[['mesh_id', 'cov_area', 'cov_ratio']],
            on='mesh_id', how='left'
        )
        dominant['cov_ratio'] = dominant['cov_ratio'].fillna(0)
        dominant['dominant_v'] = dominant.apply(
            lambda row: row[source_field] if row['cov_ratio'] >= threshold else nodata,
            axis=1
        )

        # 結果をマージ
        base_gdf = base_gdf.merge(
            dominant[['mesh_id', 'dominant_v']],
            on='mesh_id', how='left'
        )

        # ここで欠損（mesh_id が dominant になかった行など）を nodata で埋める
        base_gdf['dominant_v'] = base_gdf['dominant_v'].fillna(nodata)
        # output_field        # 文字列化関数
        def to_str_no_dot0(v):
            try:
                f = float(v)
            except Exception:
                return str(v)
            if f.is_integer():
                return str(int(f))
            return str(f)
        # 出力フィールド名が10文字を超える場合は短縮
        output_field_short = output_field[:10] if len(output_field) > 10 else output_field
        base_gdf[output_field_short] = base_gdf['dominant_v'].apply(to_str_no_dot0)
        base_gdf.drop(columns=['dominant_v'], inplace=True)

    # 出力パス自動生成
    if output_path is None:
        base_name, _ = os.path.splitext(os.path.basename(base_path))
        output_path = os.path.join(os.path.dirname(base_path), f"{base_name}_dominant.shp")
    
    # 出力前に不要なカラムを削除
    columns_to_drop = ['base_area', 'cov_area', 'cov_ratio']
    columns_to_drop = [col for col in columns_to_drop if col in base_gdf.columns]
    if columns_to_drop:
        base_gdf = base_gdf.drop(columns=columns_to_drop)
    
    # Shapefile書出し
    print("\n[5/5] 結果を出力中...")
    base_gdf.to_file(output_path)
    
    # 完了メッセージ
    print("\n== 処理が正常に完了しました ==")
    print(f"出力ファイル: {output_path}")
    
    # ログにも記録
    logger.info(f"処理が完了しました: 出力ファイル={output_path}")
    logger.info(f"出力レコード数: {len(base_gdf)}")
    
    # 処理結果のサマリーを表示
    if output_field in base_gdf.columns:
        value_counts = base_gdf[output_field].value_counts()
        print("\n[処理結果サマリー]")
        print(f"合計メッシュ数: {len(base_gdf)}")
        print("\n代表値の内訳:")
        print(value_counts.head(10))  # 上位10件のみ表示
        if len(value_counts) > 10:
            print(f"... 他 {len(value_counts) - 10} 種類の値")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='メッシュ属性代表値付与ツール')
    parser.add_argument('--base', required=True, help='基準メッシュのShapefileパス')
    parser.add_argument('--land', required=True, help='属性メッシュのShapefileパス')
    parser.add_argument('--source-field', default='landuse', help='属性フィールド名')
    parser.add_argument('--output-field', default='dominant_value', help='出力属性フィールド名')
    parser.add_argument('--threshold', type=float, default=0.5, help='面積割合の閾値')
    parser.add_argument('--nodata', default=-9999, help='nodata値')
    parser.add_argument('--output', default=None, help='出力Shapefileパス')
    args = parser.parse_args()

    assign_dominant_values(
        base_path=args.base,
        land_path=args.land,
        source_field=args.source_field,
        output_field=args.output_field,
        threshold=args.threshold,
        nodata=args.nodata,
        output_path=args.output
    )



"""
python src/mesh_dominant_module/mesh_dominant.py `
--base output/50/domain_mesh_elev.shp `
--land basin_mesh_elev_seq.shp `
--source-field seq `
--output-field d_sequence `
--threshold 0.5 `
--nodata -9999 `
--output result5.shp
"""

"""
python src/mesh_dominant_module/mesh_dominant.py `
--base C:/Users/yuuta.ochiai/Documents/GitHub/shp_to_asc_converter/output/100/domain_mesh_elev.shp `
--land basin_mesh_elev_seq25.shp `
--source-field seq25 `
--output-field d_sequence `
--threshold 0.5 `
--nodata -9999 `
--output result25.shp
"""
