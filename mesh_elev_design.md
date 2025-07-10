
# メッシュ生成＋標高付与プロセス設計書

## 1. 概要
本設計書は、計算領域ポリゴンを任意セルサイズでグリッド化し、流域界ポリゴンでトリムした後、点群 CSV から平均標高を算出してメッシュに付与する一連の処理フローをまとめたものです。  
処理は **「メッシュ生成」** と **「標高付与」** の2段構成とし、CLI スクリプトで実装します（GUI はラッパとして後付け可能）。

## 2. 入力データ

| ファイル | 内容 | 必須条件 |
|----------|------|----------|
| `domain_polygon.shp` | 計算領域（矩形でなくても可） | 投影座標系（距離が m 単位で扱える） |
| `basin_polygon.shp`  | 流域界ポリゴン | CRS は自動で `domain` に合わせる |
| `elevation_points.csv` | 3 列以上の点群 (x, y, z) | `x` / `y` 列は必須、z 列は自動判定 |

### CSV 列判定ロジック
1. `x` または `X` 列、`y` または `Y` 列を必須とする  
2. z 列は以下の優先順で 1 列を採用  
   - `z`, `Z`, `elev`, `elevation`, `height`  
   - 上記が無い場合は **x/y 以外の最初の列**

## 3. 出力データ

| ファイル | 内容 |
|----------|------|
| `domain_mesh.shp`        | 計算領域全体の矩形メッシュ |
| `basin_mesh.shp`         | 流域界でトリムしたメッシュ |
| `basin_mesh_elev.shp`    | 流域メッシュ + 平均標高列 |
| `domain_mesh_elev.shp`   | 計算領域メッシュ + 標高列 (流域外は -9999) |

## 4. 共通パラメータ

| パラメータ | 説明 | 既定値 |
|------------|------|--------|
| `cell_size` | セル一辺長 (m 等) | CLI で必須指定 |
| `NODATA`    | 標高が無いセルに入れる値 | `-9999` |
| `CRS`       | 入力すべてを `domain_polygon` の CRS に統一 | ― |

## 5. 処理フロー

```
domain_polygon.shp ─┐
                    ├─▶ generate_mesh.py ──▶ domain_mesh.shp
basin_polygon.shp ──┘            │
                                   └─▶ basin_mesh.shp
                                                 │
elevation_points.csv ─┐                         │
                      └─▶ add_elevation.py ─────┘
                             │                 │
                  basin_mesh_elev.shp   domain_mesh_elev.shp
```

## 6. 処理詳細

### 6.1 メッシュ生成 `generate_mesh.py`
| ステップ | 具体処理 |
|----------|----------|
| 1 | `domain_polygon`, `basin_polygon` 読込 (`geopandas.read_file`) |
| 2 | **グリッド生成**: `np.arange(minx, maxx, cell_size)` 等でセルを作成<br>  原点は *minx / miny* に揃える（デフォルト） |
| 3 | **クリップ**: `geopandas.overlay(grid, basin, how="intersection")` |
| 4 | `domain_mesh.shp`, `basin_mesh.shp` へ保存 |

CLI 例:
```bash
python generate_mesh.py --domain domain_polygon.shp \
                        --basin basin_polygon.shp \
                        --cell 50 \
                        --outdir ./outputs
```

### 6.2 標高付与 `add_elevation.py`
| ステップ | 具体処理 |
|----------|----------|
| 1 | `basin_mesh`, `domain_mesh`, `elevation_points.csv` 読込 |
| 2 | **CSV 列判定**（前述ロジック）→ `GeoDataFrame` 化 |
| 3 | `gpd.sjoin(points, basin_mesh, predicate="within")` で点をポリゴンに帰属 |
| 4 | `groupby("index_right").mean()` でポリゴン平均標高を計算 |
| 5 | `basin_mesh["elev"]` に書込み、`domain_mesh` へ転記 (外部セル `-9999`) |
| 6 | 結果を `basin_mesh_elev.shp`, `domain_mesh_elev.shp` に保存 |

CLI 例:
```bash
python add_elevation.py --basin_mesh ./outputs/basin_mesh.shp \
                        --domain_mesh ./outputs/domain_mesh.shp \
                        --points elevation_points.csv \
                        --outdir ./outputs
```

## 7. 簡易 GUI (PySimpleGUI) 概要

| UI | 説明 |
|----|------|
| ファイル選択 (3 つ) | - `Domain SHP`<br>- `Basin SHP`<br>- `Points CSV` |
| セルサイズ入力 | `InputText` (float) |
| 出力フォルダ選択 | `FolderBrowse` |
| Run ボタン | 内部で上記 2 スクリプトを順に `subprocess` 実行 |
| 実行結果表示 | `popup` で完了／エラーを通知 |

> **備考**: GUI はファイルパス・パラメータを受け取って CLI を呼ぶシンプル構成。> 進捗バーやログ出力ウィンドウは拡張で追加可能。

## 8. エラーハンドリング

| ケース | 対応 |
|--------|------|
| CSV に `x/y` 列が無い | `ValueError` を投げ GUI でダイアログ表示 |
| z 列が判定できない | 同上 |
| CRS 不一致 | 自動 `to_crs()`、失敗時はエラー |
| 出力フォルダ未作成 | `Path.mkdir(parents=True, exist_ok=True)` |

## 9. 拡張案（今後）

- **セル起点スナップ/ユーザ指定** `--origin snap / --origin_x --origin_y`  
- **巨大点群対応** Dask-GeoPandas または PostGIS 版  
- **GeoPackage 出力** 同一ファイル多レイヤ管理  
- **QGIS プラグイン化** 既存アルゴリズムラップ + UI

---

以上。
