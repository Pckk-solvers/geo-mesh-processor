# utils.py
import os
import fiona
from pyproj import CRS

def get_available_filename(directory, basename, ext):
    """
    Automatically append suffix (_1, _2, ...) if filename exists.
    Returns: full path with unique name
    """
    # 基本ファイル名
    filename = f"{basename}{ext}"
    fullpath = os.path.join(directory, filename)
    # 存在しなければそのまま返す
    if not os.path.exists(fullpath):
        return fullpath
    # 存在する場合は _1, _2, ... を付与
    counter = 1
    while True:
        new_filename = f"{basename}_{counter}{ext}"
        new_fullpath = os.path.join(directory, new_filename)
        if not os.path.exists(new_fullpath):
            return new_fullpath
        counter += 1

    
def read_crs(shp_path):
    """
    シェープファイルの座標参照系（CRS）を読み取り、
    権威コード（例: 'EPSG:4326'）として返します。
    取得できなかった場合は、簡易的にWKT文字列の先頭部分を返します。
    """
    with fiona.open(shp_path) as src:
        # pyproj を使って権威コード取得を試みる
        try:
            crs_obj = CRS(src.crs_wkt or src.crs)
            auth = crs_obj.to_authority()  # 例: ('EPSG','4326')
            if auth:
                return f"{auth[0]}:{auth[1]}"
        except Exception:
            pass

        # フォールバック: src.crs の 'init' や 'epsg' キーを確認
        crs_dict = src.crs
        if isinstance(crs_dict, dict):
            init = crs_dict.get('init') or crs_dict.get('epsg')
            if init:
                # 文字列なら大文字化、数値なら "EPSG:番号" 形式に
                return init.upper() if isinstance(init, str) else f"EPSG:{init}"

        # 最終フォールバック: WKTの1行目だけ返す
        raw = src.crs_wkt or str(src.crs)
        return raw.split('\n')[0]
