"""
mesh_dominant_gui.py
GUI: tkinter を使用してメッシュ代表値付与処理を実行するインターフェース
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import tkinter.font as tkFont
import os

from src.mesh_dominant_module.mesh_dominant import assign_dominant_values


class MeshDominantApp(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title('土地利用区分コード付与ツール')
        self.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # ウィジェットを作成
        self.create_widgets()
        
        # ウィンドウの初期サイズを計算して設定
        self.master.update_idletasks()  # ウィジェットのサイズを更新
        width = self.master.winfo_reqwidth()
        height = self.master.winfo_reqheight()
        self.master.minsize(width, height)  # 最小サイズを初期サイズに設定


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
        PADX = 5  # 横のパディング
        PADY = 5  # 縦のパディング

        # --- 基準メッシュ選択 ---
        ttk.Label(left_frame, text="計算領域メッシュ (.shp):", width=LABEL_WIDTH, anchor='e')\
            .grid(row=0, column=0, padx=PADX, pady=PADY, sticky='e')
        self.base_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.base_var, width=ENTRY_WIDTH, state='readonly')\
            .grid(row=0, column=1, sticky='we', padx=PADX, pady=PADY)
        ttk.Button(left_frame, text="参照", command=self.select_base, width=BUTTON_WIDTH)\
            .grid(row=0, column=2, padx=PADX, pady=PADY)

        # --- 属性メッシュ選択 ---
        ttk.Label(left_frame, text="属性メッシュ (.shp):", width=LABEL_WIDTH, anchor='e')\
            .grid(row=1, column=0, padx=PADX, pady=PADY, sticky='e')
        self.land_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.land_var, width=ENTRY_WIDTH, state='readonly')\
            .grid(row=1, column=1, sticky='we', padx=PADX, pady=PADY)
        ttk.Button(left_frame, text="参照", command=self.select_land, width=BUTTON_WIDTH)\
            .grid(row=1, column=2, padx=PADX, pady=PADY)

        # --- 属性フィールド選択 ---
        ttk.Label(left_frame, text="属性フィールド:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=2, column=0, padx=PADX, pady=PADY, sticky='e')
        self.source_field_cb = ttk.Combobox(left_frame, values=[], state='readonly', width=ENTRY_WIDTH-2)
        self.source_field_cb.grid(row=2, column=1, sticky='w', padx=PADX, pady=PADY)
        self.source_field_cb.bind('<<ComboboxSelected>>', self._on_field_selected)

        # --- 出力フィールド名 ---
        ttk.Label(left_frame, text="出力フィールド名:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=3, column=0, padx=PADX, pady=PADY, sticky='e')
        self.output_field_var = tk.StringVar(value='')
        ttk.Entry(left_frame, textvariable=self.output_field_var, width=ENTRY_WIDTH)\
            .grid(row=3, column=1, sticky='w', padx=PADX, pady=PADY)

        # --- 閾値 ---
        ttk.Label(left_frame, text="閾値:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=4, column=0, padx=PADX, pady=PADY, sticky='e')
        self.threshold_var = tk.DoubleVar(value=0.5)
        ttk.Entry(left_frame, textvariable=self.threshold_var, width=ENTRY_WIDTH)\
            .grid(row=4, column=1, sticky='w', padx=PADX, pady=PADY)

        # --- NODATA 値 ---
        ttk.Label(left_frame, text="NODATA値:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=5, column=0, padx=PADX, pady=PADY, sticky='e')
        self.nodata_var = tk.StringVar(value='-9999')
        ttk.Entry(left_frame, textvariable=self.nodata_var, width=ENTRY_WIDTH)\
            .grid(row=5, column=1, sticky='w', padx=PADX, pady=PADY)

        # --- 出力ファイル選択 ---
        ttk.Label(left_frame, text="出力ファイル (.shp):", width=LABEL_WIDTH, anchor='e')\
            .grid(row=6, column=0, padx=PADX, pady=PADY, sticky='e')
        self.output_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.output_var, width=ENTRY_WIDTH, state='readonly')\
            .grid(row=6, column=1, sticky='we', padx=PADX, pady=PADY)
        ttk.Button(left_frame, text="参照", command=self.select_output, width=BUTTON_WIDTH)\
            .grid(row=6, column=2, padx=PADX, pady=PADY)

        # --- 実行ボタンとステータス ---
        self.status_var = tk.StringVar()
        ttk.Label(left_frame, textvariable=self.status_var, anchor='w')\
            .grid(row=7, column=0, columnspan=2, sticky='we', padx=PADX, pady=10)
        self.run_button = ttk.Button(left_frame, text="実行", command=self.run_process, width=BUTTON_WIDTH)
        self.run_button.grid(row=7, column=2, sticky='e', padx=PADX, pady=10)
        
        # ヘルプパネル生成の直前にフォントを定義
        help_font = tkFont.Font(family='メイリオ', size=10)
        
        # ── ヘルプテキスト ──
        self.help_text = scrolledtext.ScrolledText(
            help_frame,
            wrap='none',
            font=help_font,        # ← ここで指定
            width=15,
            height=10,
            state='disabled'
        )
        self.help_text.pack(fill='both', expand=True, padx=5, pady=5)

        help_body = """
