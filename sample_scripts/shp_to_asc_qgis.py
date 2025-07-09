
from qgis.core import (
    QgsVectorLayer,
    QgsProcessingFeedback,
    QgsProject
)
import processing

# --- 1. 入力レイヤ読み込み ---
shp_path = r"C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\sample_polygon\sample_polygon.shp"
layer = QgsVectorLayer(shp_path, 'input_layer', 'ogr')
if not layer.isValid():
    raise IOError(f"Failed to load layer: {shp_path}")

# --- 2. 解像度＆範囲設定 ---
pixel_size = 2.0  # 1セルあたり2mの解像度
ext = layer.extent()
half = pixel_size / 2.0
xmin, xmax = ext.xMinimum() - half, ext.xMaximum() + half
ymin, ymax = ext.yMinimum() - half, ext.yMaximum() + half
extent_str = f"{xmin},{xmax},{ymin},{ymax}"

# --- 3. パラメータ定義 ---
params = {
    'INPUT':   layer,
    'FIELD':   'elevation',        # 属性フィールド
    'BURN':    None,               # 固定値なら数値を入れる
    'UNITS':   1,                  # 1=地物単位で WIDTH/HEIGHT を解像度(メートル等)として解釈
    'WIDTH':   pixel_size,         # 水平解像度＝pixel_size
    'HEIGHT':  pixel_size,         # 垂直解像度＝pixel_size
    'EXTENT':  extent_str,
    'NODATA':  0,
    'OPTIONS': '',                 # 追加GDALオプションがあれば文字列で（空文字可）
    'DATA_TYPE': 5,                # Float32
    'OUTPUT':  r"C:\…\out.tif"
}

# --- 4. 実行 ---
feedback = QgsProcessingFeedback()
res = processing.run('gdal:rasterize', params, feedback=feedback)
print("GeoTIFF saved to:", res['OUTPUT'])

layer = QgsVectorLayer(shp_path, 'input_layer', 'ogr')
if not layer.isValid():
    raise IOError(f"Failed to load layer: {shp_path}")

# --- 2. 解像度＆範囲設定 ---
pixel_size = 2.0  # 1セルあたり2mの解像度
ext = layer.extent()
half = pixel_size / 2.0
xmin, xmax = ext.xMinimum() - half, ext.xMaximum() + half
ymin, ymax = ext.yMinimum() - half, ext.yMaximum() + half
extent_str = f"{xmin},{xmax},{ymin},{ymax}"

# --- 3. パラメータ定義 ---
params = {
    'INPUT':   layer,
    'FIELD':   'elevation',        # 属性フィールド
    'BURN':    None,               # 固定値なら数値を入れる
    'UNITS':   1,                  # 1=地物単位で WIDTH/HEIGHT を解像度(メートル等)として解釈
    'WIDTH':   pixel_size,         # 水平解像度＝pixel_size
    'HEIGHT':  pixel_size,         # 垂直解像度＝pixel_size
    'EXTENT':  extent_str,
    'NODATA':  0,
    'OPTIONS': '',                 # 追加GDALオプションがあれば文字列で（空文字可）
    'DATA_TYPE': 5,                # Float32
    'OUTPUT':  r"C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\out.tif"
}

# --- 4. 実行 ---
feedback = QgsProcessingFeedback()
res = processing.run('gdal:rasterize', params, feedback=feedback)
print("GeoTIFF saved to:", res['OUTPUT'])
