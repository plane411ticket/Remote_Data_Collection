import socket
import ssl
import uuid
import time
import json
import psutil
import cpuinfo
import os

CONFIG = {
    "server": {
        "ip": "127.0.0.1",
        "port": 9500
    },
    "timing": {
        "dynamic_info_interval": 5,
        "shutdown_delay": 10,
        "restart_delay": 10,
        "cpu_interval": 1
    },
    "network": {
        "buffer_size": 4096
    }
}


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
                "cpu_usage": psutil.cpu_percent(interval=CONFIG["timing"]["cpu_interval"]),
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
        data = conn.recv(CONFIG["network"]["buffer_size"]).decode("utf-8")
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
            error_message = response.get("message", "Unknown error")
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[ERROR] Có lỗi xảy ra: {error_message}\')"')
        # elif response.get("status") == "success":
        #     os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[INFO] Server chấp nhận client info.\')"')
        elif response.get("alert_level") == "shutdown":
            shutdown_delay = CONFIG["timing"]["shutdown_delay"]
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[SHUTDOWN] Máy sẽ tắt sau {shutdown_delay} giây.\')"')
            time.sleep(CONFIG["timing"]["shutdown_delay"])
            os.system("shutdown /s /t 0")
        elif response.get("alert_level") == "restart":
            restart_delay = CONFIG["timing"]["restart_delay"]
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[RESTART] Máy sẽ khởi động lại sau {restart_delay} giây.\')"')
            time.sleep(CONFIG["timing"]["restart_delay"])
            os.system("shutdown /r /t 0") 
        elif response.get("alert_level") == "alert":
            suggestion_message = response.get("alert_message", "No suggestion")
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[ALERT] {suggestion_message}\')"')
        elif response.get("alert_level") == "notify":
            suggestion_message = response.get("alert_message", "No notification")
            os.system(f'powershell -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(\'[NOTIFY] {suggestion_message}\')"')
    except Exception as e:
        print(f"[LỖI] không nhận được phản hồi hợp lệ từ server: {e}")

def connect_to_server():
    server_ip = CONFIG["server"]["ip"]
    port = CONFIG["server"]["port"]
    
    
    while True:
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                with context.wrap_socket(sock, server_hostname=server_ip) as client_socket:
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
                            time.sleep(CONFIG["timing"]["dynamic_info_interval"])
                    
        except Exception as e:
            print(f"[LỖI] Mất kết nối hoặc lỗi xảy ra: {e}")
            print("[~] Đợi 5 giây trước khi thử lại kết nối...")
            time.sleep(5)
if __name__ == "__main__":
    connect_to_server()