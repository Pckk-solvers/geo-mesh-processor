# shp\_to\_asc\_converter

シェープファイル（Shapefile）の **加工・変換** をワンストップで行う Python ツール集です。主な機能は以下の 3 つです。

* **メッシュ生成＋標高付与**
  計算領域ポリゴンと流域界ポリゴンを同じセル数でグリッド化し、点群データから平均標高を算出してメッシュに書き込みます。
  \[[GitHub](https://github.com/Pckk-solvers/shp_to_asc_converter/tree/main/src/make_shp)]
* **メッシュ属性代表値付与**
  基準メッシュと属性メッシュを重ね、各セル内で面積割合が最大の属性値を代表値として付与します。
  \[[GitHub](https://github.com/Pckk-solvers/shp_to_asc_converter/tree/main/src/mesh_dominant_module)]
* **Shapefile → ASCII Grid 変換**
  属性付きシェープファイルを ESRI ASCII Grid（.asc）へ変換します。グリッド数は入力シェープファイルの形状から自動計算されます。
  \[[GitHub](https://github.com/Pckk-solvers/shp_to_asc_converter/tree/main/src/shp_to_asc)]

以下では **ユーザ向け** と **開発者向け** に分けて使い方を説明します。

---

## 主な機能一覧

| 機能                     | 概要                                                           | 対象スクリプト / GUI                                                                                                |
| ---------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| メッシュ生成＋標高付与            | 計算領域ポリゴンをグリッド化し、流域界ポリゴンでトリムした後、点群 CSV/SHP から平均標高を計算してメッシュに付与 | `src/make_shp/pipeline.py` (CLI)  <br>`src/make_shp/mesh_elev_gui.py` (GUI)                                  |
| メッシュ属性代表値付与            | 基準メッシュと属性メッシュを重ね、各セル内で面積割合が最大の属性値を代表値として付与（閾値未満は NODATA）     | `src/mesh_dominant_module/mesh_dominant.py` (CLI)  <br>`src/mesh_dominant_module/mesh_dominant_gui.py` (GUI) |
| Shapefile → ASCII Grid | ポリゴンデータを指定属性で ESRI ASCII Grid へラスター化。グリッド数は自動計算              | `src/shp_to_asc/core.py` (ライブラリ)  <br>`src/shp_to_asc/gui.py` (GUI)                                          |

---

## サンプルデータセット

サンプルはリポジトリの `data/` または `input/` ディレクトリに配置されています。社内共有フォルダ内に置かれている場合もあるため、管理者へご確認ください。例: `\\z101070380\fujimoto\RRI-dataset\DEM\sample`。

---

## ダウンロードと実行手順（ユーザ向け）

### 1. リリース版のダウンロード

1. GitHub の **Releases** ページから最新リリースを開く。
2. **Assets** にある Windows 用 zip（例: `shp_to_asc_converter_x.y.z_win.zip`）をダウンロード。
3. 任意のフォルダに解凍し、含まれる `.exe` をダブルクリックで **Tkinter ランチャー** を起動。

### 2. ランチャーで選択できるツール

* **メッシュ生成＋標高付与** — 計算領域 SHP・流域界 SHP・点群 CSV/SHP を選択し、セル数や NODATA 値を指定して実行。
* **Shapefile → ASCII 変換** — 入力 SHP と属性フィールドを選択し、出力先 `.asc` と NODATA 値を指定して実行。
* **代表属性値付与** — 基準メッシュと属性メッシュを選択し、属性フィールド名・出力フィールド名・閾値・NODATA 値を入力して実行。

---

## Python 環境での実行（CLI）

### 1. 仮想環境のセットアップ

```bash
git clone https://github.com/Pckk-solvers/shp_to_asc_converter.git
cd shp_to_asc_converter
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
pip install -r requirements.txt
```

### 2. メッシュ生成＋標高付与

```bash
python src/make_shp/pipeline.py \
  --domain path/to/domain_polygon.shp \
  --basin  path/to/basin_polygon.shp \
  --cells_x 100 --cells_y 100 \
  --points path/to/elevation_points.csv \
  --zcol elevation \
  --outdir ./outputs
```

### 3. メッシュ属性代表値付与

```bash
python src/mesh_dominant_module/mesh_dominant.py \
  --base path/to/domain_mesh_elev.shp \
  --land path/to/landuse_mesh.shp \
  --source-field landuse \
  --output-field dominant_value \
  --threshold 0.5 \
  --nodata -9999 \
  --output result_dominant.shp
```

### 4. Shapefile → ASCII Grid（ライブラリ呼び出し）

```python
from src.shp_to_asc.core import shp_to_ascii

ncols, nrows, dx, dy = shp_to_ascii(
    shp_path="path/to/polygon.shp",
    field="value_field",
    output_path="output.asc",
    nodata=-9999
)
print(f"grid: {ncols} cols × {nrows} rows, cell size dx={dx}, dy={dy}")
```

---

## よくある質問（FAQ）

<details>
<summary>CSV に <code>x</code> と <code>y</code> 列が無いと言われる</summary>

点群 CSV から X / Y 列を自動検出する際、`x`/`y` または `lon`/`lat` 列を参照します。該当列が無い場合はエラーになるため、列名を修正するか SHP 形式を使用してください。

</details>

<details>
<summary>標高列が複数ある場合どれが使われる？</summary>

`--zcol` オプションで列名を明示しない場合、数値型の列が **1 つだけ** ならそれが使用されます。複数ある場合は `--zcol` を指定してください。

</details>

<details>
<summary>CRS 不一致エラー</summary>

`mesh_dominant.py` は基準メッシュと属性メッシュの CRS が一致している必要があります。異なる場合は `to_crs()` で統一してから実行してください。

</details>

<details>
<summary>出力がすべて NODATA になる</summary>

基準メッシュと属性メッシュが交差しない場合、全セルが NODATA になります。入力データの範囲や閾値設定を確認してください。

</details>

---

## 開発者向けガイド

### 想定環境

* **Python** ≥ 3.12
* **主要ライブラリ**: `geopandas`, `pandas`, `shapely`, `rasterio`, `pyproj`, `fiona` ほか
* **Git**: clone / branch / PR の基本操作

### セットアップ

```bash
git clone https://github.com/Pckk-solvers/shp_to_asc_converter.git
cd shp_to_asc_converter
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

### パッケージ構成

```text
├─ src/
│  ├─ app.py                  # Tkinter ランチャー
│  ├─ shp_to_asc/             # Shapefile → ASCII 変換
│  ├─ make_shp/               # メッシュ生成・標高付与
│  └─ mesh_dominant_module/   # メッシュ属性代表値付与
├─ notebooks/                 # 設計資料
└─ tests/                     # テスト
```

### 開発の流れ

1. **Issue 登録**: バグ報告・機能提案はまず Issue へ。
2. **ブランチ作成**: `feature/xxx` で開発を開始。
3. **動作確認**: ローカルでサンプルデータを用いてテスト。
4. **Pull Request**: テスト OK を確認後、main へ PR。

### リリースとバージョニング

大きな変更時に GitHub の **Release** でタグを作成し、PyInstaller で Windows 用実行ファイルをビルドします。ビルドオプションのメモは `notebooks/pyinstaller用.txt` にあります。

---

## ライセンス

MIT License で公開しています。詳細は `LICENSE` ファイルを参照してください。
