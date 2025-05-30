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
            password="1161944565K",
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
    
    def create_static_computer_info(self):
        self.mycursor.execute("""
            CREATE TABLE IF NOT EXISTS static_info (
                id INT AUTO_INCREMENT PRIMARY KEY,            
                mac_address BIGINT UNSIGNED UNIQUE,
                cpu_brand VARCHAR(255),
                cpu_arch VARCHAR(50),
                cpu_bits INT,
                cpu_logical INT,
                cpu_physical INT,
                memory_total BIGINT,
                swap_total BIGINT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        self.mydb.commit()
    
    # def create_static_info_history (self):
    #     self.mycursor.execute("""
    #         CREATE TABLE IF NOT EXISTS static_info_history (
    #             id INT AUTO_INCREMENT PRIMARY KEY,
    #             mac_address BIGINT UNSIGNED,          
    #             cpu_brand VARCHAR(255),
    #             cpu_arch VARCHAR(50),
    #             cpu_bits INT,
    #             cpu_logical INT,
    #             cpu_physical INT,
    #             memory_total BIGINT,
    #             swap_total BIGINT,
    #             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #         )""")
    #     self.mydb.commit()


    def create_dynamic_computer_info(self):
        self.mycursor.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mac_address BIGINT UNSIGNED,
                cpu_usage FLOAT,
                memory_available BIGINT,
                memory_used BIGINT,
                memory_percent FLOAT,
                swap_used BIGINT,
                swap_percent FLOAT,
                disk_used BIGINT,
                disk_free BIGINT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mac_address) REFERENCES static_info(mac_address)
            )""")
        self.mydb.commit()
    
    def insert_users_info(self, username, password):
        self.mycursor.execute("""
            INSERT INTO users_info (username, password) VALUES (%s, %s)""", (username, password))
        
        self.mydb.commit()

    def insert_static_computer_info(self, mac_address, payload):
        try:
            cpu = payload["cpu"]
            memory = payload["memory"]
            swap = payload["swap"]

            self.mycursor.execute("""
                INSERT INTO static_info (
                    mac_address, cpu_brand, cpu_arch, cpu_bits, cpu_logical, cpu_physical, 
                    memory_total, swap_total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    mac_address,
                    cpu["brand"], cpu["arch"], cpu["bits"], cpu["count_logical"], cpu["count_physical"], memory["total"], swap["total"]
                )
            )
            self.mydb.commit()
            return True
        except mysql.connector.Error as err:
            return False  
        
    # def insert_static_info_history(self, mac_address, payload):
    #     try:
    #         cpu = payload["cpu"]
    #         memory = payload["memory"]
    #         swap = payload["swap"]

    #         self.mycursor.execute("""
    #             INSERT INTO static_info_history (
    #                 mac_address, cpu_brand, cpu_arch, cpu_bits, cpu_logical, cpu_physical, 
    #                 memory_total, swap_total
    #             ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    #             """, (
    #                 mac_address,
    #                 cpu["brand"], cpu["arch"], cpu["bits"], cpu["count_logical"], cpu["count_physical"], memory["total"], swap["total"]
    #             )
    #         )
    #         self.mydb.commit()
    #         return True
    #     except mysql.connector.Error as err:
    #         return False  
    
    def insert_dynamic_computer_info(self, mac_address, payload):
        try:
            cpu = payload["cpu"]
            memory = payload["memory"]
            swap = payload["swap"]
            disk = payload["disk"]

            self.mycursor.execute("""
                INSERT INTO dynamic_info (
                    mac_address, cpu_usage, memory_available, memory_used, memory_percent, swap_used, 
                    swap_percent, disk_used, disk_free
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    mac_address,
                    cpu["cpu_usage"], memory["available"], memory["used"], memory["percent"], swap["used"], 
                    swap["percent"], disk["disk_used"], disk["disk_free"]
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
            
    def get_all_static_info(self):
        self.mycursor.execute("SELECT * FROM static_info")
        for row in self.mycursor.fetchall():
            print(row)
    
    def get_all_dynamic_info(self):
        self.mycursor.execute("SELECT * FROM dynamic_info")
        for row in self.mycursor.fetchall():
            print(row)

    def delete_all_users(self):
        self.mycursor.execute("DELETE FROM users_info")
        self.mydb.commit()

    def delete_all_static_info(self):
        self.mycursor.execute("DELETE FROM static_info")
        self.mydb.commit()
    
    def delete_all_dynamic_info(self):
        self.mycursor.execute("DELETE FROM dynamic_info")
        self.mydb.commit()

    def close(self):
        self.mydb.close()
        self.mycursor.close()  

    def has_static_data(self, mac_address):
        self.mycursor.execute("SELECT * FROM static_info WHERE mac_address = %s", (mac_address,))
        result = self.mycursor.fetchone()
        return result is not None
    
    def has_dynamic_data(self, mac_address):
        self.mycursor.execute("SELECT * FROM dynamic_info WHERE mac_address = %s", (mac_address,))
        result = self.mycursor.fetchone()
        return result is not None

if __name__ == "__main__":
    db = Database()
    db.drop_all_tables()
    db.create_table_user()
    db.create_static_computer_info()
    db.create_dynamic_computer_info()
    
    db.close()

