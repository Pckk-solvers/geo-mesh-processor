#!/usr/bin/env python3
"""
標高付与ツール (GUI)

流域メッシュと計算領域メッシュに標高値を付与するためのGUIツールです。
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from src.make_shp.add_elevation import get_xy_columns, get_z_candidates
import pandas as pd
import threading
import queue
import tkinter.font as tkFont

from src.make_shp.elevation_assigner import add_elevation

# ベースディレクトリの設定
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

class ElevAssignerApp(ttk.Frame):
    def __init__(self, master, initial_values=None):
        """
        初期化
        
        Args:
            master: 親ウィジェット
            initial_values (dict): 初期値設定用の辞書
        """
        super().__init__(master)
        self.master = master
        master.title('標高付与ツール')
        self.initial_values = initial_values or {}

        # メインフレームの設定
        self.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # ウィジェットの作成
        self.create_widgets()
        
        # 初期値の設定
        self._set_initial_values()
        
        # ウィンドウの最小サイズを設定
        self.update_idletasks()
        master.minsize(600, 300)
        
        # 非同期処理用のキュー
        self.result_queue = queue.Queue()
        self.after(100, self.check_queue)

    def create_widgets(self):
        """ウィジェットを作成"""
        # 左右分割用のPanedWindow
        paned = ttk.PanedWindow(self, orient='horizontal')
        paned.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        # 左ペイン：入力項目用フレーム
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=0)

        # 右ペイン：ヘルプガイド用フレーム
        help_frame = ttk.LabelFrame(paned, text='使い方ガイド')
        paned.add(help_frame, weight=1)

        # 定数定義
        LABEL_WIDTH  = 20
        ENTRY_WIDTH  = 40
        BUTTON_WIDTH = 12
        
        # 計算領域シェープファイル
        ttk.Label(left_frame, text="計算領域メッシュ (.shp):", width=LABEL_WIDTH, anchor='e').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.domain_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.domain_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text="参照", command=self.browse_domain, width=BUTTON_WIDTH).grid(
            row=0, column=2, padx=5, pady=5)
        
        # 流域界シェープファイル
        ttk.Label(left_frame, text="流域界メッシュ (.shp):", width=LABEL_WIDTH, anchor='e').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.basin_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.basin_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text="参照", command=self.browse_basin, width=BUTTON_WIDTH).grid(
            row=1, column=2, padx=5, pady=5)
        
        # 点群ファイル（複数選択可）
        ttk.Label(left_frame, text="点群ファイル (.csv):", width=LABEL_WIDTH, anchor='e').grid(
            row=2, column=0, sticky='w', padx=5, pady=5)
        self.points_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.points_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text="参照", command=self.browse_points, width=BUTTON_WIDTH).grid(
            row=2, column=2, padx=5, pady=5)
        
        # 標高値列 Combobox
        ttk.Label(left_frame, text='標高値列:',
                  width=LABEL_WIDTH, anchor='e').grid(row=3, column=0, padx=5, pady=5)
        self.z_var = tk.StringVar()
        self.z_combo = ttk.Combobox(left_frame, textvariable=self.z_var, values=[], width=ENTRY_WIDTH, state='readonly')
        self.z_combo.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        self.z_combo['state'] = 'readonly'
        
        # NODATA値
        ttk.Label(left_frame, text="NODATA値:", width=LABEL_WIDTH, anchor='e').grid(
            row=4, column=0, sticky='w', padx=5, pady=5)
        self.nodata_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.nodata_var, width=ENTRY_WIDTH).grid(
            row=4, column=1, padx=5, pady=5, sticky='w')
        self.nodata_var.set('-9999')
        
        # 出力フォルダ
        ttk.Label(left_frame, text="出力フォルダ:", width=LABEL_WIDTH, anchor='e').grid(
            row=5, column=0, sticky='w', padx=5, pady=5)
        self.outdir_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.outdir_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=5, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text="参照", command=self.browse_outdir, width=BUTTON_WIDTH).grid(
            row=5, column=2, padx=5, pady=5)
        
        # ステータス & 実行ボタン
        self.status_var = tk.StringVar()
        ttk.Label(left_frame, textvariable=self.status_var, anchor='w').grid(
            row=6, column=0, columnspan=2, sticky='w', padx=5, pady=10)
        
        self.run_button = ttk.Button(left_frame, text='実行', command=self.run_process, width=BUTTON_WIDTH)
        self.run_button.grid(row=6, column=2, sticky='e', padx=5, pady=10)
        
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
【メッシュ化済み計算領域 (.shp）】
計算領域のメッシュ化済みポリゴンシェープファイルを選択してください。

【メッシュ化済み流域界 (.shp）】
流域界のメッシュ化済みポリゴンシェープファイルを選択してください。

【点群データ (.csv）】
・標高値を含むCSVファイル
・座標の項目名はx,y(X,Y)を遵守してください。
・複数の点群データを指定する場合、列名を統一するようにしてください。

【標高値列】
CSVデータ内の標高値の列名を選択してください。

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
        
    def _set_initial_values(self):
        """初期値を設定"""
        if not self.initial_values:
            return
            
        if 'basin' in self.initial_values:
            self.basin_var.set(self.initial_values['basin'])
        if 'domain' in self.initial_values:
            self.domain_var.set(self.initial_values['domain'])
        if 'points' in self.initial_values:
            self.points_var.set(';'.join(self.initial_values['points']))
            self._update_z_candidates(self.points_var.get().split(';'))
        if 'zcol' in self.initial_values:
            self.z_var.set(self.initial_values['zcol'])
        if 'nodata' in self.initial_values:
            self.nodata_var.set(str(self.initial_values['nodata']))
        if 'out_dir' in self.initial_values:
            self.outdir_var.set(self.initial_values['out_dir'])

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

    def browse_basin(self):
        """流域メッシュを選択"""
        path = filedialog.askopenfilename(filetypes=[('Shapefile', '*.shp')])
        if path:
            self.basin_var.set(path)

    def browse_domain(self):
        """計算領域メッシュを選択"""
        path = filedialog.askopenfilename(filetypes=[('Shapefile', '*.shp')])
        if path:
            self.domain_var.set(path)

    def browse_points(self):
        """点群ファイルを選択（複数可）"""
        paths = filedialog.askopenfilenames(
            filetypes=[('CSV', '*.csv')],
            title='点群ファイルを選択（複数可）'
        )
        if paths:
            # 既存のパスと結合（あれば）
            current = self.points_var.get()
            if current:
                current_paths = current.split(';')
                paths = list(set(current_paths + list(paths)))  # 重複を除去
            self.points_var.set(';'.join(paths))
            # 標高値列の候補を更新
            self._update_z_candidates(paths)

    def browse_outdir(self):
        """出力ディレクトリを選択"""
        path = filedialog.askdirectory()
        if path:
            self.outdir_var.set(path)

    def validate_inputs(self):
        """入力チェック"""
        if not all([self.basin_var.get(), self.domain_var.get(), self.points_var.get()]):
            messagebox.showerror('エラー', '必須項目が入力されていません。')
            return False
        
        # 点群ファイルの存在確認
        for path in self.points_var.get().split(';'):
            if not os.path.exists(path):
                messagebox.showerror('エラー', f'指定されたファイルが見つかりません: {path}')
                return False
                
        return True

    def run_process(self):
        """標高付与処理を実行"""
        if not self.validate_inputs():
            return

        # ボタンを無効化
        self.run_button.config(state='disabled')
        self.status_var.set('処理を実行中...')
        
        # 別スレッドで実行
        threading.Thread(target=self._run_in_thread, daemon=True).start()

    def _run_in_thread(self):
        """別スレッドで実行する処理"""
        try:
            points = self.points_var.get().split(';')
            zcol = self.z_var.get() if self.z_var.get() else None
            nodata = float(self.nodata_var.get()) if self.nodata_var.get() else None
            
            add_elevation(
                basin_mesh=self.basin_var.get(),
                domain_mesh=self.domain_var.get(),
                points_path=points,
                out_dir=self.outdir_var.get(),
                zcol=zcol,
                nodata=nodata
            )
            self.result_queue.put(('success', '標高付与が完了しました'))
        except Exception as e:
            self.result_queue.put(('error', str(e)))

    def check_queue(self):
        """キューをチェックして結果を処理"""
        try:
            while True:
                result_type, message = self.result_queue.get_nowait()
                if result_type == 'success':
                    messagebox.showinfo('完了', message)
                else:
                    messagebox.showerror('エラー', message)
                self.status_var.set(message)
                self.run_button.config(state='normal')
        except queue.Empty:
            pass
        
        # 100ms後に再チェック
        self.after(100, self.check_queue)

def main():
    """メイン関数"""
    root = tk.Tk()
    app = ElevAssignerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
