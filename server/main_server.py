import socket
import ssl
import json
import threading
import logging
from database import Database
import auth
import sys
import io


HOST = '0.0.0.0'
PORT = 9999
BUFFER_SIZE = 4096

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# Cấu hình ghi log
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),   # Ghi ra file
        logging.StreamHandler(sys.stdout)             # In ra terminal
    ]
)

def send_response(conn, status, message, code=None):
    response = {
        "status": status,
        "message": message,
    }
    if code is not None:
        response["code"] = code
    conn.sendall(json.dumps(response).encode('utf-8'))

def handle_client(conn, addr):
    client_ip = addr[0]
    logging.info(f"Kết nối từ {client_ip}")

    try:
        data = conn.recv(BUFFER_SIZE).decode('utf-8')
        if not data:
            logging.warning(f"{client_ip} - Không nhận được dữ liệu")
            send_response(conn, "error", "No data received", code=400)
            return

        try:
            json_data = json.loads(data)
        except json.JSONDecodeError:
            logging.warning(f"{client_ip} - JSON không hợp lệ: {data}")
            send_response(conn, "error", "Invalid JSON format", code=401)
            return

        token = json_data.get('token')
        if not auth.verify_token(token):
            logging.warning(f"{client_ip} - Token không hợp lệ: {token}")
            send_response(conn, "auth_failed", "Invalid token", code=403)
            return

        payload = json_data.get('payload')
        client_id = json_data.get('client_id')
        if not payload:
            logging.warning(f"{client_ip} - Thiếu payload")
            send_response(conn, "error", "Missing payload", code=404)
            return

        db = Database()
        success = db.insert_computer_info(client_id, payload)
        if success:
            logging.info(f"{client_ip} - Lưu dữ liệu thành công")
            send_response(conn, "success", "Data saved successfully", code=200)
        else:
            logging.error(f"{client_ip} - Lỗi lưu vào database")
            send_response(conn, "error", "Failed to save data", code=500)

    except Exception as e:
        logging.exception(f"{client_ip} - Lỗi xử lý")
        send_response(conn, "error", "Server error", code=501)
    finally:
        conn.close()
        logging.info(f"{client_ip} - Đã đóng kết nối")

def start_server():
    # Cấu hình SSL
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='server.crt', keyfile='server.key')


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[+] Server đang lắng nghe tại {HOST}:{PORT}...")

        while True:
            conn, addr = server_socket.accept()

            # Wrap connection with SSL
            conn = context.wrap_socket(conn, server_side=True)
            
            # Tạo thread riêng cho mỗi client
            client_thread = threading.Thread(
                target=handle_client, 
                args=(conn, addr),
                name=f"Client-{addr[0]}:{addr[1]}"
            )

            client_thread.start()

if __name__ == "__main__":
    start_server()
