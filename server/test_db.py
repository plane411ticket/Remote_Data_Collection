import mysql.connector

try:
    conn = mysql.connector.connect(
        host="mainline.proxy.rlwy.net",
        port=23149,
        user="root",
        password="uPilDXhcwYNlYwvcUACLfFgSOJwiGCaW",
        database="railway"
    )
    if conn.is_connected():
        print("✅ Kết nối thành công với database!")
    conn.close()
except mysql.connector.Error as err:
    print("❌ Kết nối thất bại:", err)
