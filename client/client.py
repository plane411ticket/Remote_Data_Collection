import socket
import cpuinfo
import psutil
import json
import ssl
import uuid
import time

def static_system_info():
    cpu_info = cpuinfo.get_cpu_info()

    disk_partitions = psutil.disk_partitions()

    for part in disk_partitions:
        usage = psutil.disk_usage(part.mountpoint)

    mac = uuid.getnode()

    data = {
        "payload": 
        {
            "cpu": 
            {
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
            "MAC":
            {
                "mac_address": mac,            
            },
            "dynamic":
            {
                "dynamic": False,
            }
        },
    }
    return data


def dynamic_system_info():  
    disk_partitions = psutil.disk_partitions()
    disk_total_used = 0
    disk_total_free = 0

    for part in disk_partitions:
        usage = psutil.disk_usage(part.mountpoint)
        disk_total_used += usage.used
        disk_total_free += usage.free

    mac = uuid.getnode()

    data = {
        "payload": 
        {
            "cpu": 
            {
                "usage_percent": psutil.cpu_percent(interval=1),
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
            "disk":{
                "disk_used": disk_total_used,
                "disk_free": disk_total_free,
            },
            "MAC":
            {
                "mac_address": mac,            
            },
            "dynamic":
            {
                "dynamic": True,
            }
        },
    }
    return data

def connect_to_server():
    # Địa chỉ IP và cổng của server
    server_ip = "127.0.0.1" # Địa chỉ IP của Laptop đang chạy
    port = 9999

    # Tạo SSL context
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket = context.wrap_socket(client_socket)
    try:
        # Tạo socket TCP/IP
        client_socket.connect((server_ip, port))
        print(f"Đã kết nối tới server {server_ip}:{port}")

        # Gửi lần đầu tiên
        cpu_info = static_system_info()
        payload = json.dumps(cpu_info)
        client_socket.sendall((payload + '\n').encode('utf-8'))
        print("Đã gửi thông tin lần đầu tới server!")

        while True:
            # Thu thập thông tin CPU
            cpu_info = dynamic_system_info()

            # Gửi dữ liệu dạng JSON
            payload = json.dumps(cpu_info)
            client_socket.sendall((payload + '\n').encode('utf-8'))
            print("Đã gửi thông tin CPU tới server!")
            time.sleep(5)

    except Exception as error:
        print("Lỗi:", error)

    finally:
        client_socket.close()

if __name__ == "__main__":
    connect_to_server()
