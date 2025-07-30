# 実装計画：メッシュ属性代表値付与機能（8時間想定）

以下の要件定義をもとに、`app.py` のランチャーから呼び出せるモジュール実装の計画を、合計**8時間**で完了する想定でまとめました。

## 1. 機能要件

* **機能名**：メッシュへ指定属性代表値付与
* **目的**：基準メッシュに対し、属性メッシュの指定フィールド値をセル内面積割合の最大値で選択し、出力メッシュに付与する
* **入力／出力パラメータ**：

  * `--base` : 基準メッシュ（Shapefile）
  * `--land` : 属性メッシュ（Shapefile）
  * `--source-field`（デフォルト `landuse`）
  * `--output-field`（デフォルト `dominant_value`）
  * `--threshold`（デフォルト `0.5`）
  * `--nodata`（デフォルト `-9999`）
  * `--output` : 出力ファイル名（Shapefile）

## 2. モジュール構成

```
src/
 ┣ mesh_dominant_module/
 ┃ ┣ mesh_dominant.py        ← コア処理モジュール
 ┃ ┣ mesh_dominant_gui.py    ← GUI連携モジュール
 ┃ ┗ __init__.py             ← パッケージ初期化
```

※ 本機能は既存モジュールから完全に独立した形で管理します。

## 3. `mesh_dominant.py` 詳細設計

* **関数**：

  ```python
  def assign_dominant_values(
        base_path: str,
        land_path: str,
        source_field: str,
        output_field: str,
        threshold: float,
        nodata: Any,
        output_path: str
  ) -> None:
      """
      - Shapefile 読込 (GeoDataFrame)
      - mesh_id 自動付与
      - `overlay(..., how='intersection')`
      - 面積計算・集計 → `ratio`
      - 最大割合代表値抽出 (同率は先出し)
      - 閾値以下は `nodata`
      - Shapefile 出力
      """
  ```
* **例外処理**：CRS不一致・フィールド不存在・Intersectionゼロ行等

## 4. `mesh_dominant_gui.py` 詳細設計

* **UI要素**：

  * 基準メッシュ選択、属性メッシュ選択
  * プルダウン：`source_field` 候補一覧
  * 入力：`output_field`、`threshold`、`nodata`
  * 実行ボタン → `assign_dominant_values` 呼び出し
  * ステータス表示・完了ダイアログ

## 5. `app.py` への統合

1. `import MeshDominantApp`
2. ランチャーボタン追加
3. `open_mesh_dominant` メソッド実装

## 6. テスト計画

* **ユニットテスト**（pytest）

  * CRS一致／不一致
  * 同率ケース
  * 閾値境界・Intersectionゼロ行
* **サンプルデータ検証**：小規模メッシュで自動CI

## 7. スケジュール（合計 8時間）

| タスク                          | 時間      |
| ---------------------------- | ------- |
| 1. 仕様調整・詳細設計                 | 1時間     |
| 2. `mesh_dominant.py` 実装     | 2時間     |
| 3. CLIテスト・ドキュメント整備           | 1時間     |
| 4. `mesh_dominant_gui.py` 実装 | 2時間     |
| 5. GUI統合・`app.py`連携          | 1時間     |
| 6. ユニットテスト・CI連携              | 1時間     |
| **合計**                       | **8時間** |
