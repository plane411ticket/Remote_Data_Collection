import socket
import threading
import ssl
from collections import deque, defaultdict
import time

# Hằng số cấu hình
import os
CERT_FILE = os.path.join(os.path.dirname(__file__), "cert.pem")
KEY_FILE = os.path.join(os.path.dirname(__file__), "key.pem")
LOAD_BALANCER_HOST = "0.0.0.0"
LOAD_BALANCER_PORT = 9500
MAX_CONNECTIONS = 10
BUFFER_SIZE = 4096

# Danh sách server (host, port, trọng số)
SERVERS = [
    ("127.0.0.1", 9001, 3),
    ("127.0.0.1", 9002, 1),
    # ("127.0.0.1", 9003, 2),
]

MAX_CONNECTION_SERVER = {
    ("127.0.0.1", 9001): 3,
    ("127.0.0.1", 9002): 1,
    ("127.0.0.1", 9003): 2,
}
current_connections = defaultdict(int)

lock = threading.Lock()
server_queue = deque()

for host, port, weight in SERVERS:
    for _ in range(weight):
        server_queue.append((host, port))

def get_next_server():
    """Lấy server tiếp theo theo thuật toán Round Robin có trọng số"""
    with lock:
        for _ in range(len(server_queue)):
           server = server_queue.popleft()
           if current_connections[server] < MAX_CONNECTION_SERVER[server]:
               current_connections[server] += 1
               server_queue.append(server)
               return server
           server_queue.append(server)
        raise Exception("Không có server nào sẵn sàng hoặc đã đạt giới hạn kết nối tối đa")               

def health_check(host, port, timeout=2):
        server_addr = (host, port)
        context_to_server = ssl.create_default_context()
        context_to_server.check_hostname = False
        context_to_server.verify_mode = ssl.CERT_NONE
        try:
            raw_sock = socket.create_connection(server_addr,timeout = timeout)
            server_socket = context_to_server.wrap_socket(raw_sock, server_hostname=server_addr[0])
            server_socket.do_handshake()
            server_socket.close()
            return True
        except:
            return False

def check_recover_servers():
    rebuild_queue = deque()
       
    for host, port, weight in SERVERS:
        if health_check(host, port):
            for _ in range (weight):
                rebuild_queue.append((host, port))
    with lock:
        global server_queue
        server_queue.clear()
        server_queue.extend(rebuild_queue)

def health_monitor(timer_interval=5):
    while True:
        check_recover_servers()
        time.sleep(timer_interval)

def forward_data(src_sock, dst_sock):
    """Chuyển tiếp dữ liệu giữa client và server"""
    try:  
        while True:
            data = src_sock.recv(BUFFER_SIZE)
            if not data:
                break
            dst_sock.sendall(data)
    except Exception:
        pass
    finally:
        src_sock.close()
        dst_sock.close()

def handle_client(client_socket):
    server_addr = None
    connected = False
    try:
        server_addr = get_next_server()
        print(f"[INFO] Chuyển tiếp đến server {server_addr}")
        try:
            # Tạo context SSL phía client (vì load balancer đóng vai trò client khi kết nối tới server)
            context_to_server = ssl.create_default_context()
            context_to_server.check_hostname = False
            context_to_server.verify_mode = ssl.CERT_NONE

            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.connect(server_addr)
            server_socket = context_to_server.wrap_socket(raw_sock, server_hostname=server_addr[0])

            connected = True

            # Tạo 2 thread chuyển tiếp dữ liệu 2 chiều
            threading.Thread(target=forward_data, args=(client_socket, server_socket), daemon=True).start()
            threading.Thread(target=forward_data, args=(server_socket, client_socket), daemon=True).start()
        except Exception as e:
            print(f"[LỖI] Không thể kết nối tới server {server_addr}: {e}")
            client_socket.close()
    except Exception as e:
        print(f"[LỖI] Xử lý client gặp lỗi: {e}")
        client_socket.close()
    finally:
        if server_addr and connected:
            with lock:
                current_connections[server_addr] -= 1
                print(f"[DEBUG] current_connections: {dict(current_connections)}")


def start_load_balancer():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    balancer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    balancer_socket.bind((LOAD_BALANCER_HOST, LOAD_BALANCER_PORT))
    balancer_socket.listen(MAX_CONNECTIONS)
    print(f"[+] Load Balancer đang chạy tại cổng {LOAD_BALANCER_PORT}...")

    while True:
        try:
            client_sock, addr = balancer_socket.accept()
            client_ssl = context.wrap_socket(client_sock, server_side=True)
            print(f"[+] Kết nối TLS từ {addr}")
            threading.Thread(target=handle_client, args=(client_ssl,), daemon=True).start()
        except ssl.SSLError as e:
            print(f"[SSL ERROR] {e}")
            client_sock.close()
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    threading.Thread(target=health_monitor, daemon=True).start()
    start_load_balancer()
