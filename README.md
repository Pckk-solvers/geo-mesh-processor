# shp_to_asc_converter
シェープファイルをASCⅡ形式のラスタへ変換する。

memo
CSVについては列名は（X,Y）という形式にする。

src
 ┣ make_shp
 ┃ ┣ add_elevation.py
 ┃ ┣ generate_mesh.py
 ┃ ┗ mesh_elec_gui.py
 ┗ shp_to_asc
 ┃ ┣ core.py
 ┃ ┣ gui.py
 ┃ ┗ utils.py
