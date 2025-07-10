# mesh_elev_gui.py
#!/usr/bin/env python3
"""
Tkinter ベースの簡易 GUI。
内部で generate_mesh.py → add_elevation.py を順に呼び出します。
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mesh & Elevation Generator")
        self.create_widgets()

    def create_widgets(self):
        # Domain SHP
        tk.Label(self, text="Domain SHP:").grid(row=0, column=0, sticky="e")
        self.domain_var = tk.StringVar()
        tk.Entry(self, textvariable=self.domain_var, width=50).grid(row=0, column=1)
        tk.Button(self, text="Browse", command=self.browse_domain).grid(row=0, column=2)

        # Basin SHP
        tk.Label(self, text="Basin SHP:").grid(row=1, column=0, sticky="e")
        self.basin_var = tk.StringVar()
        tk.Entry(self, textvariable=self.basin_var, width=50).grid(row=1, column=1)
        tk.Button(self, text="Browse", command=self.browse_basin).grid(row=1, column=2)

        # Points CSV
        tk.Label(self, text="Points CSV:").grid(row=2, column=0, sticky="e")
        self.points_var = tk.StringVar()
        tk.Entry(self, textvariable=self.points_var, width=50).grid(row=2, column=1)
        tk.Button(self, text="Browse", command=self.browse_points).grid(row=2, column=2)

        # Cell size
        tk.Label(self, text="Cell size:").grid(row=3, column=0, sticky="e")
        self.cell_var = tk.StringVar()
        tk.Entry(self, textvariable=self.cell_var, width=20).grid(row=3, column=1, sticky="w")

        # Output dir
        tk.Label(self, text="Output Dir:").grid(row=4, column=0, sticky="e")
        self.outdir_var = tk.StringVar(value="./outputs")
        tk.Entry(self, textvariable=self.outdir_var, width=50).grid(row=4, column=1)
        tk.Button(self, text="Browse", command=self.browse_outdir).grid(row=4, column=2)

        # Run / Exit
        tk.Button(self, text="Run", command=self.run_process).grid(row=5, column=1, sticky="e")
        tk.Button(self, text="Exit", command=self.quit).grid(row=5, column=2, sticky="w")

    def browse_domain(self):
        p = filedialog.askopenfilename(filetypes=[("Shapefile","*.shp")])
        if p: self.domain_var.set(p)

    def browse_basin(self):
        p = filedialog.askopenfilename(filetypes=[("Shapefile","*.shp")])
        if p: self.basin_var.set(p)

    def browse_points(self):
        p = filedialog.askopenfilename(filetypes=[("CSV","*.csv"),("Text","*.txt"),("Shapefile","*.shp")])
        if p: self.points_var.set(p)

    def browse_outdir(self):
        p = filedialog.askdirectory()
        if p: self.outdir_var.set(p)

    def run_process(self):
        domain = self.domain_var.get()
        basin  = self.basin_var.get()
        points = self.points_var.get()
        cell   = self.cell_var.get()
        outdir = self.outdir_var.get()

        if not all([domain, basin, points, cell, outdir]):
            messagebox.showerror("Error", "すべての入力を指定してください")
            return

        os.makedirs(outdir, exist_ok=True)

        cmd1 = f"{sys.executable} generate_mesh.py --domain \"{domain}\" --basin \"{basin}\" --cell {cell} --outdir \"{outdir}\""
        cmd2 = f"{sys.executable} add_elevation.py --basin_mesh \"{outdir}/basin_mesh.shp\" --domain_mesh \"{outdir}/domain_mesh.shp\" --points \"{points}\" --outdir \"{outdir}\""
        try:
            subprocess.check_call(cmd1, shell=True)
            subprocess.check_call(cmd2, shell=True)
            messagebox.showinfo("Success", "処理が完了しました！")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"処理中にエラーが発生しました:\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
