# import socket

# def connect_to_server():
#     server_ip = "127.0.0.1"
#     server_port = 5000
    
#     # Tạo socket
#     client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     client_socket.connect((server_ip, server_port))
    
#     message = "Hello Server!"
#     client_socket.send(message.encode())
    
#     data = client_socket.recv(1024)
#     print("Server response:", data.decode())
    
#     client_socket.close()

# if __name__ == "__main__":
#     connect_to_server()


import socket
import json

SERVER_HOST = '127.0.0.1'  # hoặc IP của server nếu khác máy
SERVER_PORT = 9999

def send_data():
    # Dữ liệu mẫu gửi lên server
    data = {
        "token": "abc123",  # token để xác thực
        "payload": {
            "device_id": "sensor_01",
            "temperature": 25.4,
            "humidity": 60,
            "status": "ok"
        }
    }

    try:
        # Tạo kết nối TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            # Gửi dữ liệu dưới dạng JSON
            s.sendall(json.dumps(data).encode('utf-8'))

            # Nhận phản hồi từ server
            response = s.recv(1024)
            print("[Server]:", response.decode())

    except Exception as e:
        print("Lỗi khi kết nối tới server:", e)


if __name__ == "__main__":
    send_data()

