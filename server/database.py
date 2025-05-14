import mysql.connector


class Database:
    def __init__(self):
        # self.mydb = mysql.connector.connect(
        #     host="mainline.proxy.rlwy.net",
        #     port=23149,
        #     user="root",
        #     password="uPilDXhcwYNlYwvcUACLfFgSOJwiGCaW",
        #     database = 'railway'
        # )
        self.mydb = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="",
        )

        self.mycursor = self.mydb.cursor()

        self.mycursor.execute("CREATE DATABASE IF NOT EXISTS remote_collection")
        self.mydb.database = 'remote_collection'

    def drop_all_tables(self):
        self.mycursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        self.mycursor.execute("SHOW TABLES")
        tables = self.mycursor.fetchall()

        for table in tables:
            print(f"🗑️ Đang xóa bảng: {table[0]}")
            self.mycursor.execute(f"DROP TABLE IF EXISTS `{table[0]}`")

        self.mycursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        self.mydb.commit()

    def create_table_user(self):
        self.mycursor.execute("""
            CREATE TABLE IF NOT EXISTS users_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                client_id INT NOT NULL,
                username VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL
            )""")
        self.mydb.commit()
    
    def create_table_client_computer_info(self):
        self.mycursor.execute("""
            CREATE TABLE IF NOT EXISTS computer_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                client_id INT NOT NULL,
                cpu_brand VARCHAR(255),
                cpu_arch VARCHAR(50),
                cpu_bits INT,
                cpu_logical INT,
                cpu_physical INT,
                cpu_usage FLOAT,
                memory_total BIGINT,
                memory_available BIGINT,
                memory_used BIGINT,
                memory_percent FLOAT,
                swap_total BIGINT,
                swap_used BIGINT,
                swap_percent FLOAT,
                disk_used BIGINT,
                disk_free BIGINT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        self.mydb.commit()
        # FOREIGN KEY (client_id) REFERENCES users_info(id)
    
    def insert_users_info(self, username, password):
        self.mycursor.execute("""
            INSERT INTO users_info (username, password) VALUES (%s, %s)""", (username, password))
        
        self.mydb.commit()
        
    # def insert_computer_info(self, client_id, cpu_usage, memory_usage, disk_usage, network_usage):
    #     self.mycursor.execute("""
    #         INSERT INTO computer_info (client_id, cpu_usage, memory_usage, disk_usage, network_usage) 
    #         VALUES (%s, %s, %s, %s, %s)""", (client_id, cpu_usage, memory_usage, disk_usage, network_usage))
    #     self.mydb.commit()

    def insert_computer_info(self, client_id, payload):
        try:
            cpu = payload["cpu"]
            memory = payload["memory"]
            swap = payload["swap"]
            disk = payload["disk"]

            self.mycursor.execute("""
                INSERT INTO computer_info (
                    client_id, cpu_brand, cpu_arch, cpu_bits, cpu_logical, cpu_physical, cpu_usage,
                    memory_total, memory_available, memory_used, memory_percent,
                    swap_total, swap_used, swap_percent,
                    disk_used, disk_free
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    client_id,
                    cpu["brand"], cpu["arch"], cpu["bits"], cpu["count_logical"], cpu["count_physical"], cpu["usage_percent"],
                    memory["total"], memory["available"], memory["used"], memory["percent"],
                    swap["total"], swap["used"], swap["percent"],
                    disk["disk_used"], disk["disk_free"]
                )
            )
            self.mydb.commit()
            return True
        except mysql.connector.Error as err:
            return False  

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
    
    db.close()

