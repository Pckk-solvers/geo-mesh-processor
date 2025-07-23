#!/usr/bin/env python3
"""
メッシュ生成と標高付与ツール

使用方法:
    python run.py [オプション] [値]...

オプション:
    --domain-shp PATH      計算領域シェープファイルのパス
    --basin-shp PATH       流域界シェープファイルのパス
    --points-csv PATH      点群CSVファイルのパス（複数指定可）
    --zcol COLUMN          標高値の列名
    --cells-x NUM          X方向のセル数
    --cells-y NUM          Y方向のセル数
    --nodata VALUE         NODATA値（デフォルト: -9999）
    --out-dir DIR          出力ディレクトリ
    --help                ヘルプを表示
"""
import argparse
import sys
from src.make_shp.mesh_elev_gui import MeshElevApp
import tkinter as tk

def parse_args():
    parser = argparse.ArgumentParser(description='メッシュ生成と標高付与ツール', add_help=False)
    parser.add_argument('--domain-shp', help='計算領域シェープファイルのパス', default="./input/SHP→ASC変換作業_サンプルデータ/計算領域_POL.shp")
    parser.add_argument('--basin-shp', help='流域界シェープファイルのパス', default="./input/SHP→ASC変換作業_サンプルデータ/流域界_POL.shp")
    parser.add_argument('--points-csv', nargs='+', help='点群CSVファイルのパス（複数指定可）', default="./input/SHP→ASC変換作業_サンプルデータ/標高点群.csv")
    parser.add_argument('--zcol', help='標高値の列名', default="elevation")
    parser.add_argument('--cells-x', type=int, help='X方向のセル数', default=100)
    parser.add_argument('--cells-y', type=int, help='Y方向のセル数', default=100)
    parser.add_argument('--nodata', help='NODATA値', default="-9999")
    parser.add_argument('--out-dir', help='出力ディレクトリ', default="./output")
    parser.add_argument('--help', action='store_true', help='ヘルプを表示')
    
    # 常にデフォルト値を含む辞書を返す
    args = parser.parse_args()
    
    # ヘルプ表示の場合はここで終了
    if hasattr(args, 'help') and args.help:
        parser.print_help()
        print()
        print('デフォルト値:')
        for action in parser._actions:
            if action.dest != 'help':
                print(f'  {action.dest}: {action.default}')
        sys.exit(0)
    
    if args.help:
        print(__doc__)
        sys.exit(0)
    
    # すべての引数を辞書に変換（デフォルト値も含む）
    initial_values = {
        'domain_shp': args.domain_shp,
        'basin_shp': args.basin_shp,
        'points_csv': args.points_csv,
        'zcol': args.zcol,
        'cells_x': args.cells_x,
        'cells_y': args.cells_y,
        'nodata': args.nodata,
        'out_dir': args.out_dir
    }
    
    return initial_values

def main():
    initial_values = parse_args()
    root = tk.Tk()
    app = MeshElevApp(root, initial_values=initial_values)
    root.mainloop()

if __name__ == "__main__":
    # デフォルト値の確認用
    if len(sys.argv) == 1:
        print("デフォルト設定で起動します。ヘルプを表示するには 'python run.py --help' を実行してください。")
    main()
