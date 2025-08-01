
# AGENT.md — PyQt への移植・運用 **実行ガイド（アクション指示付き）**

このドキュメントは「**何を・どの順で・どう実装するか**」を明確にした**実行指示書**です。  
目的は、Tkinter ベースの既存 GUI を **PyQt へ段階移行**しつつ、当面は **Tkinter と併存**して運用することです。

---

## 0. 前提と用語
- **PyQt 版**: `src/qt_app.py` と `src/qt_gui/` を起点とする新 UI 実装
- **Tkinter 版**: 既存 `src/app.py` (および `app2.py`)。ロールバック先として維持
- **ワーカー**: 長時間処理を UI ブロックせず実行するバックグラウンド実行クラス（`QThread` 派生）

---

## 1. 今すぐ着手するタスク（Next Actions）
> 本セクションは**必須の実作業リスト**です。上から順に対応してください。

1. **依存ライブラリ方針の固定**
   - `requirements.txt` に `PyQt5` を追記（固定バージョン推奨）。
   - 可能なら `wheelhouse/` を用意し、`pip install --no-index --find-links=wheelhouse -r requirements.txt` で**社内/閉域でも再現**できるようにする。
   - プロジェクト外のグローバル環境に依存しない（**ポータブル venv + runスクリプト**運用）。

2. **起動スクリプト（Windows）を整備**
   - ルートに `go.bat`（初回セットアップ＋起動）と `run.bat`（2回目以降の起動）を置く。
   - 処理内容（疑似コード）:
     ```bat
     REM go.bat（初回）
     if not exist .venv (
       py -3 -m venv .venv
     )
     call .venv\Scripts\activate
     python -m pip install --upgrade pip
     if exist wheelhouse (
       pip install --no-index --find-links=wheelhouse -r requirements.txt
     ) else (
       pip install -r requirements.txt
     )
     python src\qt_app.py
     ```
     ```bat
     REM run.bat（2回目以降）
     call .venv\Scripts\activate
     pip install -r requirements.txt  REM 依存差分のみ解決
     python src\qt_app.py
     ```

3. **共通ワーカークラスを追加（UI 非ブロッキングの標準化）**
   - 追加ファイル: `src/qt_gui/core/worker.py`
   - 役割: `QThread` or `QRunnable` ベースで「実行・完了・失敗（例外）」シグナルを標準化。
   - 例（骨子）:
     ```python
     # src/qt_gui/core/worker.py
     from PyQt5.QtCore import QThread, pyqtSignal

     class Worker(QThread):
         progress = pyqtSignal(str)     # ステータスメッセージ
         finished = pyqtSignal(object)  # 結果オブジェクト
         failed   = pyqtSignal(str)     # 例外メッセージ

         def __init__(self, fn, *args, **kwargs):
             super().__init__()
             self._fn = fn
             self._args = args
             self._kwargs = kwargs

         def run(self):
             try:
                 self.progress.emit("開始")
                 result = self._fn(*self._args, **self._kwargs)
                 self.finished.emit(result)
             except Exception as e:
                 self.failed.emit(str(e))
     ```

4. **PyQt ランチャーを最小実装で立ち上げ**
   - 追加/確認: `src/qt_app.py`, `src/qt_gui/main_launcher.py`
   - ランチャーは**各ウィンドウを別インスタンスで開く**（ブロックしない）。

5. **優先ウィンドウの移植順（段階移行）**
   - ① `mesh_dominant_window.py`（ユーザー需要と不具合報告が多い領域）
   - ② `shp_to_asc_window.py`
   - ③ `mesh_gen_window.py`
   - ④ `elev_assigner_window.py`
   - 各ウィンドウから**共通ワーカー**を利用するよう差し替え。

6. **ログの標準化**
   - 追加: `src/common/logging_conf.py`  
   - ログ出力先: `logs/app_%Y%m%d.log`（ローテーション）  
   - UI には「概要（INFO）」、ログには「詳細（DEBUG）」を出す方針。

7. **例外メッセージの整備（ユーザ向け和文化）**
   - 技術詳細はログ、UI は要点＋原因候補＋次の一手（ファイル選択誤り/CRS 未一致 等）を表示。

---

## 2. 変更差分（コード指示）
**A. ディレクトリ**
```
src/
├─ qt_app.py
├─ qt_gui/
│  ├─ main_launcher.py
│  ├─ core/
│  │  └─ worker.py        # ← 新規（共通ワーカー）
│  ├─ mesh_dominant_window.py
│  ├─ shp_to_asc_window.py
│  ├─ mesh_gen_window.py
│  └─ elev_assigner_window.py
├─ common/
│  └─ logging_conf.py     # ← 新規（標準ログ設定）
└─ ...
```

**B. ランチャー骨子（抜粋）**
```python
# src/qt_app.py
from PyQt5.QtWidgets import QApplication
from qt_gui.main_launcher import MainLauncher
import sys

def main():
    app = QApplication(sys.argv)
    w = MainLauncher()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
```

