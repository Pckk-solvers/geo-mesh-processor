#!/usr/bin/env python3
import os
import sys
import subprocess
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

# ヘルパー関数を外部から参照する場合はモジュール化しても良い
from add_elevation import get_xy_columns, get_z_candidates

class MeshElevApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title('メッシュ生成と標高付与ツール')
        self.grid(sticky='nsew', padx=10, pady=10)

        # ウィンドウのグリッド設定
        master.columnconfigure(1, weight=1)
        for i in range(8):
            master.rowconfigure(i, weight=0)
        master.rowconfigure(7, weight=1)

        self.create_widgets()

    def create_widgets(self):
        LABEL_WIDTH = 20
        ENTRY_WIDTH = 40
        BUTTON_WIDTH = 12

        # 計算領域 (.shp)
        ttk.Label(self, text='計算領域 (.shp):', width=LABEL_WIDTH, anchor='e') \
            .grid(row=0, column=0, padx=5, pady=5)
        self.domain_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.domain_var, width=ENTRY_WIDTH, state='readonly') \
            .grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self, text='参照', command=self.browse_domain, width=BUTTON_WIDTH) \
            .grid(row=0, column=2, padx=5, pady=5)

        # 流域界 (.shp)
        ttk.Label(self, text='流域界 (.shp):', width=LABEL_WIDTH, anchor='e') \
            .grid(row=1, column=0, padx=5, pady=5)
        self.basin_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.basin_var, width=ENTRY_WIDTH, state='readonly') \
            .grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self, text='参照', command=self.browse_basin, width=BUTTON_WIDTH) \
            .grid(row=1, column=2, padx=5, pady=5)

        # 点群データ (.csv)
        ttk.Label(self, text='点群データ (.csv):', width=LABEL_WIDTH, anchor='e') \
            .grid(row=2, column=0, padx=5, pady=5)
        self.points_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.points_var, width=ENTRY_WIDTH, state='readonly') \
            .grid(row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self, text='参照', command=self.browse_points, width=BUTTON_WIDTH) \
            .grid(row=2, column=2, padx=5, pady=5)

        # Z 列選択 Combobox
        ttk.Label(self, text='Z 列:', width=LABEL_WIDTH, anchor='e') \
            .grid(row=3, column=0, padx=5, pady=5)
        self.z_var = tk.StringVar()
        self.z_combo = ttk.Combobox(
            self, textvariable=self.z_var, values=[], width=ENTRY_WIDTH, state='readonly'
        )
        self.z_combo.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        # セル数 X/Y
        ttk.Label(self, text='X方向セル数:', width=LABEL_WIDTH, anchor='e') \
            .grid(row=4, column=0, padx=5, pady=5)
        self.cells_x_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.cells_x_var, width=10) \
            .grid(row=4, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(self, text='Y方向セル数:', width=LABEL_WIDTH, anchor='e') \
            .grid(row=5, column=0, padx=5, pady=5)
        self.cells_y_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.cells_y_var, width=10) \
            .grid(row=5, column=1, padx=5, pady=5, sticky='w')

        # 出力フォルダ
        ttk.Label(self, text='出力フォルダ:', width=LABEL_WIDTH, anchor='e') \
            .grid(row=6, column=0, padx=5, pady=5)
        self.outdir_var = tk.StringVar(value=os.path.join(os.getcwd(), 'outputs'))
        ttk.Entry(self, textvariable=self.outdir_var, width=ENTRY_WIDTH, state='readonly') \
            .grid(row=6, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self, text='参照', command=self.browse_outdir, width=BUTTON_WIDTH) \
            .grid(row=6, column=2, padx=5, pady=5)

        # 実行ボタン
        self.run_button = ttk.Button(self, text='実行', command=self.run_process, width=BUTTON_WIDTH)
        self.run_button.grid(row=7, column=1, padx=5, pady=15, sticky='e')

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
        domain = self.domain_var.get()
        basin = self.basin_var.get()
        points = self.points_var.get()
        z_col = self.z_var.get()
        cells_x = self.cells_x_var.get()
        cells_y = self.cells_y_var.get()
        outdir = self.outdir_var.get()

        # 入力チェック
        if not all([domain, basin, points, z_col, cells_x, cells_y, outdir]):
            messagebox.showerror('エラー','全ての項目を入力してください')
            return
        try:
            ix, iy = int(cells_x), int(cells_y)
            if ix <= 0 or iy <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('エラー','セル数は正の整数を入力してください')
            return

        os.makedirs(outdir, exist_ok=True)

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'pipeline.py'),
            '--domain', domain,
            '--basin', basin,
            '--cells_x', str(ix),
            '--cells_y', str(iy),
            '--points', points,
            '--zcol', z_col,
            '--outdir', outdir
        ]
        try:
            subprocess.check_call(cmd)
            messagebox.showinfo('完了','メッシュ生成と標高付与が完了しました！')
        except subprocess.CalledProcessError as e:
            messagebox.showerror('エラー', f'処理中にエラーが発生しました: {e}')

if __name__ == '__main__':
    root = tk.Tk()
    root.columnconfigure(1, weight=1)
    root.rowconfigure(7, weight=1)
    app = MeshElevApp(root)
    root.mainloop()
