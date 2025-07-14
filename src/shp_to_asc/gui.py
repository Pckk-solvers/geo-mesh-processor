import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fiona
import os
import threading
import queue
from src.shp_to_asc.core import analyze_grid_structure, shp_to_ascii
from src.shp_to_asc.utils import get_available_filename

class ShpToAscApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(sticky='nsew', padx=10, pady=10)
        master.title("シェープファイル → ASCII グリッド変換ツール")
        master.columnconfigure(1, weight=1)
        # 行の柔軟性設定
        for i in range(7):
            master.rowconfigure(i, weight=0)
        master.rowconfigure(5, weight=1)
        self.create_widgets()

    def create_widgets(self):
        LABEL_WIDTH = 25
        ENTRY_WIDTH = 50
        BUTTON_WIDTH = 12

        # --- シェープファイル選択 ---
        ttk.Label(self, text="シェープファイル (.shp):", width=LABEL_WIDTH, anchor='e')\
            .grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.input_path_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.input_path_var, width=ENTRY_WIDTH, state='readonly')\
            .grid(row=0, column=1, sticky='we', padx=5, pady=5)
        ttk.Button(self, text="参照", command=self.select_input, width=BUTTON_WIDTH)\
            .grid(row=0, column=2, padx=5, pady=5)

        # --- 属性フィールド選択 ---
        ttk.Label(self, text="焼き込み属性フィールド:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.field_cb = ttk.Combobox(self, values=[], state='readonly', width=ENTRY_WIDTH-2)
        self.field_cb.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        # --- NoData 値設定 ---
        ttk.Label(self, text="NoData 値:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.nodata_var = tk.StringVar(value="-9999")
        ttk.Entry(self, textvariable=self.nodata_var, width=ENTRY_WIDTH)\
            .grid(row=2, column=1, sticky='w', padx=5, pady=5)

        # --- 出力ファイル選択 ---
        ttk.Label(self, text="出力ファイル (.asc):", width=LABEL_WIDTH, anchor='e')\
            .grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.output_path_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.output_path_var, width=ENTRY_WIDTH, state='readonly')\
            .grid(row=3, column=1, sticky='we', padx=5, pady=5)
        ttk.Button(self, text="参照", command=self.select_output_file, width=BUTTON_WIDTH)\
            .grid(row=3, column=2, padx=5, pady=5)

        # --- グリッド情報表示 ---
        self.info_frame = ttk.LabelFrame(self, text="グリッド情報 (参考)", padding=10)
        self.info_frame.grid(row=5, column=0, columnspan=3, sticky='nsew', padx=5, pady=5)
        self.grid_info_var = tk.StringVar(value="シェープファイル選択後に表示されます")
        ttk.Label(self.info_frame, textvariable=self.grid_info_var, wraplength=600, justify='left')\
            .pack(fill='both', expand=True)

        # --- 実行ボタンとステータス --- 
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, anchor='w').grid(row=6, column=0, columnspan=2, sticky='we', padx=5, pady=10)

        self.run_button = ttk.Button(self, text="実行", command=self.run_conversion, width=BUTTON_WIDTH)
        self.run_button.grid(row=6, column=2, sticky='e', padx=5, pady=10)

    def select_input(self):
        path = filedialog.askopenfilename(filetypes=[("Shapefile", "*.shp")])
        if not path:
            return
        self.input_path_var.set(path)
        try:
            with fiona.open(path) as src:
                fields = list(src.schema['properties'].keys())
            self.field_cb['values'] = fields
        except Exception as e:
            messagebox.showerror("エラー", f"シェープファイル読み込み失敗:\n{e}")
            return
        try:
            grid_info = analyze_grid_structure(path)
            info_text = (
                f"セル数: {grid_info['ncols']} × {grid_info['nrows']}\n"
                f"平均セルサイズ: dx={grid_info['cell_size_x']:.8f}, dy={grid_info['cell_size_y']:.8f}\n"
                f"範囲: X={grid_info['extent'][0]:.6f}〜{grid_info['extent'][2]:.6f}, "
                f"Y={grid_info['extent'][1]:.6f}〜{grid_info['extent'][3]:.6f}"
            )
            self.grid_info_var.set(info_text)
        except Exception as e:
            self.grid_info_var.set("グリッド情報取得エラー")
            messagebox.showwarning("警告", f"セルサイズ自動計算失敗:\n{e}")

    def select_output_file(self):
        input_shp = self.input_path_var.get()
        initial_dir = os.path.dirname(input_shp) if input_shp else ''
        initial_file = os.path.splitext(os.path.basename(input_shp))[0] if input_shp else ''

        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=initial_file,
            filetypes=[("ASCII Grid", "*.asc")],
            defaultextension=".asc"
        )
        if path:
            self.output_path_var.set(path)

    def run_conversion(self):
        shp = self.input_path_var.get()
        if not shp:
            messagebox.showwarning("警告", "入力ファイルを選択してください")
            return
        field = self.field_cb.get()
        if not field:
            messagebox.showwarning("警告", "属性フィールドを選択してください")
            return
        nodata_str = self.nodata_var.get()
        try:
            nodata = float(nodata_str)
        except ValueError:
            messagebox.showwarning("警告", "NoDataは数値で入力してください")
            return
        outpath = self.output_path_var.get()
        if not outpath:
            messagebox.showwarning("警告", "出力ファイルを選択してください")
            return

        # GUIを更新し、スレッドを開始
        self.run_button.config(state='disabled')
        self.status_var.set("処理中...")
        self.result_queue = queue.Queue()

        threading.Thread(
            target=self._conversion_worker,
            args=(shp, field, nodata, outpath)
        ).start()

        self.master.after(100, self.check_queue)

    def _conversion_worker(self, shp, field, nodata, outpath):
        """ワーカースレッドで実行される変換処理"""
        try:
            result = shp_to_ascii(
                shp_path=shp,
                field=field,
                nodata=nodata,
                output_path=outpath
            )
            self.result_queue.put(('success', result, outpath))
        except Exception as e:
            self.result_queue.put(('error', e))

    def check_queue(self):
        """キューをチェックしてGUIを更新する"""
        try:
            # キューからノンブロッキングでアイテムを取得
            message_type, data, *optional_data = self.result_queue.get_nowait()
            self.run_button.config(state='normal')
            self.status_var.set("完了")

            if message_type == 'success':
                ncols, nrows, dx, dy = data
                outpath = optional_data[0]
                messagebox.showinfo(
                    "完了",
                    f"出力先: {outpath}\n"
                    f"セル数: {ncols} × {nrows}\n"
                    f"セルサイズ: dx={dx:.12f}, dy={dy:.12f}"
                )
            elif message_type == 'error':
                messagebox.showerror("エラー", f"変換中にエラーが発生しました:\n{data}")

        except queue.Empty:
            # キューが空なら、100ms後にもう一度チェック
            self.master.after(100, self.check_queue)

if __name__ == '__main__':
    root = tk.Tk()
    root.columnconfigure(1, weight=1)
    root.rowconfigure(5, weight=1)
    app = ShpToAscApp(root)
    root.mainloop()
