import mysql.connector

class Database:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host="mainline.proxy.rlwy.net",
            port=23149,
            user="root",
            password="uPilDXhcwYNlYwvcUACLfFgSOJwiGCaW",
            database="railway"
        )
        self.cursor = self.conn.cursor()

    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            cpu_usage FLOAT,
            ram_usage FLOAT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def insert_data(self, cpu, ram):
        self.cursor.execute("INSERT INTO system_data (cpu_usage, ram_usage) VALUES (%s, %s)", (cpu, ram))
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
