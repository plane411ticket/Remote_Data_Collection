import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",
        database="remote_collection"
    )
    if conn.is_connected():
        print("✅ Kết nối thành công với database!")
    conn.close()
except mysql.connector.Error as err:
    print("❌ Kết nối thất bại:", err)
