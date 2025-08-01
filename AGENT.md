# AGENT.md — PyQt への移植 / GUI 統合・運用ガイド

このドキュメントは、Tkinter ベースの GUI ツール群を **PyQt** に移植し、両 UI を併存させながら運用・拡張するための作業手順とチェックリストをまとめたものです。

---

## 1. 目的と背景（Scope）
- 既存の Tkinter 依存を解消し、**モダンで拡張性の高い UI** を PyQt で提供する。
- Tkinter 版を残しつつ、**PyQt 版を並行運用**して段階的に移行できるようにする。

## 2. 対象リポジトリの構成（関連部分）
```
src/
├─ app.py                      # Tkinter 版ランチャー
├─ app2.py                     # Tkinter 版（追加実装）
├─ qt_app.py                   # PyQt 版エントリポイント
└─ qt_gui/                     # PyQt 版 GUI モジュール
   ├─ main_launcher.py         # PyQt ランチャー
   ├─ shp_to_asc_window.py     # Shapefile→ASCII 変換ウィンドウ
   ├─ mesh_gen_window.py       # メッシュ生成ウィンドウ
   ├─ elev_assigner_window.py  # 標高付与ウィンドウ
   └─ mesh_dominant_window.py  # 代表値付与ウィンドウ
```

### 各モジュールの役割（要点）
- **main_launcher.py**: 各ツールを起動するボタンを配置。新規ウィンドウとして開く。
- **shp_to_asc_window.py**: Shapefile 選択、属性フィールド選択、NODATA 設定、出力ファイル指定。バックグラウンドで `shp_to_ascii` 実行。
- **mesh_gen_window.py**: 計算領域/流域界 SHP、セル数、出力フォルダ、標準メッシュ・ID 列を指定し `generate_mesh` をスレッド実行。
- **elev_assigner_window.py**: 計算領域メッシュ・流域メッシュ・点群 CSV/SHP（複数）・標高列・NODATA・出力フォルダを設定し `add_elevation` を実行。CSV 先頭 100 行から X/Y 列を検出し、Z 列候補を提示。
- **mesh_dominant_window.py**: 基準メッシュ＋属性メッシュを読み込み、属性フィールド・出力名・閾値・NODATA・出力ファイルを指定して `assign_dominant_values` を実行。属性メッシュからカラム一覧を取得して候補表示。

> 補足: PyQt 側では `QThread` 派生のバックグラウンド実行クラスを用意し、UI のブロックを回避。進捗はラベルで通知。

## 3. セットアップ（依存関係）
- Python（プロジェクトの既定バージョンに合わせる）
- ライブラリ: `PyQt5` ほかプロジェクト標準の requirements.txt を利用  
  ```bash
  pip install PyQt5
  ```

## 4. 起動方法（ランチャー）
- **PyQt 版**: リポジトリ直下で以下を実行  
  ```bash
  python src/qt_app.py
  ```
- **Tkinter 版**: 従来どおり  
  ```bash
  python src/app.py
  ```

## 5. 作業タスク（進捗と Backlog）
### ✅ 完了済み
- `src/qt_gui/` を新設し、PyQt 版の各ウィンドウを分割実装。
- `src/qt_app.py` をエントリポイントとして追加し、ランチャーから各ツールを起動。
- `QThread` による非ブロッキング実行と簡易進捗表示（ラベル）。
- Tkinter 版は現状維持し、**併存運用**を可能に。

### ⏳ 今後の拡張（Backlog）
- **スタイル統一**: Qt Style Sheets による共通テーマの適用。
- **進捗バーの実装**: 長時間処理に `QProgressBar` を導入。
- **エラーメッセージ整備**: 例外メッセージの日本語化・ユーザ向け要約。

## 6. 動作確認チェックリスト（各ツール共通）
- [ ] ランチャー起動（PyQt 版 / Tkinter 版）。
- [ ] 各ウィンドウが新規に開く（ランチャーがブロックされない）。
- [ ] 必須入力のバリデーション（パス未指定、フィールド未選択など）。
- [ ] 実行時に UI が応答し続ける（`QThread` / スレッド実行）。
- [ ] 進捗・ステータスメッセージが更新される。
- [ ] 正常終了ダイアログ（または明確なエラーダイアログ）が表示される。
- [ ] 出力ファイルの存在／内容（件数・フィールド）を確認。

### ツール別の追加チェック
**shp_to_asc_window.py**
- [ ] NODATA 値が反映される。
- [ ] 属性フィールド選択が出力に反映される。

**mesh_gen_window.py**
- [ ] 入力 SHP（領域/流域界）・セル数・出力ディレクトリ・標準メッシュ/ID 指定が妥当。
- [ ] 生成メッシュのセル数・ID 付与を確認。

**elev_assigner_window.py**
- [ ] 複数 CSV/SHP の取り込みと Z 列候補提示（X/Y 自動検出）を確認。
- [ ] NODATA の正しい伝播。

**mesh_dominant_window.py**
- [ ] 属性メッシュのカラム一覧取得と選択 UI。
- [ ] `threshold` 未満/以上での割り当て結果、NODATA の付与を確認。

## 7. 受け入れ基準（Definition of Done）
- [ ] 上記チェックリストを全て満たす。
- [ ] 主要ユースケースの実データでの E2E 試験に合格。
- [ ] 例外時のメッセージがユーザにとって理解可能。

## 8. 運用メモ
- 併存期間中は **PyQt 版を優先的に改善**。Tkinter 版は互換性維持に留める。
- 例外ログは（仮）`logs/` 配下に集約する方針。必要に応じてハンドラ整備。

## 9. リリース手順（例）
1) `requirements.txt` を最新化（`PyQt5` を明記）。  
2) `CHANGELOG.md` に差分を追記。  
3) バージョンタグ付与 → アーティファクト配布（必要に応じて）。

## 10. ロールバック方針
- クリティカル不具合時は Tkinter 版（`src/app.py`）の利用を告知し暫定対応。

## 11. 連絡先 / 担当
- オーナー: （記入）
- レビュアー: （記入）

---

### 付録: コマンド早見表
```bash
# 依存関係の導入
pip install -r requirements.txt
pip install PyQt5

# ランチャー起動
python src/qt_app.py   # PyQt 版
python src/app.py      # Tkinter 版
```
