from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTabWidget, QWidget, QMessageBox, QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import pymysql
import hashlib


class AuthDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Admin Authentication - Remote Data Collection')
        self.setFixedSize(400, 500)
        self.setModal(True)
        self.db_connection = None
        self.init_database()
        self.init_ui()

    def init_database(self):
        """Initialize database connection."""
        try:
            self.db_connection = pymysql.connect(
                host="localhost", 
                port=3306, 
                user="root", 
                password="3a0M1n4@gahoasoi", 
                database="remote_collection", 
                charset='utf8mb4', 
                autocommit=True
            )
            print("✅ Auth Dialog connected to database successfully!")
        except pymysql.Error as e:
            QMessageBox.critical(self, "Database Error", f"Cannot connect to database:\n{e}")

    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        title_label = self.create_label('🖥️ Remote Data Collection\nAdmin Dashboard', 16, QFont.Weight.Bold)
        layout.addWidget(title_label)

        # Tab Widget for Login/Register
        self.tab_widget = QTabWidget()
        self.setup_tabs()
        layout.addWidget(self.tab_widget)

    def setup_tabs(self):
        """Set up the login and register tabs."""
        login_tab = self.create_tab("🔑 Login", self.setup_login_tab)
        register_tab = self.create_tab("📝 Register", self.setup_register_tab)
        self.tab_widget.addTab(login_tab, "🔑 Login")
        self.tab_widget.addTab(register_tab, "📝 Register")

    def create_tab(self, tab_name, setup_func):
        """Helper function to create a tab."""
        tab = QWidget()
        setup_func(tab)
        return tab

    def create_label(self, text, font_size, font_weight):
        """Helper function to create styled label."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont('Arial', font_size, font_weight))
        label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                margin: 20px 0;
                padding: 10px;
            }
        """)
        return label

    def setup_login_tab(self, tab):
        """Setup the login tab UI."""
        layout = self.create_form_layout(tab)
        self.login_username = self.create_input_field("Enter your username", layout)
        self.login_password = self.create_input_field("Enter your password", layout, True)
        # self.remember_checkbox = QCheckBox('Remember me')
        # layout.addWidget(self.remember_checkbox)
        self.create_button('🔓 Login', layout, '#27ae60', self.handle_login)

    def setup_register_tab(self, tab):
        """Setup the register tab UI."""
        layout = self.create_form_layout(tab)
        self.register_fullname = self.create_input_field("Enter your full name", layout)
        self.register_username = self.create_input_field("Choose a username (3-20 characters)", layout)
        self.register_email = self.create_input_field("Enter your email address", layout)
        self.register_password = self.create_input_field("Enter password (min 6 characters)", layout, True)
        self.register_confirm = self.create_input_field("Confirm your password", layout, True)
        self.create_button('📝 Register', layout, '#3498db', self.handle_register)

    def create_form_layout(self, tab):
        """Helper function to create form layout for tabs."""
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 20, 30, 20)
        return layout

    def create_input_field(self, placeholder, layout, password=False):
        """Helper function to create input fields with placeholders."""
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setEchoMode(QLineEdit.EchoMode.Password if password else QLineEdit.EchoMode.Normal)
        line_edit.setStyleSheet(self.get_input_style())
        layout.addWidget(line_edit)
        return line_edit

    def create_button(self, text, layout, color, handler):
        """Helper function to create styled buttons."""
        button = QPushButton(text)
        button.setStyleSheet(self.get_button_style(color))
        button.clicked.connect(handler)
        layout.addWidget(button)

    def get_input_style(self):
        """Style for input fields."""
        return """
            QLineEdit {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 12px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """

    def get_button_style(self, color):
        """Style for buttons."""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color, 0.8)};
            }}
        """

    def darken_color(self, hex_color, factor=0.9):
        """Darken a given color."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * factor) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def handle_login(self):
        """Handle login logic."""
        self.handle_authentication(self.login_username.text().strip(), self.login_password.text(), "login")

    def handle_register(self):
        """Handle registration logic."""
        self.handle_authentication(self.register_username.text().strip(), self.register_password.text(), "register")

    def handle_authentication(self, username, password, action):
        """Common authentication handler."""
        if not username or not password:
            QMessageBox.warning(self, "Input Error", f"Please enter both username and password!")
            return

        try:
            cursor = self.db_connection.cursor()
            password_hash = self.hash_password(password)
            if action == "login":
                cursor.execute("SELECT id, full_name FROM admin_users WHERE username = %s AND password_hash = %s", (username, password_hash))
                result = cursor.fetchone()
                if result:
                    cursor.execute("UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE username = %s", (username,))
                    QMessageBox.information(self, "Login Successful", f"Welcome back, {result[1]}!")
                    self.accept()  # Close dialog with success
                else:
                    QMessageBox.warning(self, "Login Failed", "Invalid username or password!")
            else:
                # Registration logic
                self.register_user(cursor, username, password_hash)
        except pymysql.Error as e:
            QMessageBox.critical(self, f"{action.capitalize()} Error", f"Database error: {e}")

    def register_user(self, cursor, username, password_hash):
        """Handle user registration."""
        fullname = self.register_fullname.text().strip()
        email = self.register_email.text().strip()
        try:
            cursor.execute("INSERT INTO admin_users (username, password_hash, full_name, email) VALUES (%s, %s, %s, %s)", 
                           (username, password_hash, fullname, email))
            QMessageBox.information(self, "Registration Successful", f"Account created successfully for {fullname}!")
            self.tab_widget.setCurrentIndex(0)  # Switch to login tab
        except pymysql.IntegrityError as e:
            QMessageBox.warning(self, "Registration Error", f"Error: {e}")

    def hash_password(self, password):
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def closeEvent(self, event):
        """Close the database connection on dialog close."""
        if self.db_connection:
            self.db_connection.close()
            print("✅ Auth dialog database connection closed")
        event.accept()
