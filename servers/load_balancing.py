import socket
import threading
import ssl
from collections import deque

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

# Tạo hàng đợi theo trọng số
server_queue = deque()
for host, port, weight in SERVERS:
    for _ in range(weight):
        server_queue.append((host, port))

def get_next_server():
    """Lấy server tiếp theo theo thuật toán Round Robin có trọng số"""
    server = server_queue.popleft()
    server_queue.append(server)
    return server

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
    server_addr = get_next_server()
    print(f"[INFO] Chuyển tiếp đến server {server_addr}")
    try:
        # Tạo context SSL phía client (vì load balancer đóng vai trò client khi kết nối tới server)
        context_to_server = ssl.create_default_context()
        context_to_server.check_hostname = False
        context_to_server.verify_mode = ssl.CERT_NONE

        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket = context_to_server.wrap_socket(raw_sock)
        server_socket.connect(server_addr)

        # Tạo 2 thread chuyển tiếp dữ liệu 2 chiều
        threading.Thread(target=forward_data, args=(client_socket, server_socket), daemon=True).start()
        threading.Thread(target=forward_data, args=(server_socket, client_socket), daemon=True).start()
    except Exception as e:
        print(f"[LỖI] Không thể kết nối tới server {server_addr}: {e}")
        client_socket.close()

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
    start_load_balancer()
