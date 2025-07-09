# ASCIIGrid ファイルの形式
QGISで読み取ることができる、または QGIS で出力できる、ファイル形式です。

## 1. 角基準（corner-registered）＋正方セル
もっとも一般的な形。セルは正方形で CELLSIZE が１行だけ。

```text
NCOLS       100
NROWS       80
XLLCORNER   123.000
YLLCORNER   45.000
CELLSIZE    10
NODATA_VALUE -9999      # ←省略可、無ければ既定 -9999
```

QGIS ではこの５(+１)行さえあればそのまま読み込めます。

## 2. センタ基準（center-registered）＋正方セル
左下セルの 中心 座標を書くバリエーション。

```text
NCOLS       100
NROWS       80
XLLCENTER   123.000
YLLCENTER   45.000
CELLSIZE    10
NODATA_VALUE -9999
```
corner/cellsize 版との違いは CORNER → CENTER だけ。QGIS も完全対応。

## 3. 矩形セル（DX/DY）
縦横ピクセル寸法が異なる場合、CELLSIZE の代わりに DX / DY（あるいは XDIM / YDIM）を並べる書式が出てきます。

```text
NCOLS     120
NROWS      60
XLLCORNER 500000
YLLCORNER 4200000
DX         30          # 水平解像度
DY         20          # 垂直解像度
NODATA_VALUE -9999
GDAL は非正方ピクセルを書き出すとき自動で DX/DY を採用（FORCE_CELLSIZE=YES で強制抑止可）
```
QGIS は読み込み時に DX/DY を正しく認識し、セルを矩形として扱います。


> センタ基準＋DX/DY という組み合わせも許容されます。書き換えるのは XLLCORNER/YLLCORNER → XLLCENTER/YLLCENTER だけです。