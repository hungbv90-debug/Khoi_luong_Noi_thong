import sys

file_path = r'd:\Antigravity_Phan_Tich\AI_suport_work (app lẻ)\Check_KL_Ngam_XHH\streamlit_app.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace db init
old_init = content[content.find('if "db_ket_cau" not in st.session_state:'):content.find('    }\n')+5]

new_init = '''def init_db_ket_cau():
    db = {}
    for loai in ["Asphalt", "Hè bê tông", "Đường bê tông", "Terrazo"]:
        for so_ong in [1, 2, 3]:
            for noi in ["Bể - Bể", "Ganivo - Ganivo, Bể"]:
                key = f"{loai} {so_ong} ống ({noi})"
                if so_ong == 1:
                    wt, wb = 0.35, 0.25
                elif so_ong == 2:
                    wt, wb = 0.45, 0.35
                else: 
                    wt, wb = 0.45, 0.35
                
                h_def = 0.91
                layers = []
                if noi == "Bể - Bể":
                    if loai == "Asphalt":
                        h_def = 0.91 if so_ong < 3 else 1.05
                        layers = [ {"name": "BT nhựa hạt mịn", "h": 0.05, "type": "m2"}, {"name": "BT nhựa hạt trung", "h": 0.07, "type": "m3"}, {"name": "Đá dăm loại 1", "h": 0.18, "type": "m3"}, {"name": "Đá dăm loại 2", "h": 0.25, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                    elif loai == "Hè bê tông":
                        h_def = 0.85 if so_ong == 3 else 0.71
                        ten_bt = "Bê tông mác 250"
                        ten_dat = "Đất đầm chặt K=0.95" if so_ong == 3 else "Đất đầm chặt k=0.95"
                        layers = [ {"name": ten_bt, "h": 0.10, "type": "m3"}, {"name": ten_dat, "h": 0.25, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                    elif loai == "Đường bê tông":
                        h_def = 1.05 if so_ong == 3 else 0.91
                        ten_bt = "Bê tông mác 250"
                        ten_dat = "Đất đầm chặt K=0.95" if so_ong == 3 else "Đất đầm chặt k=0.95"
                        layers = [ {"name": ten_bt, "h": 0.20, "type": "m3"}, {"name": ten_dat, "h": 0.35, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                    elif loai == "Terrazo":
                        h_def = 0.85 if so_ong == 3 else 0.71
                        layers = [ {"name": "Lát gạch terazo,BT,đá xanh + vữa", "h": 0.05, "type": "m2"}, {"name": "Bê tông M150", "h": 0.08, "type": "m3"}, {"name": "Đất đầm chặt k=0.95", "h": 0.22, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                else:
                    if loai == "Asphalt":
                        h_def = 0.60
                        layers = [ {"name": "BT nhựa hạt mịn", "h": 0.05, "type": "m2"}, {"name": "BT nhựa hạt trung", "h": 0.07, "type": "m3"}, {"name": "Đá dăm loại 1", "h": 0.18, "type": "m3"}, {"name": "Bê tông M150", "h": 0.10, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                    elif loai == "Hè bê tông":
                        h_def = 0.60
                        layers = [ {"name": "Bê tông mác 250", "h": 0.10, "type": "m3"}, {"name": "Đất đầm chặt k=0.95", "h": 0.14, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                    elif loai == "Đường bê tông":
                        h_def = 0.60
                        layers = [ {"name": "Bê tông mác 250", "h": 0.20, "type": "m3"}, {"name": "Đất đầm chặt k=0.95", "h": 0.10, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                    elif loai == "Terrazo":
                        h_def = 0.60
                        layers = [ {"name": "Lát gạch terazo,BT,đá xanh + vữa", "h": 0.05, "type": "m2"}, {"name": "Bê tông M150", "h": 0.08, "type": "m3"}, {"name": "Đất đầm chặt K=0.95", "h": 0.11, "type": "m3"}, {"name": "Cát đen đầm chặt", "h": "Auto", "type": "m3"} ]
                
                db[key] = { "W_top": wt, "W_bot": wb, "H_def": h_def, "layers": layers }
    return db

# Force refresh if the database is old
if "db_ket_cau" not in st.session_state or "đá 2x4" in str(st.session_state.db_ket_cau) or st.session_state.db_ket_cau.get("Terrazo 3 ống (Bể - Bể)", {}).get("W_top") == 0.55:
    st.session_state.db_ket_cau = init_db_ket_cau()
'''
content = content.replace(old_init, new_init)

