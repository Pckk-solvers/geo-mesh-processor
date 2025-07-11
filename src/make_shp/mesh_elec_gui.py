#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import os
import sys

class MeshElevApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        # 余白を設定
        self.grid(sticky='nsew', padx=10, pady=10)
        master.title('メッシュ生成と標高付与ツール')
        master.columnconfigure(1, weight=1)
        # 各行に柔軟性を持たせる
        for i in range(7):
            master.rowconfigure(i, weight=0)
        master.rowconfigure(6, weight=1)
        self.create_widgets()

    def create_widgets(self):
        # 各ウィジェットの幅定義
        LABEL_WIDTH = 20
        ENTRY_WIDTH = 40
        BUTTON_WIDTH = 12

        # 計算領域
        ttk.Label(self, text='計算領域 (.shp):', width=LABEL_WIDTH, anchor='e').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.domain_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.domain_var, width=ENTRY_WIDTH).grid(row=0, column=1, sticky='w', padx=5, pady=5)
        ttk.Button(self, text='参照', command=self.browse_domain, width=BUTTON_WIDTH).grid(row=0, column=2, padx=5, pady=5)

        # 流域界
        ttk.Label(self, text='流域界 (.shp):', width=LABEL_WIDTH, anchor='e').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.basin_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.basin_var, width=ENTRY_WIDTH).grid(row=1, column=1, sticky='w', padx=5, pady=5)
        ttk.Button(self, text='参照', command=self.browse_basin, width=BUTTON_WIDTH).grid(row=1, column=2, padx=5, pady=5)

        # 点群データ
        ttk.Label(self, text='点群データ (.csv/.shp):', width=LABEL_WIDTH, anchor='e').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.points_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.points_var, width=ENTRY_WIDTH).grid(row=2, column=1, sticky='w', padx=5, pady=5)
        ttk.Button(self, text='参照', command=self.browse_points, width=BUTTON_WIDTH).grid(row=2, column=2, padx=5, pady=5)

        # セル数
        ttk.Label(self, text='X方向セル数:', width=LABEL_WIDTH, anchor='e').grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.cells_x_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.cells_x_var, width=10).grid(row=3, column=1, sticky='w', padx=5, pady=5)
        ttk.Label(self, text='Y方向セル数:', width=LABEL_WIDTH, anchor='e').grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.cells_y_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.cells_y_var, width=10).grid(row=4, column=1, sticky='w', padx=5, pady=5)

        # 出力フォルダ
        ttk.Label(self, text='出力フォルダ:', width=LABEL_WIDTH, anchor='e').grid(row=5, column=0, sticky='e', padx=5, pady=5)
        self.outdir_var = tk.StringVar(value=os.path.join(os.getcwd(), 'outputs'))
        ttk.Entry(self, textvariable=self.outdir_var, width=ENTRY_WIDTH).grid(row=5, column=1, sticky='w', padx=5, pady=5)
        ttk.Button(self, text='参照', command=self.browse_outdir, width=BUTTON_WIDTH).grid(row=5, column=2, padx=5, pady=5)

        # 実行ボタン
        self.run_button = ttk.Button(self, text='実行', command=self.run_process, width=BUTTON_WIDTH)
        self.run_button.grid(row=6, column=1, sticky='e', padx=5, pady=15)

    def browse_domain(self):
        p = filedialog.askopenfilename(filetypes=[('Shapefile','*.shp')])
        if p:
            self.domain_var.set(p)

    def browse_basin(self):
        p = filedialog.askopenfilename(filetypes=[('Shapefile','*.shp')])
        if p:
            self.basin_var.set(p)

    def browse_points(self):
        p = filedialog.askopenfilename(filetypes=[('CSV','*.csv'),('Shapefile','*.shp')])
        if p:
            self.points_var.set(p)

    def browse_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    def run_process(self):
        domain = self.domain_var.get()
        basin = self.basin_var.get()
        points = self.points_var.get()
        cells_x = self.cells_x_var.get()
        cells_y = self.cells_y_var.get()
        outdir = self.outdir_var.get()

        if not all([domain, basin, points, cells_x, cells_y, outdir]):
            messagebox.showerror('エラー','全ての項目を入力してください')
            return
        try:
            ix = int(cells_x)
            iy = int(cells_y)
            if ix <= 0 or iy <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('エラー','セル数は正の整数を入力してください')
            return

        os.makedirs(outdir, exist_ok=True)

        # パイプラインスクリプトを呼び出し
        cmd = [sys.executable, os.path.join(os.path.dirname(__file__), 'pipeline.py'),
               '--domain', domain,
               '--basin', basin,
               '--cells_x', str(ix),
               '--cells_y', str(iy),
               '--points', points,
               '--outdir', outdir]
        try:
            subprocess.check_call(cmd)
            messagebox.showinfo('完了','メッシュ生成と標高付与が完了しました！')
        except subprocess.CalledProcessError as e:
            messagebox.showerror('エラー', f'処理中にエラーが発生しました: {e}')

if __name__ == '__main__':
    root = tk.Tk()
    root.columnconfigure(1, weight=1)
    root.rowconfigure(6, weight=1)
    app = MeshElevApp(root)
    root.mainloop()
