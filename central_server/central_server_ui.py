from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListWidget, QLabel, QTableWidget, QTableWidgetItem, QComboBox, QStackedWidget, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import sys

class CentralServerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Central Server Dashboard')
        self.resize(1200, 700)
        self.init_ui()

    def handle_shutdown(self):
        print("Shutdown button clicked")

    def handle_restart(self):
        print("Restart button clicked")

    def handle_notify(self):
        print("Send Notification button clicked")

    def handle_ai_predict(self):
        print("AI Predict button clicked")

    def handle_mac_selected(self, index):
        mac = self.mac_selector.itemText(index)
        print(f"MAC selected: {mac}")

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Left: Command Buttons
        left_box = QGroupBox('Commands')
        left_layout = QVBoxLayout()
        self.btn_shutdown = QPushButton('Shutdown')
        self.btn_restart = QPushButton('Restart')
        self.btn_notify = QPushButton('Send Notification')
        self.btn_ai_predict = QPushButton('AI Predict')
        for btn, handler in zip(
            [self.btn_shutdown, self.btn_restart, self.btn_notify, self.btn_ai_predict],
            [self.handle_shutdown, self.handle_restart, self.handle_notify, self.handle_ai_predict]
        ):
            btn.setMinimumHeight(40)
            left_layout.addWidget(btn)
            btn.clicked.connect(handler)
        left_layout.addStretch()
        left_box.setLayout(left_layout)

        # Center: Client Info
        center_box = QGroupBox('Client Info')
        center_layout = QVBoxLayout()
        self.mac_selector = QComboBox()
        self.mac_selector.setPlaceholderText('Select MAC Address')
        center_layout.addWidget(self.mac_selector)
        self.static_label = QLabel('Static Info:')
        self.static_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        center_layout.addWidget(self.static_label)
        self.static_info = QLabel('(Static info will be shown here)')
        self.static_info.setWordWrap(True)
        center_layout.addWidget(self.static_info)
        self.dynamic_label = QLabel('Dynamic Info:')
        self.dynamic_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        center_layout.addWidget(self.dynamic_label)
        # Placeholder for dynamic chart area
        self.dynamic_chart = QLabel('(Dynamic charts will be shown here)')
        self.dynamic_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dynamic_chart.setStyleSheet('border: 1px solid #aaa; min-height: 200px;')
        center_layout.addWidget(self.dynamic_chart)
        center_layout.addStretch()
        center_box.setLayout(center_layout)

        # Right: Alerts and Server Logs
        right_box = QGroupBox('Alerts & Server Logs')
        right_layout = QVBoxLayout()
        self.alerts_label = QLabel('Alerts:')
        self.alerts_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        right_layout.addWidget(self.alerts_label)
        self.alerts_table = QTableWidget(0, 4)
        self.alerts_table.setHorizontalHeaderLabels(['Time', 'MAC', 'Type', 'Message'])
        self.alerts_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.alerts_table)
        self.logs_label = QLabel('Server Logs:')
        self.logs_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        right_layout.addWidget(self.logs_label)
        self.logs_table = QTableWidget(0, 3)
        self.logs_table.setHorizontalHeaderLabels(['Time', 'Address', 'Message'])
        self.logs_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.logs_table)
        right_box.setLayout(right_layout)

        main_layout.addWidget(left_box, 1)
        main_layout.addWidget(center_box, 3)
        main_layout.addWidget(right_box, 2)
        self.mac_selector.currentIndexChanged.connect(self.handle_mac_selected)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CentralServerUI()
    window.show()
    sys.exit(app.exec())
