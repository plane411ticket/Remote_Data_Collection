import socket
import json
from server import auth, database

HOST = '0.0.0.0'   # lắng nghe tất cả IP
PORT = 9999        # port server

BUFFER_SIZE = 4096  # kích thước bộ đệm

def handle_client(conn, addr):
    print(f"[+] Kết nối từ {addr}")

    try:
        # Bước 1: Nhận dữ liệu JSON
        data = conn.recv(BUFFER_SIZE).decode('utf-8')
        if not data:
            print("[-] Không nhận được dữ liệu")
            return

        try:
            json_data = json.loads(data)
        except json.JSONDecodeError:
            print("[-] Dữ liệu không phải JSON hợp lệ")
            conn.sendall(b'Invalid JSON')
            return

        # Bước 2: Xác thực client (nếu có trường 'token')
        token = json_data.get('token')
        if not auth.verify_token(token):  # auth.verify_token là giả định
            conn.sendall(b'Authentication failed')
            return

        # Bước 3: Phân tích & xử lý dữ liệu
        payload = json_data.get('payload')
        if not payload:
            conn.sendall(b'Missing payload')
            return

        # Bước 4: Lưu vào database
        success = database.save_data(payload)  # database.save_data là giả định
        if success:
            conn.sendall(b'ACK')  # Gửi xác nhận
        else:
            conn.sendall(b'Database error')

    except Exception as e:
        print(f"[-] Lỗi: {e}")
        conn.sendall(b'Server error')
    finally:
        conn.close()

def send_response(conn, status, message, code=None):
    response = {
        "status": status,
        "message": message,
    }
    if code is not None:
        response["code"] = code
    conn.sendall(json.dumps(response).encode('utf-8'))




def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[+] Server đang lắng nghe tại {HOST}:{PORT}...")

        while True:
            conn, addr = server_socket.accept()
            handle_client(conn, addr)


if __name__ == "__main__":
    start_server()
