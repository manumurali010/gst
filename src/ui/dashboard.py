from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGridLayout, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from src.database.db_manager import DatabaseManager
from src.ui.styles import Theme, Styles

class DashboardCard(QFrame):
    def __init__(self, title, index, color, callback):
        super().__init__()
        self.index = index
        self.callback = callback
        self.default_color = color
        
        self.setFixedSize(220, 140) # Reduced from 260x160
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Style
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 12px;
                border: 1px solid {Theme.BORDER};
            }}
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(Qt.GlobalColor.lightGray)
        self.setGraphicsEffect(shadow)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon/Color Strip
        self.strip = QFrame()
        self.strip.setFixedHeight(6)
        self.strip.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        layout.addWidget(self.strip)
        
        layout.addSpacing(10)
        
        # Title
        self.label = QLabel(title)
        self.label.setStyleSheet(f"""
            font-size: 16px; /* Reduced from 20px */
            font-weight: bold; 
            color: {Theme.TEXT_PRIMARY};
            border: none;
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.index)

    def enterEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 12px;
                border: 2px solid {self.default_color};
            }}
        """)
        self.label.setStyleSheet(f"""
            font-size: 20px; 
            font-weight: bold; 
            color: {self.default_color};
            border: none;
        """)

    def leaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Theme.SURFACE};
                border-radius: 12px;
                border: 1px solid {Theme.BORDER};
            }}
        """)
        self.label.setStyleSheet(f"""
            font-size: 20px; 
            font-weight: bold; 
            color: {Theme.TEXT_PRIMARY};
            border: none;
        """)

class Dashboard(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Welcome Section
        welcome = QLabel("Executive Dashboard")
        welcome.setStyleSheet(f"font-size: 32px; color: {Theme.PRIMARY}; font-weight: 800;")
        layout.addWidget(welcome)
        
        self.pending_label = QLabel("Overview of Case Statistics")
        self.pending_label.setStyleSheet(f"font-size: 16px; color: {Theme.TEXT_SECONDARY};")
        layout.addWidget(self.pending_label)
        
        layout.addSpacing(20)

        # Placeholder for Graphs
        placeholder_frame = QFrame()
        placeholder_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #bdc3c7;
                border-radius: 10px;
                background-color: #f8f9fa;
            }
        """)
        frame_layout = QVBoxLayout(placeholder_frame)
        
        info_label = QLabel("Analytics & Reporting Module")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #95a5a6;")
        frame_layout.addWidget(info_label)
        
        sub_label = QLabel("Interactive Graphs and Charts will be displayed here in the next update.")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        frame_layout.addWidget(sub_label)
        
        layout.addWidget(placeholder_frame)
        
    def refresh_counts(self):
        # Placeholder for future data refresh
        pass
