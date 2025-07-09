import os
import math
from osgeo import gdal, ogr
from qgis.core import QgsVectorLayer

# --- 0. 既存ファイルの削除 ---
out_tif = r"C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\output_elevation - コピー.tif"
if os.path.exists(out_tif):
    os.remove(out_tif)

# --- 1. シェープファイルの読み込み (OGR) ---
shp_path = r"C:\Users\yuuta.ochiai\Documents\GitHub\shp_to_asc_converter\sample_polygon\sample_polygon.shp"
drv      = ogr.GetDriverByName("ESRI Shapefile")
src_ds   = drv.Open(shp_path, 0)
src_lyr  = src_ds.GetLayer()
src_lyr.ResetReading()
feat     = src_lyr.GetNextFeature()
if feat is None:
    raise IOError(f"No features found in layer: {shp_path}")
# OGR ジオメトリ取得
geom     = feat.GetGeometryRef()

# --- 2. 最小回転長方形の取得 (QGIS API) ---
layer_q = QgsVectorLayer(shp_path, "tmp", "ogr")
if not layer_q.isValid():
    raise IOError(f"Failed to load layer in QGIS API: {shp_path}")
feat_q = next(layer_q.getFeatures())
rect_geom, area, angle, rect_width, rect_height = feat_q.geometry().orientedMinimumBoundingBox()

# --- 3. GDAL 用回転角度変換 （東基準0°） ---
angle_east = 90.0 - angle
theta      = math.radians(angle_east)

# --- 4. 解像度設定と GeoTransform 要素計算 ---
pixel_size = 2.0
px_w   = pixel_size * math.cos(theta)
px_sk  = -pixel_size * math.sin(theta)
py_sk  = pixel_size * math.sin(theta)
py_h   = pixel_size * math.cos(theta)

# --- 5. グリッド行列サイズ計算 ---
cols = int(rect_width  / pixel_size)
rows = int(rect_height / pixel_size)

# --- 6. 原点座標取得 (回転矩形の最初の頂点) ---
rect_wkt = rect_geom.asWkt()
ogr_geom = ogr.CreateGeometryFromWkt(rect_wkt)
pts      = ogr_geom.GetGeometryRef(0).GetPoints()
origin_x, origin_y = pts[0]

# --- 7. 出力ラスタ作成 & ラスタライズ ---
drv_t  = gdal.GetDriverByName("GTiff")
dst_ds = drv_t.Create(out_tif, cols, rows, 1, gdal.GDT_Float32)
# GeoTransform: [originX, pixelWidth, xSkew, originY, ySkew, -pixelHeight]
dst_ds.SetGeoTransform([origin_x, px_w, px_sk, origin_y, py_sk, -py_h])
dst_ds.SetProjection(src_lyr.GetSpatialRef().ExportToWkt())
gdal.RasterizeLayer(
    dst_ds,
    [1],
    src_lyr,
    options=["ATTRIBUTE=elevation"]
)
dst_ds.FlushCache()
dst_ds = None

print("回転出力完了:", out_tif)
