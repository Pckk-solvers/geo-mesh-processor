#!/usr/bin/env python3
"""
シェープファイル → ASCIIグリッド変換ツール (コマンドライン版)

使用方法:
    python run2.py [オプション] [値]...

オプション:
    --input-shp PATH     入力シェープファイルのパス (必須)
    --field FIELD        変換対象の属性フィールド名 (必須)
    --output PATH        出力ファイルパス (.asc)
    --nodata VALUE       NoData値 (デフォルト: -9999)
    --bounds MINX,MINY,MAXX,MAXY  範囲を手動で指定 (オプション)
    --help               ヘルプを表示
"""
import argparse
import sys
import os
from src.shp_to_asc.core import shp_to_ascii

def parse_args():
    parser = argparse.ArgumentParser(description='シェープファイル → ASCIIグリッド変換ツール', add_help=False)
    
    # 必須引数
    parser.add_argument('--input-shp', required=True, help='入力シェープファイルのパス')
    parser.add_argument('--field', required=True, help='変換対象の属性フィールド名')
    
    # オプション引数
    parser.add_argument('--output', help='出力ファイルパス (.asc)')
    parser.add_argument('--nodata', type=float, default=-9999, help='NoData値 (デフォルト: -9999)')
    parser.add_argument('--bounds', help='範囲を "minx,miny,maxx,maxy" 形式で指定')
    parser.add_argument('--help', action='store_true', help='ヘルプを表示')
    
    args = parser.parse_args()
    
    # ヘルプ表示
    if args.help or len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)
    
    # 出力ファイルパスのデフォルト値
    if not args.output and args.input_shp:
        input_dir = os.path.dirname(args.input_shp)
        input_name = os.path.splitext(os.path.basename(args.input_shp))[0]
        args.output = os.path.join(input_dir, f"{input_name}.asc")
    
    # 範囲のパース
    bounds = None
    if args.bounds:
        try:
            bounds = tuple(map(float, args.bounds.split(',')))
            if len(bounds) != 4:
                raise ValueError("範囲は 'minx,miny,maxx,maxy' の形式で指定してください")
        except ValueError as e:
            print(f"エラー: 範囲の形式が無効です: {e}")
            sys.exit(1)
    
    return {
        'shp_path': args.input_shp,
        'field': args.field,
        'output_path': args.output,
        'nodata': args.nodata,
        'bounds': bounds
    }

def main():
    try:
        # 引数の解析
        kwargs = parse_args()
        
        # 入力ファイルの存在確認
        if not os.path.exists(kwargs['shp_path']):
            print(f"エラー: 入力ファイルが見つかりません: {kwargs['shp_path']}")
            sys.exit(1)
        
        # 出力ディレクトリの作成
        output_dir = os.path.dirname(kwargs['output_path'])
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 変換の実行
        print(f"変換を開始します...")
        print(f"  入力ファイル: {kwargs['shp_path']}")
        print(f"  出力ファイル: {kwargs['output_path']}")
        print(f"  対象フィールド: {kwargs['field']}")
        print(f"  NoData値: {kwargs['nodata']}")
        if kwargs.get('bounds'):
            print(f"  範囲: {kwargs['bounds']}")
        
        # 変換を実行
        ncols, nrows, dx, dy = shp_to_ascii(**kwargs)
        
        print(f"変換が完了しました。")
        print(f"  グリッドサイズ: {ncols} × {nrows} セル")
        print(f"  セルサイズ: {dx:.6f} × {dy:.6f}")
        print(f"  出力先: {kwargs['output_path']}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

# python run2.py --input-shp output\domain_mesh_elev.shp --field elevation --output output\domain_mesh_elev.asc