【計算領域メッシュ (.shp)】
計算領域のメッシュ化済みポリゴンシェープファイルを選択してください。

【属性メッシュ (.shp)】
付与する属性を持つファイルを選択してください。（例；土地利用データ）

【属性フィールド】
属性メッシュから計算領域メッシュへ付与させる属性名を選択してください。

【出力フィールド名】
計算領域メッシュに付与する際の属性名

【閾値】
土地利用メッシュと計算格子の重複率に対する閾値
設定した閾値よりも重複率が高い場合；土地利用メッシュの属性情報を付与
設定した閾値よりも重複率が低い場合；NODATA値を設定
例）閾値0.5の場合；土地利用メッシュと計算格子の重複率が50％以上であれば値を付与
※閾値範囲；0.1～1.0（小数点以下一桁）

【NODATA値】
外部領域や閾値で値なしと判定した領域に設定する値。デフォルトは -9999。

【出力ファイル (.shp)】
結果ファイルを保存するフォルダとファイル名を選択してください。
        """.strip()

        self.help_text.config(state='normal')
        self.help_text.insert('1.0', help_body)
        self.help_text.config(state='disabled')

    def select_base(self):
        path = filedialog.askopenfilename(
            filetypes=[('Shapefile', '*.shp')]
        )
        if path:
            self.base_var.set(path)
            # self.update_fields()

    def select_land(self):
        path = filedialog.askopenfilename(
            filetypes=[('Shapefile', '*.shp')]
        )
        if path:
            self.land_var.set(path)
            self.update_fields(encoding='cp932')

    def select_output(self):
        base = self.base_var.get()
        default = os.path.splitext(base)[0] + '_dominant.shp' if base else ''
        path = filedialog.asksaveasfilename(
            defaultextension='.shp',
            filetypes=[('Shapefile', '*.shp')],
            initialfile=os.path.basename(default)
        )
        if path:
            self.output_var.set(path)

    def _on_field_selected(self, event=None):
        """属性フィールドが選択されたときの処理"""
        selected_field = self.source_field_cb.get()
        if selected_field:
            # 出力フィールド名を更新
            self.output_field_var.set(f'{selected_field}')

    def update_fields(self, encoding='cp932'):
        # 属性フィールド一覧を更新
        land_path = self.land_var.get()
        try:
            import geopandas as gpd
            gdf = gpd.read_file(land_path, encoding=encoding)
            fields = [c for c in gdf.columns if c not in gdf.geometry.name]
            self.source_field_cb['values'] = fields
            if fields:
                self.source_field_cb.set(fields[0])
                # 初期選択時に出力フィールド名も更新
                self.output_field_var.set(f'{fields[0]}')
        except Exception as e:
            print(f"フィールド更新エラー: {e}")

    def run_process(self):
        # 入力チェック
        if not self.base_var.get() or not self.land_var.get():
            messagebox.showwarning('入力エラー', '基準メッシュと属性メッシュを指定してください。')
            return
        params = {
            'base_path': self.base_var.get(),
            'land_path': self.land_var.get(),
            'source_field': self.source_field_cb.get(),
            'output_field': self.output_field_var.get(),
            'threshold': self.threshold_var.get(),
            'nodata': type(self.nodata_var.get())(self.nodata_var.get()),
            'output_path': self.output_var.get() or None
        }
        self.run_button.config(state='disabled')
        self.status_var.set('処理中...')
        threading.Thread(target=self._worker, args=(params,), daemon=True).start()

    def _worker(self, params):
        try:
            assign_dominant_values(**params)
            self.status_var.set('完了')
            messagebox.showinfo('完了', f'"{self.output_field_var.get()}" を付与しました。')
        except Exception as e:
            self.status_var.set('エラー')
            messagebox.showerror('エラー', str(e))
        finally:
            self.run_button.config(state='normal')


def main():
    root = tk.Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    app = MeshDominantApp(master=root)
    app.mainloop()


if __name__ == '__main__':
    main()
