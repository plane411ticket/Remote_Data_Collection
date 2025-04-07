import socket

def connect_to_server():
    server_ip = "127.0.0.1"
    server_port = 5000
    
    # Tạo socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    
    message = "Hello Server!"
    client_socket.send(message.encode())
    
    data = client_socket.recv(1024)
    print("Server response:", data.decode())
    
    client_socket.close()

if __name__ == "__main__":
    connect_to_server()
