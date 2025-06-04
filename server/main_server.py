import socket
import ssl
import json
import threading
import logging
from database import Database
import ssl
import sys
import io
import queue
import os
import argparse



HOST = '0.0.0.0'
parser = argparse.ArgumentParser(description="Run multi-port server")
parser.add_argument('--port', type=int, default=9999, help='Port to listen on')
args = parser.parse_args()
PORT = args.port


# PORT = int(os.getenv("SERVER_PORT", 9999))
# PORT = 9999
BUFFER_SIZE = 4096

db = Database()

# HOST = '0.0.0.0'
# parser = argparse.ArgumentParser()
# parser.add_argument('--port', type=int, default=9999)
# args = parser.parse_args()
# PORT = args.port
# BUFFER_SIZE = 4096

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# Lớp ghi vào sql
class Handler_MySQL(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record)
            address = get_local_ip()
            db.insert_server_log(address, log_entry) 
        except Exception as e:
            print(f"Lỗi khi ghi log vào MySQL: {e}")
# Cấu hình ghi log
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s',
    handlers=[
        logging.FileHandler("server.log", encoding='utf-8'),   # Ghi ra file
        logging.StreamHandler(sys.stdout)             # In ra terminal
        
    ]
)

mysql_handler = Handler_MySQL()
mysql_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s'))
logging.getLogger().addHandler(mysql_handler)

# Hàng đợi để truyền kết nối cho thread giao diện admin
client_queue = queue.Queue()

# Danh sách các lệnh quản trị viên
ADMIN_COMMANDS = [
    {"command": "shutdown"},
    {"command": "restart"},
    {"command": "screenshot"},
    {"command": "end_process"},
    {"command": "alert"},
    {"command": "notify"},
    {"suggestion": "RAM nên nâng cấp"},
    {"suggestion": "Máy bạn không phù hợp chạy song song Dual Boot"}
]

# Lấy địa chỉ IP và port cục bộ
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip, port = s.getsockname()
    except Exception:
        ip = "127.0.0.1", 9001
    finally:
        s.close()
    return f"{ip}"



def send_response(conn, status, message, code=None):
    response = {
        "status": status,
        "message": message,
    }
    if code is not None:
        response["code"] = code
    conn.sendall((json.dumps(response) + "\n").encode('utf-8'))


def send_command(mac_address, type, command, suggestion=None):
    message = {"mac_address": mac_address, "alert_type": type, "alert_level": command}
    
    if suggestion:
        message["alert_message"] = suggestion
    try:
        db.insert_alerts(mac_address, type, command, suggestion)
        logging.info(f"Đã gửi lệnh tới client: {message}")
    except Exception as e:
        logging.error(f"Lỗi khi gửi lệnh: {e}")