# Replace map_ket_cau
old_map = '''def map_ket_cau(raw_str, so_ong):
    raw = str(raw_str).upper()
    ong_str = f"{so_ong} ống" if so_ong in [1, 2, 3] else "1 ống"
    
    if "AL" in raw:
        return f"Asphalt {ong_str}"
    elif "HBT" in raw:
        return f"Hè bê tông {ong_str}"
    elif "ĐBT" in raw:
        return f"Đường bê tông {ong_str}"
    elif "TE" in raw:
        return f"Terrazo {ong_str}"
    
    # Mặc định fallback
    return f"Asphalt {ong_str}"'''

new_map = '''def map_ket_cau(raw_str, so_ong, h_val=0.91):
    raw = str(raw_str).upper()
    ong_str = f"{so_ong} ống" if so_ong in [1, 2, 3] else "1 ống"
    
    if "AL" in raw: loai = "Asphalt"
    elif "HBT" in raw: loai = "Hè bê tông"
    elif "ĐBT" in raw: loai = "Đường bê tông"
    elif "TE" in raw: loai = "Terrazo"
    else: loai = "Asphalt"
    
    noi_tu = "Ganivo - Ganivo, Bể" if h_val <= 0.6 else "Bể - Bể"
    
    return f"{loai} {ong_str} ({noi_tu})"'''
content = content.replace(old_map, new_map)

# Update map_ket_cau calls
content = content.replace('ket_cau = map_ket_cau(ket_cau_raw, so_ong)',
                          'H_temp = float(row["Độ sâu rãnh"]) if not pd.isna(row["Độ sâu rãnh"]) else 0.6\\n                ket_cau = map_ket_cau(ket_cau_raw, so_ong, H_temp)')

content = content.replace('H = float(row["Độ sâu rãnh"]) if not pd.isna(row["Độ sâu rãnh"]) else 0.6',
                          'H = H_temp')

# Update UI elements
old_ui_select = '''    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        so_ong_chon = st.selectbox("Chọn số ống trong rãnh:", options=[1, 2, 3], index=1)
    with col_sel3:
        loai_kc_chon = st.selectbox("Chọn xem loại kết cấu (Drop-down để chọn):", options=["Asphalt", "Hè bê tông", "Đường bê tông", "Terrazo"])
    
    selected_kc = f"{loai_kc_chon} {so_ong_chon} ống"
    
    h_temp = float(st.session_state.db_ket_cau.get(selected_kc, {}).get("H_def", 0.91))
    noi_options = ["Bể - Bể", "Ganivo - Ganivo, Bể"]
    def_idx = 0 if h_temp >= 0.71 else 1
    with col_sel2:
        noi_tu_chon = st.selectbox("Nối từ:", options=noi_options, index=def_idx)'''

new_ui_select = '''    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        so_ong_chon = st.selectbox("Chọn số ống trong rãnh:", options=[1, 2, 3], index=0)
    with col_sel3:
        loai_kc_chon = st.selectbox("Chọn xem loại kết cấu (Drop-down để chọn):", options=["Asphalt", "Hè bê tông", "Đường bê tông", "Terrazo"])
    
    noi_options = ["Bể - Bể", "Ganivo - Ganivo, Bể"]
    with col_sel2:
        noi_tu_chon = st.selectbox("Nối từ:", options=noi_options, index=1)

    selected_kc = f"{loai_kc_chon} {so_ong_chon} ống ({noi_tu_chon})"'''
content = content.replace(old_ui_select, new_ui_select)


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement done")
