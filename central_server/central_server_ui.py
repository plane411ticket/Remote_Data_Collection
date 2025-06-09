import io
import json
import socket
import sys
import pymysql
import ollama
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QPixmap, QTextOption
from PySide6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QComboBox, QGroupBox,
    QMessageBox, QSplitter, QInputDialog, QLineEdit, QScrollBar, QTextEdit
)

from auth_dialog import AuthDialog

# Danh sách các main_server (broadcast tới tất cả)
MAIN_SERVERS = [
    {"host": "127.0.0.1", "port": 10001},
    {"host": "127.0.0.1", "port": 10002},
    # {"host": "192.168.1.102", "port": 10000},
]


class OllamaChatThread(QThread):
    finished = Signal(str)  # Signal để gửi kết quả trả về UI

    def __init__(self, user_message):
        super().__init__()
        self.user_message = user_message

    def run(self):
        try:
            response = ollama.chat(model='llama3.2:3b', messages=[{"role": "user", "content": self.user_message}])
            bot_reply = response['message']['content'] if 'message' in response and 'content' in response['message'] else str(response)
        except Exception as e:
            bot_reply = f"[Error] {e}"
        self.finished.emit(bot_reply)

class CentralServerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Central Server Dashboard')
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
                password="nndd411",
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

    def load_dynamic_info(self, mac_address, limit=10):
        """Tạo nhiều biểu đồ thông tin dynamic từ database cho MAC address được chọn (bỏ Disk)"""
        if not self.db_connection or mac_address is None:
            for chart in [self.cpu_chart, self.memory_chart, self.swap_chart, self.memory_gb_chart]:
                chart.setText("No MAC address selected")
            return
        query = """
            SELECT timestamp, cpu_usage, memory_percent, swap_percent, 
                   memory_used, memory_available, swap_used, disk_used, disk_free
            FROM dynamic_info 
            WHERE mac_address = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        results = self.execute_query(query, (mac_address, limit))
        if not results or len(results) < 2:
            for chart in [self.cpu_chart, self.memory_chart, self.swap_chart, self.memory_gb_chart]:
                chart.setText("Insufficient data to generate chart (need at least 2 data points)")
            return
        try:
            # Prepare data for plotting
            timestamps = [row[0] for row in results]
            cpu_data = [row[1] if row[1] is not None else 0 for row in results]
            memory_data = [row[2] if row[2] is not None else 0 for row in results]
            swap_data = [row[3] if row[3] is not None else 0 for row in results]
            memory_used = [row[4] if row[4] is not None else 0 for row in results]
            memory_available = [row[5] if row[5] is not None else 0 for row in results]
            # Helper to plot and set pixmap for a QLabel
            def plot_to_label(x, y_list, label, title, ylabel, legend, colors, yunit=None):
                plt.style.use('default')
                fig, ax = plt.subplots(figsize=(6, 2.2))
                fig.patch.set_facecolor('#f8f9fa')
                for y, leg, color in zip(y_list, legend, colors):
                    ax.plot(x, y, label=leg, color=color, linewidth=2)
                ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
                ax.set_xlabel('Time', fontsize=9)
                ax.set_ylabel(ylabel, fontsize=9)
                if yunit == 'percent':
                    ax.set_ylim(0, 100)
                ax.grid(True, alpha=0.3)
                ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
                if len(x) > 10:
                    ax.xaxis.set_major_locator(plt.MaxNLocator(6))
                plt.xticks(rotation=45, fontsize=8)
                plt.tight_layout()
                canvas = FigureCanvasAgg(fig)
                canvas.draw()
                buf = io.BytesIO()
                canvas.print_png(buf)
                buf.seek(0)
                pixmap = QPixmap()
                pixmap.loadFromData(buf.getvalue())
                scaled_pixmap = pixmap.scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled_pixmap)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                plt.close(fig)
                buf.close()
            # CPU Usage
            plot_to_label(
                timestamps, [cpu_data], self.cpu_chart,
                f'CPU Usage - {self.format_mac_address(mac_address)}',
                'CPU (%)', ['CPU Usage'], ['#e74c3c'], yunit='percent'
            )
            # Memory Usage
            plot_to_label(
                timestamps, [memory_data], self.memory_chart,
                'Memory Usage (%)', 'Memory (%)', ['Memory Usage'], ['#3498db'], yunit='percent'
            )
            # Swap Usage
            plot_to_label(
                timestamps, [swap_data], self.swap_chart,
                'Swap Usage (%)', 'Swap (%)', ['Swap Usage'], ['#f39c12'], yunit='percent'
            )
            # Memory GB (used & available)
            mem_used_gb = [v/(1024**3) for v in memory_used]
            mem_avail_gb = [v/(1024**3) for v in memory_available]
            plot_to_label(
                timestamps, [mem_used_gb, mem_avail_gb], self.memory_gb_chart,
                'Memory (GB)', 'GB', ['Used', 'Available'], ['#2ecc71', '#95a5a6']
            )
            # Status label
            if results:
                latest = results[-1]
                tooltip_text = f"Latest: CPU {latest[1] or 0:.1f}%, Mem {latest[2] or 0:.1f}%, Swap {latest[3] or 0:.1f}% (Updated: {latest[0]})"
                # print(tooltip_text)
                self.status_label.setText(tooltip_text)
        except Exception as e:
            print(f"Error creating charts: {e}")
            for chart in [self.cpu_chart, self.memory_chart, self.swap_chart, self.memory_gb_chart]:
                chart.setText(f"Error creating chart: {str(e)}")

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
                # Format time as hh:mm:ss
                if hasattr(timestamp, 'strftime'):
                    time_str = timestamp.strftime('%H:%M:%S')
                else:
                    # fallback if timestamp is string
                    import datetime
                    try:
                        dt = datetime.datetime.fromisoformat(str(timestamp))
                        time_str = dt.strftime('%H:%M:%S')
                    except Exception:
                        time_str = str(timestamp)
                self.alerts_table.insertRow(row_index)
                self.alerts_table.setItem(row_index, 0, QTableWidgetItem(time_str))
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
                # Format time as hh:mm:ss
                if hasattr(timestamp, 'strftime'):
                    time_str = timestamp.strftime('%H:%M:%S')
                else:
                    import datetime
                    try:
                        dt = datetime.datetime.fromisoformat(str(timestamp))
                        time_str = dt.strftime('%H:%M:%S')
                    except Exception:
                        time_str = str(timestamp)
                self.logs_table.insertRow(row_index)
                self.logs_table.setItem(row_index, 0, QTableWidgetItem(time_str))
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

    def send_command_to_main_server(self, mac_address, command_type, message=None):
        """Broadcast lệnh tới tất cả main_server trong danh sách"""
        command = {
            "mac_address": mac_address,
            "command": command_type
        }
        if message:
            command["message"] = message
        responses = []
        for server in MAIN_SERVERS:
            host = server["host"]
            port = server["port"]
            try:
                with socket.create_connection((host, port), timeout=3) as sock:
                    sock.sendall((json.dumps(command) + "\n").encode('utf-8'))
                    response = sock.recv(1024).decode('utf-8')
                    responses.append(f"{host}:{port} => {response}")
            except Exception as e:
                responses.append(f"{host}:{port} => Error: {e}")
        return "\n".join(responses)

    def handle_command(self, command_type):
        """Xử lý chung cho các lệnh shutdown, restart, notify, AI predict"""
        current_mac = self.mac_selector.currentData()
        if current_mac is None:
            QMessageBox.warning(self, "Warning", "Please select a MAC address first!")
            return
        mac_str = self.format_mac_address(current_mac)
        if command_type in ["shutdown", "restart"]:
            confirm_msg = f"Are you sure you want to {command_type} the client with MAC: {mac_str}?"
            reply = QMessageBox.question(self, f"Confirm {command_type.capitalize()}", confirm_msg)
            if reply != QMessageBox.StandardButton.Yes:
                return
            response = self.send_command_to_main_server(current_mac, command_type)
            if response:
                QMessageBox.information(self, "Success", f"{command_type.capitalize()} command sent to MAC: {mac_str}\nServer response: {response}")
                print(f"{command_type.capitalize()} command sent to MAC: {mac_str}")
            else:
                QMessageBox.warning(self, "Error", f"Failed to send {command_type} command to main_server")
        elif command_type == "notify":
            text, ok = QInputDialog.getText(self, "Send Notification", f"Enter notification message for {mac_str}:")
            if not ok or not text.strip():
                return
            # Gửi message tới client qua main_server
            response = self.send_command_to_main_server(current_mac, "notify", message=text.strip())
            if response:
                QMessageBox.information(self, "Success", f"Notification sent to MAC: {mac_str}\nServer response: {response}")
                print(f"Notification sent to MAC: {mac_str}")
            else:
                QMessageBox.warning(self, "Error", "Failed to send notification to main_server")
        elif command_type == "ai_predict":
            QMessageBox.information(self, "AI Predict", "AI prediction feature is not implemented yet.")
            print("AI prediction feature is not implemented yet.")

    def init_ui(self):
        """Khởi tạo giao diện người dùng với layout hiện đại, chuyên nghiệp"""
        main_layout = QVBoxLayout(self)

        # Top: User Info Bar
        user_info_layout = QHBoxLayout()
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

        # Main splitter for 3 panels
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Panel: Commands & Client Info ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Command Buttons
        commands_box = QGroupBox('Commands')
        commands_layout = QVBoxLayout()
        self.btn_shutdown = QPushButton('🔴 Shutdown')
        self.btn_restart = QPushButton('🔄 Restart')
        self.btn_notify = QPushButton('📢 Send Notification')
        self.btn_ai_predict = QPushButton('🤖 AI Predict')
        buttons = [
            (self.btn_shutdown, lambda: self.handle_command("shutdown")),
            (self.btn_restart, lambda: self.handle_command("restart")),
            (self.btn_notify, lambda: self.handle_command("notify")),
            (self.btn_ai_predict, lambda: self.handle_command("ai_predict"))
        ]
        for btn, handler in buttons:
            btn.setMinimumHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 13px;
                    font-weight: bold;
                    border: 2px solid #3498db;
                    border-radius: 8px;
                    padding: 8px;
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
            btn.clicked.connect(handler)
            commands_layout.addWidget(btn)
        commands_box.setLayout(commands_layout)
        left_layout.addWidget(commands_box)

        # Client Info
        client_info_box = QGroupBox('Client Information')
        client_info_layout = QVBoxLayout()
        mac_label = QLabel('Select Client:')
        mac_label.setFont(QFont('Arial', 10, QFont.Weight.Bold))
        client_info_layout.addWidget(mac_label)
        self.mac_selector = QComboBox()
        self.mac_selector.setMinimumHeight(35)
        self.mac_selector.setStyleSheet("""
            QComboBox {
                font-size: 11px;
                padding: 5px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
            }
        """)
        client_info_layout.addWidget(self.mac_selector)
        self.static_info = QLabel('Select a MAC address to view static information')
        self.static_info.setWordWrap(True)
        self.static_info.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.static_info.setStyleSheet("""
            QLabel {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 10px;
                background-color: #f8f9fa;
                min-height: 200px;
            }
        """)
        client_info_layout.addWidget(self.static_info)
        client_info_box.setLayout(client_info_layout)
        left_layout.addWidget(client_info_box)

        # --- Chat with Ollama Chatbot ---
        chat_box = QGroupBox('Chat with Ollama')
        chat_layout = QVBoxLayout()
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                background-color: #f8f9fa;
                min-height: 80px;
                max-height: 120px;
            }
        """)
        self.chat_history.setText('')
        chat_layout.addWidget(self.chat_history)
        chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText('Type your message to Ollama...')
        self.chat_input.setMinimumHeight(30)
        chat_input_layout.addWidget(self.chat_input)
        self.send_chat_btn = QPushButton('Send')
        self.send_chat_btn.setMinimumHeight(30)
        self.send_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                padding: 6px 15px;
            }
            QPushButton:hover {
                background-color: #219150;
            }
        """)
        self.send_chat_btn.clicked.connect(self.handle_send_chat)
        chat_input_layout.addWidget(self.send_chat_btn)
        chat_layout.addLayout(chat_input_layout)
        chat_box.setLayout(chat_layout)
        left_layout.addWidget(chat_box)
        left_layout.addStretch()
        main_splitter.addWidget(left_panel)

        # --- Center Panel: Multi-Chart ---
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        charts_title = QLabel('Performance Monitoring - Real-time Charts')
        charts_title.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        charts_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        charts_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        center_layout.addWidget(charts_title)
        # Thêm các QLabel cho từng loại biểu đồ (bỏ Disk)
        self.cpu_chart = QLabel('(CPU Usage chart)')
        self.memory_chart = QLabel('(Memory Usage chart)')
        self.swap_chart = QLabel('(Swap Usage chart)')
        self.memory_gb_chart = QLabel('(Memory GB chart)')
        for chart in [self.cpu_chart, self.memory_chart, self.swap_chart, self.memory_gb_chart]:
            chart.setAlignment(Qt.AlignmentFlag.AlignTop)
            chart.setWordWrap(True)
            chart.setStyleSheet("""
                QLabel {
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                    padding: 10px;
                    min-height: 120px;
                }
            """)
            center_layout.addWidget(chart)
        self.status_label = QLabel("No data available")
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 5px;
                background-color: #ecf0f1;
                border-radius: 3px;
                border: 1px solid #bdc3c7;
            }
        """)
        center_layout.addWidget(self.status_label)
        center_layout.addStretch()
        main_splitter.addWidget(center_panel)

        # --- Right Panel: Alerts & Logs ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        alerts_label = QLabel('Recent Alerts:')
        alerts_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        right_layout.addWidget(alerts_label)
        self.alerts_table = QTableWidget(0, 4)
        self.alerts_table.setHorizontalHeaderLabels(['Time', 'MAC', 'Type/Level', 'Message'])
        self.alerts_table.horizontalHeader().setStretchLastSection(True)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.alerts_table)
        logs_label = QLabel('Server Logs:')
        logs_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        right_layout.addWidget(logs_label)
        self.logs_table = QTableWidget(0, 3)
        self.logs_table.setHorizontalHeaderLabels(['Time', 'Address', 'Message'])
        self.logs_table.horizontalHeader().setStretchLastSection(True)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.logs_table)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 700, 400])
        main_layout.addWidget(main_splitter)

        # Connect signals
        self.mac_selector.currentIndexChanged.connect(self.handle_mac_selected)
        # Load initial data
        self.load_alerts()
        self.load_server_logs()

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
            for chart in [self.cpu_chart, self.memory_chart, self.swap_chart, self.memory_gb_chart]:
                chart.setText("(Dynamic charts will be implemented here)")

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

    def handle_send_chat(self):
        """Gửi tin nhắn tới Ollama chatbot trên thread khác và hiển thị phản hồi"""
        user_message = self.chat_input.text().strip()
        if not user_message:
            return
        self.chat_input.setDisabled(True)
        self.send_chat_btn.setDisabled(True)
        self.chat_history.append(f"<b>You:</b> {user_message}<br>")
        # Tạo thread mới để gọi ollama
        self.ollama_thread = OllamaChatThread(user_message)
        self.ollama_thread.finished.connect(self.display_ollama_response)
        self.ollama_thread.start()

    def display_ollama_response(self, bot_reply):
        self.chat_history.append(f"<b>Ollama:</b> {bot_reply}<br>")
        self.chat_input.clear()
        self.chat_input.setDisabled(False)
        self.send_chat_btn.setDisabled(False)
        self.chat_input.setFocus()
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    window = CentralServerUI()
    window.show()
    sys.exit(app.exec())
