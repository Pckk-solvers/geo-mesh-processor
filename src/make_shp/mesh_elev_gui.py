#!/usr/bin/env python3
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
import queue
import tkinter.font as tkFont
import os
import sys

from src.make_shp.add_elevation import get_xy_columns, get_z_candidates
from src.make_shp.pipeline import pipeline

# ── 実行モード判別 ──
# - PyInstaller の exe 化時には _MEIPASS に資源が展開される
# - スクリプト実行時にはこのファイルのある場所から project root (= 上２階層) を参照
BASE_DIR = getattr(
    sys, '_MEIPASS',
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',  # src/make_shp のひとつ上 → src
            '..'   # src のひとつ上 → プロジェクトルート
        )
    )
)

# data フォルダをプロジェクトルート直下に置く想定
STANDARD_MESH = os.path.join(BASE_DIR, 'data', 'standard_mesh.shp')
MESH_ID       = None

class MeshElevApp(ttk.Frame):
    def __init__(self, master, initial_values=None):
        """
        初期化
        
        Args:
            master: 親ウィジェット
            initial_values (dict): 初期値設定用の辞書。以下のキーを指定可能
                - domain_shp: 計算領域シェープファイルパス
                - basin_shp: 流域界シェープファイルパス
                - points_csv: 点群CSVファイルパス（複数可、リストまたはセミコロン区切り）
                - zcol: 標高値列名
                - cells_x: X方向セル数
                - cells_y: Y方向セル数
                - nodata: NODATA値
                - out_dir: 出力ディレクトリ
        """
        super().__init__(master)
        master.title('メッシュ生成と標高付与ツール')
        self.initial_values = initial_values or {}

        # ── メインフレーム(self) をルートに配置 ──
        # row=0, column=0 のセルに sticky で全方向展開
        self.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        # ── self（フレーム） 内部のリサイズ設定 ──
        # PanedWindow を置いている column=0 を伸縮対象に
        self.columnconfigure(0, weight=1)
        # 行０～? まで rowspan しているので、row=0 に余白を割り当て
        self.rowconfigure(0, weight=1)

        # ウィジェット生成（ここで PanedWindow → left_frame/help_frame を構築）
        self.create_widgets()
        
        # 初期値の設定
        self._set_initial_values()
        
        self.master.update_idletasks()
        self.master.minsize(self.master.winfo_width(), self.master.winfo_height())
        
        # 1) Queue を作成
        self.result_queue = queue.Queue()
        # 2) 定期的に結果をチェックするコールバックを登録
        self.after(100, self.check_queue)
        
    def _set_initial_values(self):
        """初期値を設定する"""
        if not self.initial_values:
            return
            
        # 各ウィジェットに初期値を設定
        if 'domain_shp' in self.initial_values:
            self.domain_var.set(self.initial_values['domain_shp'])
        if 'basin_shp' in self.initial_values:
            self.basin_var.set(self.initial_values['basin_shp'])
        if 'points_csv' in self.initial_values:
            points = self.initial_values['points_csv']
            if isinstance(points, list):
                points = ";".join(points)
            self.points_var.set(points)
            self._update_z_candidates(points.split(';') if ';' in points else [points])
        if 'zcol' in self.initial_values:
            self.z_var.set(self.initial_values['zcol'])
        if 'cells_x' in self.initial_values:
            self.cells_x_var.set(str(self.initial_values['cells_x']))
        # if 'cells_y' in self.initial_values:
        #     self.cells_y_var.set(str(self.initial_values['cells_y']))
        if 'nodata' in self.initial_values:
            self.nodata_var.set(str(self.initial_values['nodata']))
        if 'out_dir' in self.initial_values:
            self.outdir_var.set(self.initial_values['out_dir'])
            
    def create_widgets(self):
        # ── PanedWindow で左右分割 ──
        paned = ttk.PanedWindow(self, orient='horizontal')
        paned.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # ── 左ペイン：入力項目用フレーム ──
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=0)   # weight=0 → 固定幅

        # ── 右ペイン：ヘルプガイド用フレーム ──
        help_frame = ttk.LabelFrame(paned, text='使い方ガイド')
        paned.add(help_frame, weight=1)   # weight=1 → 伸縮対象

        # --- 左側入力群 ---
        LABEL_WIDTH  = 20
        ENTRY_WIDTH  = 40
        BUTTON_WIDTH = 12

        # 計算領域 (.shp)
        ttk.Label(left_frame, text='計算領域 (.shp):',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=0, column=0, padx=5, pady=5)
        self.domain_var = tk.StringVar()
        self.domain_var_entry = ttk.Entry(
            left_frame, textvariable=self.domain_var,
            width=ENTRY_WIDTH, state='readonly'
        )
        self.domain_var_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text='参照',
                   command=self.browse_domain,
                   width=BUTTON_WIDTH) \
            .grid(row=0, column=2, padx=5, pady=5)

        # 流域界 (.shp)
        ttk.Label(left_frame, text='流域界 (.shp):',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=1, column=0, padx=5, pady=5)
        self.basin_var = tk.StringVar()
        self.basin_var_entry = ttk.Entry(
            left_frame, textvariable=self.basin_var,
            width=ENTRY_WIDTH, state='readonly'
        )
        self.basin_var_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text='参照',
                   command=self.browse_basin,
                   width=BUTTON_WIDTH) \
            .grid(row=1, column=2, padx=5, pady=5)

        # 点群データ (.csv)
        ttk.Label(left_frame, text='点群データ (.csv):',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=2, column=0, padx=5, pady=5)
        self.points_var = tk.StringVar()
        self.points_var_entry = ttk.Entry(
            left_frame, textvariable=self.points_var,
            width=ENTRY_WIDTH, state='readonly'
        )
        self.points_var_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text='参照',
                   command=self.browse_points,
                   width=BUTTON_WIDTH) \
            .grid(row=2, column=2, padx=5, pady=5)

        # 標高値列 Combobox
        ttk.Label(left_frame, text='標高値列:',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=3, column=0, padx=5, pady=5)
        self.z_var = tk.StringVar()
        self.z_combo = ttk.Combobox(
            left_frame, textvariable=self.z_var,
            values=[], width=ENTRY_WIDTH, state='readonly'
        )
        self.z_combo.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        # セル数 X/Y
        ttk.Label(left_frame, text='メッシュ分割数:',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=4, column=0, padx=5, pady=5)
        self.cells_x_var = tk.StringVar()
        self.cells_x_entry = ttk.Entry(
            left_frame, textvariable=self.cells_x_var, width=10
        )
        self.cells_x_entry.grid(row=4, column=1, padx=5, pady=5, sticky='w')

        # ttk.Label(left_frame, text='Y方向セル数:',
        #           width=LABEL_WIDTH, anchor='e') \
        #     .grid(row=5, column=0, padx=5, pady=5)
        # self.cells_y_var = tk.StringVar()
        # self.cells_y_entry = ttk.Entry(
        #     left_frame, textvariable=self.cells_y_var, width=10
        # )
        # self.cells_y_entry.grid(row=5, column=1, padx=5, pady=5, sticky='w')

        # NODATA値
        ttk.Label(left_frame, text='NODATA値:',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=6, column=0, padx=5, pady=5)
        self.nodata_var = tk.StringVar(value='-9999')
        self.nodata_entry = ttk.Entry(
            left_frame, textvariable=self.nodata_var, width=10
        )
        self.nodata_entry.grid(row=6, column=1, padx=5, pady=5, sticky='w')

        # 出力フォルダ
        ttk.Label(left_frame, text='出力フォルダ:',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=7, column=0, padx=5, pady=5)
        self.outdir_var = tk.StringVar()
        self.outdir_entry = ttk.Entry(
            left_frame, textvariable=self.outdir_var,
            width=ENTRY_WIDTH, state='readonly'
        )
        self.outdir_entry.grid(row=7, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text='参照',
                   command=self.browse_outdir,
                   width=BUTTON_WIDTH) \
            .grid(row=7, column=2, padx=5, pady=5)

        # ステータス & 実行ボタン
        self.status_var = tk.StringVar()
        ttk.Label(left_frame, textvariable=self.status_var,
                  anchor='w') \
            .grid(row=8, column=0, columnspan=2,
                  sticky='we', padx=5, pady=10)
        self.run_button = ttk.Button(left_frame, text='実行',
                   command=self.run_process,
                   width=BUTTON_WIDTH)
        self.run_button.grid(row=8, column=2, sticky='e',
                  padx=5, pady=10)

        # ヘルプパネル生成の直前にフォントを定義
        help_font = tkFont.Font(family='メイリオ', size=10)

        # ── ヘルプテキスト ──
        self.help_text = scrolledtext.ScrolledText(
            help_frame,
            wrap='none',
            font=help_font,        # ← ここで指定
            width=25,
            height=10,
            state='disabled'
        )
        self.help_text.pack(fill='both', expand=True, padx=5, pady=5)

        help_body = """
【計算領域 (.shp）】
処理対象のポリゴンシェープファイルを選択してください。

【流域界 (.shp）】
平均標高を算出する範囲のシェープファイルを指定します。

【点群データ (.csv）】
・標高値を含むCSVファイル
・座標の項目名はx,y(X,Y)を遵守してください。
・複数の点群データを指定する場合、列名を統一するようにしてください。

【標高値列】
CSVデータ内の標高値の列名を選択してください。

【メッシュ分割数】
標準メッシュの分割数。数値が大きいほど細かくなりますが、処理時間が長くなります。

例）分割数の設定例
分割数 → 生成される1メッシュあたりの大きさ
 1000 → 1m
 500 → 2m
 250 → 4m
 200 → 5m
 100 → 10m
 50 → 20m
 40 → 25m
 20 → 50m

【NODATA値】
外部領域や欠損セルに設定する値。デフォルトは -9999。

【出力フォルダ】
結果ファイルを保存するフォルダを選択してください。

【出力されるデータについて】
domain_mesh_elev；計算領域の標高メッシュ
basin_mesh_elev；流域界の標高メッシュ
        """.strip()

        self.help_text.config(state='normal')
        self.help_text.insert('1.0', help_body)
        self.help_text.config(state='disabled')


    def browse_domain(self):
        p = filedialog.askopenfilename(filetypes=[('Shapefile','*.shp')])
        if p:
            self.domain_var.set(p)

    def browse_basin(self):
        p = filedialog.askopenfilename(filetypes=[('Shapefile','*.shp')])
        if p:
            self.basin_var.set(p)

    def browse_points(self):
        paths = filedialog.askopenfilenames(
            filetypes=[('CSV','*.csv')],
            title="点群データを選択 (複数可)"
        )
        if paths:
            # 可読性のため ';' 区切りで表示
            self.points_var.set(";".join(paths))
            self._update_z_candidates(paths)


    def browse_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)


    def _update_z_candidates(self, paths):
        # パスをリストに統一
        paths = [paths] if isinstance(paths, str) else paths
        
        all_candidates = []
        
        try:
            # 各ファイルから列候補を取得
            for i, path in enumerate(paths):
                df = pd.read_csv(path)
                x_col, y_col = get_xy_columns(df)
                candidates = get_z_candidates(df, x_col, y_col)
                
                if i == 0:
                    # 最初のファイルの候補をベースに
                    common_candidates = set(candidates)
                else:
                    # 共通の候補のみを残す
                    common_candidates.intersection_update(set(candidates))
                
                all_candidates.extend(candidates)
            
            # 共通の候補がない場合は警告を表示
            if not common_candidates:
                self.z_combo['values'] = []
                self.z_var.set('')
                messagebox.showwarning(
                    '警告', 
                    'ファイル間で共通の標高値列が見つかりません。\n' +
                    '以下の理由が考えられます：\n' +
                    '1. 選択したファイルに共通の列名が存在しない\n' +
                    '2. ファイルの形式が異なる\n\n' +
                    '全てのファイルで同じ列名を使用していることを確認してください。'
                )
                return
                
            # 共通の候補を使用
            final_candidates = list(common_candidates)
            
            # ドロップダウンに設定
            self.z_combo['values'] = final_candidates
            
            # 現在の選択を維持（無効な場合は先頭を選択）
            current = self.z_var.get()
            if current not in final_candidates:
                self.z_var.set(final_candidates[0])
                
        except Exception as e:
            messagebox.showwarning('警告', f'列候補の取得中にエラーが発生しました:\n{str(e)}')
            self.z_combo['values'] = []
            self.z_var.set('')
    # 元実装: path が文字列のみ :contentReference[oaicite:1]{index=1}


    def run_process(self):
        raw = self.points_var.get()
        paths = raw.split(";") if ";" in raw else [raw]
        # 入力チェック
        if not all([self.domain_var.get(), self.basin_var.get(), paths[0], self.outdir_var.get()]):
            messagebox.showerror('エラー', '必須項目が入力されていません。')
            return

        self.run_button.config(state='disabled')
        self.status_var.set('実行中...')

        def worker():
            try:
                pipeline(
                    domain_shp=self.domain_var.get(),
                    basin_shp=self.basin_var.get(),
                    num_cells_x=int(self.cells_x_var.get()),
                    # Y方向セル数をX方向セル数と同一にする
                    num_cells_y=int(self.cells_x_var.get()),
                    points_path=paths,
                    out_dir=self.outdir_var.get(),
                    zcol=self.z_var.get(),
                    nodata=float(self.nodata_var.get()),
                    standard_mesh=STANDARD_MESH,
                    mesh_id=MESH_ID
                )
                self.result_queue.put(('success', 'メッシュ抽出・生成と標高付与が完了しました'))
            except Exception as e:
                self.result_queue.put(('error', str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def check_queue(self):
        """キューをチェックし、メッセージがあれば処理する"""
        try:
            # キューからメッセージを取得（ブロックなし）
            message_type, data = self.result_queue.get_nowait()
            
            # ボタンの状態を元に戻す
            self.run_button.config(state='normal')
            
            # メッセージタイプに応じた処理
            if message_type == 'success':
                self.status_var.set("完了")
                messagebox.showinfo('完了', data)
            elif message_type == 'error':
                self.status_var.set("エラーが発生しました")
                messagebox.showerror('エラー', f'処理中にエラーが発生しました: {data}')
                
            # 処理完了をマーク
            self.result_queue.task_done()
            
        except queue.Empty:
            # キューが空の場合は何もしない
            pass
        except Exception as e:
            # 予期せぬエラーをログに記録
            print(f"キュー処理中にエラーが発生しました: {e}")
        finally:
            # 次回のチェックをスケジュール
            self.after(100, self.check_queue)
            

def main():
    root = tk.Tk()
    app = MeshElevApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
