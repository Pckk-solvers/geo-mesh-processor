import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

try:
    from shp_to_asc.gui import ShpToAscApp
    from make_shp.mesh_elev_gui import MeshElevApp
except ImportError as e:
    # モジュールが見つからない場合に備えて、分かりやすいエラーメッセージを表示します
    print(f"エラー: GUIモジュールのインポートに失敗しました。 {e}")
    print("'src' ディレクトリが存在し、必要なスクリプトが含まれていることを確認してください。")
    sys.exit(1)


class MainLauncher:
    """地理空間情報ツール用のシンプルなTkinterランチャー"""
    def __init__(self, master):
        self.master = master
        master.title("地理空間情報ツール ランチャー")
        master.geometry("350x250")
        master.resizable(False, False)

        # スタイルの設定
        style = ttk.Style()
        # "Launcher.TButton" というカスタムスタイルを作成します
        style.configure("Launcher.TButton", padding=8, font=(10))

        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(expand=True, fill="y")

        ttk.Label(main_frame, text="起動するツールを選択してください:", font=(11)).pack(pady=(0, 10))

        ttk.Button(
            main_frame,
            text="メッシュ生成と標高付与",
            command=self.open_mesh_elev,
            style="Launcher.TButton"  # カスタムスタイルを適用
        ).pack(pady=5, fill='x')

        ttk.Button(
            main_frame,
            text="Shapefile → ASCII 変換",
            command=self.open_shp_to_asc,
            style="Launcher.TButton"  # カスタムスタイルを適用
        ).pack(pady=5, fill='x')


    def open_new_window(self, app_class, title):
        """指定されたアプリケーションクラスの新しいトップレベルウィンドウを開きます。"""
        try:
            window = tk.Toplevel(self.master)
            window.title(title)
            app = app_class(window)
        except Exception as e:
            messagebox.showerror("エラー", f"アプリケーションの起動に失敗しました: {e}")

    def open_shp_to_asc(self):
        """ShapefileからASCIIへの変換ツールを起動します。"""
        self.open_new_window(ShpToAscApp, "Shapefile → ASCII 変換ツール")

    def open_mesh_elev(self):
        """メッシュ生成と標高付与ツールを起動します。"""
        self.open_new_window(MeshElevApp, "メッシュ生成と標高付与ツール")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainLauncher(root)
    root.mainloop()
