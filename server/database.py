import mysql.connector


class Database:
    def __init__(self):
        self.mydb = mysql.connector.connect(
            host="mainline.proxy.rlwy.net",
            port=23149,
            user="root",
            password="uPilDXhcwYNlYwvcUACLfFgSOJwiGCaW",
            database = 'railway'
        )
        self.mycursor = self.mydb.cursor()

    def create_table_user(self):
        self.mycursor.execute("""
            CREATE TABLE IF NOT EXISTS users_info(
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL)""")
        self.mydb.commit()
    
    def create_table_client_computer_info(self):
        self.mycursor.execute("""
           CREATE TABLE IF NOT EXISTS computer_info(
                id INT AUTO_INCREMENT  PRIMARY KEY,
                client_id INT NOT NULL,
                cpu_usage FLOAT,
                memory_usage FLOAT,
                disk_usage FLOAT,
                network_usage FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES users_info(id))""")
        self.mydb.commit()
    
    def insert_users_info(self, username, password):
        self.mycursor.execute("""
            INSERT INTO users_info (username, password) VALUES (%s, %s)""", (username, password))
        
        self.mydb.commit()
        
    def insert_computer_info(self, client_id, cpu_usage, memory_usage, disk_usage, network_usage):
        self.mycursor.execute("""
            INSERT INTO computer_info (client_id, cpu_usage, memory_usage, disk_usage, network_usage) 
            VALUES (%s, %s, %s, %s, %s)""", (client_id, cpu_usage, memory_usage, disk_usage, network_usage))
        self.mydb.commit()

    def get_all_users(self):
        self.mycursor.execute("SELECT * FROM users_info")
        for row in self.mycursor.fetchall():
            print(row)
            
    def get_all_computers_info(self):
        self.mycursor.execute("SELECT * FROM computer_info")
        for row in self.mycursor.fetchall():
            print(row)

    def delete_all_users(self):
        self.mycursor.execute("DELETE FROM users_info")
        self.mydb.commit()

    def delete_all_computer_info(self):
        self.mycursor.execute("DELETE FROM computer_info")
        self.mydb.commit()

    def close(self):
        self.mydb.close()
        self.mycursor.close()

    

if __name__ == "__main__":
    db = Database()
    db.create_table_user()
    db.create_table_client_computer_info()
    print("✅ Đã tạo bảng!")

    db.insert_users_info("testuser", "testpass")
    print("✅ Đã thêm user!")

    db.insert_computer_info(client_id=1, cpu_usage=55.5, memory_usage=70.2, disk_usage=80.1, network_usage=200.5)
    print("✅ Đã thêm thông tin máy!")

    db.get_all_users()
    db.get_all_computers_info()

    db.delete_all_computer_info()
    db.delete_all_users()

    print("✅ Đã xóa tất cả người dùng và thông tin máy!")

    db.get_all_computers_info()
    db.get_all_users()

    db.close()

