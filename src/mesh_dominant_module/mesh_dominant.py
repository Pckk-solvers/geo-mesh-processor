import logging
import os
import argparse
import geopandas as gpd
from pyproj import Geod

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
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
    デバッグログを豊富に出力します。
    """
    # 入力パスとパラメータのログ
    logger.debug(f"入力 base_path = {base_path}")
    logger.debug(f"入力 land_path = {land_path}")
    logger.debug(f"source_field = {source_field}, output_field = {output_field}, threshold = {threshold}, nodata = {nodata}")

    # Shapefile 読込
    base_gdf = gpd.read_file(base_path)
    land_gdf = gpd.read_file(land_path)
    logger.debug(f"base_gdf: {len(base_gdf)} フィーチャ, CRS={base_gdf.crs}")
    logger.debug(f"land_gdf: {len(land_gdf)} フィーチャ, CRS={land_gdf.crs}")

    # CRSチェック
    if base_gdf.crs != land_gdf.crs:
        logger.error(f"CRS不一致: base={base_gdf.crs}, land={land_gdf.crs}")
        raise ValueError(f"CRS不一致: base={base_gdf.crs}, land={land_gdf.crs}")

    # mesh_id付与（存在しない場合）
    if 'mesh_id' not in base_gdf.columns:
        base_gdf = base_gdf.copy()
        base_gdf['mesh_id'] = base_gdf.index
        logger.debug("mesh_id 列をインデックスから作成しました。")

    # 面積の計算
    geod = Geod(ellps="WGS84")
    base_gdf['base_area'] = base_gdf.geometry.apply(
        lambda geom: abs(geod.geometry_area_perimeter(geom)[0])
    )
    logger.debug(f"base_area 計算完了: min={base_gdf['base_area'].min()}, max={base_gdf['base_area'].max()}")

    # 空間オーバーレイ
    land_subset = land_gdf[[source_field, 'geometry']]
    inter = gpd.overlay(base_gdf, land_subset, how='intersection', keep_geom_type="Polygon")
    logger.debug(f"overlay 結果: inter に {len(inter)} フィーチャ。")

    if inter.empty:
        # 交差なし → nodata, coverage_ratio は 0
        base_gdf['cov_area'] = 0
        base_gdf['cov_ratio'] = 0
        base_gdf[output_field] = nodata
    else:
        # 交差領域面積計算
        inter['int_area'] = inter.geometry.apply(
            lambda geom: abs(geod.geometry_area_perimeter(geom)[0])
        )
        logger.debug(f"inter.int_area 計算完了: min={inter['int_area'].min()}, max={inter['int_area'].max()}")

        # 属性を問わず総カバー面積
        coverage = (
            inter.groupby('mesh_id')['int_area']
                 .sum()
                 .reset_index(name='cov_area')
        )
        coverage = coverage.merge(
            base_gdf[['mesh_id', 'base_area']], on='mesh_id', how='left'
        )
        coverage['cov_ratio'] = coverage['cov_area'] / coverage['base_area']
        coverage['cov_ratio'] = coverage['cov_ratio'].round(4)
        logger.debug(f"coverage_ratio 計算完了: min={coverage['cov_ratio'].min()}, max={coverage['cov_ratio'].max()}")

        # Baseに coverage 情報をマージ
        base_gdf = base_gdf.merge(
            coverage[['mesh_id', 'cov_area', 'cov_ratio']],
            on='mesh_id', how='left'
        )
        base_gdf[['cov_area', 'cov_ratio']] = base_gdf[['cov_area', 'cov_ratio']].fillna(0)
        base_gdf['cov_ratio'] = base_gdf['cov_ratio'].round(4)

        # landuseごとの面積合計
        grp = (
            inter.groupby(['mesh_id', source_field])['int_area']
                 .sum()
                 .reset_index(name='tot_area')
        )
        grp = grp.merge(base_gdf[['mesh_id', 'base_area']], on='mesh_id', how='left')
        grp['area_ratio'] = grp['tot_area'] / grp['base_area']
        logger.debug(f"landuseごとの ratio サンプル: {grp.head()}")

        # 最大ratio選択
        grp_sorted = grp.sort_values(['mesh_id', 'area_ratio'], ascending=[True, False])
        dominant = grp_sorted.groupby('mesh_id', as_index=False).first()

        # coverage_ratio を dominant にマージ
        dominant = dominant.merge(
            coverage[['mesh_id', 'cov_area', 'cov_ratio']],
            on='mesh_id', how='left'
        )
        dominant['cov_ratio'] = dominant['cov_ratio'].fillna(0)

        # 閾値適用
        dominant['dominant_v'] = dominant.apply(
            lambda row: row[source_field] if row['cov_ratio'] >= threshold else nodata,
            axis=1
        )
        logger.debug(f"dominant_v 値の内訳: {dominant['dominant_v'].value_counts(dropna=False)}")

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
    logger.info(f"出力ファイル: {output_path}")

    # Shapefile書出し
    base_gdf.to_file(output_path)


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
