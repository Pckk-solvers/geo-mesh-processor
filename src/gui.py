import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fiona
import os
from core import analyze_grid_structure, shp_to_ascii
from utils import get_available_filename, read_crs

class ShpToAscApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("シェープファイル → ASCII グリッド変換ツール")

        # --- シェープファイル選択 ---
        self.input_path_var = tk.StringVar()
        tk.Button(self, text="シェープファイル選択", command=self.select_input).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self, textvariable=self.input_path_var).grid(row=0, column=1, sticky='w')

        # --- 属性フィールド選択 ---
        tk.Label(self, text="焼き込みに使う属性フィールド:").grid(row=1, column=0, padx=5, pady=5)
        self.field_cb = ttk.Combobox(self, values=[], state="readonly")
        self.field_cb.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        # --- NoData 値設定 ---
        tk.Label(self, text="NoData 値:").grid(row=2, column=0, padx=5, pady=5)
        self.nodata_var = tk.StringVar(value="-9999")
        tk.Entry(self, textvariable=self.nodata_var).grid(row=2, column=1, sticky='w', padx=5, pady=5)

        # # --- CRS 表示 ---
        # self.crs_var = tk.StringVar(value="CRS: 未取得")
        # tk.Label(self, textvariable=self.crs_var).grid(row=3, column=0, columnspan=2, sticky='w', padx=5)

        # --- 出力フォルダ選択 ---
        self.output_dir_var = tk.StringVar()
        tk.Button(self, text="出力フォルダ選択", command=self.select_output).grid(row=6, column=0, padx=5, pady=5)
        tk.Label(self, textvariable=self.output_dir_var).grid(row=6, column=1, sticky='w')

        # --- グリッド情報表示用フレーム ---
        self.info_frame = ttk.LabelFrame(self, text="グリッド情報 (参考値)", padding=5)
        self.info_frame.grid(row=7, column=0, columnspan=2, sticky='ew',padx=5, pady=5)
        
        # グリッド情報表示用のラベル
        self.grid_info_var = tk.StringVar(value="シェープファイルを選択するとグリッド情報が表示されます")
        self.grid_info_label = ttk.Label(
            self.info_frame,
            textvariable=self.grid_info_var,
            wraplength=400,
            justify='left',
            foreground='gray30'
        )
        self.grid_info_label.pack(fill='x')

        # --- 実行ボタン ---
        tk.Button(self, text="実行", command=self.run_conversion).grid(row=8, column=0, columnspan=2, pady=10)

    def select_input(self):
        path = filedialog.askopenfilename(filetypes=[("Shapefile", "*.shp")])
        if not path:
            return
        self.input_path_var.set(path)
        try:
            # フィールド一覧取得
            with fiona.open(path) as src:
                fields = list(src.schema['properties'].keys())
            self.field_cb['values'] = fields
            # # CRS 取得
            # crs = read_crs(path)
            # self.crs_var.set(f"CRS: {crs}")
        except Exception as e:
            messagebox.showerror("エラー", f"シェープファイルの読み込みに失敗しました:\n{e}")
            return

        # --- セルサイズ自動計算 & GUI 反映 ---
        try:
            grid_info = analyze_grid_structure(path)
            
            # グリッド情報を表示
            info_text = (
                f"セル数: {grid_info['ncols']} (列) × {grid_info['nrows']} (行)\n"
                f"平均セルサイズ: dx={grid_info['cell_size_x']:.8f}, dy={grid_info['cell_size_y']:.8f}\n"
                f"グリッド範囲: X={grid_info['extent'][0]:.6f} 〜 {grid_info['extent'][2]:.6f}, "
                f"Y={grid_info['extent'][1]:.6f} 〜 {grid_info['extent'][3]:.6f}"
            )
            self.grid_info_var.set(info_text)
            
        except Exception as e:
            self.grid_info_var.set(f"グリッド情報の取得中にエラーが発生しました: {str(e)}")
            messagebox.showwarning("警告", f"セルサイズの自動計算に失敗しました。手動で入力してください:\n{e}")

    def select_output(self):
        directory = filedialog.askdirectory()
        if not directory:
            return
        self.output_dir_var.set(directory)

    def run_conversion(self):
        shp = self.input_path_var.get()
        if not shp:
            messagebox.showwarning("警告", "入力シェープファイルを選択してください")
            return
        field = self.field_cb.get()
        if not field:
            messagebox.showwarning("警告", "属性フィールドを選択してください")
            return
        nodata = self.nodata_var.get()
        try:
            nodata = float(nodata)
        except ValueError:
            messagebox.showwarning("警告", "NoData 値は数値で入力してください")
            return
        outdir = self.output_dir_var.get()
        if not outdir:
            messagebox.showwarning("警告", "出力フォルダを選択してください")
            return


        # 出力ファイル名自動生成
        base = os.path.splitext(os.path.basename(shp))[0]
        outpath = get_available_filename(outdir, base, ".asc")

        # 変換実行
        try:
            ncols, nrows, actual_dx, actual_dy = shp_to_ascii(
                shp_path=shp,
                field=field,
                nodata=nodata,
                output_path=outpath
            )
            # 実際のグリッド数を表示
            messagebox.showinfo(
                "完了",
                f"変換が完了しました:\n"
                f"出力先: {outpath}\n\n"
                f"使用されたグリッド数:\n"
                f"ncols, nrows = {ncols}, {nrows}\n"
                f"使用されたグリッド間隔:\n"
                f"dx, dy = {actual_dx:.12f}, {actual_dy:.12f}\n"
            )
        except Exception as e:
            messagebox.showerror("エラー", f"変換中にエラーが発生しました:\n{e}")

if __name__ == "__main__":
    app = ShpToAscApp()
    app.mainloop()
