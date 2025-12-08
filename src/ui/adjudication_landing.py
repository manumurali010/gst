from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame)
from PyQt6.QtCore import Qt

class AdjudicationLanding(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)

        # Title
        title = QLabel("Adjudication Module")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Select an option to proceed")
        subtitle.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Buttons Container
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(40)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Option 1: Start New Proceeding
        self.new_case_btn = self.create_option_button(
            "Start New Proceeding",
            "Initiate a fresh case for a specific GSTIN and Financial Year.",
            "#3498db"
        )
        self.new_case_btn.clicked.connect(lambda: self.navigate_callback("new_case"))
        btn_layout.addWidget(self.new_case_btn)

        # Option 2: Continue Existing Case
        self.continue_case_btn = self.create_option_button(
            "Continue Existing Case",
            "Manage lifecycle: DRC-01A → SCN → PH → Order.",
            "#2ecc71"
        )
        self.continue_case_btn.clicked.connect(lambda: self.navigate_callback("continue_case"))
        btn_layout.addWidget(self.continue_case_btn)

        layout.addLayout(btn_layout)

    def create_option_button(self, title, description, color):
        btn = QPushButton()
        btn.setFixedSize(300, 200)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 15px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {color}10; /* 10% opacity */
                margin-top: -5px;
            }}
        """)
        
        # Create layout for button content
        btn_layout = QVBoxLayout(btn)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color}; background: transparent;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setWordWrap(True)
        
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("font-size: 14px; color: #7f8c8d; background: transparent;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        
        btn_layout.addWidget(title_lbl)
        btn_layout.addWidget(desc_lbl)
        
        return btn
