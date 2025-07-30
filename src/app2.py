import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.shp_to_asc.gui import ShpToAscApp
    from src.make_shp.elev_assigner_gui import ElevAssignerApp
    from src.make_shp.mesh_gen_gui import MeshGenApp
    from src.mesh_dominant_module.mesh_dominant_gui import MeshDominantApp
except ImportError as e:
    # モジュールが見つからない場合のエラーメッセージ
    import traceback
    print(f"エラー: GUIモジュールのインポートに失敗しました。 {e}")
    print("トレースバック:")
    traceback.print_exc()
    print("\nPythonパス:", sys.path)
    print("\nカレントディレクトリ:", os.getcwd())
    print("\n'src' ディレクトリが存在し、必要なスクリプトが含まれていることを確認してください。")


class MainLauncher:
    """地理空間情報ツール用のシンプルなTkinterランチャー"""
    def __init__(self, master):
        self.master = master
        master.title("地理空間情報ツール ランチャー")
        master.geometry("350x300")
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
            text="メッシュ生成",
            command=self.open_generate_mesh,
            style="Launcher.TButton"  # カスタムスタイルを適用
        ).pack(pady=5, fill='x')

        ttk.Button(
            main_frame,
            text="標高付与",
            command=self.open_elev_assigner,
            style="Launcher.TButton"  # カスタムスタイルを適用
        ).pack(pady=5, fill='x')

        ttk.Button(
            main_frame,
            text="土地利用区分コード付与",
            command=self.open_mesh_dominant,
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

    def open_mesh_dominant(self):
        """土地利用区分コード付与ツールを起動します。"""
        self.open_new_window(MeshDominantApp, "土地利用区分コード付与ツール")
    
    def open_elev_assigner(self):
        """標高付与ツールを起動します。"""
        self.open_new_window(ElevAssignerApp, "標高付与ツール")

    def open_generate_mesh(self):
        """メッシュ生成ツールを起動します。"""
        self.open_new_window(MeshGenApp, "メッシュ生成ツール")

if __name__ == "__main__":
    root = tk.Tk()
    app = MainLauncher(root)
    root.mainloop()