**C. ウィンドウ → ワーカー連携（典型パターン）**
```python
# 例: src/qt_gui/mesh_dominant_window.py（概念）
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout
from qt_gui.core.worker import Worker
from mesh_dominant import assign_dominant_values  # 既存ロジックをそのまま呼ぶ

class MeshDominantWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.btn = QPushButton("実行")
        self.status = QLabel("待機中")
        self.btn.clicked.connect(self.run_job)
        lay = QVBoxLayout(self); lay.addWidget(self.btn); lay.addWidget(self.status)

    def run_job(self):
        # TODO: 入力値のバリデーション
        self.worker = Worker(assign_dominant_values,
                             base_path="...", land_path="...", source_field="landuse",
                             output_field="dominant_value", threshold=0.5, nodata=-9999)
        self.worker.progress.connect(self.status.setText)
        self.worker.finished.connect(lambda _: self.status.setText("完了"))
        self.worker.failed.connect(lambda msg: self.status.setText(f"失敗: {msg}"))
        self.worker.start()
```

---

## 3. バリデーション規約（全ウィンドウ共通）
- ファイル/フォルダ選択: 存在・拡張子・アクセス権限をチェック
- フィールド選択: 存在確認、空/欠損時の警告
- 数値入力: 範囲（例: `threshold ∈ [0,1]`、セル数>0）
- CRS 要件: 面積計算前に**平面直角座標系**へ変換 → 終了時に元へ戻す
- NODATA: 入力受け取りと**出力への確実な伝播**
- 長時間処理: UI 非ブロッキング、キャンセルボタン（将来対応）

---

## 4. UI/UX 規約（最小）
- 基本構成: 入力（グループ化）→ 実行 → 進捗 → 結果/エラー
- 進捗表示: ラベル必須、将来 `QProgressBar`（比率が出せる処理のみ）
- メッセージ: 1文目に**要点**、2文目に**原因候補**、3文目に**推奨行動**
- 設定の復元: 直近の選択パス/値を保存（`~/.config/<app>/settings.json` 等）

---

## 5. 受け入れ条件（Definition of Done）
- [ ] 上記 **Next Actions 1〜7** を実装し、`mesh_dominant_window.py` が PyQt で動作
- [ ] 主要ウィンドウで **非ブロッキング実行**（共通ワーカー利用）
- [ ] 正常終了/失敗時の**ユーザ向けメッセージ**が適切
- [ ] 出力ファイル/属性の**自動テスト or スモークチェック**が通る
- [ ] `go.bat` / `run.bat` により**新規PCでも起動**できる

---

## 6. ブランチ運用・PR チェックリスト
- ブランチ命名: `feat/qt-<window>`、`chore/qt-setup`、`fix/qt-<issue>`
- コミット: Conventional Commits 準拠（例: `feat(qt): add common worker`）
- PR テンプレ
  - [ ] 動作確認手順（スクショ/動画歓迎）
  - [ ] 影響範囲（モジュール/外部 I/F）
  - [ ] リスクとリリース手順（ロールバック含む）
  - [ ] ユーザ向け変更点（必要なら CHANGELOG 追記）

---

## 7. テスト方針（最低限）
- **スモークテスト**: 代表入力で各ウィンドウを起動→実行→出力の存在確認
- **構成テスト**: 設定ファイルの保存/復元、NODATA の伝播確認
- 余力があれば `pytest-qt` でイベント駆動の単体テストを拡張

---

## 8. リリース・ロールバック手順
- リリース:
  1) `requirements.txt` 更新 → `go.bat`/`run.bat` 配布
  2) `CHANGELOG.md` に PyQt 版の変更点を記載
  3) 重要: 不具合時の連絡先/回避策（Tkinter 版起動）を README/AGENT に明記
- ロールバック:
  - PyQt 停止 → `src/app.py`（Tkinter）で運用継続
  - 依存ライブラリは **非破壊**（Tkinter 版の実行に支障が出ない構成）

---

## 9. 保守の指針
- **PyQt 版を優先改善**、Tkinter 版はバグ修正と互換維持に限定
- ワーカー/ログ/メッセージなどの**共通部品化**を先に行い、各ウィンドウへ展開
- 依存ライブラリは**上げ過ぎない**（運用安定重視）。アップデートは四半期単位で検討

---

## 付録 A: 参考コマンド
```bash
# 初回（go.bat 内と同等）
py -3 -m venv .venv
.\.venv\Scriptsctivate
pip install --upgrade pip
pip install -r requirements.txt
python src\qt_app.py

# 2回目以降（run.bat 内と同等）
.\.venv\Scriptsctivate
pip install -r requirements.txt
python src\qt_app.py
```

## 付録 B: 想定 FAQ（運用）
- Q: Python が入っていない端末は？  
  A: 原則サポート外。必要時は「ポータブル Python + .venv」を別途検討。
- Q: CRS が違うデータを混在させたら？  
  A: ウィンドウ内で変換ガード（平面直角座標に統一→処理→元へ戻す）を実装。
- Q: NODATA が `None` 化される/文字列混在の列が壊れる？  
  A: 型付けを最後に強制整形（`astype(str)`／`fillna(nodata)`）し、書き出し前に検査。

---

**オーナー**: （記入） / **レビュアー**: （記入） / **最終更新**: 自動生成（この AGENT.md を修正したら日付更新）
