import socket
import threading
from collections import deque

# Server: (host, port, weight)
SERVERS = [
    ('127.0.0.1', 9001, 3),
    ('127.0.0.1', 9002, 1),
    ('127.0.1', 9003, 2),
]

# Tạo hàng đợi theo trọng số
server_queue = deque()
for host, port, weight in SERVERS:
    for _ in range(weight):
        server_queue.append((host, port))

def get_next_server():
    server = server_queue.popleft()
    server_queue.append(server)
    return server

def handle_client(client_socket):
    server_addr = get_next_server()
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect(server_addr)

        data = client_socket.recv(4096)
        if data:
            server_socket.sendall(data)
            response = server_socket.recv(4096)
            client_socket.sendall(response)

        server_socket.close()
    except Exception as e:
        print("Lỗi:", e)
    finally:
        client_socket.close()

def start_load_balancer():
    balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    balancer_socket.bind(('0.0.0.0', 9500))
    balancer_socket.listen(5)
    print("Load Balancer đang chạy tại cổng 9500...")

    while True:
        client_sock, addr = balancer_socket.accept()
        threading.Thread(target=handle_client, args=(client_sock,)).start()

if __name__ == "__main__":
    start_load_balancer()
