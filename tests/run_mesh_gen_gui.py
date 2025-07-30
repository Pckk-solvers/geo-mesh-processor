#!/usr/bin/env python3
"""
メッシュ生成ツールのGUIを起動するスクリプト
"""
import os
import sys

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.make_shp.mesh_gen_gui import main

if __name__ == "__main__":
    main()
