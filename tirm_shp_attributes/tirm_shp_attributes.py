#!/usr/bin/env python3
"""
trim_shp_attributes.py

シェープファイルから不要属性を削除し、軽量化したシェープを出力するスクリプト。
設定ファイル（JSON）で入力・出力パスと `keep_columns` または `drop_columns` を指定し、
複数プロジェクトで再利用できます。

注意: JSON の仕様ではコメントをサポートしていません。
実際の `config.json` にはコメント行を含めず、純粋な JSON フォーマットで記述してください。

Usage:
    python trim_shp_attributes.py config.json

設定ファイル (config.json) の例:
{
  "input_shp": "path/to/input.shp",
  "output_shp": "path/to/output.shp",
  /* 以下いずれかを指定（JSON 本来はコメント不可） */
  "keep_columns": ["ID", "Name", "Type"]
  // または
  // "drop_columns": ["UnneededField1", "UnneededField2"]
}
"""
import argparse
import json
import os
import sys

import geopandas as gpd


def load_config(path):
    """JSON 設定ファイルから input_shp, output_shp, keep_columns / drop_columns を読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    input_shp = cfg.get('input_shp')
    output_shp = cfg.get('output_shp')
    keep = cfg.get('keep_columns')
    drop = cfg.get('drop_columns')

    if not input_shp or not output_shp:
        raise ValueError("config.json に input_shp と output_shp を必ず指定してください。")
    if not (keep or drop):
        raise ValueError("config.json に keep_columns または drop_columns のいずれかを指定してください。")

    return input_shp, output_shp, keep, drop


def trim_shp(input_shp, output_shp, keep=None, drop=None):
    """GeoDataFrame を読み込み、属性を削除・抽出して新しいシェープを出力する"""
    # 入力シェープを読み込む
    gdf = gpd.read_file(input_shp)

    # geometry カラムは必ず保持
    if keep:
        cols = [c for c in keep if c in gdf.columns]
        cols.append('geometry')
        gdf = gdf[cols]
    else:
        to_drop = [c for c in drop if c in gdf.columns]
        gdf = gdf.drop(columns=to_drop)

    # 出力先ディレクトリが存在しない場合は作成
    dirpath = os.path.dirname(output_shp)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    # シェープファイルを書き出す
    gdf.to_file(output_shp)
    print(f"Trimmed shapefile saved to: {output_shp}")


def main():
    parser = argparse.ArgumentParser(
        description='Trim shapefile attributes based on JSON config'
    )
    parser.add_argument('config_json', help='JSON 設定ファイルのパス')
    args = parser.parse_args()

    try:
        input_shp, output_shp, keep, drop = load_config(args.config_json)
        trim_shp(input_shp, output_shp, keep, drop)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