def handle_client(conn, addr):
    client_ip = addr[0]
    logging.info(f"Kết nối từ {client_ip}")
    # static_saved = False
    client_queue.put(conn)  # Đẩy kết nối vào hàng đợi để giao diện sử dụng
    try:
        buffer = ""
        while True:
            data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                logging.warning(f"{client_ip} - Không nhận được dữ liệu")
                # send_response(conn, "error", "No data received", code=400)
                return

            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    json_data = json.loads(line)
                except json.JSONDecodeError:
                    logging.warning(f"{client_ip} - JSON không hợp lệ: {line}")
                    send_response(conn, "error", "Invalid JSON format", code=401)
                    continue


                payload = json_data.get('payload')
                if not payload:
                    logging.warning(f"{client_ip} - Thiếu payload")
                    send_response(conn, "error", "Missing payload", code=404)
                    continue
                
                mac_address = payload.get("MAC", {}).get("mac_address", "unknown")
                data_type = payload.get("type", "unknown")
                check = True

                if data_type == "static":
                    if not db.has_static_data(mac_address):  
                            print("insert_static_computer_info",payload )
                            db.insert_static_computer_info(mac_address, payload)
                            logging.info(f"{client_ip} - Lưu dữ liệu static thành công")
                            send_response(conn, "success", "Data saved successfully", code=200)

                            memory_total = payload.get("memory", {}).get("total", 0)
                            if memory_total <= 8 * 1024**3:  # <= 8GB
                                send_command(mac_address, type="memory", command="alert", suggestion="Máy bạn không phù hợp chạy song song Dual Boot")

                            swap_total = payload.get("swap", {}).get("total", 0)  
                            if swap_total <= 4 * 1024**3:  # <= 4GB
                                send_command(mac_address, type="swap", command="alert", suggestion="Dung lượng swap quá thấp! Cần nâng cấp swap partition")
                    else:
                        logging.info(f"{mac_address} - Static data đã có, bỏ qua gói static")
                        send_response(conn, "ignore", "Static already exists", code=208)

                elif data_type == "dynamic":
                    print("insert_dynamic_computer_info",payload )
                    db.insert_dynamic_computer_info(mac_address, payload)
                    logging.info(f"{client_ip} - Lưu dynamic data thành công")
                    if check:
                        send_response(conn, "success", "Data saved successfully", code=200)
                        check = False
                

                    # Kiểm tra hiệu năng vượt ngưỡng
                    cpu = payload.get("cpu", {}).get("usage_percent", 0)
                       
                    if cpu > 90:
                        send_command(mac_address, type="cpu", command="shutdown", suggestion="Cảnh báo: CPU đang quá tải, Cần shutdown máy!")
                    elif cpu > 80:
                        send_command(mac_address, type="cpu", suggestion="Cảnh báo: CPU đang quá tải, Cần restart máy!")
                    elif cpu > 70:
                        send_command(mac_address, type="cpu", command="alert", suggestion="Cảnh báo: CPU sắp quá tải! Cần đóng ứng dụng không cần thiết!")
                    elif cpu > 50:
                        send_command(mac_address, type="cpu", command="notify", suggestion="Cảnh báo: CPU đang vượt ngưỡng sử dụng!")

                    ram_percent = payload.get("memory", {}).get("percent", 0)
                    
                    if ram_percent > 90:
                        send_command(mac_address, type="ram", command="shutdown", suggestion="Cảnh báo: RAM đang quá tải, Cần shutdown máy!")
                    elif ram_percent > 80:
                        send_command(mac_address, type="ram", command="restart", suggestion="Cảnh báo: RAM đang quá tải, Cần restart máy!")
                    elif ram_percent > 70:
                        send_command(mac_address, type="ram", command="alert", suggestion="Cảnh báo: RAM sắp quá tải! Cần đóng ứng dụng không cần thiết!")
                    elif ram_percent > 50:
                        send_command(mac_address, type="ram", command="notify", suggestion="Cảnh báo: RAM đang vượt ngưỡng sử dụng!")
                    
                    
                    swap_percent = payload.get("swap", {}).get("percent", 0)

                    
                    if swap_percent > 90:
                        send_command(mac_address, type="swap", command="shutdown", suggestion="Cảnh báo: SWAP đang quá tải, Cần shutdown máy!")
                    elif swap_percent > 80:
                        send_command(mac_address, type="swap", command="restart", suggestion="Cảnh báo: SWAP đang quá tải, Cần restart máy!")
                    elif swap_percent > 70:
                        send_command(mac_address, type="swap", command="alert", suggestion="Cảnh báo: SWAP sắp quá tải! Cần đóng ứng dụng không cần thiết!")
                    elif swap_percent > 50:
                        send_command(mac_address, type="swap", command="notify", suggestion="Cảnh báo: SWAP đang vượt ngưỡng sử dụng!")
                    
                else:
                    logging.warning(f"{mac_address} - Gói tin không hợp lệ: thiếu type")
                    send_response(conn, "error", "Invalid data type", code=400)


                

    except Exception as e:
        logging.exception(f"{client_ip} - Lỗi xử lý")
        send_response(conn, "error", "Server error", code=501)

    finally:
        conn.close()
        logging.info(f"{client_ip} - Đã đóng kết nối")



# def admin_interface():
#     while True:
#         conn = client_queue.get()  # Lấy kết nối client đầu tiên
#         print("\n[ADMIN] Có client kết nối. Bạn muốn gửi gì?")
#         for idx, cmd in enumerate(ADMIN_COMMANDS):
#             label = cmd.get("command") or cmd.get("suggestion")
#             print(f"[{idx}] {label}")

#         try:
#             choice = int(input("Nhập số để gửi lệnh: "))
#             selected = ADMIN_COMMANDS[choice]
#             send_command(conn, selected.get("command"), selected.get("suggestion"))
#         except (ValueError, IndexError):
#             logging.warning("Lựa chọn không hợp lệ hoặc lỗi nhập.")



def start_server():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        ip, port = server_socket.getsockname()
        print(f"Server đang lắng nghe tại địa chỉ IP: {ip}, cổng: {port}")
        print(f"[+] Server đang lắng nghe tại {HOST}:{PORT}...")

        # server_socket.settimeout(10)
        while True:
            # try:
            conn, addr = server_socket.accept()
            # except socket.timeout:
            #     continue  
            # except KeyboardInterrupt:
            #     print("Server đã tắt.")
            #     break
    
            try:
                ssl_conn = context.wrap_socket(conn, server_side=True)
            except ssl.SSLError as e:
                logging.error(f"Lỗi SSL: {e}")
                conn.close()
                continue
            
            # Tạo thread riêng cho mỗi client
            client_thread = threading.Thread(
                target=handle_client, 
                args=(ssl_conn, addr),
                name=f"Client-{addr[0]}:{addr[1]}",
                daemon=True
            )

            client_thread.start()

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("Server đã tắt.")
