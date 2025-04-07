import socket
import threading
from database import Database

# Hàm xử lý kết nối từ client
db = Database()
db.create_table()
db.insert_data(cpu=23.5, ram=60.2)
db.close()


def handle_client(client_socket):
    request = client_socket.recv(1024)
    print("Received:", request.decode())
    
    # Lấy dữ liệu từ database (ví dụ)
    db = Database()
    db_data = db.get_data()
    
    # Gửi phản hồi cho client
    client_socket.send(f"Server received your message. Database data: {db_data}".encode())
    client_socket.close()

# Mở server để lắng nghe client
def start_server():
    server_ip = "0.0.0.0"
    server_port = 5000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, server_port))
    server_socket.listen(5)
    print(f"Server listening on {server_ip}:{server_port}")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Accepted connection from {addr}")
        
        # Xử lý client trong thread riêng
        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.start()

if __name__ == "__main__":
    start_server()
