#!/usr/bin/env python3
"""
メッシュ生成ツール (GUI)

計算領域と流域界からメッシュを生成するためのGUIツールです。
標準メッシュを使用した事前抽出にも対応しています。
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import threading
import queue
import tkinter.font as tkFont

from src.make_shp.mesh_generator import generate_mesh

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

class MeshGenApp(ttk.Frame):
    def __init__(self, master, initial_values=None):
        """
        初期化
        
        Args:
            master: 親ウィジェット
            initial_values (dict): 初期値設定用の辞書。以下のキーを指定可能
                - domain_shp: 計算領域シェープファイルパス
                - basin_shp: 流域界シェープファイルパス
                - cells: メッシュの分割数
                - out_dir: 出力ディレクトリ
                - standard_mesh: 標準メッシュファイルパス
                - mesh_id: 標準メッシュのID列名
        """
        
        super().__init__(master)
        self.master = master
        master.title('メッシュ生成ツール')
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
        
        # 計算領域シェープファイル
        ttk.Label(left_frame, text="計算領域ポリゴン (.shp):", width=LABEL_WIDTH, anchor='e').grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.domain_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.domain_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text="参照", command=self.browse_domain).grid(
            row=0, column=2, padx=5, pady=5)
        
        # 流域界シェープファイル
        ttk.Label(left_frame, text="流域界ポリゴン (.shp):", width=LABEL_WIDTH, anchor='e').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.basin_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.basin_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(left_frame, text="参照", command=self.browse_basin).grid(
            row=1, column=2, padx=5, pady=5)
        
        # メッシュ分割数
        ttk.Label(left_frame, text="メッシュ分割数:", width=LABEL_WIDTH, anchor='e').grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.cells_var = tk.StringVar(value="20")
        ttk.Spinbox(left_frame, from_=1, to=1000, textvariable=self.cells_var, width=10).grid(
            row=2, column=1, padx=5, pady=5, sticky='w')
        
        # 出力フォルダ
        ttk.Label(left_frame, text="出力フォルダ:", width=LABEL_WIDTH, anchor='e').grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.outdir_var = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.outdir_var, width=ENTRY_WIDTH, state='readonly').grid(
            row=3, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        ttk.Button(left_frame, text="参照", command=self.browse_outdir, width=BUTTON_WIDTH).grid(
            row=3, column=2, sticky='e', padx=5, pady=5)
        
        # ステータス & 実行ボタン
        self.status_var = tk.StringVar()
        ttk.Label(left_frame, textvariable=self.status_var, anchor='w').grid(
            row=4, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        self.run_button = ttk.Button(left_frame, text='実行', command=self.run_process, width=BUTTON_WIDTH)
        self.run_button.grid(row=4, column=2, sticky='e', padx=5, pady=5)
        
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
【計算領域ポリゴン (.shp）】
計算領域のポリゴンシェープファイルを選択してください。

【流域界ポリゴン (.shp）】
RRI計算対象領域となる流域のポリゴンシェープファイルを選択してください。

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

【出力フォルダ】
結果ファイルを保存するフォルダを選択してください。

【出力されるデータ】
1. domain_standard_mesh
   - 説明: 計算領域が含まれる標準地域メッシュのポリゴンデータ
   - 内容: 標準的な地域メッシュを計算領域で切り出したもの
   - 用途: 本アプリの他ツールでは使用しません

2. domain_mesh
   - 説明: 計算領域をカバーするように生成されたメッシュ
   - 内容: 標準地域メッシュをベースにした計算領域メッシュ
   - 用途: 標高・土地利用区分コード付与ツールの入力データ（計算領域メッシュ）として使用

3. basin_mesh
   - 説明: 流域界に基づいて生成されたメッシュ
   - 内容: 標準地域メッシュを流域界で区切ったもの
   - 用途: 標高コード付与ツールの入力データ（流域メッシュ）として使用
        """.strip()

        self.help_text.config(state='normal')
        self.help_text.insert('1.0', help_body)
        self.help_text.config(state='disabled')

    def _set_initial_values(self):
        """初期値を設定"""
        if not self.initial_values:
            return
            
        if 'domain_shp' in self.initial_values:
            self.domain_var.set(self.initial_values['domain_shp'])
        if 'basin_shp' in self.initial_values:
            self.basin_var.set(self.initial_values['basin_shp'])
        if 'cells' in self.initial_values:
            self.cells_var.set(str(self.initial_values['cells']))
        if 'out_dir' in self.initial_values:
            self.outdir_var.set(self.initial_values['out_dir'])


    def browse_domain(self):
        """計算領域シェープファイルを選択"""
        path = filedialog.askopenfilename(filetypes=[('Shapefile', '*.shp')])
        if path:
            self.domain_var.set(path)

    def browse_basin(self):
        """流域界シェープファイルを選択"""
        path = filedialog.askopenfilename(filetypes=[('Shapefile', '*.shp')])
        if path:
            self.basin_var.set(path)

    def browse_outdir(self):
        """出力ディレクトリを選択"""
        path = filedialog.askdirectory()
        if path:
            self.outdir_var.set(path)


    def run_process(self):
        """メッシュ生成処理を実行"""
        # 入力チェック
        if not all([self.domain_var.get(), self.basin_var.get(), self.outdir_var.get()]):
            messagebox.showerror('エラー', '必須項目が入力されていません。')
            return

        # ボタンを無効化
        self.status_var.set('処理を実行中...')
        self.master.config(cursor='wait')
        self.update()

        # 別スレッドで処理を実行
        threading.Thread(target=self._run_in_thread, daemon=True).start()

    def _run_in_thread(self):
        """別スレッドで実行する処理"""
        try:
            generate_mesh(
                domain_shp=self.domain_var.get(),
                basin_shp=self.basin_var.get(),
                cells=int(self.cells_var.get()),
                out_dir=self.outdir_var.get(),
                standard_mesh=STANDARD_MESH,
                mesh_id=MESH_ID
            )
            self.result_queue.put(('success', 'メッシュの生成が完了しました'))
        except Exception as e:
            self.result_queue.put(('error', f'エラーが発生しました: {str(e)}'))

    def check_queue(self):
        """キューをチェックして結果を処理"""
        try:
            message_type, message = self.result_queue.get_nowait()
            
            if message_type == 'success':
                messagebox.showinfo('完了', message)
                self.status_var.set('完了')
            else:
                messagebox.showerror('エラー', message)
                self.status_var.set('エラーが発生しました')
                
            self.master.config(cursor='')
            self.result_queue.task_done()
            
        except queue.Empty:
            pass
            
        self.after(100, self.check_queue)

def main():
    """メイン関数"""
    root = tk.Tk()
    app = MeshGenApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
