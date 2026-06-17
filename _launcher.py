"""
Silent Launcher for Streamlit App
- Khởi chạy Streamlit ẩn (không hiện console)
- Tự mở trình duyệt
- Giám sát kết nối: khi đóng tab/trình duyệt → tự tắt Streamlit
"""
import subprocess
import sys
import os
import time
import webbrowser
import socket

CREATE_NO_WINDOW = 0x08000000
PORT = 8510
IDLE_CHECKS_BEFORE_SHUTDOWN = 10  # Tăng lên ~30s không có kết nối mới tắt
CHECK_INTERVAL = 3                 # Giây giữa mỗi lần kiểm tra
GRACE_PERIOD = 15                  # Tăng lên 15s chờ trình duyệt kết nối lần đầu
LOG_FILE = "_launcher.log"         # File ghi log để debug

def log(message):
    """Ghi log kèm timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")


def install_requirements():
    """Cài đặt thư viện cần thiết (chỉ chạy nếu thiếu thư viện)."""
    try:
        # Kiểm tra nhanh xem các thư viện chính đã có chưa
        import streamlit
        import pandas
        import openpyxl
        import xlsxwriter
        return
    except ImportError:
        pass

    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    if os.path.exists(req_file):
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', req_file,
             '--quiet', '--disable-pip-version-check'],
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )


def wait_for_server(port, timeout=30):
    """Chờ server sẵn sàng trên port."""
    for _ in range(timeout):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(('localhost', port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def count_established_connections(port):
    """Đếm số kết nối ESTABLISHED đến port (WebSocket từ trình duyệt)."""
    try:
        result = subprocess.run(
            ['netstat', '-an'],
            capture_output=True, text=True,
            creationflags=CREATE_NO_WINDOW
        )
        count = 0
        for line in result.stdout.splitlines():
            # Tìm dòng có port và trạng thái ESTABLISHED
            # Format: TCP  127.0.0.1:8501  127.0.0.1:XXXXX  ESTABLISHED
            parts = line.split()
            if len(parts) >= 4:
                local_addr = parts[1]
                state = parts[3]
                if local_addr.endswith(f':{port}') and state == 'ESTABLISHED':
                    count += 1
        return count
    except Exception:
        return -1  # Lỗi → không tắt app


def is_port_in_use(port):
    """Kiểm tra xem port có đang bị chiếm dụng hay không."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def find_available_port(start_port, max_tries=10):
    """Tìm port trống bắt đầu từ start_port."""
    for port in range(start_port, start_port + max_tries):
        if not is_port_in_use(port):
            return port
    return start_port  # Trả về mặc định nếu không tìm thấy


def update_url_shortcut(port):
    """Cập nhật port trong file Open_App.url."""
    url_file = "Open_App.url"
    if os.path.exists(url_file):
        try:
            with open(url_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            with open(url_file, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("URL="):
                        f.write(f"URL=http://localhost:{port}/\n")
                    else:
                        f.write(line)
            log(f"Updated {url_file} to port {port}.")
        except Exception as e:
            log(f"Warning: Could not update shortcut: {e}")


def main():
    # Chuyển về thư mục chứa script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Xóa log cũ
    if os.path.exists(LOG_FILE):
        try: os.remove(LOG_FILE)
        except: pass
    log("Launcher started.")

    # 1. Cài thư viện
    install_requirements()

    # 2. Tìm port trống
    port = find_available_port(PORT)
    if port != PORT:
        log(f"Port {PORT} is in use. Switching to {port}.")
        update_url_shortcut(port) # Cập nhật shortcut nếu đổi port
    else:
        log(f"Using port {port}.")
        # Đảm bảo shortcut luôn khớp với port mặc định nếu dùng port mặc định
        update_url_shortcut(port)

    # 3. Khởi chạy Streamlit (ẩn hoàn toàn)
    log("Starting Streamlit...")
    proc = subprocess.Popen(
        [sys.executable, '-m', 'streamlit', 'run', 'streamlit_app.py',
         '--server.headless=true', f'--server.port={port}'],
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # 4. Chờ server sẵn sàng
    if not wait_for_server(port):
        log(f"ERROR: Server not ready on port {port}. Terminating.")
        proc.terminate()
        return

    # 5. Mở trình duyệt
    log(f"Server ready on port {port}. Opening browser.")
    webbrowser.open(f'http://localhost:{port}')

    # 6. Chờ trình duyệt thiết lập kết nối WebSocket
    time.sleep(GRACE_PERIOD)

    # 7. Giám sát kết nối - tự tắt khi đóng trình duyệt
    idle_count = 0
    while proc.poll() is None:
        time.sleep(CHECK_INTERVAL)

        connections = count_established_connections(port)
        # log(f"Monitoring: {connections} connections established.") # Uncomment for verbose logging

        if connections == 0:
            idle_count += 1
            if idle_count >= IDLE_CHECKS_BEFORE_SHUTDOWN:
                log(f"IDLE LIMIT REACHED ({idle_count} checks). Terminating app.")
                proc.terminate()
                break
        elif connections > 0:
            if idle_count > 0:
                log(f"Connection resumed. Resetting idle count.")
            idle_count = 0
        # connections == -1 (lỗi) → bỏ qua, không tăng idle

    # 7. Dọn dẹp
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


if __name__ == '__main__':
    main()
