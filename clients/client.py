import socket
import ssl
import uuid
import time
import json
import psutil
import cpuinfo
import os


def static_system_info():
    cpu_info = cpuinfo.get_cpu_info()
    mac = uuid.getnode()

    return {
        "payload": {
            "cpu": {
                "brand": cpu_info.get("brand_raw"),
                "arch": cpu_info.get("arch"),
                "bits": cpu_info.get("bits"),
                "count_logical": psutil.cpu_count(logical=True),
                "count_physical": psutil.cpu_count(logical=False),
            },
            "memory": {
                "total": psutil.virtual_memory().total,
            },
            "swap": {
                "total": psutil.swap_memory().total,
            },
            "MAC": {
                "mac_address": mac,
            },
            "type": "static"
        }
    }


def dynamic_system_info():
    disk_used = 0
    disk_free = 0
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disk_used += usage.used
            disk_free += usage.free
        except PermissionError:
            continue

    mac = uuid.getnode()

    return {
        "payload": {
            "cpu": {
                "cpu_usage": psutil.cpu_percent(interval=1),
            },
            "memory": {
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent,
            },
            "swap": {
                "used": psutil.swap_memory().used,
                "percent": psutil.swap_memory().percent,
            },
            "disk": {
                "disk_used": disk_used,
                "disk_free": disk_free,
            },
            "MAC": {
                "mac_address": mac,
            },
            "type": "dynamic"
        }
    }


def receive_response(conn):
    buffer = ""
    while True:
        data = conn.recv(4096).decode("utf-8")
        buffer += data
        print(buffer)
        if "\n" in buffer:
            line, _ = buffer.split("\n", 1)
            return json.loads(line)

def listen_to_server(client_socket):
    try:
        response = receive_response(client_socket)
        if response.get("status") == "ignore":
            os.system('powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[INFO] Server đã có static info, bỏ qua.\')"')
        elif response.get("status") == "error":
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[ERROR] Có lỗi xảy ra: {response.get('message')}\')"')
        # elif response.get("status") == "success":
        #     os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[INFO] Server chấp nhận client info.\')"')
        elif response.get("command") == "shutdown":
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[SHUTDOWN] Máy sẽ tắt sau 5 giây.\')"')
            time.sleep(10)
            os.system("shutdown /s /t 0")
        elif response.get("command") == "restart":
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[RESTART] Máy sẽ khởi động lại sau 5 giây.\')"')
            time.sleep(10)
            os.system("shutdown /r /t 0") 
        elif response.get("command") == "alert":
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[ALERT] {response.get('suggestion')}\')"')
        elif response.get("command") == "notify":
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[NOTIFY] {response.get('suggestion')}\')"')
    except Exception as e:
        print(f"[LỖI] không nhận được phản hồi hợp lệ từ server: {e}")

def connect_to_server():
    server_ip = "127.0.0.1"
    port = 9500

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with context.wrap_socket(sock, server_hostname=server_ip) as client_socket:
            try:
                client_socket.connect((server_ip, port))
                print(f"[+] Đã kết nối TLS tới server {server_ip}:{port}")

                # Gửi thông tin hệ thống tĩnh (static)
                static_info = static_system_info()
                client_socket.sendall((json.dumps(static_info) + '\n').encode('utf-8'))
                listen_to_server(client_socket)
                
                # Gửi định kỳ thông tin động (dynamic)
                while True:
                    dyn_info = dynamic_system_info()
                    client_socket.sendall((json.dumps(dyn_info) + '\n').encode('utf-8'))
                    listen_to_server(client_socket)
                    print("[>] Đã gửi dynamic info.")
                    time.sleep(5)

            except Exception as e:
                print(f"[LỖI] Không thể kết nối/gửi dữ liệu: {e}")
if __name__ == "__main__":
    connect_to_server()