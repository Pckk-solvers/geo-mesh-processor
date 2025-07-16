#!/usr/bin/env python3
#!/usr/bin/env python3
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue

from src.make_shp.add_elevation import get_xy_columns, get_z_candidates
from src.make_shp.pipeline import pipeline

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
            
        # NODATA値
        ttk.Label(self, text='NODATA値:', width=LABEL_WIDTH, anchor='e') \
            .grid(row=6, column=0, padx=5, pady=5)
        self.nodata_var = tk.StringVar(value="-9999")
        ttk.Entry(self, textvariable=self.nodata_var, width=10) \
            .grid(row=6, column=1, padx=5, pady=5, sticky='w')

        # 出力フォルダ
        ttk.Label(self, text='出力フォルダ:', width=LABEL_WIDTH, anchor='e') \
            .grid(row=6, column=0, padx=5, pady=5)
        self.outdir_var = tk.StringVar(value="")
        ttk.Entry(self, textvariable=self.outdir_var, width=ENTRY_WIDTH, state='readonly') \
            .grid(row=6, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(self, text='参照', command=self.browse_outdir, width=BUTTON_WIDTH) \
            .grid(row=6, column=2, padx=5, pady=5)

        # 実行ボタンとステータス
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, anchor='w').grid(row=8, column=0, columnspan=2, sticky='we', padx=5, pady=10)

        self.run_button = ttk.Button(self, text='実行', command=self.run_process, width=BUTTON_WIDTH)
        self.run_button.grid(row=8, column=2, sticky='e', padx=5, pady=10)

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

if __name__ == '__main__':
    root = tk.Tk()
    root.columnconfigure(1, weight=1)
    root.rowconfigure(7, weight=1)
    app = MeshElevApp(root)
    root.mainloop()
