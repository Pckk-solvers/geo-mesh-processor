# shp\_to\_asc\_converter

このリポジトリは、**シェープファイル（Shapefile）の加工と変換をワンストップで行うツール群**です。主な機能は次の三つです。

1. **メッシュ生成＋標高付与** – 計算領域ポリゴンと流域界ポリゴンを同じセル数でグリッド化し、点群データから平均標高を算出してメッシュに書き込みます【8777747444581†L3-L5】。
2. **メッシュ属性代表値付与** – 基準メッシュと属性メッシュを重ね、各セル内で面積割合が最大の属性値を代表値として付与します【365323462916918†L24-L26】。
3. **Shapefile→ASCII Grid変換** – 属性付きシェープファイルを ESRI ASCII グリッド（`.asc`）に変換します。グリッド数は入力シェープファイルの形状から自動計算されます【128855128016211†L100-L104】。

## サンプルデータセット

リポジトリの `data` または `input` ディレクトリにサンプルデータが置かれている場合があります。社内共有フォルダなどに配置されていることもあるので、管理者に確認してください（例：`\\z101070380\\fujimoto\\RRI-dataset\\DEM\\sample`）。

## ダウンロードと実行手順（ユーザ向け）

### リリース版のダウンロード

GUI で簡単に実行したい場合は、GitHub の [Releases](https://github.com/Pckk-solvers/shp_to_asc_converter/releases) ページに公開されている最新リリースをご利用ください。ページの「Assets」から zip ファイル（例: `shp_to_asc_converter_v1.2.3.zip`）をダウンロードし、お使いのPCに展開します。

展開後、フォルダ内の `.exe` ファイルをダブルクリックすると、ランチャーGUIが起動します。次の三つの機能を選択して実行できます。

* **メッシュ生成と標高付与**
  計算領域シェープファイル(.shp)、流域界シェープファイル(.shp)、点群データ(CSV/SHP)を指定し、セル数やNODATA値を設定して実行します。
* **Shapefile → ASCII グリッド**
  入力シェープファイル(.shp)と属性フィールド名、出力先ASCII(.asc)ファイル名を指定して実行します。
* **代表属性値付与**
  基準メッシュ(.shp)と属性メッシュ(.shp)、属性フィールド名、出力フィールド名、閾値、NODATA値を指定して実行します。

### Python 環境での実行

Python がインストールされた環境であれば、CLI から直接実行できます。以下はリポジトリをクローンした上での例です。

```bash
git clone https://github.com/Pckk-solvers/shp_to_asc_converter.git
cd shp_to_asc_converter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# メッシュ生成と標高付与
python run.py --domain-shp input/domain.shp \
              --basin-shp input/basin.shp \
              --points-csv input/points.csv \
              --cells-x 100 \
              --cells-y 100 \
              --nodata -9999 \
              --out-dir outputs

# Shapefile→ASCII変換
python -m src.shp_to_asc.core shp_to_ascii input/domain.shp elevation outputs/domain.asc

# 代表属性値付与
python -m src.mesh_dominant_module.mesh_dominant \
       --base input/base_mesh.shp \
       --land input/land_mesh.shp \
       --source-field landuse \
       --output-field dominant_value \
       --threshold 0.5 \
       --nodata -9999 \
       --output outputs/base_dominant.shp
```

## 開発者ガイド

* **依存関係**: `geopandas`, `pandas`, `shapely`, `fiona`, `rasterio` など。
* **モジュール構成**:

  ```
  src/
   ┣ shp_to_asc/          ← ASC 変換コアモジュール
   ┃ ┗ core.py            ← `analyze_grid_structure`, `shp_to_ascii` 実装
   ┣ make_shp/            ← メッシュ生成＋標高付与モジュール
   ┃ ┣ generate_mesh.py   ← グリッド化処理
   ┃ ┣ add_elevation.py    ← 平均標高算出・付与
   ┃ ┗ pipeline.py        ← 一括実行スクリプト
   ┣ mesh_dominant_module/ ← 属性代表値付与モジュール
   ┃ ┣ mesh_dominant.py    ← 洗い出し・代表値計算
   ┃ ┗ mesh_dominant_gui.py← GUI 連携
   ┗ app.py               ← Tkinter ランチャー
  ```
* **テスト**: `pytest` でユニットテストを追加。CI で自動実行。
* **コーディング規約**: PEP8 準拠、型ヒント推奨。
