import streamlit as st
import pandas as pd
import math
import io
import re
import hashlib
import json
import os
import urllib.request
import socket
from datetime import datetime, timezone, timedelta

# Create a constant for Vietnam timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

# --- CẤU HÌNH TRANG LÀM VIỆC ---
st.set_page_config(page_title="Công cụ Nối thông", layout="wide")

# ==========================================
# HỆ THỐNG XÁC THỰC (AUTHENTICATION SYSTEM)
# ==========================================

# Đường dẫn file lưu trữ dữ liệu người dùng
_USER_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data.json")

def _hash_pw(password):
    """Băm mật khẩu bằng SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def _load_users():
    """Tải danh sách người dùng từ file JSON."""
    if os.path.exists(_USER_DB_PATH):
        try:
            with open(_USER_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Dữ liệu mặc định với tài khoản admin
    return {
        "hungbv14": {
            "password_hash": "f4b9032ee7ad594c5dcf927e707a6fb4f1e288b4f2de6cbd6a97e1e0ca57d88a",
            "role": "admin",
            "display_name": "Admin - HungBV14",
            "created_at": "2026-03-06T18:34:00",
            "last_login": None,
            "login_count": 0,
            "last_ip": "N/A",
            "last_location": "N/A"
        }
    }

def _save_users(users):
    """Lưu danh sách người dùng vào file JSON."""
    try:
        with open(_USER_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Lỗi lưu dữ liệu người dùng: {e}")

def _get_client_ip():
    """Lấy IP của người dùng."""
    # Thử qua st.context (Mới nhất)
    try:
        from streamlit import context
        headers = context.headers
        ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", ""))
        if ip: return ip.split(",")[0].strip()
    except:
        pass
    
    return "Local/Unknown"

def _get_location_from_ip(ip):
    """Phân giải IP thành vị trí địa lý dùng API miễn phí ip-api.com."""
    if not ip or ip in ["Local/Unknown", "127.0.0.1", "::1"]:
        return "Mạng nội bộ (Local)"
    try:
        req = urllib.request.Request(f"http://ip-api.com/json/{ip}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 'success':
                city = data.get('city', '')
                region = data.get('regionName', '')
                return f"{city}, {region}"
    except:
        pass
    return "Không xác định"

def _record_login(username):
    """Ghi nhận thời gian đăng nhập và vị trí IP."""
    users = _load_users()
    if username in users:
        users[username]["last_login"] = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
        users[username]["login_count"] = users[username].get("login_count", 0) + 1
        
        # Lưu vết IP và địa điểm
        client_ip = _get_client_ip()
        users[username]["last_ip"] = client_ip
        users[username]["last_location"] = _get_location_from_ip(client_ip)
        
        _save_users(users)
def _record_activity(username):
    """Ghi nhận hoạt động gần nhất (heartbeat)."""
    if "active_users" not in st.session_state:
        st.session_state.active_users = {}
    st.session_state.active_users[username] = datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")

def _authenticate(username):
    """Xác thực người dùng. Không còn yêu cầu mật khẩu ở đây."""
    users = _load_users()
    
    if username in users:
        return True, users[username]
    else:
        # Tự động tạo user mới nếu chưa có
        new_user = {
            "role": "user",
            "display_name": username,
            "created_at": datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "last_login": None,
            "login_count": 0
        }
        users[username] = new_user
        _save_users(users)
        return True, new_user

def _show_login_page():
    """Hiển thị trang đăng nhập."""
    st.markdown("""
    <style>
    .login-container { max-width: 400px; margin: 5rem auto; padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); }
    .login-header { text-align: center; color: white; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem; }
    .login-sub { text-align: center; color: rgba(255,255,255,0.8); font-size: 0.9rem; margin-bottom: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-header">🔐 Đăng nhập hệ thống</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Công cụ Kiểm tra Khối lượng Nối thông - FPT Telecom</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            # Lấy tên người dùng đã lưu từ query params nếu có
            saved_username = st.query_params.get("saved_user", "")
            
            username = st.text_input("👤 Tên sử dụng", value=saved_username, placeholder="Nhập tên của bạn để bắt đầu...")
            # Bỏ mật khẩu ở màn hình chính theo yêu cầu
            remember_me = st.checkbox("Ghi nhớ tên sử dụng trên thiết bị này", value=bool(saved_username))
            
            submit = st.form_submit_button("🚀 Bắt đầu", use_container_width=True, type="primary")
            
            if submit:
                if not username:
                    st.error("Vui lòng nhập tên sử dụng!")
                else:
                    success, user_info = _authenticate(username)
                    if success:
                        if remember_me:
                            st.query_params["saved_user"] = username
                        else:
                            if "saved_user" in st.query_params:
                                del st.query_params["saved_user"]
                                
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_role = user_info["role"]
                        st.session_state.display_name = user_info.get("display_name", username)
                        _record_login(username)
                        st.rerun()
        


def _show_admin_panel():
    """Hiển thị trang quản trị."""
    st.markdown("### 🔧 Bảng Quản Trị (Admin Panel)")
    
    users = _load_users()
    
    admin_tab1, admin_tab2 = st.tabs(["👥 Quản lý người dùng", "➕ Thêm tài khoản"])
    
    with admin_tab1:
        st.markdown("#### Danh sách tất cả tài khoản")
        user_rows = []
        for uname, udata in users.items():
            user_rows.append({
                "Tài khoản": uname,
                "Tên hiển thị": udata.get("display_name", ""),
                "Vai trò": "🔴 Admin" if udata.get("role") == "admin" else "🟢 User",
                "Đăng nhập lần cuối": udata.get("last_login", "Chưa đăng nhập"),
                "Số lần đăng nhập": udata.get("login_count", 0),
                "IP Cuối": udata.get("last_ip", "N/A"),
                "Vị trí": udata.get("last_location", "N/A"),
                "Ngày tạo": udata.get("created_at", "N/A")
            })
        
        if user_rows:
            df_users = pd.DataFrame(user_rows)
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### ⚙️ Quản lý tài khoản")
        
        # Xóa tài khoản
        deletable = [u for u in users.keys() if u != st.session_state.username]
        if deletable:
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                del_user = st.selectbox("Chọn tài khoản cần xóa:", deletable)
            with col_del2:
                if st.button("🗑️ Xóa", type="primary", use_container_width=True):
                    del users[del_user]
                    _save_users(users)
                    st.success(f"Đã xóa tài khoản '{del_user}'")
                    st.rerun()

    with admin_tab2:
        st.markdown("#### Tạo tài khoản mới")
        with st.form("add_user_form"):
            new_username = st.text_input("Tài khoản mới:", placeholder="vd: nguyenvana")
            new_display = st.text_input("Tên hiển thị:", placeholder="vd: Nguyễn Văn A - CN Đà Nẵng")
            new_role = st.selectbox("Vai trò:", ["user", "admin"])
            
            if st.form_submit_button("✅ Tạo tài khoản", use_container_width=True, type="primary"):
                if not new_username or not new_display:
                    st.error("Vui lòng điền đầy đủ thông tin!")
                elif new_username in users:
                    st.error(f"Tài khoản '{new_username}' đã tồn tại!")
                else:
                    users[new_username] = {
                        "role": new_role,
                        "display_name": new_display,
                        "created_at": datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                        "last_login": None,
                        "login_count": 0
                    }
                    _save_users(users)
                    st.success(f"✅ Đã tạo tài khoản '{new_username}' ({new_display})")

# --- TỰ ĐỘNG ĐĂNG NHẬP ---
if "authenticated" not in st.session_state:
    computer_name = socket.gethostname()
    st.session_state.authenticated = True
    st.session_state.username = computer_name
    st.session_state.user_role = "user"
    st.session_state.display_name = f"Máy: {computer_name}"
    _authenticate(computer_name) # Tạo user nếu chưa có
    _record_login(computer_name) # Ghi nhận lần đầu truy cập

# Ghi nhận hoạt động
_record_activity(st.session_state.username)

# Xử lý trang Admin
if st.session_state.get("show_admin", False):
    with st.sidebar:
        if st.button("⬅️ Quay lại Ứng dụng", use_container_width=True):
            st.session_state.show_admin = False
            st.rerun()
    
    # Kiểm tra mật khẩu admin (232109)
    if not st.session_state.get("admin_verified", False):
        st.markdown("### 🔐 Xác thực Quyền Quản trị")
        admin_pw = st.text_input("Nhập mật khẩu quản trị để tiếp tục:", type="password")
        if st.button("Xác nhận", type="primary"):
            if admin_pw == "232109":
                st.session_state.admin_verified = True
                st.rerun()
            else:
                st.error("❌ Mật khẩu không chính xác!")
        st.stop()
        
    _show_admin_panel()
    st.stop()
# --- CSS TÙY CHỈNH ĐỂ GỌN GIAO DIỆN ---
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    [data-testid="stSidebar"] {
        padding-top: 1rem;
    }
    /* Đảm bảo bảng hiển thị đủ chữ, tự động xuống dòng */
    table {
        width: 100%;
        table-layout: auto !important;
    }
    th, td {
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# KNOWLEDGE BASE (CƠ SỞ DỮ LIỆU CHUẨN)
# ==========================================

def init_db_ket_cau():
    db = {}
    for loai in ["Asphalt", "Hè bê tông", "Đường bê tông", "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá", "Đất cấp 2", "Đất cấp 3"]:
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
                name_cat = "Cát đen đầm chặt"
                name_dat = "Đất đầm chặt K=0.95"
                if noi == "Bể - Bể":
                    if loai == "Asphalt":
                        h_def = 0.91 if so_ong < 3 else 1.05
                        layers = [ {"name": "BT nhựa hạt mịn", "h": 0.05, "type": "m2"}, {"name": "BT nhựa hạt trung", "h": 0.07, "type": "m3"}, {"name": "Đá dăm loại 1", "h": 0.18, "type": "m3"}, {"name": "Đá dăm loại 2", "h": 0.25, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                    elif loai == "Hè bê tông":
                        h_def = 0.85 if so_ong == 3 else 0.71
                        ten_bt = "Bê tông mác 250"
                        layers = [ {"name": ten_bt, "h": 0.10, "type": "m3"}, {"name": name_dat, "h": 0.25, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                    elif loai == "Đường bê tông":
                        h_def = 1.05 if so_ong == 3 else 0.91
                        ten_bt = "Bê tông mác 250"
                        layers = [ {"name": ten_bt, "h": 0.20, "type": "m3"}, {"name": name_dat, "h": 0.35, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                    elif loai == "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá":
                        h_def = 0.85 if so_ong == 3 else 0.71
                        layers = [ {"name": "Lát gạch terrazzo,BT,đá xanh + vữa", "h": 0.05, "type": "m2"}, {"name": "Bê tông M150", "h": 0.08, "type": "m3"}, {"name": name_dat, "h": 0.22, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                else:
                    if loai == "Asphalt":
                        h_def = 0.60
                        layers = [ {"name": "BT nhựa hạt mịn", "h": 0.05, "type": "m2"}, {"name": "BT nhựa hạt trung", "h": 0.07, "type": "m3"}, {"name": "Đá dăm loại 1", "h": 0.18, "type": "m3"}, {"name": "Bê tông M150", "h": 0, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                    elif loai == "Hè bê tông":
                        h_def = 0.60
                        layers = [ {"name": "Bê tông mác 250", "h": 0.10, "type": "m3"}, {"name": name_dat, "h": 0.14, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                    elif loai == "Đường bê tông":
                        h_def = 0.60
                        layers = [ {"name": "Bê tông mác 250", "h": 0.20, "type": "m3"}, {"name": name_dat, "h": 0.10, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                    elif loai == "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá":
                        h_def = 0.60
                        layers = [ {"name": "Lát gạch terrazzo,BT,đá xanh + vữa", "h": 0.05, "type": "m2"}, {"name": "Bê tông M150", "h": 0.08, "type": "m3"}, {"name": name_dat, "h": 0.11, "type": "m3"}, {"name": name_cat, "h": "Auto", "type": "m3"} ]
                
                db[key] = { "W_top": wt, "W_bot": wb, "H_def": h_def, "layers": layers }
                
    name_cat = "Cát đen đầm chặt"
    name_dat = "Đất đầm chặt K=0.95"
    db["Hè bê tông 4 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.85, 
        "layers": [ 
            {"name": "Bê tông mác 250", "h": 0.10, "type": "m3"}, 
            {"name": name_dat, "h": 0.25, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Terrazzo, Đá xanh, Gạch nung, Gạch giả đá 4 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.85, 
        "layers": [ 
            {"name": "Lát gạch terrazzo,BT,đá xanh + vữa", "h": 0.05, "type": "m2"}, 
            {"name": "Bê tông M150", "h": 0.08, "type": "m3"}, 
            {"name": name_dat, "h": 0.22, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Asphalt 4 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 1.05, 
        "layers": [ 
            {"name": "BT nhựa hạt mịn", "h": 0.05, "type": "m2"}, 
            {"name": "BT nhựa hạt trung", "h": 0.07, "type": "m3"}, 
            {"name": "Đá dăm loại 1", "h": 0.18, "type": "m3"}, 
            {"name": "Đá dăm loại 2", "h": 0.25, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Asphalt 2 ống (Ganivo - Ganivo, Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.60, 
        "layers": [ 
            {"name": "BT nhựa hạt mịn", "h": 0.05, "type": "m2"}, 
            {"name": "BT nhựa hạt trung", "h": 0.07, "type": "m3"}, 
            {"name": "Đá dăm loại 1", "h": 0.18, "type": "m3"}, 
            {"name": "Bê tông M150", "h": 0, "type": "m3"},
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Đất cấp 2 1 ống (Ganivo - Ganivo, Bể)"] = {
        "W_top": 0.35, "W_bot": 0.25, "H_def": 0.60, 
        "layers": [ 
            {"name": "Đất đầm chặt K=0.95", "h": 0.31, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Đất cấp 2 2 ống (Ganivo - Ganivo, Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.60, 
        "layers": [ 
            {"name": "Đất đầm chặt K=0.95", "h": 0.31, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Đất cấp 2 2 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.71, 
        "layers": [ 
            {"name": "Đất đầm chặt K=0.95", "h": 0.35, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Đất cấp 2 3 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.85, 
        "layers": [ 
            {"name": "Đất đầm chặt K=0.95", "h": 0.35, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Đất cấp 3 1 ống (Ganivo - Ganivo, Bể)"] = {
        "W_top": 0.35, "W_bot": 0.25, "H_def": 0.60, 
        "layers": [ 
            {"name": "Đất đầm chặt K=0.95", "h": 0.30, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Đất cấp 3 2 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.71, 
        "layers": [ 
            {"name": "Đất đầm chặt K=0.95", "h": 0.35, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Block_KC_B1 1 ống (Ganivo - Ganivo, Bể)"] = {
        "W_top": 0.35, "W_bot": 0.25, "H_def": 0.60, 
        "layers": [ 
            {"name": "Lát gạch block dày 6cm", "h": 0.06, "type": "m2"}, 
            {"name": "Đệm cát vàng dày 5cm", "h": 0.05, "type": "m3"}, 
            {"name": "Đệm cát vàng (XM 8%) dày 10cm", "h": 0.10, "type": "m3"}, 
            {"name": "Đất đầm chặt K=0.95", "h": 0.10, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Block_KC_B1 2 ống (Ganivo - Ganivo, Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.60, 
        "layers": [ 
            {"name": "Lát gạch block dày 6cm", "h": 0.06, "type": "m2"}, 
            {"name": "Đệm cát vàng dày 5cm", "h": 0.05, "type": "m3"}, 
            {"name": "Đệm cát vàng (XM 8%) dày 10cm", "h": 0.10, "type": "m3"}, 
            {"name": "Đất đầm chặt K=0.95", "h": 0.10, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Block_KC_B1 2 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.71, 
        "layers": [ 
            {"name": "Lát gạch block dày 6cm", "h": 0.06, "type": "m2"}, 
            {"name": "Đệm cát vàng dày 5cm", "h": 0.05, "type": "m3"}, 
            {"name": "Đệm cát vàng (XM 8%) dày 10cm", "h": 0.10, "type": "m3"}, 
            {"name": "Đất đầm chặt K=0.95", "h": 0.14, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    db["Block_KC_B1 3 ống (Bể - Bể)"] = {
        "W_top": 0.45, "W_bot": 0.35, "H_def": 0.85, 
        "layers": [ 
            {"name": "Lát gạch block dày 6cm", "h": 0.06, "type": "m2"}, 
            {"name": "Đệm cát vàng dày 5cm", "h": 0.05, "type": "m3"}, 
            {"name": "Đệm cát vàng (XM 8%) dày 10cm", "h": 0.10, "type": "m3"}, 
            {"name": "Đất đầm chặt K=0.95", "h": 0.14, "type": "m3"}, 
            {"name": name_cat, "h": "Auto", "type": "m3"} 
        ]
    }
    return db
# Force refresh if the database is old
if "db_ket_cau" not in st.session_state or "Hè bê tông 4 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá 4 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Asphalt 4 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Asphalt 2 ống (Ganivo - Ganivo, Bể)" not in st.session_state.db_ket_cau or "Đất cấp 2 1 ống (Ganivo - Ganivo, Bể)" not in st.session_state.db_ket_cau or "Đất cấp 2 2 ống (Ganivo - Ganivo, Bể)" not in st.session_state.db_ket_cau or "Đất cấp 2 2 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Đất cấp 2 3 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Đất cấp 3 1 ống (Ganivo - Ganivo, Bể)" not in st.session_state.db_ket_cau or "Đất cấp 3 2 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Block_KC_B1 1 ống (Ganivo - Ganivo, Bể)" not in st.session_state.db_ket_cau or "Block_KC_B1 2 ống (Ganivo - Ganivo, Bể)" not in st.session_state.db_ket_cau or "Block_KC_B1 2 ống (Bể - Bể)" not in st.session_state.db_ket_cau or "Block_KC_B1 3 ống (Bể - Bể)" not in st.session_state.db_ket_cau:
    st.session_state.db_ket_cau = init_db_ket_cau()

if "tables_expanded" not in st.session_state:
    st.session_state.tables_expanded = True


# 1. THƯ VIỆN BỂ CÁP CHI TIẾT
DB_BE_SPECS = {
    "1DD": {"dai": 1.69, "rong": 1.01, "cao_day": 0.15, "wall": 0.33, "flange": 0.10},
    "1DH": {"dai": 1.516, "rong": 0.836, "cao_day": 0.10, "wall": 0.22, "flange": 0.05},
    "2VD": {"dai": 1.69, "rong": 1.51, "cao_day": 0.15, "wall": 0.33, "flange": 0.10},
    "2VH": {"dai": 1.516, "rong": 1.336, "cao_day": 0.10, "wall": 0.22, "flange": 0.05},
    "3VD": {"dai": 2.01, "rong": 1.69, "cao_day": 0.15, "wall": 0.33, "flange": 0.10},
    "3VH": {"dai": 1.836, "rong": 1.516, "cao_day": 0.10, "wall": 0.22, "flange": 0.05},
    "GH300": {"dai": 0.44, "rong": 0.44, "cao_day": 0.05, "wall": 0.11, "flange": 0.0},
    "GH400": {"dai": 0.55, "rong": 0.55, "cao_day": 0.05, "wall": 0.11, "flange": 0.0},
    "GD400": {"dai": 0.744, "rong": 0.744, "cao_day": 0.05, "wall": 0.22, "flange": 0.0},
    "GH600": {"dai": 0.724, "rong": 0.724, "cao_day": 0.05, "wall": 0.11, "flange": 0.0},
    "GD600": {"dai": 0.924, "rong": 0.924, "cao_day": 0.05, "wall": 0.22, "flange": 0.0}
}

def generate_db_be(specs):
    db = {}
    for name, s in specs.items():
        # Dọc: Lấy dai
        db[f"{name} (Dọc)"] = {
            "bi": s["dai"] + 2 * s["flange"],
            "long": s["dai"] - 2 * s["wall"]
        }
        # Ngang: Lấy rong
        db[f"{name} (Ngang)"] = {
            "bi": s["rong"] + 2 * s["flange"],
            "long": s["rong"] - 2 * s["wall"]
        }
    db["Không có"] = {"bi": 0.0, "long": 0.0}
    return db

DB_BE = generate_db_be(DB_BE_SPECS)

# 1.5. ÁNH XẠ TÊN HẠNG MỤC (Shorthand -> Official)
DISPLAY_NAME_MAP = {
    "Đá dăm loại 1": "Thi công móng cấp phối đá dăm lớp trên dầy 18cm",
    "Đá dăm loại 2": "Rải cấp phối đá dăm mặt đường đá nhựa cũ. Lớp dưới 25cm",
    "Lát gạch terrazzo,BT,đá xanh + vữa": "Lát gạch terrazzo, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )",
    "BT nhựa hạt mịn": "Làm mặt đường BT nhựa hạt mịn, chiều dày mặt đường đã lèn ép 5cm",
    "Bê tông mác 250": "Bê tông mặt đường, chiều dày mặt đường <=25cm, đá 2x4, vữa BT M250",
    "Bê tông M150": "Bê tông nền, đá 2x4, vữa BT M150",
    "Đất đầm chặt K=0.95": "Lấp đất và đầm rãnh cáp đào qua hè, đường, độ chặt yêu cầu K=0,95",
    "Cát đen đầm chặt": "Phân rải và đầm nén cát tuyến ống dẫn cáp thông tin. Đầm bằng thủ công"
}

# 2. THƯ VIỆN KẾT CẤU RÃNH (Dùng làm mẫu khởi tạo)
DB_KET_CAU = st.session_state.db_ket_cau

def validate_be_row(row):
    row_err = []
    # 1. Các cột bắt buộc phải có giá trị
    required_missing = []
    required = ["Kết cấu bể/ga", "Cấp đất", "Vị trí bể", "Loại bể", "Sâu bể (Đo)"]
    for col in required:
        val = row.get(col)
        if pd.isna(val) or str(val).strip() == "" or (col == "Sâu bể (Đo)" and val == 0):
            required_missing.append(col)
    
    if required_missing:
        return f"Thiếu: {', '.join(required_missing)}"
    
    # 2. Kiểm tra tính hợp lệ của dữ liệu
    kc_be = str(row.get("Kết cấu bể/ga", "")).strip()
    if kc_be not in RAW_KET_CAU:
        row_err.append(f"Kết cấu '{kc_be}' không hợp lệ")
        
    loai_be = str(row.get("Loại bể", "")).strip()
    if loai_be not in WELL_NAMES:
        row_err.append(f"Loại bể '{loai_be}' không hợp lệ")
        
    cap_dat = row.get("Cấp đất")
    if cap_dat not in DATA_CAP_DAT:
        row_err.append(f"Cấp đất '{cap_dat}' không hợp lệ")

    return ", ".join(row_err) if row_err else ""

# Helper: Chuẩn hóa tên cột linh hoạt (Fuzzy Mapping)
def normalize_cols(df, target_cols):
    mapping = {
        "stt": "STT", "kết cấu": "Kết cấu rãnh", "cấp đất": "Cấp đất",
        "bể đầu": "Bể đầu", "bể cuối": "Bể cuối",
        "số ống": "Số ống tầng 1", "loại ống": "Loại ống tầng 1", "độ sâu": "Độ sâu rãnh",
        "dài đo": "Dài đo", "l ống": "Dài đo", "tâm-tâm": "Dài đo",
        "số tầng": "Số tầng ống", "số ống tầng 2": "Số ống tầng 2", "loại ống tầng 2": "Loại ống tầng 2",
        "kiểu kết nối": "Kiểu kết nối", "kết nối": "Kiểu kết nối",
        "vị trí": "Vị trí bể", "sâu bể": "Sâu bể (Đo)"
    }
    new_names = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for key, target in mapping.items():
            if key in c_low and target in target_cols:
                if target not in new_names.values():
                    new_names[col] = target
                break
    return df.rename(columns=new_names)

# --- KHỞI TẠO CỘT TIÊU CHUẨN THEO FILE EXCEL ---
# --- HELPER MAPPING FUNCTIONS FOR IMPORT ---

def map_pipe_type(val):
    if pd.isna(val) or str(val).strip() == "": return None
    v = str(val).strip().lower()
    if "pvc61" in v: return "D61"
    if "pvc" in v: return "D110x5.5"
    if "sb" in v: return "D110x6.8"
    return val # Keep original if no match

def map_kc_keyword(val):
    if pd.isna(val) or str(val).strip() == "": return None
    v = str(val).strip().upper()
    if "ASPHALT" in v or "NHỰA" in v or "AL" in v: return "AL"
    if v == "TE": return "TE"
    if v == "ĐX": return "ĐX"
    if v == "GN": return "GN"
    if v == "GBT_DA" or "GBT" in v: return "GBT_DA"
    if "TE, ĐX, GN" in v: return "TE"
    if "ĐƯỜNG" in v or "ĐBT" in v or "BTXM" in v or ("BÊ TÔNG" in v and "HÈ" not in v): return "ĐBT"
    if "HÈ" in v or "HBT" in v: return "HBT"
    if "ĐẤT CẤP 2" in v or "CẤP 2" in v: return "Đất cấp 2"
    if "ĐẤT CẤP 3" in v or "CẤP 3" in v: return "Đất cấp 3"
    if "BLOCK" in v or "B1" in v: return "Block_KC_B1"
    if "NGOC" in v: return "Ngoc"
    return v # Giữ nguyên để validate sau

def map_cap_dat_val(v):
    if pd.isna(v): return None
    sv = str(v).strip().upper()
    if sv in ["NAN", "NONE", ""]: return None
    if "2" in sv or "II" == sv or "II" in sv.split(): return 2
    if "3" in sv or "III" == sv or "III" in sv.split(): return 3
    return None

TEMPLATE_COLUMNS = [
    "STT", "Kết cấu rãnh", "Cấp đất", "Bể đầu", "Bể cuối", "Dài đo", 
    "Số ống tầng 1", "Loại ống tầng 1", "Độ sâu rãnh", "Số tầng ống", "Số ống tầng 2", "Loại ống tầng 2",
    "Kiểu kết nối"
]
WELL_IMPORT_COLUMNS = ["STT", "Kết cấu bể/ga", "Cấp đất", "Vị trí bể", "Loại bể", "Sâu bể (Đo)"]

# Tự động lấy danh sách tên Bể từ DB_BE, ưu tiên Ga (G...) lên đầu
_raw_names = list(set([k.split(" (")[0] for k in DB_BE.keys() if " (" in k]))
# Sắp xếp: Ưu tiên Ga (bắt đầu bằng G), sau đó alphabetic
WELL_NAMES_BASIC = sorted(_raw_names, key=lambda x: (0 if x.startswith('G') else 1, x)) + ["Không có"]
WELL_NAMES_END = WELL_NAMES_BASIC + ["Cột", "Tường"]
WELL_NAMES = WELL_NAMES_BASIC

RAW_KET_CAU = ["AL", "HBT", "TE", "ĐX", "GN", "GBT_DA", "ĐBT", "Đất cấp 2", "Đất cấp 3", "Block_KC_B1", "Ngoc"]
DATA_CAP_DAT = [2, 3]
DATA_LOAI_ONG = [
    "D110x5.5", "D110x6.8", "D110/90", "D61", "D32", "D85/65", "D65/50", "D40/30", "D32/25", "Không ống",
    "D110x5.5 + D110x6.8", "D110x5.5 + D61", "D110x6.8 + D61"
]
def clean_excel_value(val):
    if pd.isna(val) or val == "":
        return ""
    # Remove brackets, dropdown arrows (▼), and extra spaces
    val = str(val).replace("[", "").replace("]", "").replace("▼", "").strip()
    return val

def map_ket_cau(raw_str, so_ong, kieu_ket_noi):
    raw = str(raw_str).upper()
    ong_str = f"{so_ong} ống" if so_ong in [1, 2, 3, 4] else "1 ống"
    
    if raw == "AL": loai = "Asphalt"
    elif raw == "HBT": loai = "Hè bê tông"
    elif raw == "ĐBT": loai = "Đường bê tông"
    elif raw in ["TE", "ĐX", "GN", "GBT_DA", "TE, ĐX, GN"]: loai = "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá"
    elif raw == "ĐẤT CẤP 3": loai = "Đất cấp 3"
    elif raw == "ĐẤT CẤP 2": loai = "Đất cấp 2"
    elif raw == "BLOCK_KC_B1": loai = "Block_KC_B1"
    else: loai = f"CHƯA BIẾT ({raw})"
    
    s_kieu = str(kieu_ket_noi).strip().upper()
    if "GANIVO" in s_kieu or "GA" in s_kieu:
        noi_tu = "Ganivo - Ganivo, Bể"
    else:
        noi_tu = "Bể - Bể"
    
    return f"{loai} {ong_str} ({noi_tu})"

def get_h_def_max(kc_raw, kieu_kn, db):
    # Determine loai prefix string used in db keys
    raw = str(kc_raw).upper()
    if raw == "AL": loai = "Asphalt"
    elif raw == "HBT": loai = "Hè bê tông"
    elif raw == "ĐBT": loai = "Đường bê tông"
    elif "TE" in raw or "TER" in raw or "GẠCH" in raw: loai = "Terrazzo, Đá xanh, Gạch nung"
    elif "CẤP 3" in raw: loai = "Đất cấp 3"
    elif "CẤP 2" in raw: loai = "Đất cấp 2"
    elif "BLOCK" in raw or "B1" in raw: loai = "Block_KC_B1"
    else: loai = raw
    
    max_h = 0.0
    suffix = f"({kieu_kn})"
    for key, val in db.items():
        if key.startswith(loai) and key.endswith(suffix):
            max_h = max(max_h, val.get("H_def", 0))
    
    # Fallback if no match found
    if max_h == 0:
        if kieu_kn == "Ganivo - Ganivo, Bể": return 0.60
        return 0.71
    return max_h

def validate_row(row, db):
    row_err = []
    # 1. Các cột bắt buộc chung
    kc_ranh = row.get("Kết cấu rãnh")
    if pd.isna(kc_ranh) or str(kc_ranh).strip() == "": 
        row_err.append("Thiếu Kết cấu rãnh")
        return "Thiếu Kết cấu rãnh"
    
    kc_ranh = str(kc_ranh).strip()
    if kc_ranh not in RAW_KET_CAU:
        row_err.append(f"Kết cấu '{kc_ranh}' không hợp lệ")
        return f"Kết cấu '{kc_ranh}' không hợp lệ"

    # KIẾM TRA RIÊNG CHO NGOC
    if kc_ranh == "Ngoc":
        if pd.isna(row.get("Dài đo")) or float(row.get("Dài đo", 0)) == 0:
            row_err.append("Thiếu Dài đo")
        if pd.isna(row.get("Số ống tầng 1")):
            row_err.append("Thiếu Số ống tầng 1")
        if pd.isna(row.get("Loại ống tầng 1")):
            row_err.append("Thiếu Loại ống tầng 1")
        return ", ".join(row_err) if row_err else ""

    # KIỂM TRA CHO CÁC KẾT CẤU KHÁC (AL, HBT, ...)
    if pd.isna(row.get("Cấp đất")): row_err.append("Thiếu Cấp đất")
    if pd.isna(row.get("Kiểu kết nối")): row_err.append("Thiếu Kiểu kết nối")
    if pd.isna(row.get("Số ống tầng 1")): row_err.append("Thiếu Số ống tầng 1")
    if pd.isna(row.get("Loại ống tầng 1")): row_err.append("Thiếu Loại ống tầng 1")
    
    # 2. Kiểm tra thư viện kết cấu
    kieu_kn = row.get("Kiểu kết nối")
    if not pd.isna(kc_ranh) and kc_ranh != "" and not pd.isna(kieu_kn) and kieu_kn != "":
        try:
            # Handle numeric conversion safely
            s1 = row.get("Số ống tầng 1", 0)
            s2 = row.get("Số ống tầng 2", 0)
            
            def to_int(v):
                try: 
                    if pd.isna(v): return 0
                    return int(float(v))
                except: return 0

            s1_val = to_int(s1)
            s2_val = to_int(s2)
            
            if s1_val > 2: row_err.append("Số ống tầng 1 tối đa là 2")
            if s2_val > 2: row_err.append("Số ống tầng 2 tối đa là 2")
            
            # Tổng số ống để chọn mẫu kết cấu (1, 2, 3, 4 ống)
            total_pipes = s1_val + s2_val
            if total_pipes == 0: total_pipes = 1
            
            kc_key = map_ket_cau(kc_ranh, total_pipes, kieu_kn)
            
            if kc_key in db:
                db_item = db[kc_key]
                if not db_item.get("layers") or len(db_item.get("layers")) == 0:
                    row_err.append(f"Kết cấu {kc_key} chưa khai báo lớp vật liệu")
                
                h_def = db_item.get("H_def", 0.91)
                try:
                    h_thuc_val = row.get("Độ sâu rãnh")
                    if not pd.isna(h_thuc_val):
                        h_thuc = float(h_thuc_val)
                        if h_thuc > h_def + 0.001:
                            row_err.append(f"H thực ({h_thuc}) > H thiết kế ({h_def})")
                except: pass
            else:
                row_err.append(f"Không tìm thấy kết cấu {kc_key} trong thư viện")
        except Exception as e:
            row_err.append(f"Lỗi logic kiểm tra: {str(e)}")
        
    return ", ".join(row_err) if row_err else ""

def sync_soil_levels(df, kc_col):
    if df.empty or kc_col not in df.columns: return df
    
    # Cơ sở dữ liệu từ session_state
    db = st.session_state.get("db_ket_cau", {})
    if not db: return df
    
    def process_row(row):
        kc = row.get(kc_col)
        kc_up = str(kc).upper().strip()
        
        # 1. Cập nhật cấp đất
        if any(x in kc_up for x in ["AL", "ĐBT", "ĐẤT CẤP 3"]): 
            row["Cấp đất"] = 3
        else:
            row["Cấp đất"] = 2
            
        # 2. Tự động điền độ sâu nếu trống (Tuyến)
        if "Độ sâu rãnh" in row.index:
            h_val = row.get("Độ sâu rãnh")
            if pd.isna(h_val) or h_val == 0:
                # Cần map_ket_cau để lấy H_def
                try:
                    s1 = int(float(row.get("Số ống tầng 1", 0)))
                    s2 = int(float(row.get("Số ống tầng 2", 0)))
                    total = s1 + s2 if (s1+s2) > 0 else 1
                    kieu_kn = row.get("Kiểu kết nối", "Bể - Bể")
                    kc_key = map_ket_cau(kc, total, kieu_kn)
                    if kc_key in db:
                        row["Độ sâu rãnh"] = db[kc_key].get("H_def", 0.6)
                except: pass
                
        return row

    return df.apply(process_row, axis=1)

# Hàm tạo Template rỗng
def get_template_excel():
    df_template = pd.DataFrame(columns=TEMPLATE_COLUMNS)
    df_template.loc[0] = [1, "AL", 3, "B1", "B3", 45.5, 2, "D110x6.8", 0.71, 1, 0, "Không ống", "Bể - Bể"]
    df_template.loc[1] = [2, "HBT", 2, "B3", "G2", 15.0, 1, "D61", 0.6, 1, 0, "Không ống", "Ganivo - Ganivo, Bể"]
    
    df_be_template = pd.DataFrame(columns=WELL_IMPORT_COLUMNS)
    df_be_template.loc[0] = [1, "AL", 3, "GA1", "1DD", 1.2]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Data_Nhap_Lieu')
        df_be_template.to_excel(writer, index=False, sheet_name='Data_Be_Ga')
        
        workbook  = writer.book
        
        # --- Sheet 1: Data_Nhap_Lieu ---
        ws1 = writer.sheets['Data_Nhap_Lieu']
        # Tạo sheet hướng dẫn (Chứa danh sách validation và diễn giải)
        settings_sheet = workbook.add_worksheet('Huong_dan')
        
        # Format tiêu đề cho sheet Huong_dan
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})

        # Cột A & B: Kiểu kết nối
        settings_sheet.write(0, 0, "Loại kết nối", header_fmt)
        settings_sheet.write(0, 1, "Chi tiết", header_fmt)
        conn_data = [
            ("Bể - Bể", "Nối bể với bể"),
            ("Ganivo - Ganivo, Bể", "Nối Ganivo với Ganivo hoặc Bể")
        ]
        for r, (val, det) in enumerate(conn_data):
            settings_sheet.write(r + 1, 0, val)
            settings_sheet.write(r + 1, 1, det)

        # Cột C & D: Kết cấu rãnh
        settings_sheet.write(0, 2, "Loại kết cấu", header_fmt)
        settings_sheet.write(0, 3, "Chi tiết", header_fmt)
        kc_details = {
            "AL": "Alphalt", "HBT": "Hè bê tông", "TE": "Terrazzo", "ĐX": "Đá xanh", "GN": "Gạch Nung",
            "GBT_DA": "Gạch bê tông giả đá", "ĐBT": "Đường bê tông", "Đất cấp 2": "Đất cấp 2",
            "Đất cấp 3": "Đất cấp 3", "Block_KC_B1": "Block", "Ngoc": "Ống ngóc"
        }
        for r, val in enumerate(RAW_KET_CAU):
            settings_sheet.write(r + 1, 2, val)
            settings_sheet.write(r + 1, 3, kc_details.get(val, ""))
        
        # Cột E & F: Loại ống
        settings_sheet.write(0, 4, "Loại ống", header_fmt)
        settings_sheet.write(0, 5, "Chi tiết", header_fmt)
        pipe_details = {
            "D110x5.5": "Ống PVC 110x5.5", "D110x6.8": "Ống PVC 110x6.8", "D110/90": "Ống xoắn 110/90", "D61": "Ống PVC 61x4.1",
            "D32": "Ống PVC 32", "D85/65": "Ống xoắn 85/65", "D65/50": "Ống xoắn 65/50",
            "D40/30": "Ống xoắn 40/30", "D32/25": "Ống xoắn 32/25", "Không ống": "Không ống",
            "D110x5.5 + D110x6.8": "Dùng 2 ống khác loại",
            "D110x5.5 + D61": "Dùng 2 ống khác loại",
            "D110x6.8 + D61": "Dùng 2 ống khác loại"
        }
        for r, val in enumerate(DATA_LOAI_ONG):
            settings_sheet.write(r + 1, 4, val)
            settings_sheet.write(r + 1, 5, pipe_details.get(val, ""))
        
        settings_sheet.set_column('A:F', 25)
        
        # Thiết lập Data Validation tham chiếu sang sheet Huong_dan
        ws1.data_validation('B2:B1000', {'validate': 'list', 'source': '=Huong_dan!$C$2:$C$' + str(len(RAW_KET_CAU)+1)})
        ws1.data_validation('C2:C1000', {'validate': 'list', 'source': DATA_CAP_DAT})
        ws1.data_validation('H2:H1000', {'validate': 'list', 'source': '=Huong_dan!$E$2:$E$' + str(len(DATA_LOAI_ONG)+1)})
        ws1.data_validation('J2:J1000', {'validate': 'list', 'source': [1, 2]})
        ws1.data_validation('L2:L1000', {'validate': 'list', 'source': '=Huong_dan!$E$2:$E$' + str(len(DATA_LOAI_ONG)+1)})
        ws1.data_validation('M2:M1000', {'validate': 'list', 'source': '=Huong_dan!$A$2:$A$3'})
        
        ws1.set_column('B:C', 20)
        ws1.set_column('D:E', 12)
        ws1.set_column('F:L', 15)
        ws1.set_column('M:M', 20)
        
        # --- Sheet 2: Data_Be_Ga ---
        ws2 = writer.sheets['Data_Be_Ga']
        ws2.data_validation('B2:B1000', {'validate': 'list', 'source': '=Huong_dan!$C$2:$C$' + str(len(RAW_KET_CAU)+1)})
        ws2.data_validation('C2:C1000', {'validate': 'list', 'source': DATA_CAP_DAT})
        ws2.data_validation('E2:E1000', {'validate': 'list', 'source': WELL_NAMES})
        
        ws2.set_column('B:F', 20)
        
    return output.getvalue()

def get_db_export_excel():
    # 1. Sheet Kết cấu rãnh
    rows_kc = []
    # Sắp xếp các phím của db_ket_cau theo thứ tự bảng chữ cái
    sorted_keys = sorted(st.session_state.db_ket_cau.keys())
    for name in sorted_keys:
        data = st.session_state.db_ket_cau[name]
        for i, l in enumerate(data['layers']):
            rows_kc.append({
                "Tên kết cấu": name if i == 0 else "",
                "Rộng miệng (m)": data['W_top'] if i == 0 else "",
                "Rộng đáy (m)": data['W_bot'] if i == 0 else "",
                "Sâu mặc định (m)": data['H_def'] if i == 0 else "",
                "Thứ tự lớp": i + 1,
                "Tên lớp vật liệu": l['name'],
                "Chiều dày (h)": l['h'],
                "Đơn vị": l['type']
            })
    df_kc = pd.DataFrame(rows_kc)

    # 2. Sheet Bể cáp
    rows_be = []
    be_data_map = {}
    for k, v in DB_BE.items():
        if k == "Không có": continue
        loai_be = k.split(" (")[0]
        huong = "Dọc" if "Dọc" in k else "Ngang"
        if loai_be not in be_data_map:
            spec = DB_BE_SPECS.get(loai_be, {})
            be_data_map[loai_be] = {
                "Tên Bể/Ga": loai_be,
                "Dài bể": spec.get('dai', 0),
                "Rộng bể": spec.get('rong', 0),
                "Cao đáy bể": spec.get('cao_day', 0)
            }
        be_data_map[loai_be][f"{huong} (Phủ bì)"] = v['bi']
        be_data_map[loai_be][f"{huong} (Lòng)"] = v['long']
    df_be = pd.DataFrame(list(be_data_map.values()))

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_kc.to_excel(writer, index=False, sheet_name='DS_Ket_Cau_Ranh')
        df_be.to_excel(writer, index=False, sheet_name='DS_Be_Cap')
        
        # Format
        workbook = writer.book
        for sheet_name in ['DS_Ket_Cau_Ranh', 'DS_Be_Cap']:
            ws = writer.sheets[sheet_name]
            if sheet_name == 'DS_Ket_Cau_Ranh':
                ws.set_column('A:A', 40) # Tên kết cấu
                ws.set_column('B:D', 15) # Rộng, Sâu
                ws.set_column('E:E', 10) # Thứ tự lớp
                ws.set_column('F:F', 50) # Tên lớp
                ws.set_column('G:H', 12) # Dày, Đơn vị
            else:
                ws.set_column('A:A', 30)
                ws.set_column('B:E', 15)
            
    return output.getvalue()

def render_dynamic_svg(kc_name):
    if kc_name not in st.session_state.db_ket_cau:
        return ""
    data = st.session_state.db_ket_cau[kc_name]
    w_t = float(data.get("W_top", 0.35)) * 1000
    w_b = float(data.get("W_bot", 0.25)) * 1000
    h_def = float(data.get("H_def", 0.91))
    
    layers = data.get("layers", [])
    
    t_fixed_px = sum([float(l["h"])*1000 for l in layers if str(l["h"]).lower() != "auto" and str(l["h"]).strip() != ""])
    h_cat_min_val = 0.22 if ("3 ống" in kc_name or "4 ống" in kc_name) else 0.11
    h_min_px = t_fixed_px + h_cat_min_val * 1000
    h_def_px = h_def * 1000
    
    viz_h = []
    if h_def_px >= h_min_px:
        for l in layers:
            if str(l["h"]).lower() == "auto":
                h_layer = h_def_px - t_fixed_px
                viz_h.append(h_layer)
            else:
                viz_h.append(float(l["h"]) * 1000)
    else:
        h_cat_actual_px = h_cat_min_val * 1000 if h_def_px >= h_cat_min_val * 1000 else h_def_px
        remaining_h_px = max(0.0, h_def_px - h_cat_actual_px)
        for l in layers:
            if str(l["h"]).lower() == "auto":
                viz_h.append(h_cat_actual_px)
            else:
                h_req_px = float(l["h"]) * 1000
                h_alloc_px = min(h_req_px, remaining_h_px)
                remaining_h_px -= h_alloc_px
                viz_h.append(h_alloc_px)
    
    t_h = sum(viz_h)
    v_w, v_h = 1900, int(t_h + 250)
    cx, sy = 350, 60
    svg = f'<svg viewBox="-600 -10 {v_w} {v_h}" style="background-color:transparent;width:100%;height:auto;max-height:800px;margin:auto;display:block;" xmlns="http://www.w3.org/2000/svg">'
    svg += """
      <defs>
        <pattern id="p-min" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#444"/><circle cx="2" cy="2" r="0.5" fill="#666"/></pattern>
        <pattern id="p-trung" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#333"/><circle cx="4" cy="4" r="1.5" fill="#555"/></pattern>
        <pattern id="p-da" width="15" height="15" patternUnits="userSpaceOnUse"><rect width="15" height="15" fill="#222"/><polygon points="7.5,2 12,12 3,12" fill="none" stroke="#888" stroke-width="0.5"/></pattern>
        <pattern id="p-bt" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#222"/><circle cx="2" cy="2" r="1.5" fill="#fff" fill-opacity="0.3"/></pattern>
        <pattern id="p-cat" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#111"/><circle cx="3" cy="3" r="1" fill="#444"/><circle cx="8" cy="7" r="1" fill="#555"/></pattern>
        <pattern id="p-dat" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#000033"/><circle cx="5" cy="5" r="1" fill="#0000ff" fill-opacity="0.6"/></pattern>
        <pattern id="p-gach" width="15" height="15" patternUnits="userSpaceOnUse"><rect width="15" height="15" fill="#222"/><path d="M 0,7.5 L 15,7.5 M 7.5,0 L 7.5,15" stroke="#ccc" stroke-width="1.5" fill="none"/></pattern>
        <pattern id="p-vua" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#1a1a1a"/><circle cx="2" cy="2" r="1.5" fill="#555"/></pattern>
        <marker id="arr" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="white" /></marker>
      </defs>
      <style>text { font-family: sans-serif; fill: white; font-weight: bold; } .dim { font-size: 32px; text-anchor: middle; } .lbl { font-size: 28px; text-anchor: end; } .line-dim { stroke: white; stroke-width: 2; } .title-svg { font-size: 36px; font-weight: bold; text-anchor: middle; fill: #ffd700; }</style>
    """
    cy = sy
    for i, lyr in enumerate(layers):
        ph = viz_h[i]
        gw = lambda y: w_t - (w_t - w_b) * ((y - sy) / t_h if t_h > 0 else 0)
        w1, w2 = gw(cy), gw(cy + ph)
        x1l, x1r, x2l, x2r = cx-w1/2, cx+w1/2, cx-w2/2, cx+w2/2
        p = "p-cat"; n = lyr["name"].lower()
        if "nhựa" in n: p = "p-min" if "mịn" in n else "p-trung"
        elif "đá dăm" in n: p = "p-da"
        elif "bê tông" in n: p = "p-bt"
        elif "đất" in n: p = "p-dat"
        elif "gạch" in n or "terrazzo" in n: p = "p-gach"
        elif "vữa" in n: p = "p-vua"
        svg += f'<polygon points="{x1l},{cy} {x1r},{cy} {x2r},{cy+ph} {x2l},{cy+ph}" fill="url(#{p})" stroke="white" stroke-width="1.5" />'
        ly_pos = cy + ph/2
        
        # Word wrap text logic
        text_lines = []
        words = lyr["name"].split()
        curr_line = ""
        for w in words:
            if len(curr_line) + len(w) > 35:
                text_lines.append(curr_line.strip())
                curr_line = w + " "
            else:
                curr_line += w + " "
        if curr_line: text_lines.append(curr_line.strip())
        
        svg += f'<text x="-80" y="{ly_pos - (len(text_lines)-1)*15}" class="lbl" dominant-baseline="middle">'
        for idx, line in enumerate(text_lines):
            dy = 30 if idx > 0 else 0
            svg += f'<tspan x="-80" dy="{dy}">{line}</tspan>'
        svg += '</text>'
        
        svg += f'<polyline points="-580,{ly_pos} -30,{ly_pos} {x1l-10},{ly_pos}" fill="none" stroke="white" stroke-dasharray="4" marker-end="url(#arr)" />'
        svg += f'<line x1="{cx+w_t/2+40}" y1="{cy}" x2="{cx+w_t/2+40}" y2="{cy+ph}" stroke="white" stroke-width="2" />'
        try: ht_val = "Auto" if lyr["h"] == "Auto" else int(float(lyr["h"])*1000)
        except: ht_val = 0
        svg += f'<text x="{cx+w_t/2+70}" y="{ly_pos}" dominant-baseline="middle" text-anchor="start" font-size="28" font-weight="bold">{ht_val}</text>'
        svg += f'<line x1="{cx+w_t/2+30}" y1="{cy}" x2="{cx+w_t/2+50}" y2="{cy}" stroke="white" stroke-width="2" />'
        cy += ph
    svg += f'<line x1="{cx+w_t/2+30}" y1="{cy}" x2="{cx+w_t/2+50}" y2="{cy}" stroke="white" stroke-width="2" />'
    svg += f'<line x1="{cx-w_t/2}" y1="20" x2="{cx+w_t/2}" y2="20" class="line-dim" /><text x="{cx}" y="15" class="dim">{int(w_t)}</text>'
    svg += f'<line x1="{cx-w_b/2}" y1="{cy+30}" x2="{cx+w_b/2}" y2="{cy+30}" class="line-dim" /><text x="{cx}" y="{cy+60}" class="dim">{int(w_b)}</text>'
    # Tính tổng chiều sâu thật
    has_auto = any(str(l["h"]).lower() == "auto" for l in layers)
    s_text_sub = f"Tổng sâu (H) mặc định = {int(h_def*1000)}" if has_auto else f"Tổng sâu (H) = {int(t_fixed_px)}"
    
    # Text dưới rộng đáy
    svg += f'<text x="{cx}" y="{cy+100}" class="dim" style="fill:#00ff00; font-weight:bold;">{s_text_sub}</text>'
    # Trục kích thước tổng chiều sâu bên phải
    svg += f'<line x1="{cx+w_t/2+140}" y1="{sy}" x2="{cx+w_t/2+140}" y2="{cy}" stroke="white" stroke-width="2" />'
    svg += f'<line x1="{cx+w_t/2+120}" y1="{sy}" x2="{cx+w_t/2+160}" y2="{sy}" stroke="white" stroke-width="2" />'
    svg += f'<line x1="{cx+w_t/2+120}" y1="{cy}" x2="{cx+w_t/2+160}" y2="{cy}" stroke="white" stroke-width="2" />'
    svg += f'<text x="{cx+w_t/2+180}" y="{sy + (cy-sy)/2}" dominant-baseline="middle" text-anchor="start" fill="#00ff00" font-size="32" font-weight="bold">{s_text_sub}</text>'
    np_val = 4 if "4 ống" in kc_name else (3 if "3 ống" in kc_name else (2 if "2 ống" in kc_name else 1))
    py_bot = cy - 100
    if np_val == 1:
        svg += f'<circle cx="{cx}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/><circle cx="{cx}" cy="{py_bot}" r="51" fill="none" stroke="cyan" stroke-width="2"/>'
    elif np_val == 2:
        svg += f'<circle cx="{cx-70}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/><circle cx="{cx+70}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
    elif np_val == 3:
        py_top = py_bot - 95
        svg += f'<circle cx="{cx-55}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
        svg += f'<circle cx="{cx+55}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
        svg += f'<circle cx="{cx}" cy="{py_top}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
    else:
        py_top = py_bot - 110
        svg += f'<circle cx="{cx-60}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
        svg += f'<circle cx="{cx+60}" cy="{py_bot}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
        svg += f'<circle cx="{cx-60}" cy="{py_top}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
        svg += f'<circle cx="{cx+60}" cy="{py_top}" r="55" fill="#111" stroke="red" stroke-width="4"/>'
    svg += f'<text x="{cx}" y="{cy+150}" class="title-svg">{kc_name.upper()}</text></svg>'
    return svg


def aggregate_dims(series):
    valid = [str(x).strip() for x in series if str(x).strip() and str(x).strip() != "-"]
    unique_valid = []
    for v in valid:
        if v not in unique_valid:
            unique_valid.append(v)
    if not unique_valid: return "-"
    return ", ".join(unique_valid)

def aggregate_notes(notes):
    grouped = {}
    div_100_parts = [] # Parts of "X / 100" pattern
    pure_numbers = []  # Danh sách số đơn lẻ (KHÔNG loại trùng)
    text_others = []   # Các chuỗi văn bản khác
    
    # Khởi tạo biến cho tổng vận chuyển
    total_v_dao, total_v_pha, total_v_lap = 0.0, 0.0, 0.0
    has_vc_notes = False
    
    for n in notes:
        n = str(n).strip()
        if not n: continue
        
        # 1. Kiểm tra xem có phải dạng vận chuyển không: "X + Y - Z" hoặc "X - Y"
        m_vc_3 = re.match(r'^([\d\.]+)\s*\+\s*([\d\.]+)\s*\-\s*([\d\.]+)$', n)
        m_vc_2 = re.match(r'^([\d\.]+)\s*\-\s*([\d\.]+)$', n)
        if m_vc_3:
            v_dao, v_pha, v_lap = map(float, m_vc_3.groups())
            total_v_dao += v_dao
            total_v_pha += v_pha
            total_v_lap += v_lap
            has_vc_notes = True
            continue
        elif m_vc_2:
            v_dao, v_lap = map(float, m_vc_2.groups())
            total_v_dao += v_dao
            total_v_lap += v_lap
            has_vc_notes = True
            continue

        # 2. Kiểm tra dạng "X / 100" (Thường cho lắp đặt ống)
        m_div = re.match(r'^(.+)\s*/\s*100$', n)
        if m_div:
            div_100_parts.append(m_div.group(1).strip())
            continue

        # 3. Kiểm tra dạng L * (Specs) — phải có dấu * hoặc x kèm specs phía sau
        m = re.match(r'^([\d\.]+)\s*[\*x]\s*(.+)$', n)
        if m:
            val, specs = m.groups()
            grouped.setdefault(specs.strip(), []).append(val)
            continue
        
        # 4. Kiểm tra xem có phải số đơn lẻ không (ví dụ: "42.3", "2.5")
        m_num = re.match(r'^[\d\.]+$', n)
        if m_num:
            pure_numbers.append(n)  # KHÔNG loại trùng → giữ tất cả
        else:
            text_others.append(n)  # KHÔNG loại trùng → giữ tất cả
    
    res = []
    
    # Nếu là ghi chú vận chuyển, trả về 1 dòng tổng duy nhất
    vc_str = ""
    if has_vc_notes:
        if total_v_pha > 0:
            vc_str = f"{total_v_dao:g} + {total_v_pha:g} - {total_v_lap:g}"
        else:
            vc_str = f"{total_v_dao:g} - {total_v_lap:g}"

    if has_vc_notes and not grouped and not pure_numbers and not text_others and not div_100_parts:
        return vc_str
    elif has_vc_notes:
        res.append(vc_str)

    # Xử lý các phần / 100
    if div_100_parts:
        if len(div_100_parts) > 1:
            res.append(f"({ ' + '.join(div_100_parts) }) / 100")
        else:
            res.append(f"{div_100_parts[0]} / 100")

    for specs, vals in grouped.items():
        if len(vals) > 1:
            res.append(f"({specs}) * ({ ' + '.join(vals) })")
        else:
            res.append(f"{vals[0]} * {specs}")
    
    # Gộp các số đơn lẻ (giữ nguyên tất cả, kể cả trùng nhau)
    if pure_numbers:
        res.append(" + ".join(pure_numbers))
            
    res.extend(text_others)
    return " + ".join(res)

def create_grouped_report(all_items):
    if not all_items: return pd.DataFrame()
    df = pd.DataFrame(all_items)
    
    grouped = df.groupby(['Nhóm', 'Hạng mục', 'ĐVT'], as_index=False).agg({
        'Khối lượng': 'sum',
        'Diễn giải': aggregate_notes
    })
    
    # Sort order preference
    custom_order = ['0. Vật tư', '1. Phá dỡ nền tuyến', '2. Thi công nền tuyến', '3. Thi công bể', '4. Hoàn trả', '5. Vận chuyển đất thừa']
    grouped['Nhóm'] = pd.Categorical(grouped['Nhóm'], categories=custom_order, ordered=True)
    
    item_order = [
        # Nhóm 1: Phá dỡ
        "Cắt mặt hè bê tông xi măng, Chiều sâu vết cắt <=5cm",
        "Cắt mặt đường bê tông Asphan chiều dày lớp cắt <= 7cm",
        "Cắt mặt đường bê tông xi măng, Chiều sâu vết cắt <=7cm",
        "Phá dỡ kết cấu mặt hè bê tông xi măng bằng máy đục phá bê tông",
        "Phá dỡ kết cấu mặt đường bê tông xi măng bằng máy đục phá bê tông",
        "Phá dỡ kết cấu bê tông bê tông lót nền 10cm dưới kết cấu lớp gạch, đá",
        "Phá dỡ nền gạch giả đá coric",
        "Phá dỡ nền đá xanh",
        "Phá dỡ nền gạch terrazzo",
        "Phá dỡ nền gạch nung",
        "Phá dỡ kết cấu mặt đường bê tông Asphalt",
        "Phá dỡ nền hè gạch Block bằng thủ công",
        "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp II",
        "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp III",
        "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=2m. Đất cấp III",
        
        # Nhóm 2: Thi công nền
        "Lắp ống dẫn cáp, loại ống xoắn HDPE F65/50. Số ống tổ hợp <=3",
        "Lắp ống dẫn cáp, loại ống PVC F <= 60 mm, nong một đầu . Số ống tổ hợp <= 3",
        "Lắp ống dẫn cáp, loại ống PVC F <= 114 mm, nong một đầu . Số ống tổ hợp <= 3",
        "Phân rải và đầm nén cát tuyến ống dẫn cáp thông tin. Đầm bằng thủ công",
        "Lấp đất và đầm rãnh cáp đào qua hè, đường, độ chặt yêu cầu K=0,95",
        
        # Nhóm 3: Thi công bể
        "Đắp đất xung quanh thành bể, xung quanh tủ POP…, độ chặt yêu cầu K=0,95",
        "Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp trên hè), loại bể cáp 2 đan vuông",
        "Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp trên hè), loại bể cáp 1 đan dọc",
        "Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp dưới đường), loại bể cáp 2 đan vuông",
        "Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp dưới đường), loại bể cáp 1 đan dọc",
        "Gia công chân khung bể cáp cho loại bể cáp 2 đan vuông",
        "Gia công chân khung bể cáp cho loại bể cáp 1 đan dọc",
        "Xây bể cáp thông tin (bể 2 nắp đan vuông) bằng gạch chỉ trên hè 1 tầng ống",
        "Xây bể cáp thông tin (bể 1 nắp đan dọc) bằng gạch chỉ trên hè 1 tầng ống",
        "Xây bể cáp thông tin (bể 2 nắp đan vuông) bằng gạch chỉ dưới đường 1 tầng ống",
        "Xây bể cáp thông tin (bể 1 nắp đan dọc) bằng gạch chỉ dưới đường 1 tầng ống",
        "Sản xuất nắp đan bể xây gạch hoặc đá chẻ, trên hè 1200x500x70",
        "Sản xuất nắp đan bể xây gạch hoặc đá chẻ, dưới đường 1200x500x90",
        "Lắp đặt cấu kiện đối với bể 1 tầng cống. Loại nắp đan 1 đan dọc",
        "Lắp đặt cấu kiện đối với bể 1 tầng cống. Loại nắp đan 2 đan vuông",
        "Xây lắp Ganivo nắp bê tông 400x400 trên hè",
        "Xây lắp Ganivo nắp bê tông 400x400 dưới đường",
        "Xây lắp Ganivo nắp bê tông,loại 600 x 600 (trên hè sâu 820 )",
        
        # Nhóm 4: Hoàn trả
        "Móng cát vàng gia cố 8% xi măng",
        "Đắp cát nền hè bằng thủ công dầy 5cm",
        "Lát via hè gạch block tự chèn dầy 6cm ( gạch tận dụng 80%, 20% mua mới )",
        "Bê tông nền, đá 2x4, vữa BT M150",
        "Lát gạch terrazzo, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )",
        "Bê tông nền, đá 2x4, vữa BT M150 dầy 8cm",
        "Lát gạch BTXM giả đá conic, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )",
        "Lát hè đá xanh, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )",
        "Thi công móng cấp phối đá dăm lớp trên dầy 18cm",
        "Rải cấp phối đá dăm mặt đường đá nhựa cũ. Lớp dưới 25cm",
        "Tưới nhũ tương nhựa lót tiêu chuẩn 1,0kg/m2 thi công - nhũ tương nhựa - tưới thủ công",
        "Rải thảm mặt đường BT nhựa hạt thô, chiều dày mặt đường đã lèn ép 7 cm",
        "Tưới nhựa lót hoặc nhựa dính bám mặt đường, tiêu chuẩn 0,5kg/m2 - nhũ tương nhựa - tưới thủ công",
        "Làm mặt đường BT nhựa hạt mịn, chiều dày mặt đường đã lèn ép 5cm",
        "Bê tông mặt đường, chiều dày mặt đường <=25cm, đá 2x4, vữa BT M250",
        "Hoàn trả mặt hè bê tông dầy 10cm, đá 2x4, mác 250",
        
        # Nhóm 5: Vận chuyển
        "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp II",
        "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp III",
        "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp III"
    ]
    grouped['Item_Sort'] = grouped['Hạng mục'].apply(lambda x: item_order.index(x) if x in item_order else 999)
    
    grouped = grouped.sort_values(['Nhóm', 'Item_Sort', 'Hạng mục']).drop(columns=['Item_Sort'])
    
    # Làm tròn để phục vụ cộng dồn chính xác
    grouped['Khối lượng'] = grouped['Khối lượng'].round(2)
    return grouped

# --- KHỞI TẠO DỮ LIỆU BẢNG MẶC ĐỊNH ---
if 'df' not in st.session_state:
    row = {
        "STT": 1, "Kết cấu rãnh": "AL", "Cấp đất": 3, "Bể đầu": "B1", "Bể cuối": "B3", "Dài đo": 45.5,
        "Số ống tầng 1": 2, "Loại ống tầng 1": "D110x6.8", "Độ sâu rãnh": 0.71, "Số tầng ống": 1, "Số ống tầng 2": 0, "Loại ống tầng 2": "Không ống",
        "Kiểu kết nối": "Bể - Bể"
    }
    row["Cảnh Báo Lỗi"] = validate_row(row, st.session_state.db_ket_cau)
    st.session_state.df = pd.DataFrame([row])

if 'df_be' not in st.session_state:
    row_be = {
        "STT": 1, "Kết cấu bể/ga": "AL", "Cấp đất": 3, "Vị trí bể": "GA1", "Loại bể": "1DD", "Sâu bể (Đo)": 1.2
    }
    row_be["Cảnh Báo Lỗi"] = validate_be_row(row_be)
    st.session_state.df_be = pd.DataFrame([row_be])

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================

with st.sidebar:
    if st.button("⚙️ Trang Quản Trị", use_container_width=True):
        st.session_state.show_admin = True
        st.rerun()
            
    st.divider()

    st.markdown("### 🛠️ Nhập liệu Thủ công")
    if st.button("➕ Thêm dòng mới (Tuyến)", use_container_width=True):
        new_item = {
            "STT": len(st.session_state.df) + 1, "Kết cấu rãnh": "AL", "Cấp đất": 3, "Bể đầu": "", "Bể cuối": "", "Dài đo": 0.0,
            "Số ống tầng 1": 2, "Loại ống tầng 1": "D110x6.8", "Độ sâu rãnh": 0.6, "Số tầng ống": 1, "Số ống tầng 2": 0, "Loại ống tầng 2": "Không ống",
            "Kiểu kết nối": "Bể - Bể"
        }
        new_item["Cảnh Báo Lỗi"] = validate_row(new_item, st.session_state.db_ket_cau)
        new_row = pd.DataFrame([new_item])
        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
        st.rerun()

    if st.button("➕ Thêm dòng mới (Bể Ga)", use_container_width=True):
        new_be = {
            "STT": len(st.session_state.df_be) + 1, "Kết cấu bể/ga": "AL", "Cấp đất": 3, "Vị trí bể": "", "Loại bể": "GH400", "Sâu bể (Đo)": 1.0
        }
        new_be["Cảnh Báo Lỗi"] = validate_be_row(new_be)
        st.session_state.df_be = pd.concat([st.session_state.df_be, pd.DataFrame([new_be])], ignore_index=True)
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📥 Import / Export File")
    
    st.download_button(
        label="⬇️ Tải File Mẫu (Template) Excel",
        data=get_template_excel(),
        file_name="Template_NhapLieu_NoiThong.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    uploaded_file = st.file_uploader("Kéo thả file Excel/CSV vào đây", type=["xlsx", "xls", "csv"])
    if uploaded_file is not None:
        try:
            # 1. Thuật toán chống lặp vô tận (Infinite Rerun Loop)
            import hashlib
            file_bytes = uploaded_file.getvalue()
            file_hash = hashlib.md5(file_bytes).hexdigest()
            
            if st.session_state.get("last_file_hash") != file_hash:
                has_error = False
                # Detect sheets flexibly
                if uploaded_file.name.endswith('.csv'):
                    df_import = pd.read_csv(uploaded_file)
                    df_be_import = pd.DataFrame()
                else:
                    excel_data = pd.read_excel(uploaded_file, sheet_name=None)
                    sheet_names = list(excel_data.keys())
                    
                    df_import = excel_data.get('Data_Nhap_Lieu', pd.DataFrame())
                    if df_import.empty and len(sheet_names) > 0:
                        df_import = excel_data[sheet_names[0]]
                        
                    df_be_import = excel_data.get('Data_Be_Ga', pd.DataFrame())
                    if df_be_import.empty and len(sheet_names) > 1:
                        df_be_import = excel_data[sheet_names[1]]
                
                # --- XỬ LÝ SHEET 1: TUYẾN ---
                if not df_import.empty:
                    df_import = normalize_cols(df_import, TEMPLATE_COLUMNS)
                    
                    # Tự động điền STT nếu trống hoặc thiếu
                    if "STT" not in df_import.columns or df_import["STT"].isna().any():
                        df_import["STT"] = range(1, len(df_import) + 1)
                    
                    # Normalize data (Only for existing data)
                    for char_col in ["Chiều đặt", "Chiều đặt.1"]:
                        if char_col in df_import.columns:
                            mask = df_import[char_col].notna() & (df_import[char_col].astype(str).str.strip() != "")
                            df_import.loc[mask, char_col] = df_import.loc[mask, char_col].astype(str).str.strip().str.upper().replace(
                                {"N": "Ngang", "NGANG": "Ngang", "D": "Dọc", "DỌC": "Dọc"}
                            )

                    if "Trùng rãnh" in df_import.columns:
                        df_import["Trùng rãnh"] = df_import["Trùng rãnh"].apply(map_trung_val)
                    if "Kết cấu rãnh" in df_import.columns:
                        df_import["Kết cấu rãnh"] = df_import["Kết cấu rãnh"].apply(map_kc_keyword)
                    if "Cấp đất" in df_import.columns:
                        df_import["Cấp đất"] = df_import["Cấp đất"].apply(map_cap_dat_val)
                    
                    # Chuẩn hóa loại ống tầng 1 & 2
                    for pipe_col in ["Loại ống tầng 1", "Loại ống tầng 2"]:
                        if pipe_col in df_import.columns:
                            df_import[pipe_col] = df_import[pipe_col].apply(map_pipe_type)

                    for c in ["Dài đo", "Độ sâu rãnh", "Số ống tầng 2", "Số tầng ống"]:
                        if c in df_import.columns:
                            df_import[c] = df_import[c].astype(str).str.replace(",", ".", regex=False)
                            df_import[c] = pd.to_numeric(df_import[c], errors="coerce")

                    # Tự động điền Số tầng ống theo Số ống tầng 2 nếu trống
                    if "Số tầng ống" in df_import.columns:
                        def default_floors(row):
                            val_floors = row.get("Số tầng ống")
                            val_pipe2 = row.get("Số ống tầng 2", 0)
                            
                            p2 = float(val_pipe2) if not pd.isna(val_pipe2) else 0
                            
                            if pd.isna(val_floors) or val_floors == 0:
                                if p2 > 0: return 2
                                else: return 1
                            return val_floors
                        
                        df_import["Số tầng ống"] = df_import.apply(default_floors, axis=1)

                    if "Kiểu kết nối" in df_import.columns:
                        def clean_kieu_kn(v):
                            if pd.isna(v) or str(v).strip() == "": return None
                            s = str(v).strip().upper()
                            if "GANIVO" in s or "GA" in s: return "Ganivo - Ganivo, Bể"
                            if "BỂ" in s or "BE" in s: return "Bể - Bể"
                            return None
                        df_import["Kiểu kết nối"] = df_import["Kiểu kết nối"].apply(clean_kieu_kn)

                    errors = []
                    for _, row in df_import.iterrows():
                        try:
                            err = validate_row(row, st.session_state.db_ket_cau)
                            if err: has_error = True
                            errors.append(err)
                        except: errors.append("Lỗi hệ thống")
                    
                    df_import["Cảnh Báo Lỗi"] = errors
                    df_import = sync_soil_levels(df_import, "Kết cấu rãnh")
                    st.session_state.df = df_import

                # --- XỬ LÝ SHEET 2: BỂ GA ---
                if not df_be_import.empty:
                    df_be_import = normalize_cols(df_be_import, WELL_IMPORT_COLUMNS)
                    
                    # Tự động điền STT nếu trống hoặc thiếu
                    if "STT" not in df_be_import.columns or df_be_import["STT"].isna().any():
                        df_be_import["STT"] = range(1, len(df_be_import) + 1)

                    if "Kết cấu bể/ga" in df_be_import.columns:
                        df_be_import["Kết cấu bể/ga"] = df_be_import["Kết cấu bể/ga"].apply(map_kc_keyword)
                    if "Cấp đất" in df_be_import.columns:
                        df_be_import["Cấp đất"] = df_be_import["Cấp đất"].apply(map_cap_dat_val)
                    if "Sâu bể (Đo)" in df_be_import.columns:
                        df_be_import["Sâu bể (Đo)"] = df_be_import["Sâu bể (Đo)"].astype(str).str.replace(",", ".", regex=False)
                        df_be_import["Sâu bể (Đo)"] = pd.to_numeric(df_be_import["Sâu bể (Đo)"], errors="coerce")
                    
                    # Validate
                    be_errors = []
                    for _, row in df_be_import.iterrows():
                        be_err = validate_be_row(row)
                        if be_err: has_error = True
                        be_errors.append(be_err)
                    df_be_import["Cảnh Báo Lỗi"] = be_errors
                    df_be_import = sync_soil_levels(df_be_import, "Kết cấu bể/ga")
                    st.session_state.df_be = df_be_import

                st.session_state.last_file_hash = file_hash
                st.session_state.import_count = st.session_state.get("import_count", 0) + 1
                
                if has_error:
                    st.session_state.import_status = ("warning", "⚠️ Đã nạp dữ liệu nhưng phát hiện một số dòng chưa hợp lệ. Vui lòng kiểm tra cột 'Cảnh Báo Lỗi'!")
                else:
                    st.session_state.import_status = ("success", "✅ Import dữ liệu thành công!")
                    st.session_state.auto_calc = True
                st.rerun()

            # Hiển thị thông báo trạng thái sau khi rerun
            if "import_status" in st.session_state:
                status_type, status_msg = st.session_state.import_status
                if status_type == "success": st.success(status_msg)
                else: st.warning(status_msg)

        except Exception as e:
            st.error(f"❌ Lỗi xử lý file: {str(e)}")
            st.code(f"Traceback: {e}")

st.title("🏗️ Công cụ Bóc tách Khối lượng Nối thông")

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Tính Toán & Báo Cáo", "🔍 Tra Cứu Thông Số", "📑 Các hạng mục tính toán", "📖 Hướng dẫn sử dụng"])

with tab1:
    column_config = {
        "STT": st.column_config.NumberColumn("STT", disabled=True, width="small"),
        "Kết cấu rãnh": st.column_config.SelectboxColumn("Kết cấu rãnh", options=RAW_KET_CAU, required=True),
        "Cấp đất": st.column_config.SelectboxColumn("Cấp đất", options=DATA_CAP_DAT, required=True),
        "Bể đầu": st.column_config.TextColumn("Bể đầu", required=True),
        "Bể cuối": st.column_config.TextColumn("Bể cuối", required=True),
        "Số ống tầng 1": st.column_config.NumberColumn("Số ống tầng 1", min_value=0, step=1, required=True),
        "Loại ống tầng 1": st.column_config.SelectboxColumn("Loại ống tầng 1", options=DATA_LOAI_ONG, required=True),
        "Độ sâu rãnh": st.column_config.NumberColumn("Độ sâu rãnh", format="%.2f", required=True),
        "Số tầng ống": st.column_config.SelectboxColumn("Số tầng ống", options=[1, 2], required=True),
        "Số ống tầng 2": st.column_config.NumberColumn("Số ống tầng 2", min_value=0, step=1, required=True),
        "Loại ống tầng 2": st.column_config.SelectboxColumn("Loại ống tầng 2", options=DATA_LOAI_ONG, required=True),
        "Dài đo": st.column_config.NumberColumn("Dài đo (m)", format="%.1f", required=True),
        "Kiểu kết nối": st.column_config.SelectboxColumn("Kiểu kết nối (*)", options=["Bể - Bể", "Ganivo - Ganivo, Bể"], required=True),
        "Cảnh Báo Lỗi": st.column_config.TextColumn("⚠️ Cảnh Báo Lỗi", disabled=True, width="large")
    }

    # --- CẬP NHẬT CẢNH BÁO LIVE ---
    if not st.session_state.df.empty:
        st.session_state.df["Cảnh Báo Lỗi"] = st.session_state.df.apply(lambda r: validate_row(r, st.session_state.db_ket_cau), axis=1)

    # Dùng key động để force refresh khi import
    editor_key = f"editor_tuyen_{st.session_state.get('import_count', 0)}"
    be_key = f"editor_be_{st.session_state.get('import_count', 0)}"

    with st.expander("📝 1. Bảng Nhập Liệu Tuyến (Rãnh Cáp)", expanded=st.session_state.tables_expanded):
        edited_df = st.data_editor(
            st.session_state.df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=editor_key
        )
    
    if not edited_df.equals(st.session_state.df):
        st.session_state.df = sync_soil_levels(edited_df.copy(), "Kết cấu rãnh")
        st.rerun()

    if not st.session_state.df_be.empty:
        st.session_state.df_be["Cảnh Báo Lỗi"] = st.session_state.df_be.apply(validate_be_row, axis=1)

    with st.expander("🕳️ 2. Bảng Nhập Liệu Bể Ga", expanded=st.session_state.tables_expanded):
        column_config_be = {
            "STT": st.column_config.NumberColumn("STT", disabled=True, width="small"),
            "Kết cấu bể/ga": st.column_config.SelectboxColumn("Kết cấu bể/ga", options=RAW_KET_CAU, required=True),
            "Cấp đất": st.column_config.SelectboxColumn("Cấp đất", options=DATA_CAP_DAT, required=True),
            "Vị trí bể": st.column_config.TextColumn("Vị trí bể", required=True),
            "Loại bể": st.column_config.SelectboxColumn("Loại bể", options=WELL_NAMES, required=True),
            "Sâu bể (Đo)": st.column_config.NumberColumn("Sâu bể (Đo)", min_value=0.0, step=0.1, format="%.2f m"),
            "Cảnh Báo Lỗi": st.column_config.TextColumn("⚠️ Cảnh Báo Lỗi", disabled=True, width="large")
        }
        
        edited_df_be = st.data_editor(
            st.session_state.df_be,
            column_config=column_config_be,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=be_key
        )

    if not edited_df_be.equals(st.session_state.df_be):
        st.session_state.df_be = sync_soil_levels(edited_df_be.copy(), "Kết cấu bể/ga")
        st.rerun()
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        calc_clicked = st.button("🚀 TÍNH TOÁN & XUẤT BÁO CÁO", type="primary", use_container_width=True)
        
    # Tự động kích hoạt tính toán nếu có cờ auto_calc
    should_calculate = calc_clicked
    if st.session_state.get("auto_calc", False):
        should_calculate = True
        st.session_state.auto_calc = False # Reset cờ ngay sau khi nhận

    if should_calculate:
        st.session_state.tables_expanded = False # Tự động co bảng nhập liệu khi tính toán
        with st.spinner("Đang chạy thuật toán QS..."):
            all_results = []
            tuyen_warnings = {}
            
            for index, row in edited_df.iterrows():
                try:
                    L_actual = float(row["Dài đo"])
                    if pd.isna(L_actual) or L_actual == 0: continue
                except:
                    continue
                
                L_pipe_actual = L_actual
                ket_cau_raw = clean_excel_value(row["Kết cấu rãnh"])
                
                b1 = clean_excel_value(row.get('Bể đầu'))
                b2 = clean_excel_value(row.get('Bể cuối'))
                if ket_cau_raw.upper() == "NGOC":
                    tuyen = f"TUYẾN NGOC (Dòng {index+1})"
                    if b1 and b2:
                        tuyen = f"ĐOẠN {b1} - {b2} (Ngoc)"
                    kieu_ket_noi = row.get("Kiểu kết nối", "Bể - Bể") # Gán mặc định để tránh lỗi logic bên dưới
                else: 
                    tuyen = f"ĐOẠN {b1} - {b2}"
                    kieu_ket_noi = row.get("Kiểu kết nối")
                    if pd.isna(kieu_ket_noi) or not kieu_ket_noi:
                        st.error(f"Dòng {index+1}: Thiếu 'Kiểu kết nối'. Vui lòng chọn Bể-Bể hoặc Ganivo - Ganivo, Bể.")
                        continue
                
                # --- XỬ LÝ SỐ ỐNG VÀ KẾT CẤU ---
                so_tang = int(row.get("Số tầng ống", 1)) if not pd.isna(row.get("Số tầng ống")) else 1
                so_ong_t1 = int(row.get("Số ống tầng 1", 0)) if not pd.isna(row.get("Số ống tầng 1")) else 0
                so_ong_t2 = int(row.get("Số ống tầng 2", 0)) if not pd.isna(row.get("Số ống tầng 2")) else 0
                if so_tang == 1:
                    so_ong_t2 = 0
                
                tong_so_ong = so_ong_t1 + so_ong_t2
                if tong_so_ong == 0: tong_so_ong = 1 
                
                # --- TÍNH TOÁN THEO KẾT CẤU (BỎ QUA NẾU LÀ NGOC) ---
                if ket_cau_raw.upper() != "NGOC":
                    ket_cau = map_ket_cau(ket_cau_raw, tong_so_ong, kieu_ket_noi)
                    
                    if ket_cau not in st.session_state.db_ket_cau: 
                        st.warning(f"Bỏ qua tuyến {tuyen} do không map được kết cấu ({ket_cau}).")
                        continue
                    
                    H_def = st.session_state.db_ket_cau[ket_cau]["H_def"]
                    # Mặc định lấy theo kết cấu nếu không nhập sâu đo
                    H = float(row["Độ sâu rãnh"]) if not pd.isna(row["Độ sâu rãnh"]) and str(row["Độ sâu rãnh"]).strip() != "" and float(row["Độ sâu rãnh"]) > 0 else H_def
                    W_top = st.session_state.db_ket_cau[ket_cau]["W_top"]
                    W_bot = st.session_state.db_ket_cau[ket_cau]["W_bot"]
                    
                    # --- TÍNH ĐÀO ĐẤT ---
                    # Xác định cao độ phá dỡ
                    h_pha_do = 0.0
                    raw_upper = ket_cau_raw.upper()
                    if "AL" in raw_upper: h_pha_do = 0.12
                    elif "ĐBT" in raw_upper: h_pha_do = 0.20
                    elif "HBT" in raw_upper: h_pha_do = 0.10
                    elif any(x in raw_upper for x in ["TE", "ĐX", "GN", "GBT_DA"]): h_pha_do = 0.10
                    elif "BLOCK" in raw_upper: h_pha_do = 0.06
                    
                    H_dao = max(0, H - h_pha_do)
                    S_dao_thuc = ((W_top + W_bot) / 2) * H_dao
                    
                    V_dao_report = S_dao_thuc * L_actual 
                    
                    row_v_pha_do = 0
                    row_v_dao = V_dao_report
                    row_v_backfill = 0
                    
                    # 1. Thêm Phá dỡ 
                    if h_pha_do > 0:
                        row_v_pha_do = W_top * h_pha_do * L_actual
                        if "AL" in raw_upper:
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": "Phá dỡ kết cấu mặt đường bê tông Asphalt", 
                                "ĐVT": "m3", "Diễn giải": f"{L_actual:g} * ({W_top:g} * {h_pha_do:g})", 
                                "Khối lượng": round(row_v_pha_do, 3)
                            })
                        elif "ĐBT" in raw_upper:
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": "Phá dỡ kết cấu mặt đường bê tông xi măng bằng máy đục phá bê tông", 
                                "ĐVT": "m3", "Diễn giải": f"{L_actual:g} * ({W_top:g} * {h_pha_do:g})", 
                                "Khối lượng": round(row_v_pha_do, 3)
                            })
                        elif "HBT" in raw_upper:
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": "Phá dỡ kết cấu mặt hè bê tông xi măng bằng máy đục phá bê tông", 
                                "ĐVT": "m3", "Diễn giải": f"{L_actual:g} * ({W_top:g} * {h_pha_do:g})", 
                                "Khối lượng": round(row_v_pha_do, 3)
                            })
                        elif any(x in raw_upper for x in ["TE", "ĐX", "GN", "GBT_DA"]):
                            mapping_pha_do = {
                                "GBT_DA": "Phá dỡ nền gạch giả đá coric",
                                "ĐX": "Phá dỡ nền đá xanh",
                                "TE": "Phá dỡ nền gạch terrazzo",
                                "GN": "Phá dỡ nền gạch nung"
                            }
                            # Tìm từ khóa tương ứng để chọn tên hạng mục
                            ten_pha_do = next((v for k, v in mapping_pha_do.items() if k in raw_upper), "Phá dỡ nền gạch giả đá coric")
                            
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen, 
                                "Hạng mục": ten_pha_do,
                                "ĐVT": "m2", "Diễn giải": f"{L_actual:g} * {W_top:g}",
                                "Khối lượng": round(L_actual * W_top, 3)
                            })
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen,
                                "Hạng mục": "Phá dỡ kết cấu bê tông bê tông lót nền 10cm dưới kết cấu lớp gạch, đá",
                                "ĐVT": "m3", "Diễn giải": f"{L_actual:g} * {W_top:g} * 0.1",
                                "Khối lượng": round(L_actual * W_top * 0.1, 3)
                            })
                        elif "BLOCK" in raw_upper:
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen, 
                                "Hạng mục": "Phá dỡ nền hè gạch Block bằng thủ công",
                                "ĐVT": "m2", "Diễn giải": f"{L_actual:g} * {W_top:g}",
                                "Khối lượng": round(L_actual * W_top, 3)
                            })
                            
                        ten_cat = ""
                        if "AL" in raw_upper:
                            ten_cat = "Cắt mặt đường bê tông Asphan chiều dày lớp cắt <= 7cm"
                        elif "ĐBT" in raw_upper:
                            ten_cat = "Cắt mặt đường bê tông xi măng, Chiều sâu vết cắt <=7cm"
                        elif "HBT" in raw_upper:
                            ten_cat = "Cắt mặt hè bê tông xi măng, Chiều sâu vết cắt <=5cm"
                            
                        if ten_cat:
                            all_results.append({
                                "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": ten_cat,
                                "ĐVT": "m", "Diễn giải": f"{L_actual:g} * 2" if L_actual != 1 else "2",
                                "Khối lượng": round(L_actual * 2, 3)
                            })

                    # 2. Thêm Đào đất
                    cap_dat = row.get("Cấp đất", 3)
                    
                    # Logic đặc thù: Đất cấp II các loại gạch/đá thì trừ 0.03, còn lại trừ theo h_pha_do
                    h_sub_dao = h_pha_do
                    if (str(cap_dat) == "2" or cap_dat == 2) and any(x in raw_upper for x in ["TE", "ĐX", "GN", "GBT_DA"]):
                        h_sub_dao = 0.03
                    
                    H_dao_final = max(0, H - h_sub_dao)
                    V_dao_item = ((W_top + W_bot) / 2) * H_dao_final * L_actual
                    row_v_dao = V_dao_item # Cập nhật lại cho vận chuyển
                    
                    if str(cap_dat) == "2" or cap_dat == 2:
                        ten_dao = "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp II"
                    else:
                        ten_dao = "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp III" if H_dao_final <= 1.0 else "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=2m. Đất cấp III"
                    all_results.append({
                        "Nhóm": "2. Thi công nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": ten_dao, 
                        "ĐVT": "m3", "Diễn giải": f"{L_actual:g} * (({W_top:g} + {W_bot:g}) / 2) * {H_dao_final:g}", "Khối lượng": round(V_dao_item, 3)
                    })
                
                # --- TÍNH ỐNG NHỰA ---
                loai_ong_t1 = clean_excel_value(row.get("Loại ống tầng 1", "D110x5.5"))
                loai_ong_t2 = clean_excel_value(row.get("Loại ống tầng 2", "Không ống"))
                
                def extract_ong(loai_chuoi, so_ong_tang):
                    res = []
                    if "Không ống" in loai_chuoi:
                        return res
                    parts = [p.strip() for p in loai_chuoi.split('+') if p.strip()]
                    if not parts:
                        return res
                    
                    if len(parts) == 1:
                        res.append((parts[0], max(1, so_ong_tang)))
                    else:
                        so_loai = len(parts)
                        total_ong = max(so_ong_tang, so_loai)
                        
                        so_ong_loai_1 = total_ong - so_loai + 1
                        res.append((parts[0], so_ong_loai_1))
                        for i in range(1, so_loai):
                            res.append((parts[i], 1))
                            
                    return res
                
                danh_sach_ong = extract_ong(loai_ong_t1, so_ong_t1)
                if so_tang == 2:
                    danh_sach_ong.extend(extract_ong(loai_ong_t2, so_ong_t2))
                
                tong_pvc_114, tong_pvc_60, tong_xoan_65 = 0, 0, 0
                
                for loai_o, count_o in danh_sach_ong:
                    lo_up = loai_o.upper()
                    # Vật tư: Luôn ghi nhận vào nhóm Vật tư
                    all_results.append({
                        "Nhóm": "0. Vật tư", "Tuyến/Đoạn": tuyen, "Hạng mục": f"Ống nhựa {loai_o}", 
                        "ĐVT": "m", "Diễn giải": f"{L_pipe_actual:g}" if count_o == 1 else f"{L_pipe_actual:g} * {count_o}", 
                        "Khối lượng": round(L_pipe_actual * count_o, 3)
                    })

                    # Phân loại để tính Nhân công (Thi công nền tuyến)
                    # Theo yêu cầu: D110 tính vào mục PVC F <= 114mm, D61, D32 tính vào mục PVC F <= 60mm
                    if ket_cau_raw.upper() != "NGOC":
                        if "D110" in lo_up:
                            tong_pvc_114 += count_o
                        elif any(x in lo_up for x in ["D61", "D32"]) and "/" not in lo_up:
                            tong_pvc_60 += count_o
                        elif "D65/50" in lo_up:
                            tong_xoan_65 += count_o
                
                if ket_cau_raw.upper() != "NGOC":
                    if tong_xoan_65 > 0:
                        dg_xoan = f"{L_pipe_actual:g}" if tong_xoan_65 == 1 else f"{L_pipe_actual:g} * {tong_xoan_65}"
                        all_results.append({
                            "Nhóm": "2. Thi công nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": "Lắp ống dẫn cáp, loại ống xoắn HDPE F65/50. Số ống tổ hợp <=3", 
                            "ĐVT": "100m", "Diễn giải": f"{dg_xoan} / 100", 
                            "Khối lượng": round((L_pipe_actual * tong_xoan_65) / 100, 3)
                        })
                    if tong_pvc_114 > 0:
                        dg_pvc114 = f"{L_pipe_actual:g}" if tong_pvc_114 == 1 else f"{L_pipe_actual:g} * {tong_pvc_114}"
                        all_results.append({
                            "Nhóm": "2. Thi công nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": "Lắp ống dẫn cáp, loại ống PVC F <= 114 mm, nong một đầu . Số ống tổ hợp <= 3", 
                            "ĐVT": "100m", "Diễn giải": f"{dg_pvc114} / 100", 
                            "Khối lượng": round((L_pipe_actual * tong_pvc_114) / 100, 3)
                        })
                    if tong_pvc_60 > 0:
                        dg_pvc60 = f"{L_pipe_actual:g}" if tong_pvc_60 == 1 else f"{L_pipe_actual:g} * {tong_pvc_60}"
                        all_results.append({
                            "Nhóm": "2. Thi công nền tuyến", "Tuyến/Đoạn": tuyen, "Hạng mục": "Lắp ống dẫn cáp, loại ống PVC F <= 60 mm, nong một đầu . Số ống tổ hợp <= 3", 
                            "ĐVT": "100m", "Diễn giải": f"{dg_pvc60} / 100", 
                            "Khối lượng": round((L_pipe_actual * tong_pvc_60) / 100, 3)
                        })
                
                # --- HOÀN TRẢ VÀ VẬN CHUYỂN (BỎ QUA NẾU LÀ NGOC) ---
                if ket_cau_raw.upper() != "NGOC":
                    H_cung = sum([float(l["h"]) for l in st.session_state.db_ket_cau[ket_cau]["layers"] if str(l["h"]).lower() != "auto"])
                    def get_max_d(loai_c):
                        if "Không ống" in loai_c:
                            return 0.0
                        # Return diameter (m)
                        if "D110" in loai_c: return 0.11
                        if "D85/65" in loai_c: return 0.085
                        if "D65/50" in loai_c: return 0.065
                        if "D61" in loai_c: return 0.061
                        if "D40/30" in loai_c: return 0.04
                        if "D32" in loai_c: return 0.032
                        return 0.0
                    
                    h_cat_min = (get_max_d(loai_ong_t1) * 1) + (get_max_d(loai_ong_t2) * 1 if so_tang == 2 else 0) + 0.10 # Thêm 0.05m cát trên và 0.05m cát dưới
                    H_min = H_cung + h_cat_min
                    adjusted_layers = []
                    if H >= H_min:
                        for layer in st.session_state.db_ket_cau[ket_cau]["layers"]:
                            h_val = H - H_cung if str(layer["h"]).lower() == "auto" else float(layer["h"])
                            adjusted_layers.append({"name": layer["name"], "h": h_val, "type": layer["type"]})
                    else:
                        tuyen_warnings[tuyen] = f"Sâu rãnh đào ({H:.3f}m) < Độ sâu tối thiểu ({H_min:.3f}m). Các lớp nền bề mặt sẽ bị co giảm!"
                        h_cat_actual = h_cat_min if H >= h_cat_min else H
                        rem_H = max(0.0, H - h_cat_actual)
                        for layer in [l for l in st.session_state.db_ket_cau[ket_cau]["layers"] if str(l["h"]).lower() != "auto"]:
                            h_req = float(layer["h"])
                            h_alloc = min(h_req, rem_H)
                            rem_H -= h_alloc
                            adjusted_layers.append({"name": layer["name"], "h": h_alloc, "type": layer["type"]})
                        auto_l = next((l for l in st.session_state.db_ket_cau[ket_cau]["layers"] if str(l["h"]).lower() == "auto"), None)
                        if auto_l:
                            adjusted_layers.append({"name": auto_l["name"], "h": h_cat_actual, "type": auto_l["type"]})

                    curr_d = 0.0
                    for layer in adjusted_layers:
                        h_l = layer["h"]
                        if h_l <= 0:
                            continue
                        name_l = layer["name"]
                        type_l = layer["type"]
                        # "Bê tông mác 250" tính cho kết cấu ĐBT (Đường bê tông) và HBT (Hè bê tông)
                        if name_l == "Bê tông mác 250" and "ĐBT" not in raw_upper and "HBT" not in raw_upper:
                            curr_d += h_l
                            continue
                        w1 = round(W_top - (W_top - W_bot) * (curr_d / H), 2) if H > 0 else W_top
                        w2 = round(W_top - (W_top - W_bot) * ((curr_d + h_l) / H), 2) if H > 0 else W_top
                        
                        if name_l == "BT nhựa hạt trung":
                            all_results.append({"Nhóm": "4. Hoàn trả", "Tuyến/Đoạn": tuyen, "Hạng mục": "Tưới nhựa lót hoặc nhựa dính bám mặt đường, tiêu chuẩn 0,5kg/m2 - nhũ tương nhựa - tưới thủ công", "ĐVT": "m2", "Diễn giải": f"{L_actual:g} * {W_top:g}", "Khối lượng": round(L_actual * W_top, 3)})
                            all_results.append({"Nhóm": "4. Hoàn trả", "Tuyến/Đoạn": tuyen, "Hạng mục": "Rải thảm mặt đường BT nhựa hạt thô, chiều dày mặt đường đã lèn ép 7 cm", "ĐVT": "m2", "Diễn giải": f"{L_actual:g} * {W_top:g}", "Khối lượng": round(L_actual * W_top, 3)})
                        elif name_l == "BT nhựa hạt mịn":
                            all_results.append({"Nhóm": "4. Hoàn trả", "Tuyến/Đoạn": tuyen, "Hạng mục": "Tưới nhũ tương nhựa lót tiêu chuẩn 1,0kg/m2 thi công - nhũ tương nhựa - tưới thủ công", "ĐVT": "m2", "Diễn giải": f"{L_actual:g} * {W_top:g}", "Khối lượng": round(L_actual * W_top, 3)})
                            all_results.append({"Nhóm": "4. Hoàn trả", "Tuyến/Đoạn": tuyen, "Hạng mục": "Làm mặt đường BT nhựa hạt mịn, chiều dày mặt đường đã lèn ép 5cm", "ĐVT": "m2", "Diễn giải": f"{L_actual:g} * {W_top:g}", "Khối lượng": round(L_actual * W_top, 3)})
                        else:
                            # TÍNH KHỐI LƯỢNG CHO CÁC LỚP CÒN LẠI
                            # Yêu cầu: Bê tông, Đá dăm, Cát đệm, Lát gạch dùng Rộng miệng (W_top)
                            use_w_top = any(x in name_l for x in ["Bê tông", "Đá dăm", "Đệm cát", "Móng cát", "Lát gạch", "Hoàn trả"])
                            w_calc = round(W_top if use_w_top else (w1 + w2) / 2, 2)
                            
                            kl = w_calc * h_l * L_actual if type_l == "m3" else w_calc * L_actual
                            
                            if "cát đen" in name_l.lower():
                                def get_pipe_radius(l_c2):
                                    if "D110" in l_c2: return 0.055
                                    if "D85/65" in l_c2: return 0.0425
                                    if "D65/50" in l_c2: return 0.0325
                                    if "D61" in l_c2: return 0.0305
                                    if "D40/30" in l_c2: return 0.02
                                    if "D32" in l_c2: return 0.016
                                    return 0.0
                                
                                s_v_o = lambda l_c3, s_o: math.pi * (get_pipe_radius(l_c3)**2) * s_o if s_o > 0 else 0
                                kl = max(0, kl - (s_v_o(loai_ong_t1, so_ong_t1) + s_v_o(loai_ong_t2, so_ong_t2)) * L_pipe_actual)
                            
                            if name_l == "Đất đầm chặt K=0.95":
                                row_v_backfill += kl
                            
                            # Hiển thị con số cụ thể trong diễn giải
                            if type_l == "m3":
                                if "cát đen" in name_l.lower():
                                    sub_pi = []
                                    for l_pipe, s_pipe in danh_sach_ong:
                                        if s_pipe > 0:
                                            r = get_pipe_radius(l_pipe)
                                            if r > 0:
                                                p_sub = f"3.14 * {r:g} * {r:g}" if s_pipe == 1 else f"3.14 * {r:g} * {r:g} * {s_pipe:g}"
                                                sub_pi.append(p_sub)
                                    
                                    formula_specs = f"((({w1:g} + {w2:g}) / 2) * {h_l:g})"
                                    if sub_pi:
                                        formula_specs = f"({formula_specs} - ({' + '.join(sub_pi)}))"
                                    dg_layer = f"{L_actual:g} * {formula_specs}"
                                elif use_w_top:
                                    dg_layer = f"{L_actual:g} * {W_top:g} * {h_l:g}"
                                else:
                                    dg_layer = f"{L_actual:g} * (({w1:g} + {w2:g}) / 2) * {h_l:g}"
                            else:
                                dg_layer = f"{L_actual:g} * {w_calc:g}"
                                
                            # Xác định tên hạng mục động dựa trên lớp và kết cấu
                            item_name = DISPLAY_NAME_MAP.get(name_l, name_l)
                            if name_l == "Lát gạch terrazzo,BT,đá xanh + vữa":
                                if "GBT_DA" in raw_upper: item_name = "Lát gạch BTXM giả đá conic, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )"
                                elif "ĐX" in raw_upper: item_name = "Lát hè đá xanh, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )"
                                elif "GN" in raw_upper: item_name = "Hoàn trả mặt hè gạch nung"
                                else: item_name = "Lát gạch terrazzo, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )"
                            elif name_l == "Bê tông mác 250" and "HBT" in raw_upper:
                                item_name = "Hoàn trả mặt hè bê tông dầy 10cm, đá 2x4, mác 250"
                            elif name_l == "Bê tông M150":
                                if any(x in raw_upper for x in ["TE", "ĐX", "GN", "GBT_DA"]):
                                    item_name = "Bê tông nền, đá 2x4, vữa BT M150 dầy 8cm"
                                else:
                                    item_name = "Bê tông nền, đá 2x4, vữa BT M150"
                            elif name_l == "Lát gạch block dày 6cm":
                                item_name = "Lát via hè gạch block tự chèn dầy 6cm ( gạch tận dụng 80%, 20% mua mới )"
                            elif name_l == "Đệm cát vàng dày 5cm":
                                item_name = "Đắp cát nền hè bằng thủ công dầy 5cm"
                            elif name_l == "Đệm cát vàng (XM 8%) dày 10cm":
                                item_name = "Móng cát vàng gia cố 8% xi măng"
                            
                            # Xác định nhóm cho lớp hoàn trả
                            if any(x in name_l for x in ["Bê tông", "BT nhựa", "Đá dăm", "Hoàn trả", "Lát gạch", "Đệm cát vàng"]):
                                target_group = "4. Hoàn trả"
                            else:
                                target_group = "2. Thi công nền tuyến"
                                
                            all_results.append({
                                "Nhóm": target_group, 
                                "Tuyến/Đoạn": tuyen, 
                                "Hạng mục": item_name, 
                                "ĐVT": type_l, 
                                "Diễn giải": dg_layer, 
                                "Khối lượng": round(kl, 3)
                            })
                        curr_d += h_l
                    
                    if any(x in raw_upper for x in ["TE", "ĐX", "GN", "GBT_DA", "BLOCK"]):
                        row_v_vc = row_v_dao - row_v_backfill
                        diengiai_vc = f"{row_v_dao:g} - {row_v_backfill:g}"
                    else:
                        row_v_vc = row_v_pha_do + row_v_dao - row_v_backfill
                        diengiai_vc = f"{row_v_dao:g} + {row_v_pha_do:g} - {row_v_backfill:g}"
                        
                    if row_v_vc > 0:
                        ten_vc = "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp II" if str(cap_dat) == "2" else "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp III"
                        all_results.append({
                            "Nhóm": "5. Vận chuyển đất thừa", 
                            "Tuyến/Đoạn": tuyen, 
                            "Hạng mục": ten_vc, 
                            "ĐVT": "m3", 
                            "Diễn giải": diengiai_vc, 
                            "Khối lượng": row_v_vc
                        })

            # --- DỮ LIỆU PHƯƠNG PHÁP TÍNH (DÙNG CHO EXPORT) ---
            methodology_data = [
                ["Nhóm 0. Vật tư", "Ống nhựa D110, D61, D32 (Theo thực tế chủng loại)", "Cung cấp ống nhựa. Tính theo số liệu 'L đo' nhập vào (chính là chiều dài ống thực tế L đo).", "L đo × Số_lượng_ống"],
                ["Quy tắc chung", "Thông số Chiều rộng (Width)", "R_miệng; R_đáy: Chiều rộng tại miệng và đáy rãnh đào (toàn rãnh).\nR_miệng_lớp; R_đáy_lớp: Chiều rộng tại đỉnh và đáy của riêng lớp vật liệu đó.\n((R_miệng_lớp + R_đáy_lớp)/2): Chiều rộng trung bình của lớp vật liệu.", "Tra cứu tại Tab 2 cho từng loại kết cấu"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Cắt mặt hè các loại", "Cắt mép hè dọc theo Tuyến hoặc chu vi Bể ga", "Tuyến: L đo × 2 | Bể ga: 2 × (D_bì + R_bì)"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Cắt mặt đường (BTXM 20cm, Asphalt)", "Cắt mép đường dọc theo Tuyến hoặc chu vi Bể ga", "Tuyến: L đo × 2 | Bể ga: 2 × (D_bì + R_bì)"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền gạch giả đá coric", "Phá lớp gạch giả đá Coric vỉa hè", "Tuyến: R_miệng × L đo | Bể ga: D_bì × R_bì"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền đá xanh", "Phá lớp gạch đá xanh vỉa hè", "Tuyến: R_miệng × L đo | Bể ga: D_bì × R_bì"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền gạch terrazzo", "Phá lớp gạch Terrazzo vỉa hè", "Tuyến: R_miệng × L đo | Bể ga: D_bì × R_bì"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền gạch nung", "Phá lớp gạch nung vỉa hè", "Tuyến: R_miệng × L đo | Bể ga: D_bì × R_bì"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu bê tông không cốt thép bằng búa căn", "Phá các lớp móng bê tông M150, M250", "Tuyến: ((R_miệng + R_đáy) / 2) × Dày_BT × L đo | Bể ga: D_bì × R_bì × Dày_BT"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu mặt đường bê tông Asphalt", "Phá dỡ lớp bê tông nhựa hiện trạng", "Tuyến: R_miệng × 0.12 × L đo | Bể ga: D_bì × R_bì × 0.12"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu bê tông bê tông lót nền 10cm dưới kết cấu lớp gạch, đá", "Phá lớp bê tông lót sàn vỉa hè cho gạch, đá", "Tuyến: R_miệng × 0.10 × L đo | Bể ga: S_bì × 0.10"],
                ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền hè gạch Block bằng thủ công", "Phá lớp gạch Block mặt hè (chỉ kết cấu Block)", "R_miệng × L đo"],
                ["Nhóm 2. Thi công nền tuyến", "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp II", "Đào đất cấp 2 cho rãnh hoặc bể ga sâu <= 1m", "Tuyến: ((R_miệng + R_đáy) / 2) × H_đào × L đo | Bể ga: D_bì × R_bì × S_đo"],
                ["Nhóm 2. Thi công nền tuyến", "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp III", "Đào đất cấp 3 cho rãnh hoặc bể ga sâu <= 1m", "Tuyến: ((R_miệng + R_đáy) / 2) × H_đào × L đo | Bể ga: D_bì × R_bì × S_đo"],
                ["Nhóm 2. Thi công nền tuyến", "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=2m. Đất cấp III", "Đào đất cấp 3 cho rãnh hoặc bể ga sâu > 1m", "Tuyến: ((R_miệng + R_đáy) / 2) × H_đào × L đo | Bể ga: D_bì × R_bì × S_đo"],
                ["Nhóm 2. Thi công nền tuyến", "Lắp ống dẫn cáp, loại ống xoắn HDPE F65/50. Số ống tổ hợp <=3", "Nhân công lắp đặt tổ hợp ống HDPE D65/50.", "(L đo × Số_lượng_ống) / 100"],
                ["Nhóm 2. Thi công nền tuyến", "Lắp ống dẫn cáp, loại ống PVC F <= 114 mm, nong một đầu . Số ống tổ hợp <= 3", "Nhân công lắp đặt tổ hợp ống D110.", "(L đo × Số_lượng_ống) / 100"],
                ["Nhóm 2. Thi công nền tuyến", "Lắp ống dẫn cáp, loại ống PVC F <= 60 mm, nong một đầu . Số ống tổ hợp <= 3", "Nhân công lắp đặt tổ hợp ống D61, D32.", "(L đo × Số_lượng_ống) / 100"],
                ["Nhóm 2. Thi công nền tuyến", "Phân rải và đầm nén cát tuyến ống dẫn cáp thông tin. Đầm bằng thủ công", "Lớp lót bảo vệ ống rãnh cáp", "(V_lấp_đầy - V_ống)"],
                ["Nhóm 2. Thi công nền tuyến", "Lấp đất và đầm rãnh cáp đào qua hè, đường, độ chặt yêu cầu K=0,95", "Đất đắp hoàn trả rãnh cáp", "((R_miệng_lớp + R_đáy_lớp) / 2) × H_đất × L đo"],
                ["Nhóm 4. Hoàn trả", "Hoàn trả bê tông nền, đá 1x2, vữa BT M150 (hè lát gạch, đá, Bê tông bảo vệ ống dưới đường nhựa Asphalt)", "Lót móng hè / Bê tông bảo vệ ống", "R_miệng × Dày_lớp × L đo"],
                ["Nhóm 4. Hoàn trả", "Đệm cát vàng dày 5cm", "Lớp đệm cát vỉa hè", "R_miệng × 0.05 × L đo"],
                ["Nhóm 4. Hoàn trả", "Đệm cát vàng (XM 8%) dày 10cm", "Lớp đệm cát vỉa hè cho gạch nung", "R_miệng × 0.10 × L đo"],
                ["Nhóm 4. Hoàn trả", "Lát gạch block dày 6cm", "Lát gạch Block vỉa hè", "R_miệng × L đo"],
                ["Nhóm 3. Thi công bể ga", "Đắp đất xung quanh thành bể, xung quanh tủ POP…, độ chặt yêu cầu K=0,95", "Đắp đất khe hở thành bể ga", "(S_bi - S_thân) × H_đắp"],
                ["Nhóm 4. Hoàn trả", "Hoàn trả mặt hè gạch Terrazzo", "Lát gạch Terrazzo", "R_miệng × L đo"],
                ["Nhóm 4. Hoàn trả", "Hoàn trả mặt hè bê tông dầy 10cm", "Hoàn trả BT mặt hè (chỉ kết cấu HBT)", "R_miệng × 0.10 × L đo"],
                ["Nhóm 4. Hoàn trả", "Bê tông mặt đường, đá 1x2 - Chiều dày mặt đường ≤25cm, vữa BT M250", "Bề mặt bê tông đường", "R_miệng × Dày_lớp × L đo"],
                ["Nhóm 4. Hoàn trả", "Rải cấp phối đá dăm mặt đường đá nhựa cũ. Lớp dưới 25cm / Lớp trên 18cm", "Đá dăm hoàn trả", "R_miệng × Dày_lớp × L đo"],
                ["Nhóm 4. Hoàn trả", "Tưới nhũ tương nhựa lót tiêu chuẩn 1,1kg/m2 thi công - nhũ tương nhựa - tưới thủ công", "Tưới nhũ tương nhựa lót", "R_miệng × L đo"],
                ["Nhóm 4. Hoàn trả", "Rải thảm bê tông asphan bảo vệ mặt đường. Hạt trung dày 7cm", "Trải nhựa bề mặt Asphalt hạt trung", "R_miệng × L đo"],
                ["Nhóm 4. Hoàn trả", "Tưới nhựa lót hoặc nhựa dính bám mặt đường, tiêu chuẩn 0,5kg/m2 - nhũ tương nhựa - tưới thủ công", "Tưới dính bám", "R_miệng × L đo"],
                ["Nhóm 4. Hoàn trả", "Rải thảm bê tông asphan bảo vệ mặt đường. Hạt mịn dày 5cm", "Trải nhựa bề mặt Asphalt hạt mịn", "R_miệng × L đo"],
                ["Nhóm 5. Vận chuyển đất thừa", "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp II / cấp III", "Vận chuyển đất thừa ra bãi thải", "Đào + Phá - Lấp"],
            ]


            # --- XỬ LÝ BẢNG BỂ/GA ---
            for index, row in edited_df_be.iterrows():
                try:
                    row_v_dao_be = 0
                    row_v_pha_do_be = 0
                    row_v_backfill_be = 0
                    loai_be = clean_excel_value(row.get("Loại bể", ""))
                    if not loai_be or loai_be == "Không có": continue
                    
                    spec = DB_BE_SPECS.get(loai_be)
                    if not spec: continue
                    
                    vi_tri = clean_excel_value(row.get("Vị trí bể", f"Bể {index+1}"))
                    cap_dat = row.get("Cấp đất", 3)
                    sau_do = float(row.get("Sâu bể (Đo)", 0))
                    if sau_do <= 0:
                        st.warning(f"Bể {vi_tri}: Thiếu 'Sâu bể (Đo)'. Vui lòng nhập đầy đủ!")
                        continue
                    
                    dai_bi = spec["dai"] + 2 * spec["flange"]
                    rong_bi = spec["rong"] + 2 * spec["flange"]
                    S_bi = dai_bi * rong_bi
                    Chu_vi_bi = 2 * (dai_bi + rong_bi)
                    cao_day = spec["cao_day"]
                    
                    # --- LẤY THÔNG TIN KẾT CẤU & TÍNH CAO PHÁ DỠ ---
                    kc_be = clean_excel_value(row.get("Kết cấu bể/ga", "")).upper()
                    
                    h_pha_do_be = 0.0
                    if "AL" in kc_be: h_pha_do_be = 0.12
                    elif "ĐBT" in kc_be: h_pha_do_be = 0.20
                    elif "HBT" in kc_be: h_pha_do_be = 0.10
                    elif any(x in kc_be for x in ["TE", "ĐX", "GN", "GBT_DA"]): h_pha_do_be = 0.10
                    elif "BLOCK" in kc_be: h_pha_do_be = 0.06
                    
                    H_dao_be = max(0, sau_do - h_pha_do_be)
                    tong_sau = H_dao_be # Tạm thời không cộng thêm độ cao đáy bể: H_dao_be + cao_day
                    v_be = S_bi * tong_sau
                    
                    # Xác định hạng mục đào tương tự rãnh
                    if str(cap_dat) == "2" or cap_dat == 2:
                        ten_dao = "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp II"
                    elif str(cap_dat) == "3" or cap_dat == 3:
                        if tong_sau <= 1.0:
                            ten_dao = "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp III"
                        else:
                            ten_dao = "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=2m. Đất cấp III"
                    else:
                        ten_dao = f"Đào đất cấp {cap_dat} (Bể)"

                    # Logic đặc thù cho Bể: Đất cấp II các loại gạch/đá thì trừ 0.03, còn lại trừ theo h_pha_do_be
                    h_sub_dao_be = h_pha_do_be
                    if (str(cap_dat) == "2" or cap_dat == 2) and any(x in kc_be for x in ["TE", "ĐX", "GN", "GBT_DA"]):
                        h_sub_dao_be = 0.03
                    
                    H_dao_final_be = max(0, sau_do - h_sub_dao_be)
                    V_dao_be_item = S_bi * H_dao_final_be
                    row_v_dao_be = V_dao_be_item # Cập nhật lại cho vận chuyển
                    
                    if h_pha_do_be > 0:
                        dien_giai_be = f"1 * ({dai_bi:g} * {rong_bi:g} * {H_dao_final_be:g})"
                    else:
                        dien_giai_be = f"1 * ({dai_bi:g} * {rong_bi:g} * {sau_do:g})"
                    
                    all_results.append({
                        "Nhóm": "2. Thi công nền tuyến", 
                        "Tuyến/Đoạn": f"Bể {vi_tri}", 
                        "Hạng mục": ten_dao, 
                        "ĐVT": "m3", 
                        "Diễn giải": dien_giai_be, 
                        "Khối lượng": round(V_dao_be_item, 3)
                    })

                    # --- TÍNH ĐẮP ĐẤT CHO BỂ GA ---
                    h_backfill = H_dao_be
                    S_well = spec["dai"] * spec["rong"]
                    v_dap_be = (S_bi - S_well) * h_backfill
                    
                    if v_dap_be > 0:
                        row_v_backfill_be += v_dap_be
                        all_results.append({
                            "Nhóm": "3. Thi công bể",
                            "Tuyến/Đoạn": f"Bể {vi_tri}",
                            "Hạng mục": "Đắp đất xung quanh thành bể, xung quanh tủ POP…, độ chặt yêu cầu K=0,95",
                            "ĐVT": "m3",
                            "Diễn giải": f"1 * (({S_bi:g} - {S_well:g}) * {h_backfill:g})",
                            "Khối lượng": round(v_dap_be, 3)
                        })

                    # --- CÁC HẠNG MỤC PHỤ TRỢ BỂ (KHUNG, NẮP, GANIVO) ---
                    def add_be_sub_item(name, dvt, kl, dg):
                        all_results.append({
                            "Nhóm": "3. Thi công bể", "Tuyến/Đoạn": f"Bể {vi_tri}",
                            "Hạng mục": name, "ĐVT": dvt, "Diễn giải": dg, "Khối lượng": kl
                        })

                    # 1-4. Gia công khung bể
                    if loai_be == "2VH":
                        add_be_sub_item("Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp trên hè), loại bể cáp 2 đan vuông", "bể", 1, "1")
                    elif loai_be == "1DH":
                        add_be_sub_item("Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp trên hè), loại bể cáp 1 đan dọc", "bể", 1, "1")
                    elif loai_be == "2VD":
                        add_be_sub_item("Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp dưới đường), loại bể cáp 2 đan vuông", "bể", 1, "1")
                    elif loai_be == "1DD":
                        add_be_sub_item("Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp dưới đường), loại bể cáp 1 đan dọc", "bể", 1, "1")

                    # 5-6. Gia công chân khung (Cho loại 1 đan và 2 đan)
                    if loai_be in ["2VD", "2VH"]:
                        add_be_sub_item("Gia công chân khung bể cáp cho loại bể cáp 2 đan vuông", "bể", 1, "1")
                    elif loai_be in ["1DD", "1DH"]:
                        add_be_sub_item("Gia công chân khung bể cáp cho loại bể cáp 1 đan dọc", "bể", 1, "1")

                    # 7-8. Sản xuất nắp đan (1200x500x70) - Lấy ký tự đầu tiên của mã bể (Chỉ tính cho bể hè)
                    if loai_be in ["1DH", "2VH", "3VH"]:
                        try:
                            num_lids = int(loai_be[0])
                            add_be_sub_item("Sản xuất nắp đan bể xây gạch hoặc đá chẻ, trên hè 1200x500x70", "nắp đan", num_lids, f"{num_lids}")
                        except: pass

                    # Bổ sung theo yêu cầu mới
                    # 1. Sản xuất nắp đan dưới đường 1200x500x90
                    if loai_be in ["1DD", "2VD", "3VD"]:
                        try:
                            num_lids = int(loai_be[0])
                            add_be_sub_item("Sản xuất nắp đan bể xây gạch hoặc đá chẻ, dưới đường 1200x500x90", "nắp đan", num_lids, f"{num_lids}")
                        except: pass

                    # 2-5. Xây bể cáp thông tin bằng gạch chỉ (1 tầng ống)
                    if loai_be == "2VH":
                        add_be_sub_item("Xây bể cáp thông tin (bể 2 nắp đan vuông) bằng gạch chỉ trên hè 1 tầng ống", "bể", 1, "1")
                    elif loai_be == "1DH":
                        add_be_sub_item("Xây bể cáp thông tin (bể 1 nắp đan dọc) bằng gạch chỉ trên hè 1 tầng ống", "bể", 1, "1")
                    elif loai_be == "2VD":
                        add_be_sub_item("Xây bể cáp thông tin (bể 2 nắp đan vuông) bằng gạch chỉ dưới đường 1 tầng ống", "bể", 1, "1")
                    elif loai_be == "1DD":
                        add_be_sub_item("Xây bể cáp thông tin (bể 1 nắp đan dọc) bằng gạch chỉ dưới đường 1 tầng ống", "bể", 1, "1")

                    # 6-7. Lắp đặt cấu kiện đối với bể 1 tầng cống
                    if loai_be in ["1DD", "1DH"]:
                        add_be_sub_item("Lắp đặt cấu kiện đối với bể 1 tầng cống. Loại nắp đan 1 đan dọc", "bể", 1, "1")
                    elif loai_be in ["2VD", "2VH"]:
                        add_be_sub_item("Lắp đặt cấu kiện đối với bể 1 tầng cống. Loại nắp đan 2 đan vuông", "bể", 1, "1")

                    # 9-10. Ganivo
                    if loai_be == "GH400":
                        add_be_sub_item("Xây lắp Ganivo nắp bê tông 400x400 trên hè", "ganivo", 1, "1")
                    elif loai_be == "GD400":
                        add_be_sub_item("Xây lắp Ganivo nắp bê tông 400x400 dưới đường", "ganivo", 1, "1")
                    elif loai_be == "GH600":
                        add_be_sub_item("Xây lắp Ganivo nắp bê tông,loại 600 x 600 (trên hè sâu 820 )", "ganivo", 1, "1")

                    # --- TÍNH PHÁ DỠ & CẮT CHO BỂ GA ---
                    chu_thich_bi = f"{loai_be}: {dai_bi:g}m x {rong_bi:g}m"

                    # 1. Cắt mặt đường/hè
                    ten_cat_be = ""
                    if "HBT" in kc_be:
                        ten_cat_be = "Cắt mặt hè bê tông xi măng, Chiều sâu vết cắt <=5cm"
                    elif "AL" in kc_be:
                        ten_cat_be = "Cắt mặt đường bê tông Asphan chiều dày lớp cắt <= 7cm"
                    elif "ĐBT" in kc_be:
                        ten_cat_be = "Cắt mặt đường bê tông xi măng, Chiều sâu vết cắt <=7cm"
                    
                    if ten_cat_be:
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}", "Hạng mục": ten_cat_be,
                            "ĐVT": "m", "Diễn giải": f"1 * (2 * ({dai_bi:g} + {rong_bi:g}))",
                            "Khối lượng": round(Chu_vi_bi, 3)
                        })

                    # 2. Phá dỡ
                    if "AL" in kc_be:
                        v_pha_nhua = S_bi * 0.12 
                        row_v_pha_do_be += v_pha_nhua
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}", "Hạng mục": "Phá dỡ kết cấu mặt đường bê tông Asphalt",
                            "ĐVT": "m3", "Diễn giải": f"1 * ({dai_bi:g} * {rong_bi:g} * 0.12)",
                            "Khối lượng": round(v_pha_nhua, 3)
                        })
                    elif "ĐBT" in kc_be:
                        v_pha_bt = S_bi * 0.20 
                        row_v_pha_do_be += v_pha_bt
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}", "Hạng mục": "Phá dỡ kết cấu mặt đường bê tông xi măng bằng máy đục phá bê tông",
                            "ĐVT": "m3", "Diễn giải": f"1 * ({dai_bi:g} * {rong_bi:g} * 0.2)",
                            "Khối lượng": round(v_pha_bt, 3)
                        })
                    elif "HBT" in kc_be:
                        v_pha_hbt = S_bi * 0.10 
                        row_v_pha_do_be += v_pha_hbt
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}", "Hạng mục": "Phá dỡ kết cấu mặt hè bê tông xi măng bằng máy đục phá bê tông",
                            "ĐVT": "m3", "Diễn giải": f"1 * ({dai_bi:g} * {rong_bi:g} * 0.1)",
                            "Khối lượng": round(v_pha_hbt, 3)
                        })
                    elif any(x in kc_be for x in ["TE", "ĐX", "GN", "GBT_DA"]):
                        mapping_pha_do_be = {
                            "GBT_DA": "Phá dỡ nền gạch giả đá coric",
                            "ĐX": "Phá dỡ nền đá xanh",
                            "TE": "Phá dỡ nền gạch terrazzo",
                            "GN": "Phá dỡ nền gạch nung"
                        }
                        ten_pha_do_be = next((v for k, v in mapping_pha_do_be.items() if k in kc_be), "Phá dỡ nền gạch giả đá coric")
                        
                        v_pha_bt_lot = S_bi * 0.10
                        row_v_pha_do_be += S_bi * h_pha_do_be 
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}", 
                            "Hạng mục": ten_pha_do_be,
                            "ĐVT": "m2", "Diễn giải": f"1 * ({dai_bi:g} * {rong_bi:g})",
                            "Khối lượng": round(S_bi, 3)
                        })
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}",
                            "Hạng mục": "Phá dỡ kết cấu bê tông bê tông lót nền 10cm dưới kết cấu lớp gạch, đá",
                            "ĐVT": "m3", "Diễn giải": f"1 * ({dai_bi:g} * {rong_bi:g} * 0.1)",
                            "Khối lượng": round(v_pha_bt_lot, 3)
                        })
                    elif "BLOCK" in kc_be:
                        all_results.append({
                            "Nhóm": "1. Phá dỡ nền tuyến", "Tuyến/Đoạn": f"Bể {vi_tri}", 
                            "Hạng mục": "Phá dỡ nền hè gạch Block bằng thủ công",
                            "ĐVT": "m2", "Diễn giải": f"1 * ({dai_bi:g} * {rong_bi:g})",
                            "Khối lượng": round(S_bi, 3)
                        })


                    # --- TÍNH VẬN CHUYỂN BỂ GA ---
                    if any(x in kc_be for x in ["TE", "ĐX", "GN", "GBT_DA", "BLOCK"]):
                        v_vc_be = row_v_dao_be - row_v_backfill_be
                        diengiai_vc_be = f"{row_v_dao_be:g} - {row_v_backfill_be:g}"
                    else:
                        v_vc_be = row_v_dao_be + row_v_pha_do_be - row_v_backfill_be
                        diengiai_vc_be = f"{row_v_dao_be:g} + {row_v_pha_do_be:g} - {row_v_backfill_be:g}"

                    if v_vc_be > 0:
                        cap_dat_be = row.get("Cấp đất", 3)
                        ten_vc_be = "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp II" if str(cap_dat_be) == "2" or cap_dat_be == 2 else "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp III"
                        all_results.append({
                            "Nhóm": "5. Vận chuyển đất thừa", "Tuyến/Đoạn": f"Bể {vi_tri}", 
                            "Hạng mục": ten_vc_be, 
                            "ĐVT": "m3", 
                            "Diễn giải": diengiai_vc_be, 
                            "Khối lượng": v_vc_be
                        })

                except Exception as e:
                    st.warning(f"Lỗi tính toán bể tại dòng {index+1}: {e}")

            res_df = pd.DataFrame(all_results)
            if not res_df.empty:
                res_df["Cảnh báo thi công"] = res_df["Tuyến/Đoạn"].map(tuyen_warnings).fillna("")
            
            summary_df = create_grouped_report(all_results)

            st.success("✅ Tính toán bóc tách thành công!")
            
            if tuyen_warnings:
                with st.expander("⚠️ XEM CÁC CẢNH BÁO THI CÔNG NGẦM (THIẾU SÂU)"):
                    for t_name, t_warn in tuyen_warnings.items():
                        st.warning(f"**Tuyến '{t_name}'**: {t_warn}")
            
            st.markdown("#### 1. Bảng Tổng Hợp Khối Lượng (Grouped)")
            
            def highlight_groups(row):
                nhom = str(row['Nhóm'])
                if "0. Vật tư" in nhom:
                    return ['background-color: rgba(173, 216, 230, 0.15)'] * len(row)
                elif "1. Phá dỡ" in nhom:
                    return ['background-color: rgba(255, 182, 193, 0.15)'] * len(row)
                elif "2. Thi công nền tuyến" in nhom:
                    return ['background-color: rgba(144, 238, 144, 0.15)'] * len(row)
                elif "3. Thi công bể" in nhom:
                    return ['background-color: rgba(255, 255, 224, 0.15)'] * len(row)
                elif "4. Hoàn trả" in nhom:
                    return ['background-color: rgba(221, 160, 221, 0.15)'] * len(row)
                elif "5. Vận chuyển" in nhom:
                    return ['background-color: rgba(200, 200, 200, 0.15)'] * len(row)
                return [''] * len(row)

            if not summary_df.empty:
                summary_df.insert(0, 'STT', range(1, len(summary_df) + 1))
                # Định dạng hiển thị
                def fmt_kl(v, nhom=""):
                    if pd.isna(v): return ""
                    v_float = float(v)
                    if v_float == 0: return "0"
                    # Hạng mục vận chuyển: giữ nguyên, không làm tròn
                    if "Vận chuyển" in str(nhom):
                        # Loại bỏ trailing zeros nhưng giữ đủ chữ số
                        return f"{v_float:.10f}".rstrip('0').rstrip('.')
                    if v_float == int(v_float): return f"{int(v_float)}"
                    if abs(v_float) < 0.0001: return f"{v_float:.6f}"
                    if abs(v_float) < 0.01: return f"{v_float:.4f}"
                    return f"{v_float:.2f}"
                
                # Convert Khối lượng sang chuỗi để Streamlit không tự format
                display_df = summary_df.copy()
                display_df['Khối lượng'] = display_df.apply(lambda r: fmt_kl(r['Khối lượng'], r.get('Nhóm', '')), axis=1)
                
                st.dataframe(
                    display_df.style.apply(highlight_groups, axis=1), 
                    use_container_width=True, 
                    hide_index=True,
                    height=600
                )
            else:
                st.info("Không có dữ liệu tổng hợp.")
            
            # st.markdown("#### 2. Bảng Chi Tiết Từng Tuyến")
            if not res_df.empty:
                res_df.insert(0, 'STT', range(1, len(res_df) + 1))
                # st.dataframe(res_df.style.apply(highlight_groups, axis=1), use_container_width=True, hide_index=True)
            # else:
            #     st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                cell_wrap = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})
                cell_nowrap = workbook.add_format({'border': 1, 'text_wrap': False, 'valign': 'top'})

                def setup_ws(ws, df, sheet_name):
                    (max_row, max_col) = df.shape
                    ws.autofilter(0, 0, max_row, max_col)
                    for i, col in enumerate(df.columns):
                        # Tính chiều rộng sơ bộ
                        content_len = df[col].astype(str).map(len).max()
                        header_len = len(str(col))
                        width = min(max(content_len, header_len) + 3, 70)
                        
                        # Rule: Wrap text cho tất cả trừ 'Diễn giải' của sheet Tong_Hop
                        fmt = cell_wrap
                        if sheet_name == 'Tong_Hop' and col == 'Diễn giải':
                            fmt = cell_nowrap
                            width = 100 # Cho rộng hơn vì không wrap
                        
                        ws.set_column(i, i, width, fmt)
                        # Ghi đè header cho đẹp
                        ws.write(0, i, col, header_fmt)

                # 1. Trang đầu vào Tuyến
                edited_df.to_excel(writer, sheet_name='Data_Dau_Vao_Tuyen', index=False)
                setup_ws(writer.sheets['Data_Dau_Vao_Tuyen'], edited_df, 'Data_Dau_Vao_Tuyen')

                # 2. Trang đầu vào Bể ga
                edited_df_be.to_excel(writer, sheet_name='Data_Dau_Vao_Be', index=False)
                setup_ws(writer.sheets['Data_Dau_Vao_Be'], edited_df_be, 'Data_Dau_Vao_Be')

                # 3. Trang tổng hợp
                if not summary_df.empty:
                    summary_df.to_excel(writer, sheet_name='Tong_Hop', index=False)
                    setup_ws(writer.sheets['Tong_Hop'], summary_df, 'Tong_Hop')

                # 4. Trang chi tiết
                res_df.to_excel(writer, sheet_name='Chi_Tiet_Tuyen', index=False)
                setup_ws(writer.sheets['Chi_Tiet_Tuyen'], res_df, 'Chi_Tiet_Tuyen')

                # 5. Trang phương pháp tính
                df_meth = pd.DataFrame(methodology_data, columns=["Nhóm", "Hạng mục báo cáo", "Diễn giải chi tiết", "Công thức tính toán"])
                df_meth.to_excel(writer, sheet_name='Huong_Dan_Phuong_Phap_Tinh', index=False)
                setup_ws(writer.sheets['Huong_Dan_Phuong_Phap_Tinh'], df_meth, 'Huong_Dan_Phuong_Phap_Tinh')
                
                writer.sheets['Huong_Dan_Phuong_Phap_Tinh'].freeze_panes(1, 0)
            
            # Lưu vào session state để không bị mất khi rerun
            st.session_state.report_data = output.getvalue()

    if "report_data" in st.session_state:
        with col_btn2:
            st.download_button(
                label="📥 Tải Báo Cáo Excel (.xlsx)",
                data=st.session_state.report_data,
                file_name="Khối lượng nối thông.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

with tab2:
    col_head1, col_head2 = st.columns([2, 1])
    with col_head1:
        st.markdown("### 🔍 Tra Cứu Thông Số Chuẩn")
    with col_head2:
        # Nút xuất danh sách kết cấu
        db_xlsx = get_db_export_excel()
        st.download_button(
            label="📥 Xuất danh sách tất cả kết cấu (Excel)",
            data=db_xlsx,
            file_name="Danh_sach_ket_cau_HE_THONG.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with st.expander("1. Thông số Bể Cáp/Ga (Khấu trừ) - Bấm để mở rộng", expanded=False):
        # Tái cấu trúc Dictionary bể để hiển thị theo dạng nhiều cột
        be_data = {}
        for k, v in DB_BE.items():
            if k == "Không có": continue
            loai_be = k.split(" (")[0]
            huong = "Dọc" if "Dọc" in k else "Ngang"
            
            if loai_be not in be_data:
                spec = DB_BE_SPECS.get(loai_be, {})
                be_data[loai_be] = {
                    "Loại bể/Ga": loai_be, 
                    "Dài bể": f"{spec.get('dai', 0):.3f}",
                    "Rộng bể": f"{spec.get('rong', 0):.3f}",
                    "Cao đáy bể": f"{spec.get('cao_day', 0):.3f}",
                    "Dọc (Bì)": "-", 
                    "Ngang (Bì)": "-", 
                    "Dọc (Lòng)": "-",
                    "Ngang (Lòng)": "-"
                }
            
            if huong == "Dọc":
                be_data[loai_be]["Dọc (Bì)"] = f"{v['bi']:.3f}"
                be_data[loai_be]["Dọc (Lòng)"] = f"{v['long']:.3f}"
            else:
                be_data[loai_be]["Ngang (Bì)"] = f"{v['bi']:.3f}"
                be_data[loai_be]["Ngang (Lòng)"] = f"{v['long']:.3f}"
                
        df_be = pd.DataFrame(list(be_data.values()))
        
        st.dataframe(
            df_be, 
            hide_index=True, 
            use_container_width=True,
            height=400
        )

    st.markdown("#### 2. Thông số Kết Cấu Rãnh & Giả lập")
    
    col_sel1, col_sel2, col_sel3 = st.columns(3)
    
    with col_sel3:
        loai_kc_chon = st.selectbox("Chọn xem loại kết cấu (Drop-down để chọn):", options=["Asphalt", "Hè bê tông", "Đường bê tông", "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá", "Đất cấp 2", "Đất cấp 3", "Block_KC_B1"])
    
    noi_options = ["Bể - Bể", "Ganivo - Ganivo, Bể"]
    if loai_kc_chon == "Đất cấp 3":
        noi_options = ["Bể - Bể", "Ganivo - Ganivo, Bể"]
    elif loai_kc_chon == "Block_KC_B1":
        noi_options = ["Bể - Bể", "Ganivo - Ganivo, Bể"]
        
    with col_sel2:
        # Nếu đang là Đất cấp 2 thì mặc định chọn Ganivo
        idx_noi = 1 if len(noi_options) > 1 and loai_kc_chon == "Đất cấp 2" else 0
        noi_tu_chon = st.selectbox("Nối từ:", options=noi_options, index=idx_noi)

    ong_options = [1, 2, 3]
    if loai_kc_chon == "Đất cấp 2" and noi_tu_chon == "Ganivo - Ganivo, Bể":
        ong_options = [1, 2]
    elif loai_kc_chon == "Đất cấp 2" and noi_tu_chon == "Bể - Bể":
        ong_options = [2, 3]
    elif loai_kc_chon == "Đất cấp 3" and noi_tu_chon == "Ganivo - Ganivo, Bể":
        ong_options = [1]
    elif loai_kc_chon == "Đất cấp 3" and noi_tu_chon == "Bể - Bể":
        ong_options = [2]
    elif loai_kc_chon == "Block_KC_B1" and noi_tu_chon == "Ganivo - Ganivo, Bể":
        ong_options = [1, 2]
    elif loai_kc_chon == "Block_KC_B1" and noi_tu_chon == "Bể - Bể":
        ong_options = [2, 3]
    elif loai_kc_chon == "Asphalt" and noi_tu_chon == "Ganivo - Ganivo, Bể":
        ong_options = [1, 2]
    elif loai_kc_chon in ["Hè bê tông", "Đường bê tông", "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá"] and noi_tu_chon == "Ganivo - Ganivo, Bể":
        ong_options = [1, 2]
    elif loai_kc_chon in ["Hè bê tông", "Terrazzo, Đá xanh, Gạch nung, Gạch giả đá", "Asphalt"] and noi_tu_chon == "Bể - Bể":
        ong_options = [1, 2, 3, 4]
        
    with col_sel1:
        so_ong_chon = st.selectbox("Chọn số ống trong rãnh:", options=ong_options, index=0)

    selected_kc = f"{loai_kc_chon} {so_ong_chon} ống ({noi_tu_chon})"
    
    col_kc1, col_kc2 = st.columns([1, 1])
    
    with col_kc1:
        if selected_kc in st.session_state.db_ket_cau:
            v = st.session_state.db_ket_cau[selected_kc]
            t_fixed_layers = [float(l["h"]) for l in v.get("layers", []) if str(l["h"]).lower() != "auto" and str(l["h"]).strip() != ""]
            t_fixed = sum(t_fixed_layers)
            h_ong_min_val = 0.22 if ("3 ống" in selected_kc or "4 ống" in selected_kc) else 0.11
            h_cat_min_val = h_ong_min_val + 0.10 # Thêm 0.05 cát trên và 0.05 cát dưới
            h_min = t_fixed + h_cat_min_val
            
            formula_parts = [f"{h:g}" for h in t_fixed_layers] + ["0.05", f"{h_ong_min_val:g}", "0.05"]
            formula_str = " + ".join(formula_parts)
            
            st.markdown(f"**🔹 Tên kết cấu:** `{selected_kc}` &nbsp;&nbsp;👉 <span style='color:red; font-weight:bold;'>ĐỘ SÂU ĐÀO TỐI THIỂU: {h_min:.3f}</span><br><span style='color:red; font-weight:bold;'>(m)</span> <span style='color:red;'>(= {formula_str})</span> &nbsp;&nbsp;&nbsp;&nbsp; <span style='color:#a2a2a2; font-size: 0.9em; font-style: italic;'>* Mô phỏng độ sâu theo ống D110, tính toán báo cáo sẽ chia theo tiết diện ống thực tế</span>", unsafe_allow_html=True)
            
            with st.expander("Ghi đè thông số mặc định (Bấm để mở rộng)", expanded=False):
                new_w_top = st.number_input("Rộng miệng (W_top) (m):", value=float(v['W_top']), format="%.3f", key=f"wt_{selected_kc}")
                new_w_bot = st.number_input("Rộng đáy (W_bot) (m):", value=float(v['W_bot']), format="%.3f", key=f"wb_{selected_kc}")
                new_h_def = st.number_input("Tổng sâu (H) mặc định (m):", value=float(v.get('H_def', 0.91)), format="%.3f", key=f"hdef_{selected_kc}")
            
            st.session_state.db_ket_cau[selected_kc]["W_top"] = new_w_top
            st.session_state.db_ket_cau[selected_kc]["W_bot"] = new_w_bot
            st.session_state.db_ket_cau[selected_kc]["H_def"] = new_h_def
            
            st.markdown("**🔹 Cấu tạo các lớp từ trên xuống:**")
            st.caption("💡 Bạn có thể sửa tên, cao độ (h), ĐVT hoặc Thêm/Xóa dòng trực tiếp trên bảng này. Kết quả tính toán sẽ cập nhật theo bảng này.")
            
            df_layers = pd.DataFrame(v["layers"])
            # Convert explicitly to string to allow freely editing mixed float/string "Auto" types
            df_layers["h"] = df_layers["h"].apply(lambda x: "Auto" if str(x).lower() == "auto" else str(x))
            
            # Lấy danh sách tất cả tên lớp hiện có và thông số mặc định của chúng
            all_layer_names = set()
            layer_defaults = {}
            for kc_data in st.session_state.db_ket_cau.values():
                for lay in kc_data.get("layers", []):
                    name = lay.get("name")
                    if name is not None and str(name).strip() != "":
                        name_str = str(name).strip()
                        all_layer_names.add(name_str)
                        if name_str not in layer_defaults:
                            layer_defaults[name_str] = {"h": lay.get("h"), "type": lay.get("type")}
            
            key_editor = f"editor_{selected_kc}"
            edited_layers_df = st.data_editor(
                df_layers,
                column_config={
                    "name": st.column_config.SelectboxColumn("Tên Lớp (Mặt/Nền)", options=sorted(list(all_layer_names))),
                    "h": st.column_config.TextColumn("Dày (m)"),
                    "type": st.column_config.SelectboxColumn("ĐVT", options=["m2", "m3"])
                },
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key=key_editor
            )
            
            # Cập nhật ngược lại session state
            new_layers = []
            need_rerun = False
            for i, row in edited_layers_df.iterrows():
                current_name = row.get("name")
                if pd.isna(current_name) or current_name is None:
                    continue
                
                current_name = str(current_name).strip()
                h_val = row.get("h")
                type_val = row.get("type")
                
                original_name = None
                if i < len(df_layers):
                    orig_n = df_layers.iloc[i].get("name")
                    if not pd.isna(orig_n) and orig_n is not None:
                        original_name = str(orig_n).strip()
                
                # Cập nhật giá trị mặc định nếu người dùng vừa chọn/thay đổi tên lớp
                if current_name != original_name and current_name in layer_defaults:
                    def_h = layer_defaults[current_name]["h"]
                    h_val = "Auto" if str(def_h).lower() == "auto" else str(def_h)
                    type_val = layer_defaults[current_name]["type"]
                    need_rerun = True

                if str(h_val).strip().lower() != "auto":
                    try: h_val = float(h_val)
                    except: h_val = 0.0
                else:
                    h_val = "Auto"
                
                new_layers.append({
                    "name": current_name,
                    "h": h_val,
                    "type": type_val
                })
            
            # Đảm bảo "Cát đen đầm chặt" luôn nằm dưới cùng
            bottom_layer = None
            other_layers = []
            for lay in new_layers:
                if str(lay["name"]).lower() == "cát đen đầm chặt":
                    bottom_layer = lay
                else:
                    other_layers.append(lay)
                    
            if bottom_layer:
                new_layers = other_layers + [bottom_layer]
            else:
                new_layers = other_layers
            
            # Nếu thứ tự thực tế bị thay đổi (như lớp thêm mới nằm dưới Cát đen đang bị đẩy lên trên), thì cần rerun
            if len(new_layers) == len(df_layers):
                for i in range(len(new_layers)):
                    if new_layers[i]["name"] != df_layers.iloc[i].get("name"):
                        need_rerun = True
                        break
            elif len(new_layers) > len(df_layers):
                need_rerun = True
            
            st.session_state.db_ket_cau[selected_kc]["layers"] = new_layers
            if need_rerun:
                if key_editor in st.session_state:
                    del st.session_state[key_editor]
                st.rerun()
            st.info("Lớp cát phân rải ngậm ống sẽ được phần mềm tự động tính toán bù vào phần không gian dư kẹp giữa đáy rãnh, đường ống và lớp đáy móng đá phía trên.")


    with col_kc2:
        if selected_kc:
            disp_h = float(st.session_state.db_ket_cau[selected_kc].get('H_def', 0.91))
            st.info(f"� **Tổng sâu mô phỏng chuẩn:** {disp_h:.3f} (m) - *Lớp Cát (Auto) sẽ thay đổi để bù trừ khoảng trống*")
            
        svg_html = render_dynamic_svg(selected_kc)
        if svg_html:
            svg_clean = re.sub(r'>\s+<', '><', svg_html.replace('\n', ' ').replace('\r', ''))
            st.markdown(f'<div style="text-align:center; border:1px solid #444; border-radius:8px; padding:20px; background-color:#000;">{svg_clean}</div>', unsafe_allow_html=True)

# Shared methodology data
methodology_data_all = [
    ["Nhóm 0. Vật tư", "Ống nhựa D110, D61, D32, HDPE D85/65, D65/50, D40/30, D32/25", "Cung cấp ống nhựa các loại. Tính theo số liệu 'L đo' nhập vào (chính là chiều dài ống thực tế L đo).", "L đo × Số_lượng_ống"],
    ["Quy tắc chung", "Thông số Chiều rộng (Width)", "R_miệng; R_đáy: Chiều rộng tại miệng và đáy rãnh đào (toàn rãnh).\nR_miệng_lớp; R_đáy_lớp: Chiều rộng tại đỉnh và đáy của riêng lớp vật liệu đó.\n((R_miệng_lớp + R_đáy_lớp)/2): Chiều rộng trung bình của lớp vật liệu.", "Tra cứu tại Tab 2 cho từng loại kết cấu"],
    
    ["Nhóm 1. Phá dỡ nền tuyến", "Cắt mặt hè bê tông xi măng, Chiều sâu vết cắt <=5cm", "Cắt mép hè dọc theo Tuyến hoặc chu vi Bể ga", "Tuyến: L đo × 2 | Bể ga: 2 × (D_bì + R_bì)"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Cắt mặt đường bê tông Asphan chiều dày lớp cắt <= 7cm", "Cắt mép đường Asphalt dọc theo Tuyến hoặc chu vi Bể ga", "Tuyến: L đo × 2 | Bể ga: 2 × (D_bì + R_bì)"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Cắt mặt đường bê tông xi măng, Chiều sâu vết cắt <=7cm", "Cắt mép đường bê tông dọc theo Tuyến hoặc chu vi Bể ga", "Tuyến: L đo × 2 | Bể ga: 2 × (D_bì + R_bì)"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền hè các loại (Gạch giả đá,Terrazzo, đá xanh, hạ long, Ceramic)", "Phá lớp trang trí bề mặt vỉa hè", "Tuyến: R_miệng × L đo | Bể ga: D_bì × R_bì"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu mặt hè bê tông xi măng bằng máy đục phá bê tông", "Phá dỡ lớp bê tông mặt hè / lớp đệm BT vỉa hè", "((R_miệng + R_đáy) / 2) × Dày_BT × L đo"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu mặt đường bê tông xi măng bằng máy đục phá bê tông", "Phá dỡ lớp bê tông mặt đường", "((R_miệng + R_đáy) / 2) × Dày_BT × L đo"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu mặt đường bê tông Asphalt", "Phá dỡ lớp bê tông nhựa hiện trạng", "Tuyến: R_miệng × 0.12 × L đo | Bể ga: D_bì × R_bì × 0.12"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ kết cấu bê tông bê tông lót nền 10cm dưới kết cấu lớp gạch, đá", "Phá lớp bê tông lót sàn vỉa hè cho gạch, đá", "Tuyến: R_miệng × 0.10 × L đo | Bể ga: S_bì × 0.10"],
    ["Nhóm 1. Phá dỡ nền tuyến", "Phá dỡ nền hè gạch Block bằng thủ công", "Phá lớp gạch Block mặt hè (chỉ kết cấu Block)", "R_miệng × L đo"],

    ["Nhóm 2. Thi công nền tuyến", "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp II", "Đào đất cấp 2 cho rãnh hoặc bể ga sâu <= 1m. Riêng kết cấu gạch, đá (TE, ĐX, GN, GBT_DA) H_đào = Sâu_đo - 0.03", "Tuyến: ((R_miệng + R_đáy) / 2) × H_đào × L đo | Bể ga: D_bì × R_bì × H_đào"],
    ["Nhóm 2. Thi công nền tuyến", "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp III", "Đào đất cấp 3 cho rãnh hoặc bể ga sâu <= 1m", "Tuyến: ((R_miệng + R_đáy) / 2) × H_đào × L đo | Bể ga: D_bì × R_bì × H_đào"],
    ["Nhóm 2. Thi công nền tuyến", "Đào đất rãnh cáp, hố ga, hố trồng cột. Chiều rộng rãnh đào <=3m, sâu <=2m. Đất cấp III", "Đào đất cấp 3 cho rãnh hoặc bể ga sâu > 1m", "Tuyến: ((R_miệng + R_đáy) / 2) × H_đào × L đo | Bể ga: D_bì × R_bì × H_đào"],
    ["Nhóm 2. Thi công nền tuyến", "Lắp ống dẫn cáp, loại ống xoắn HDPE F65/50. Số ống tổ hợp <=3", "Nhân công lắp đặt tổ hợp ống HDPE D65/50.", "(L đo × Số_lượng_ống) / 100"],
    ["Nhóm 2. Thi công nền tuyến", "Lắp ống dẫn cáp, loại ống PVC F <= 114 mm, nong một đầu . Số ống tổ hợp <= 3", "Nhân công lắp đặt tổ hợp ống D110.", "(L đo × Số_lượng_ống) / 100"],
    ["Nhóm 2. Thi công nền tuyến", "Lắp ống dẫn cáp, loại ống PVC F <= 60 mm, nong một đầu . Số ống tổ hợp <= 3", "Nhân công lắp đặt tổ hợp ống D61.", "(L đo × Số_lượng_ống) / 100"],
    ["Nhóm 2. Thi công nền tuyến", "Phân rải và đầm nén cát tuyến ống dẫn cáp thông tin. Đầm bằng thủ công", "Lớp lót bảo vệ ống rãnh cáp", "(V_lấp_đầy - V_ống)"],
    ["Nhóm 2. Thi công nền tuyến", "Lấp đất và đầm rãnh cáp đào qua hè, đường, độ chặt yêu cầu K=0,95", "Đất đắp hoàn trả rãnh cáp", "((R_miệng_lớp + R_đáy_lớp) / 2) × H_đất × L đo"],
    
    ["Nhóm 3. Thi công bể ga", "Đắp đất xung quanh thành bể, xung quanh tủ POP…, độ chặt yêu cầu K=0,95", "Đắp đất khe hở thành bể ga", "(S_bì - S_thân) × H_đắp"],
    ["Nhóm 3. Thi công bể ga", "Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp trên hè), loại bể cáp 2 đan vuông / 1 đan dọc", "Khung sắt cho bể xây gạch", "1 bể"],
    ["Nhóm 3. Thi công bể ga", "Gia công khung bể cho bể xây gạch, xây đá (khung bể cáp dưới đường), loại bể cáp 2 đan vuông / 1 đan dọc", "Khung sắt cho bể dưới đường", "1 bể"],
    ["Nhóm 3. Thi công bể ga", "Gia công chân khung bể cáp cho loại bể cáp 2 đan vuông / 1 đan dọc", "Bộ chân khung bể", "1 bể"],
    ["Nhóm 3. Thi công bể ga", "Sản xuất nắp đan bể xây gạch hoặc đá chẻ, trên hè 1200x500x70", "Đúc đan nắp bể trên hè", "Ký_tự_đầu × Số_bể"],
    ["Nhóm 3. Thi công bể ga", "Sản xuất nắp đan bể xây gạch hoặc đá chẻ, dưới đường 1200x500x90", "Đúc đan nắp bể dưới đường", "Ký_tự_đầu × Số_bể"],
    ["Nhóm 3. Thi công bể ga", "Xây bể cáp thông tin (bể 2 nắp đan vuông / 1 đan dọc) bằng gạch chỉ trên hè/dưới đường 1 tầng ống", "Xây bể gạch chỉ", "1 bể"],
    ["Nhóm 3. Thi công bể ga", "Lắp đặt cấu kiện đối với bể 1 tầng cống. Loại nắp đan 1 đan dọc / 2 đan vuông", "Lắp nắp đan bể", "1 bể"],
    ["Nhóm 3. Thi công bể ga", "Xây lắp Ganivo nắp bê tông 400x400 trên hè / dưới đường", "Trọn gói hố ga Ganivo", "1 ganivo"],
    ["Nhóm 3. Thi công bể ga", "Xây lắp Ganivo nắp bê tông,loại 600 x 600 (trên hè sâu 820 )", "Trọn gói hố ga Ganivo 600", "1 ganivo"],
    
    ["Nhóm 4. Hoàn trả", "Móng cát vàng gia cố 8% xi măng", "Lớp móng cát vỉa hè cho gạch nung", "R_miệng × 0.10 × L đo"],
    ["Nhóm 4. Hoàn trả", "Đắp cát nền hè bằng thủ công dầy 5cm", "Lớp đệm cát vỉa hè", "R_miệng × 0.05 × L đo"],
    ["Nhóm 4. Hoàn trả", "Lát via hè gạch block tự chèn dầy 6cm ( gạch tận dụng 80%, 20% mua mới )", "Lát gạch Block vỉa hè", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Bê tông nền, đá 2x4, vữa BT M150", "Lót móng hè / Bê tông bảo vệ ống", "R_miệng × Dày_lớp × L đo"],
    ["Nhóm 4. Hoàn trả", "Lát gạch terrazzo, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )", "Lát gạch Terrazzo", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Bê tông nền, đá 2x4, vữa BT M150 dầy 8cm", "Bê tông lót dưới gạch hè", "R_miệng × 0.08 × L đo"],
    ["Nhóm 4. Hoàn trả", "Lát gạch BTXM giả đá conic, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )", "Lát gạch giả đá", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Lát hè đá xanh, lớp vữa XM mác 100# (gạch tận dụng 30%, 70% mua mới )", "Lát đá xanh hè", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Thi công móng cấp phối đá dăm lớp trên dầy 18cm", "Đá dăm hoàn trả lớp trên", "R_miệng × Dày_lớp × L đo"],
    ["Nhóm 4. Hoàn trả", "Rải cấp phối đá dăm mặt đường đá nhựa cũ. Lớp dưới 25cm", "Đá dăm hoàn trả lớp dưới", "R_miệng × Dày_lớp × L đo"],
    ["Nhóm 4. Hoàn trả", "Tưới nhũ tương nhựa lót tiêu chuẩn 1,0kg/m2 thi công - nhũ tương nhựa - tưới thủ công", "Tưới nhũ tương nhựa lót", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Rải thảm mặt đường BT nhựa hạt thô, chiều dày mặt đường đã lèn ép 7 cm", "Trải nhựa bề mặt Asphalt hạt thô", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Tưới nhựa lót hoặc nhựa dính bám mặt đường, tiêu chuẩn 0,5kg/m2 - nhũ tương nhựa - tưới thủ công", "Tưới dính bám", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Làm mặt đường BT nhựa hạt mịn, chiều dày mặt đường đã lèn ép 5cm", "Trải nhựa bề mặt Asphalt hạt mịn", "R_miệng × L đo"],
    ["Nhóm 4. Hoàn trả", "Bê tông mặt đường, chiều dày mặt đường <=25cm, đá 2x4, vữa BT M250", "Bề mặt bê tông đường", "R_miệng × Dày_lớp × L đo"],
    ["Nhóm 4. Hoàn trả", "Hoàn trả mặt hè bê tông dầy 10cm, đá 2x4, mác 250", "Hoàn trả BT mặt hè", "R_miệng × 0.10 × L đo"],
    ["Nhóm 5. Vận chuyển đất thừa", "Vận chuyển đất bằng ôtô tự đổ 5 tấn trong phạm vi <= 1000m, đất cấp II / cấp III", "Vận chuyển đất thừa ra bãi thải", "Đào + Phá - Lấp (Gạch/Đá, Block: Đào - Lấp)"],
]

# Function to add methodology sheet to an ExcelWriter object
def add_methodology_sheet(writer):
    df_meth = pd.DataFrame(methodology_data_all, columns=["Nhóm", "Hạng mục báo cáo", "Diễn giải chi tiết", "Công thức tính toán"])
    df_meth.to_excel(writer, sheet_name='Huong_Dan_Phuong_Phap_Tinh', index=False)
    
    workbook = writer.book
    worksheet = writer.sheets['Huong_Dan_Phuong_Phap_Tinh']
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
    cell_format = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})
    
    for col_num, value in enumerate(df_meth.columns.values):
        worksheet.write(0, col_num, value, header_format)
    
    worksheet.set_column('A:A', 25, cell_format)
    worksheet.set_column('B:B', 50, cell_format)
    worksheet.set_column('C:C', 50, cell_format)
    worksheet.set_column('D:D', 40, cell_format)
    worksheet.set_column('E:Z', None, None, {'hidden': True}) # Dọn dẹp các cột thừa
    worksheet.freeze_panes(1, 0) # Cố định dòng tiêu đề

# Placeholder for tab1's Excel export logic.
# In your actual tab1 export function (e.g., generate_main_report_excel),
# you would call add_methodology_sheet(writer) like this:
#
# def generate_main_report_excel():
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         # ... existing sheets for tab1 ...
#         # Example: df_results.to_excel(writer, sheet_name='Ket_Qua_Tinh_Toan', index=False)
#
#         add_methodology_sheet(writer) # Add the methodology sheet
#
#     return output.getvalue()


with tab3:
    # --- NÚT XUẤT HƯỚNG DẪN (TAB 3) ---
    def get_methodology_excel():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            add_methodology_sheet(writer) # Use the shared function
            
        return output.getvalue()

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        st.markdown("### 📒 Hướng dẫn phương pháp tính toán")
    with col_btn2:
        st.download_button(
            "📥 Xuất HD (Excel)",
            get_methodology_excel(),
            "Huong_Dan_HaTangNgam.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    st.divider()
    with st.expander(" Nhóm 0. Vật tư", expanded=True):
        st.markdown("""
        | Hạng mục thực tế trên báo cáo | Diễn giải chi tiết | Công thức tính toán |
        | :--- | :--- | :--- |
        | - **Ống nhựa D110, D61, D32 <br>HDPE D85/65, D65/50, D40/30, D32/25** | Cung cấp ống nhựa. Tính theo số liệu 'L đo' nhập vào (chính là chiều dài ống thực tế L đo). | `L đo × Số_lượng_ống` |
        | 📏 **Thông số Chiều rộng (R)** | **R_miệng / R_đáy**: Miệng và đáy toàn rãnh.<br>**R_miệng_lớp / R_đáy_lớp**: Đỉnh và đáy của riêng lớp đó (từ dưới lên). | **Đào đất:** Dùng `(R_miệng + R_đáy)/2`<br>**Hoàn trả:** Các lớp Móng, Đệm, Bê tông dùng `R_miệng` |
        """, unsafe_allow_html=True)

    with st.expander("🔨 Nhóm 1. Phá dỡ nền tuyến", expanded=False):
        st.markdown("""
        | Hạng mục thực tế trên báo cáo | Diễn giải chi tiết | Công thức tính toán |
        | :--- | :--- | :--- |
        | - **Cắt mặt hè bê tông xi măng, Chiều sâu vết cắt <=5cm** | Cắt mép hè BTXM (chỉ kết cấu HBT) | **Tuyến:** `L đo × 2`<br>**Bể ga:** `2 × (D_bì + R_bì)` |
        | - **Cắt mặt đường bê tông Asphan chiều dày lớp cắt <= 7cm** | Cắt mép đường Asphalt (kết cấu AL) | **Tuyến:** `L đo × 2`<br>**Bể ga:** `2 × (D_bì + R_bì)` |
        | - **Cắt mặt đường bê tông xi măng, Chiều sâu vết cắt <=7cm** | Cắt mép đường BTXM (kết cấu ĐBT) | **Tuyến:** `L đo × 2`<br>**Bể ga:** `2 × (D_bì + R_bì)` |
        | - **Phá dỡ kết cấu mặt đường bê tông Asphalt** | Phá dỡ lớp BT nhựa hiện trạng (kết cấu AL) | **Tuyến:** `L đo × (R_miệng × 0.12)`<br>**Bể ga:** `D_bì × R_bì × 0.12` |
        | - **Phá dỡ kết cấu mặt đường bê tông xi măng bằng máy đục phá bê tông** | Phá dỡ BT đường (kết cấu ĐBT) | **Tuyến:** `L đo × (R_miệng × 0.20)`<br>**Bể ga:** `D_bì × R_bì × 0.20` |
        | - **Phá dỡ kết cấu mặt hè bê tông xi măng bằng máy đục phá bê tông** | Phá dỡ BT vỉa hè (kết cấu HBT) | **Tuyến:** `L đo × (R_miệng × 0.10)`<br>**Bể ga:** `D_bì × R_bì × 0.10` |
        | - **Phá dỡ nền gạch giả đá coric** | Phá lớp gạch giả đá Coric vỉa hè | **Tuyến:** `L đo × R_miệng`<br>**Bể ga:** `D_bì × R_bì` |
        | - **Phá dỡ nền đá xanh** | Phá lớp đá xanh vỉa hè | **Tuyến:** `L đo × R_miệng`<br>**Bể ga:** `D_bì × R_bì` |
        | - **Phá dỡ nền gạch terrazzo** | Phá lớp gạch Terrazzo vỉa hè | **Tuyến:** `L đo × R_miệng`<br>**Bể ga:** `D_bì × R_bì` |
        | - **Phá dỡ nền gạch nung** | Phá lớp gạch nung vỉa hè | **Tuyến:** `L đo × R_miệng`<br>**Bể ga:** `D_bì × R_bì` |
        | - **Phá dỡ kết cấu bê tông bê tông lót nền 10cm dưới kết cấu lớp gạch, đá** | Phá lớp BT lót sàn vỉa hè cho gạch, đá | **Tuyến:** `L đo × R_miệng × 0.10`<br>**Bể ga:** `D_bì × R_bì × 0.10` |
        | - **Phá dỡ nền hè gạch Block bằng thủ công** | Phá lớp gạch Block mặt hè (chỉ kết cấu Block) | `L đo × R_miệng` |
        """, unsafe_allow_html=True)

    with st.expander("🏗️ Nhóm 2. Thi công nền tuyến", expanded=False):
        st.markdown("""
        | Hạng mục thực tế trên báo cáo | Diễn giải chi tiết | Công thức tính toán |
        | :--- | :--- | :--- |
        | - **Đào đất rãnh cáp, hố ga, hố trồng cột. <br>Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp II** | Đào đất cấp 2 sâu <= 1m. Riêng gạch/đá (TE, ĐX, GN, GBT_DA) H_đào = Sâu_đo - 0.03 | **Tuyến:** `L đo × ((R_miệng + R_đáy) / 2) × H_đào`<br>**Bể ga:** `1 × (D_bì × R_bì × H_đào)` |
        | - **Đào đất rãnh cáp, hố ga, hố trồng cột. <br>Chiều rộng rãnh đào <=3m, sâu <=1m. Đất cấp III** | Đào đất cấp 3 cho rãnh hoặc bể ga sâu <= 1m | **Tuyến:** `L đo × ((R_miệng + R_đáy) / 2) × H_đào`<br>**Bể ga:** `1 × (D_bì × R_bì × H_đào)` |
        | - **Đào đất rãnh cáp, hố ga, hố trồng cột. <br>Chiều rộng rãnh đào <=3m, sâu <=2m. Đất cấp III** | Đào đất cấp 3 cho rãnh hoặc bể ga sâu > 1m | **Tuyến:** `L đo × ((R_miệng + R_đáy) / 2) × H_đào`<br>**Bể ga:** `1 × (D_bì × R_bì × H_đào)` |
        | - **Lắp ống dẫn cáp, loại ống xoắn HDPE F65/50. <br>Số ống tổ hợp <=3** | Nhân công lắp đặt tổ hợp ống HDPE D65/50 | `L đo × Số_ống / 100` |
        | - **Lắp ống dẫn cáp, loại ống PVC F <= 114 mm, nong một đầu . <br>Số ống tổ hợp <= 3** | Nhân công lắp đặt tổ hợp ống PVC D110 | `L đo × Số_ống / 100` |
        | - **Lắp ống dẫn cáp, loại ống PVC F <= 60 mm, nong một đầu . <br>Số ống tổ hợp <= 3** | Nhân công lắp đặt tổ hợp ống PVC D61 | `L đo × Số_ống / 100` |
        | - **Phân rải và đầm nén cát tuyến ống dẫn cáp thông tin. Đầm bằng thủ công** | Lớp lót bảo vệ ống rãnh cáp | `L đo × (V_mặt_cắt - V_ống)` |
        | - **Lấp đất và đầm rãnh cáp đào qua hè, đường, độ chặt yêu cầu K=0,95** | Đất đắp hoàn trả rãnh cáp | `L đo × ((R_miệng_lớp + R_đáy_lớp) / 2) × H_đất` |
        """, unsafe_allow_html=True)

    with st.expander("🕳️ Nhóm 3. Thi công bể ga", expanded=False):
        st.markdown("""
        | Hạng mục thực tế trên báo cáo | Diễn giải chi tiết | Công thức tính toán |
        | :--- | :--- | :--- |
        | - **Đắp đất xung quanh thành bể, xung quanh tủ POP…, <br>độ chặt yêu cầu K=0,95** | Đắp đất khe hở thành bể ga | `(S_bì - S_thân) × H_đắp` |
        | - **Gia công khung bể cho bể xây gạch, xây đá <br>(khung bể cáp trên hè/dưới đường), <br>loại bể cáp 2 đan vuông / 1 đan dọc** | Khung sắt cho bể xây gạch | 1 bể |
        | - **Gia công chân khung bể cáp <br>cho loại bể cáp 2 đan vuông / 1 đan dọc** | Bộ chân khung cho bể | 1 bể |
        | - **Sản xuất nắp đan bể xây gạch hoặc đá chẻ, <br>trên hè 1200x500x70 / dưới đường 1200x500x90** | Đúc đan nắp bể | `Ký_tự_đầu × Số_bể` |
        | - **Xây bể cáp thông tin bằng gạch chỉ <br>trên hè/dưới đường 1 tầng ống** | Xây bể gạch chỉ | 1 bể |
        | - **Lắp đặt cấu kiện đối với bể 1 tầng cống. <br>Loại nắp đan 1 đan dọc / 2 đan vuông** | Lắp nắp đan bể | 1 bể |
        | - **Xây lắp Ganivo nắp bê tông 400x400 <br>trên hè / dưới đường** | Trọn gói hố ga | 1 ganivo |
        | - **Xây lắp Ganivo nắp bê tông,loại 600 x 600 <br>(trên hè sâu 820 )** | Trọn gói hố ga 600 | 1 ganivo |
        """, unsafe_allow_html=True)

    with st.expander("🧱 Nhóm 4. Hoàn trả", expanded=False):
        st.markdown("""
        | Hạng mục thực tế trên báo cáo | Diễn giải chi tiết | Công thức tính toán |
        | :--- | :--- | :--- |
        | - **Thi công móng cấp phối đá dăm lớp trên dầy 18cm** | Đá dăm hoàn trả lớp trên | `L đo × R_miệng × Dày_lớp` |
        | - **Rải cấp phối đá dăm mặt đường đá nhựa cũ. Lớp dưới 25cm** | Đá dăm hoàn trả lớp dưới | `L đo × R_miệng × Dày_lớp` |
        | - **Bê tông nền, đá 2x4, vữa BT M150** | Lớp móng bê tông chung (đường) | `L đo × R_miệng × Dày_lớp` |
        | - **Bê tông nền, đá 2x4, vữa BT M150 dầy 8cm** | BT lót nền dưới gạch hè (TE, ĐX, GN, GBT_DA) | `L đo × R_miệng × 0.08` |
        | - **Bê tông mặt đường, chiều dày mặt đường <=25cm, đá 2x4, vữa BT M250** | Bề mặt bê tông đường (kết cấu ĐBT) | `L đo × R_miệng × Dày_lớp` |
        | - **Hoàn trả mặt hè bê tông dầy 10cm, đá 2x4, mác 250** | Hoàn trả BT mặt hè (kết cấu HBT) | `L đo × R_miệng × 0.10` |
        | - **Tưới nhựa lót hoặc nhựa dính bám mặt đường, <br>tiêu chuẩn 0,5kg/m2 - nhũ tương nhựa - tưới thủ công** | Tưới dính bám (BT nhựa hạt trung) | `L đo × R_miệng` |
        | - **Rải thảm mặt đường BT nhựa hạt thô, <br>chiều dày mặt đường đã lèn ép 7 cm** | Trải nhựa bề mặt hạt thô | `L đo × R_miệng` |
        | - **Tưới nhũ tương nhựa lót tiêu chuẩn 1,0kg/m2 <br>thi công - nhũ tương nhựa - tưới thủ công** | Tưới nhũ tương nhựa lót (BT nhựa hạt mịn) | `L đo × R_miệng` |
        | - **Làm mặt đường BT nhựa hạt mịn, <br>chiều dày mặt đường đã lèn ép 5cm** | Trải nhựa bề mặt hạt mịn | `L đo × R_miệng` |
        | - **Móng cát vàng gia cố 8% xi măng** | Lớp đệm cho gạch nung | `L đo × R_miệng × 0.10` |
        | - **Đắp cát nền hè bằng thủ công dầy 5cm** | Lớp đệm cho gạch vỉa hè | `L đo × R_miệng × 0.05` |
        | - **Lát via hè gạch block tự chèn dầy 6cm <br>( gạch tận dụng 80%, 20% mua mới )** | Lát gạch Block vỉa hè | `L đo × R_miệng` |
        | - **Lát gạch terrazzo, lớp vữa XM mác 100# <br>(gạch tận dụng 30%, 70% mua mới )** | Lát gạch Terrazzo | `L đo × R_miệng` |
        | - **Lát gạch BTXM giả đá conic, lớp vữa XM mác 100# <br>(gạch tận dụng 30%, 70% mua mới )** | Lát gạch giả đá (kết cấu GBT_DA) | `L đo × R_miệng` |
        | - **Lát hè đá xanh, lớp vữa XM mác 100# <br>(gạch tận dụng 30%, 70% mua mới )** | Lát đá xanh (kết cấu ĐX) | `L đo × R_miệng` |
        | - **Hoàn trả mặt hè gạch nung** | Lát gạch nung (kết cấu GN) | `L đo × R_miệng` |
        """, unsafe_allow_html=True)

    with st.expander("🚚 Nhóm 5. Vận chuyển đất thừa", expanded=False):
        st.markdown("""
        | Hạng mục thực tế trên báo cáo | Diễn giải chi tiết | Công thức tính toán |
        | :--- | :--- | :--- |
        | - **Vận chuyển đất bằng ôtô tự đổ 5 tấn <br>trong phạm vi <= 1000m, đất cấp II / cấp III** | Vận chuyển đất thừa | **Chung:** `Đào + Phá - Lấp`<br>**Gạch/Đá, Block:** `Đào - Lấp` |
        """, unsafe_allow_html=True)

    st.markdown("""
    > [!NOTE]
    > **Logic Co Giãn Cấu Trúc:** Khi $H_{thực} < H_{thiết\_kế}$, phần mềm sẽ ưu tiên giữa nguyên chiều dày các lớp bề mặt (Nhựa, Bê tông, Đá dăm) và sẽ bóp nhỏ chiều dày lớp **Đất đắp** hoặc **Cát đệm** từ dưới lên để đảm bảo rãnh khớp với thực tế.
    """)

with tab4:
    st.markdown("### 📖 Hướng dẫn sử dụng & Tính năng sản phẩm")
    try:
        # Sử dụng đường dẫn tuyệt đối hoặc tương đối an toàn
        hdsd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HDSD_Tinh_Nang_San_Pham.md")
        with open(hdsd_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)
    except Exception as e:
        st.info("Chưa có file hướng dẫn hoặc lỗi đọc file.")

