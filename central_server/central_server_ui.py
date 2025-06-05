from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QComboBox, QGroupBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap
import sys
import pymysql
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io
from auth_dialog import AuthDialog


class CentralServerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Central Server Dashboard - pymysql Version')
        self.resize(1200, 700)
        self.db_connection = None
        self.current_user = None
        
        # Show authentication dialog first
        if not self.authenticate_user():
            sys.exit(0)  # Exit if authentication fails
            
        self.init_database()
        self.init_ui()
        self.load_mac_addresses()
        
        # Setup timer for auto-refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def authenticate_user(self):
        """Hiển thị dialog authentication và xác thực user"""
        auth_dialog = AuthDialog()
        result = auth_dialog.exec()
        
        if result == AuthDialog.DialogCode.Accepted:
            # Get user info from database
            try:
                temp_connection = pymysql.connect(
                    host="localhost",
                    port=3306,
                    user="root",
                    password="",
                    database="remote_collection",
                    charset='utf8mb4',
                    autocommit=True
                )
                cursor = temp_connection.cursor()
                cursor.execute("""
                    SELECT username, full_name, email, last_login 
                    FROM admin_users 
                    WHERE last_login = (SELECT MAX(last_login) FROM admin_users)
                """)
                user_info = cursor.fetchone()
                if user_info:
                    self.current_user = {
                        'username': user_info[0],
                        'full_name': user_info[1],
                        'email': user_info[2],
                        'last_login': user_info[3]
                    }
                temp_connection.close()
                print(f"✅ User authenticated: {self.current_user['full_name']}")
                return True
            except Exception as e:
                print(f"❌ Error getting user info: {e}")
                return False
        else:
            return False

    def init_database(self):
        """Khởi tạo kết nối database bằng pymysql"""
        try:
            self.db_connection = pymysql.connect(
                host="localhost",
                port=3306,
                user="root",
                password="",
                database="remote_collection",
                charset='utf8mb4',
                autocommit=True
            )
            print("✅ Connected to database successfully using pymysql!")
        except pymysql.Error as e:
            QMessageBox.critical(self, "Database Error", 
                               f"Cannot connect to database:\n{e}")
            sys.exit(1)

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=True):
        """Thực thi query với xử lý lỗi"""
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(query, params or ())
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.rowcount
        except pymysql.Error as e:
            print(f"Database error: {e}")
            return None

    def load_mac_addresses(self):
        """Tải danh sách địa chỉ MAC từ database"""
        if not self.db_connection:
            return
            
        query = "SELECT DISTINCT mac_address FROM static_info ORDER BY mac_address"
        results = self.execute_query(query)
        
        if results is not None:
            self.mac_selector.clear()
            self.mac_selector.addItem("Select MAC Address", None)
            
            for row in results:
                mac_address = row[0]
                # Convert MAC address from BIGINT to readable format
                mac_formatted = self.format_mac_address(mac_address)
                self.mac_selector.addItem(mac_formatted, mac_address)
        else:
            QMessageBox.warning(self, "Query Error", 
                              "Failed to load MAC addresses from database")

    def format_mac_address(self, mac_int):
        """Chuyển đổi MAC address từ BIGINT sang định dạng readable"""
        if mac_int is None:
            return "Unknown"
        
        # Convert to hex and format as MAC address
        mac_hex = format(mac_int, '012x')
        return ':'.join(mac_hex[i:i+2] for i in range(0, 12, 2))

    def load_static_info(self, mac_address):
        """Tải thông tin static cho MAC address được chọn"""
        if not self.db_connection or mac_address is None:
            self.static_info.setText("No MAC address selected")
            return
            
        query = """
            SELECT cpu_brand, cpu_arch, cpu_bits, cpu_logical, cpu_physical, 
                   memory_total, swap_total, timestamp 
            FROM static_info 
            WHERE mac_address = %s
        """
        result = self.execute_query(query, (mac_address,), fetch_one=True)
        
        if result:
            cpu_brand = result[0] or "Unknown"
            cpu_arch = result[1] or "Unknown"
            cpu_bits = result[2] or 0
            cpu_logical = result[3] or 0
            cpu_physical = result[4] or 0
            memory_total = result[5] or 0
            swap_total = result[6] or 0
            timestamp = result[7]
            
            # Format memory sizes
            memory_gb = memory_total / (1024**3) if memory_total else 0
            swap_gb = swap_total / (1024**3) if swap_total else 0
            
            info_text = f"""
<b>CPU Information:</b><br>
• Brand: {cpu_brand}<br>
• Architecture: {cpu_arch}<br>
• Bits: {cpu_bits}<br>
• Logical Cores: {cpu_logical}<br>
• Physical Cores: {cpu_physical}<br><br>

<b>Memory Information:</b><br>
• Total RAM: {memory_gb:.2f} GB<br>
• Total Swap: {swap_gb:.2f} GB<br><br>

<b>Last Updated:</b> {timestamp}
            """
            self.static_info.setText(info_text)
        else:
            self.static_info.setText("No static information found for this MAC address")

    def load_dynamic_info(self, mac_address, limit=50):
        """Tạo biểu đồ thông tin dynamic từ database cho MAC address được chọn"""
        if not self.db_connection or mac_address is None:
            self.dynamic_chart.setText("No MAC address selected")
            return
            
        query = """
            SELECT timestamp, cpu_usage, memory_percent, swap_percent, 
                   memory_used, memory_available, swap_used, disk_used, disk_free
            FROM dynamic_info 
            WHERE mac_address = %s
            ORDER BY timestamp ASC
            LIMIT %s
        """
        results = self.execute_query(query, (mac_address, limit))
        
        if not results or len(results) < 2:
            self.dynamic_chart.setText("Insufficient data to generate chart (need at least 2 data points)")
            return
        
        try:
            # Prepare data for plotting
            timestamps = []
            cpu_data = []
            memory_data = []
            swap_data = []
            
            for row in results:
                timestamps.append(row[0])
                cpu_data.append(row[1] if row[1] is not None else 0)
                memory_data.append(row[2] if row[2] is not None else 0)
                swap_data.append(row[3] if row[3] is not None else 0)
            
            # Create matplotlib figure
            plt.style.use('default')
            fig, ax = plt.subplots(figsize=(8, 6))
            fig.patch.set_facecolor('#f8f9fa')
            
            # Plot lines
            ax.plot(timestamps, cpu_data, label='CPU Usage (%)', color='#e74c3c', linewidth=2, marker='o', markersize=4)
            ax.plot(timestamps, memory_data, label='Memory Usage (%)', color='#3498db', linewidth=2, marker='s', markersize=4)
            ax.plot(timestamps, swap_data, label='Swap Usage (%)', color='#f39c12', linewidth=2, marker='^', markersize=4)
            
            # Customize chart
            ax.set_title(f'System Performance - {self.format_mac_address(mac_address)}', 
                        fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Usage (%)', fontsize=12)
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right', framealpha=0.9)
            
            # Format x-axis timestamps
            if len(timestamps) > 10:
                # Show fewer labels for readability
                ax.xaxis.set_major_locator(plt.MaxNLocator(6))
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convert plot to image
            canvas = FigureCanvasAgg(fig)
            canvas.draw()
            
            # Get image as bytes
            buf = io.BytesIO()
            canvas.print_png(buf)
            buf.seek(0)
            
            # Convert to QPixmap and display
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            
            # Scale pixmap to fit the label
            scaled_pixmap = pixmap.scaled(
                self.dynamic_chart.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.dynamic_chart.setPixmap(scaled_pixmap)
            self.dynamic_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Clean up
            plt.close(fig)
            buf.close()
              # Also display latest values as tooltip or status
            if results:
                latest = results[-1]  # Last entry (most recent)
                timestamp = latest[0]
                cpu_usage = latest[1] or 0
                memory_percent = latest[2] or 0
                swap_percent = latest[3] or 0
                
                tooltip_text = f"Latest: CPU {cpu_usage:.1f}%, Memory {memory_percent:.1f}%, Swap {swap_percent:.1f}% (Updated: {timestamp})"
                self.dynamic_chart.setToolTip(tooltip_text)
                
        except Exception as e:
            print(f"Error creating chart: {e}")
            self.dynamic_chart.setText(f"Error creating chart: {str(e)}")

    def load_alerts(self):
        """Tải danh sách alerts từ database"""
        if not self.db_connection:
            return
            
        query = """
            SELECT created_at, mac_address, alert_type, alert_message, alert_level
            FROM alerts
            ORDER BY created_at DESC
            LIMIT 50
        """
        results = self.execute_query(query)
        
        if results is not None:
            self.alerts_table.setRowCount(0)
            
            for row_index, row_data in enumerate(results):
                timestamp = row_data[0]
                mac_address = row_data[1]
                alert_type = row_data[2]
                alert_message = row_data[3]
                alert_level = row_data[4]
                
                self.alerts_table.insertRow(row_index)
                self.alerts_table.setItem(row_index, 0, QTableWidgetItem(str(timestamp)))
                self.alerts_table.setItem(row_index, 1, QTableWidgetItem(self.format_mac_address(mac_address)))
                self.alerts_table.setItem(row_index, 2, QTableWidgetItem(f"{alert_type} ({alert_level})"))
                self.alerts_table.setItem(row_index, 3, QTableWidgetItem(alert_message))
        else:
            print("Error loading alerts")

    def load_server_logs(self):
        """Tải server logs từ database"""
        if not self.db_connection:
            return
            
        query = """
            SELECT timestamp, address, log_message
            FROM server_logs
            ORDER BY timestamp DESC
            LIMIT 50
        """
        results = self.execute_query(query)
        
        if results is not None:
            self.logs_table.setRowCount(0)
            
            for row_index, row_data in enumerate(results):
                timestamp = row_data[0]
                address = row_data[1]
                log_message = row_data[2]
                
                self.logs_table.insertRow(row_index)
                self.logs_table.setItem(row_index, 0, QTableWidgetItem(str(timestamp)))
                self.logs_table.setItem(row_index, 1, QTableWidgetItem(address))
                self.logs_table.setItem(row_index, 2, QTableWidgetItem(log_message))
        else:
            print("Error loading server logs")

    def refresh_data(self):
        """Refresh all data"""
        self.load_alerts()
        self.load_server_logs()
        # Refresh static and dynamic info if a MAC is selected
        current_data = self.mac_selector.currentData()
        if current_data is not None:
            self.load_static_info(current_data)
            self.load_dynamic_info(current_data)

    def send_command_to_database(self, mac_address, alert_type, alert_level, alert_message):
        """Gửi lệnh vào database (alerts table)"""
        if not self.db_connection:
            return False
            
        query = """
            INSERT INTO alerts (mac_address, alert_type, alert_level, alert_message)
            VALUES (%s, %s, %s, %s)
        """
        result = self.execute_query(query, (mac_address, alert_type, alert_level, alert_message), fetch_all=False)
        return result is not None

    def handle_shutdown(self):
        """Xử lý lệnh shutdown"""
        current_mac = self.mac_selector.currentData()
        if current_mac is None:
            QMessageBox.warning(self, "Warning", "Please select a MAC address first!")
            return
            
        reply = QMessageBox.question(self, "Confirm Shutdown", 
                                   f"Are you sure you want to shutdown the client with MAC: {self.format_mac_address(current_mac)}?")
        if reply == QMessageBox.StandardButton.Yes:
            success = self.send_command_to_database(current_mac, "system", "shutdown", "Remote shutdown command from dashboard")
            if success:
                QMessageBox.information(self, "Success", f"Shutdown command sent to MAC: {self.format_mac_address(current_mac)}")
                print(f"Shutdown command sent to MAC: {self.format_mac_address(current_mac)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to send shutdown command")

    def handle_restart(self):
        """Xử lý lệnh restart"""
        current_mac = self.mac_selector.currentData()
        if current_mac is None:
            QMessageBox.warning(self, "Warning", "Please select a MAC address first!")
            return
            
        reply = QMessageBox.question(self, "Confirm Restart", 
                                   f"Are you sure you want to restart the client with MAC: {self.format_mac_address(current_mac)}?")
        if reply == QMessageBox.StandardButton.Yes:
            success = self.send_command_to_database(current_mac, "system", "restart", "Remote restart command from dashboard")
            if success:
                QMessageBox.information(self, "Success", f"Restart command sent to MAC: {self.format_mac_address(current_mac)}")
                print(f"Restart command sent to MAC: {self.format_mac_address(current_mac)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to send restart command")

    def handle_notify(self):
        """Xử lý gửi notification"""
        current_mac = self.mac_selector.currentData()
        if current_mac is None:
            QMessageBox.warning(self, "Warning", "Please select a MAC address first!")
            return
            
        success = self.send_command_to_database(current_mac, "notification", "notify", "General notification from dashboard")
        if success:
            QMessageBox.information(self, "Success", f"Notification sent to MAC: {self.format_mac_address(current_mac)}")
            print(f"Notification sent to MAC: {self.format_mac_address(current_mac)}")
        else:
            QMessageBox.warning(self, "Error", "Failed to send notification")

    def handle_ai_predict(self):
        """Xử lý AI prediction"""
        print("AI prediction feature is not implemented yet.")

    def handle_mac_selected(self, index):
        """Xử lý khi MAC address được chọn"""
        mac_data = self.mac_selector.itemData(index)
        if mac_data is not None:
            mac_formatted = self.format_mac_address(mac_data)
            print(f"MAC selected: {mac_formatted}")
            self.load_static_info(mac_data)
            self.load_dynamic_info(mac_data)
        else:
            self.static_info.setText("No MAC address selected")
            self.dynamic_chart.setText("(Dynamic charts will be implemented here)")

    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        main_layout = QVBoxLayout(self)
        
        # Top: User Info Bar
        user_info_layout = QHBoxLayout()
        # Welcome message
        welcome_label = QLabel(f"👤 Welcome, {self.current_user['full_name']} ({self.current_user['username']})")
        welcome_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        welcome_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 8px;
                background-color: #ecf0f1;
                border-radius: 5px;
            }
        """)
        user_info_layout.addWidget(welcome_label)
        
        user_info_layout.addStretch()
        
        # Logout button
        logout_btn = QPushButton('🚪 Logout')
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        logout_btn.clicked.connect(self.handle_logout)
        user_info_layout.addWidget(logout_btn)
        
        main_layout.addLayout(user_info_layout)
        
        # Main Content Layout
        content_layout = QHBoxLayout()

        # Left: Command Buttons
        left_box = QGroupBox('Commands')
        left_layout = QVBoxLayout()
        
        self.btn_shutdown = QPushButton('🔴 Shutdown')
        self.btn_restart = QPushButton('🔄 Restart')
        self.btn_notify = QPushButton('📢 Send Notification')
        self.btn_ai_predict = QPushButton('🤖 AI Predict')
        
        buttons = [
            (self.btn_shutdown, self.handle_shutdown),
            (self.btn_restart, self.handle_restart),
            (self.btn_notify, self.handle_notify),
            (self.btn_ai_predict, self.handle_ai_predict)
        ]
        
        for btn, handler in buttons:
            btn.setMinimumHeight(50)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #3498db;
                    border-radius: 8px;
                    padding: 10px;
                    background-color: #ecf0f1;
                }
                QPushButton:hover {
                    background-color: #3498db;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #2980b9;
                }
            """)
            left_layout.addWidget(btn)
            btn.clicked.connect(handler)
        
        left_layout.addStretch()
        left_box.setLayout(left_layout)

        # Center: Client Info
        center_box = QGroupBox('Client Information')
        center_layout = QVBoxLayout()
        
        # MAC Selector
        mac_label = QLabel('Select Client:')
        mac_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        center_layout.addWidget(mac_label)
        
        self.mac_selector = QComboBox()
        self.mac_selector.setMinimumHeight(35)
        self.mac_selector.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                padding: 5px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
            }
        """)
        center_layout.addWidget(self.mac_selector)
        
        # Static Info
        self.static_label = QLabel('Static Information:')
        self.static_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        center_layout.addWidget(self.static_label)
        
        self.static_info = QLabel('Select a MAC address to view static information')
        self.static_info.setWordWrap(True)
        self.static_info.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.static_info.setStyleSheet("""
            QLabel {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                background-color: #f8f9fa;
                min-height: 180px;
            }
        """)
        center_layout.addWidget(self.static_info)
        
        # Dynamic Info
        self.dynamic_label = QLabel('Dynamic Information:')
        self.dynamic_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        center_layout.addWidget(self.dynamic_label)
        
        self.dynamic_chart = QLabel('(Dynamic information will be shown here)')
        self.dynamic_chart.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.dynamic_chart.setWordWrap(True)
        self.dynamic_chart.setStyleSheet("""
            QLabel {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #f8f9fa;
                padding: 10px;
                min-height: 180px;
            }
        """)
        center_layout.addWidget(self.dynamic_chart)
        
        center_layout.addStretch()
        center_box.setLayout(center_layout)

        # Right: Alerts and Server Logs
        right_box = QGroupBox('Alerts & Server Logs')
        right_layout = QVBoxLayout()
        
        # Alerts
        self.alerts_label = QLabel('Recent Alerts:')
        self.alerts_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        right_layout.addWidget(self.alerts_label)
        
        self.alerts_table = QTableWidget(0, 4)
        self.alerts_table.setHorizontalHeaderLabels(['Time', 'MAC', 'Type/Level', 'Message'])
        self.alerts_table.horizontalHeader().setStretchLastSection(True)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.alerts_table)
        
        # Server Logs
        self.logs_label = QLabel('Server Logs:')
        self.logs_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        right_layout.addWidget(self.logs_label)
        
        self.logs_table = QTableWidget(0, 3)
        self.logs_table.setHorizontalHeaderLabels(['Time', 'Address', 'Message'])
        self.logs_table.horizontalHeader().setStretchLastSection(True)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.logs_table)
        right_box.setLayout(right_layout)

        # Add all sections to content layout
        content_layout.addWidget(left_box, 1)
        content_layout.addWidget(center_box, 3)
        content_layout.addWidget(right_box, 2)
        
        # Add content layout to main layout
        main_layout.addLayout(content_layout)
        
        # Connect signals
        self.mac_selector.currentIndexChanged.connect(self.handle_mac_selected)
        
        # Load initial data
        self.load_alerts()
        self.load_server_logs()

    def handle_logout(self):
        """Xử lý đăng xuất"""
        reply = QMessageBox.question(self, "Confirm Logout", 
                                   "Are you sure you want to logout?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            print(f"✅ User {self.current_user['username']} logged out")
            self.close()
            QApplication.quit()

    def closeEvent(self, event):
        """Đóng kết nối database khi thoát ứng dụng"""
        if self.db_connection:
            self.db_connection.close()
            print("✅ Database connection closed")
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    window = CentralServerUI()
    window.show()
    sys.exit(app.exec())
