#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シェープファイルに連番属性を追加するスクリプト

同じ番号を指定回数繰り返す連番を指定属性名で追加し、
出力ファイル名は自動で「入力ファイル名_属性名.shp」となります。
例：repeat=2 → 1,1,2,2,3,3,…

Usage:
    python add_sequence_attribute.py \
        --input input.shp \
        --attr sequence \
        --repeat 2
"""
import argparse
import os
import math
import geopandas as gpd
import numpy as np

def add_sequence_attribute(shp_path, attr_name, repeat_count):
    """
    指定シェープファイルに繰り返し連番属性を追加して返します。

    Args:
        shp_path (str): 入力シェープファイルのパス
        attr_name (str): 追加する属性名
        repeat_count (int): 同じ番号を繰り返す回数

    Returns:
        GeoDataFrame: 追加後のGeoDataFrame
    """
    gdf = gpd.read_file(shp_path)
    n = len(gdf)
    if n == 0:
        raise ValueError("シェープファイルにフィーチャが存在しません。")
    # 連番生成
    num_groups = math.ceil(n / repeat_count)
    seq = np.repeat(np.arange(1, num_groups + 1), repeat_count)[:n]
    gdf[attr_name] = seq
    return gdf

def parse_args():
    parser = argparse.ArgumentParser(description="シェープファイルに連番属性を追加")
    parser.add_argument("--input", "-i", required=True, help="入力シェープファイル (.shp)")
    parser.add_argument("--attr", "-a", required=True, help="追加する属性名")
    parser.add_argument("--repeat", "-r", type=int, default=1, help="同じ番号を繰り返す回数")
    return parser.parse_args()

def main():
    args = parse_args()
    # 連番属性追加
    gdf = add_sequence_attribute(args.input, args.attr, args.repeat)
    # 自動で出力ファイル名生成：元ファイル名_属性名.shp
    base, _ = os.path.splitext(os.path.basename(args.input))
    out_path = f"{base}_{args.attr}.shp"
    gdf.to_file(out_path)
    print(f"属性 '{args.attr}' を追加し、出力: {out_path}")

if __name__ == "__main__":
    main()

# python sample_scripts\add_sequence_attribute.py --input output\25\basin_mesh_elev.shp --attr seq --repeat 1