#!/usr/bin/env python3
#!/usr/bin/env python3
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
import queue
import tkinter.font as tkFont

from src.make_shp.add_elevation import get_xy_columns, get_z_candidates
from src.make_shp.pipeline import pipeline

class MeshElevApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title('メッシュ生成と標高付与ツール')

        # ── メインフレーム(self) をルートに配置 ──
        # row=0, column=0 のセルに sticky で全方向展開
        self.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        # ── ルート(master)側のリサイズ設定 ──
        # row=0, column=0 のセル（＝ self フレーム）がリサイズで伸びる
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        # ── self（フレーム） 内部のリサイズ設定 ──
        # PanedWindow を置いている column=0 を伸縮対象に
        self.columnconfigure(0, weight=1)
        # 行０～? まで rowspan しているので、row=0 に余白を割り当て
        self.rowconfigure(0, weight=1)

        # ウィジェット生成（ここで PanedWindow → left_frame/help_frame を構築）
        self.create_widgets()
        
        self.master.update_idletasks()
        self.master.minsize(self.master.winfo_width(), self.master.winfo_height())
        
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
        ttk.Label(left_frame, text='X方向セル数:',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=4, column=0, padx=5, pady=5)
        self.cells_x_var = tk.StringVar()
        self.cells_x_entry = ttk.Entry(
            left_frame, textvariable=self.cells_x_var, width=10
        )
        self.cells_x_entry.grid(row=4, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(left_frame, text='Y方向セル数:',
                  width=LABEL_WIDTH, anchor='e') \
            .grid(row=5, column=0, padx=5, pady=5)
        self.cells_y_var = tk.StringVar()
        self.cells_y_entry = ttk.Entry(
            left_frame, textvariable=self.cells_y_var, width=10
        )
        self.cells_y_entry.grid(row=5, column=1, padx=5, pady=5, sticky='w')

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

【X方向セル数】
グリッドの横分割数。数値が大きいほど細かくなりますが、処理時間が長くなります。

【Y方向セル数】
グリッドの縦分割数。Xと同じ値を推奨します。

【NODATA値】
外部領域や欠損セルに設定する値。デフォルトは -9999。

【出力フォルダ】
結果ファイルを保存するフォルダを選択してください。

【出力されるデータについて】
domain_mesh_elev；計算領域の標高メッシュ（RRI用にASC変換する場合使用するのはこちらのデータ）
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
        p = filedialog.askopenfilename(filetypes=[('CSV','*.csv')])
        if p:
            self.points_var.set(p)
            self._update_z_candidates(p)

    def browse_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    def _update_z_candidates(self, path):
        try:
            df = pd.read_csv(path)
        except Exception:
            return
        try:
            x_col, y_col = get_xy_columns(df)
            cands = get_z_candidates(df, x_col, y_col)
        except ValueError as e:
            messagebox.showwarning('警告', str(e))
            return

        self.z_combo['values'] = cands
        if cands:
            self.z_var.set(cands[0])

    def run_process(self):
        args = {
            'domain_shp': self.domain_var.get(),
            'basin_shp': self.basin_var.get(),
            'points_path': self.points_var.get(),
            'zcol': self.z_var.get(),
            'cells_x_str': self.cells_x_var.get(),
            'cells_y_str': self.cells_y_var.get(),
            'out_dir': self.outdir_var.get(),
            'nodata': self.nodata_var.get()
        }

        if not all(args.values()):
            messagebox.showerror('エラー', '全ての項目を入力してください')
            return
        try:
            args['cells_x'] = int(args['cells_x_str'])
            args['cells_y'] = int(args['cells_y_str'])
            if args['cells_x'] <= 0 or args['cells_y'] <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('エラー', 'セル数は正の整数を入力してください')
            return

        self.run_button.config(state='disabled')
        self.status_var.set("処理中...")
        self.result_queue = queue.Queue()

        threading.Thread(
            target=self._pipeline_worker,
            args=(args,)
        ).start()

        self.master.after(100, self.check_queue)

    def _pipeline_worker(self, args):
        try:
            pipeline(
                domain_shp=args['domain_shp'],
                basin_shp=args['basin_shp'],
                num_cells_x=args['cells_x'],
                num_cells_y=args['cells_y'],
                points_path=args['points_path'],
                zcol=args['zcol'],
                out_dir=args['out_dir'],
                nodata=float(args['nodata']) if args['nodata'] else None
            )
            self.result_queue.put(('success', 'メッシュ生成と標高付与が完了しました！'))
        except Exception as e:
            self.result_queue.put(('error', e))

    def check_queue(self):
        try:
            message_type, data = self.result_queue.get_nowait()
            self.run_button.config(state='normal')
            self.status_var.set("完了")

            if message_type == 'success':
                messagebox.showinfo('完了', data)
            elif message_type == 'error':
                messagebox.showerror('エラー', f'処理中にエラーが発生しました: {data}')
        except queue.Empty:
            self.master.after(100, self.check_queue)

def main():
    root = tk.Tk()
    app = MeshElevApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
