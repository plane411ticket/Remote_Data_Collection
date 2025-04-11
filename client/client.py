import socket
import cpuinfo
import psutil
import json

def collect_system_info():
    cpu_info = cpuinfo.get_cpu_info()

    disk_partitions = psutil.disk_partitions()
    disk_total_used = 0
    disk_total_free = 0
    disk_info = []

    for part in disk_partitions:
        usage = psutil.disk_usage(part.mountpoint)
        disk_total_used += usage.used
        disk_total_free += usage.free

    data = {
        "cpu": {
            "brand": cpu_info.get("brand_raw"),
            "arch": cpu_info.get("arch"),
            "bits": cpu_info.get("bits"),
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "usage_percent": psutil.cpu_percent(interval=1),
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent,
        },
        "swap": {
            "total": psutil.swap_memory().total,
            "used": psutil.swap_memory().used,
            "percent": psutil.swap_memory().percent,
        },
        "disk": [
            {
                "disk_used": disk_total_used,
                "disk_free": disk_total_free,
            }
        ],
    }
    return data


def connect_to_server():
    # Địa chỉ IP và cổng của server
    server_ip = "172.17.19.239" # Địa chỉ IP của Laptop đang chạy
    port = 9999

    try:
        # Tạo socket TCP/IP
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server_ip, port))
        print(f"Đã kết nối tới server {server_ip}:{port}")

        # Thu thập thông tin CPU
        cpu_info = collect_system_info()

        # Gửi dữ liệu dạng JSON
        payload = json.dumps(cpu_info)
        client_socket.sendall(payload.encode('utf-8'))
        print("Đã gửi thông tin CPU tới server!")

    except Exception as error:
        print("Lỗi:", error)

    finally:
        client_socket.close()

if __name__ == "__main__":
    connect_to_server()
