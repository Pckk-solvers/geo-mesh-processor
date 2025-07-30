import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fiona
import os
import threading
import queue

# 絶対インポートに変更
from src.shp_to_asc.core import analyze_grid_structure, shp_to_ascii

# デフォルトのNODATA値
DEFAULT_NODATA = -9999

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
        
        # メッセージキューを初期化
        self.message_queue = queue.Queue()
        
        # ウィジェットを作成
        self.create_widgets()
        
        # ウィンドウの初期サイズを計算して設定
        self.master.update_idletasks()  # ウィジェットのサイズを更新
        width = self.master.winfo_reqwidth()
        height = self.master.winfo_reqheight()
        self.master.minsize(width, height)  # 最小サイズを初期サイズに設定
        
        # キューを定期的にチェックするコールバックを登録
        self.after(100, self.check_queue)

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

        # --- NODATA 値設定 ---
        ttk.Label(self, text="NODATA値:", width=LABEL_WIDTH, anchor='e')\
            .grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.nodata_var = tk.StringVar(value=str(DEFAULT_NODATA))
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

    def check_queue(self):
        """メッセージキューをチェックしてUIを更新"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                if message[0] == 'status':
                    self.status_var.set(message[1])
                elif message[0] == 'enable_button':
                    self.run_button.config(state='normal')
                elif message[0] == 'error':
                    messagebox.showerror("エラー", message[1])
                    self.run_button.config(state='normal')
                    self.status_var.set("エラーが発生しました")
                
                self.message_queue.task_done()
        except queue.Empty:
            pass
        
        # 次のチェックをスケジュール
        self.after(100, self.check_queue)
        
    def update_status(self, message):
        """ステータスを更新"""
        self.message_queue.put(('status', message))
        
    def run_conversion(self):
        shp = self.input_path_var.get()
        if not shp:
            messagebox.showwarning("警告", "入力ファイルを選択してください")
            return
            
        field = self.field_cb.get()
        if not field:
            messagebox.showwarning("警告", "属性フィールドを選択してください")
            return
            
        try:
            shp_path = self.input_path_var.get()
            output_path = self.output_path_var.get()
            
            if not output_path:
                messagebox.showwarning("警告", "出力ファイルを指定してください")
                return
            
            # NoData値が空の場合はデフォルト値を使用
            nodata_str = self.nodata_var.get().strip()
            nodata = float(nodata_str) if nodata_str else DEFAULT_NODATA
            
            # ボタンを無効化して処理中状態に
            self.run_button.config(state='disabled')
            self.status_var.set("処理中...")
            self.update()  # UIを即時更新

            # バックグラウンドで実行
            threading.Thread(
                target=self._run_conversion,
                args=(shp_path, field, output_path, nodata),
                daemon=True
            ).start()

        except ValueError as e:
            self.status_var.set("エラー: NoData値が無効です")
            messagebox.showerror("エラー", "NoData値は数値で指定してください。")
            self.run_button.config(state='normal')
        except Exception as e:
            self.status_var.set("エラーが発生しました")
            messagebox.showerror("エラー", f"予期せぬエラーが発生しました: {e}")
            self.run_button.config(state='normal')

    def _run_conversion(self, shp_path, field, output_path, nodata):
        """変換を実行する内部メソッド"""
        try:
            self.update_status("処理中...")
            # グリッド情報を取得
            grid_info = analyze_grid_structure(shp_path)
            
            self.update_status("処理中...")
            # 変換を実行
            ncols, nrows, dx, dy = shp_to_ascii(shp_path, field, output_path, nodata)
            
            # 完了メッセージをキューに追加
            self.message_queue.put(('status', '完了'))
            self.message_queue.put(('enable_button', True))
            
            # 結果を表示
            messagebox.showinfo(
                "完了",
                f"変換が完了しました。\n\n"
                f"出力先: {output_path}\n"
                f"セル数: {ncols} × {nrows}\n"
                f"セルサイズ: dx={dx:.12f}, dy={dy:.12f}"
            )
            
        except Exception as e:
            self.message_queue.put(('error', f"変換中にエラーが発生しました:\n{str(e)}"))

    def _check_queue(self):
        """キューをチェックしてGUIを更新する"""
        try:
            # キューからノンブロッキングでアイテムを取得
            message_type, data = self.queue.get_nowait()
            self.run_button.config(state='normal')
            self.status_var.set("完了")

            if message_type == 'success':
                ncols, nrows, dx, dy, outpath = data
                messagebox.showinfo(
                    "完了",
                    f"変換が完了しました。\n\n"
                    f"出力先: {outpath}\n"
                    f"セル数: {ncols} × {nrows}\n"
                    f"セルサイズ: dx={dx:.12f}, dy={dy:.12f}"
                )
            elif message_type == 'error':
                messagebox.showerror("エラー", f"変換中にエラーが発生しました:\n{data}")

        except queue.Empty:
            # キューが空なら、100ms後にもう一度チェック
            self.master.after(100, self._check_queue)

def main():
    root = tk.Tk()
    app = ShpToAscApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()

