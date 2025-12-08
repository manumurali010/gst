from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, 
                             QSpacerItem, QSizePolicy, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QColor

class SidebarButton(QPushButton):
    def __init__(self, text, icon_char, index, callback):
        super().__init__()
        self.index = index
        self.callback = callback
        self.text_label = text
        self.icon_char = icon_char
        
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        
        # Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 0, 0)
        self.layout.setSpacing(15)
        
        # Icon (Text-based for now, can be replaced with QIcon)
        self.icon_label = QLabel(self.icon_char)
        self.icon_label.setFixedSize(30, 30)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.icon_label)
        
        # Text
        self.lbl = QLabel(text)
        self.lbl.setStyleSheet("font-size: 14px; font-weight: 500;")
        self.layout.addWidget(self.lbl)
        
        self.layout.addStretch()
        
        self.clicked.connect(self.on_click)
        
        # Initial Style
        self.update_style(False)

    def on_click(self):
        self.callback(self.index)

    def setChecked(self, checked):
        super().setChecked(checked)
        self.update_style(checked)

    def update_style(self, checked):
        if checked:
            bg = "#34495e"
            color = "#ffffff"
            border = "#3498db"
        else:
            bg = "transparent"
            color = "#ecf0f1"
            border = "transparent"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: none;
                border-left: 4px solid {border};
            }}
        """)
        self.lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        self.icon_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; border: none; background: transparent;")

class Sidebar(QFrame):
    # Signals
    navigate_signal = pyqtSignal(int) # For Global Navigation
    action_signal = pyqtSignal(str)   # For Case Workflow Actions (e.g., "summary", "scn")
    
    def __init__(self):
        super().__init__()
        self.setFixedWidth(250)
        self.setStyleSheet("background-color: #2c3e50; border-right: 1px solid #1a252f;")
        
        self.is_expanded = True
        self.current_mode = "global" # or "case"
        self.buttons = []
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header (Hamburger + Title)
        self.create_header()
        
        # Content Area for Buttons
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 10, 0, 0)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.content_widget)
        
        self.layout.addStretch()
        
        # Footer
        self.create_footer()
        
        # Initialize Global Menu
        self.set_mode("global")

    def create_header(self):
        self.header = QFrame()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet("background-color: #1a252f;")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        # Hamburger Button
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 20px;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #34495e;
                border-radius: 5px;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.toggle_btn)
        
        # Title
        self.title_lbl = QLabel("GST DESK")
        self.title_lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold; margin-left: 10px;")
        header_layout.addWidget(self.title_lbl)
        
        header_layout.addStretch()
        self.layout.addWidget(self.header)

    def create_footer(self):
        self.footer = QFrame()
        self.footer.setFixedHeight(50)
        self.footer.setStyleSheet("background-color: #1a252f;")
        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.ver_label = QLabel("v1.0")
        self.ver_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        footer_layout.addWidget(self.ver_label)
        
        self.layout.addWidget(self.footer)

    def toggle_sidebar(self):
        if self.is_expanded:
            # Collapse
            self.setFixedWidth(70)
            self.title_lbl.hide()
            self.ver_label.hide()
            for btn in self.buttons:
                btn.lbl.hide()
                btn.layout.setContentsMargins(0,0,0,0)
                btn.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.is_expanded = False
        else:
            # Expand
            self.setFixedWidth(250)
            self.title_lbl.show()
            self.ver_label.show()
            for btn in self.buttons:
                btn.lbl.show()
                btn.layout.setContentsMargins(10,0,0,0)
                btn.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.is_expanded = True

    def clear_buttons(self):
        for btn in self.buttons:
            self.content_layout.removeWidget(btn)
            btn.deleteLater()
        self.buttons = []

    def set_mode(self, mode):
        self.current_mode = mode
        self.clear_buttons()
        
        if mode == "global":
            self.title_lbl.setText("GST DESK")
            items = [
                ("Home", "🏠", 0),
                ("Adjudication", "⚖️", 2),
                ("Reports", "📊", 3),
                ("Pending Works", "⏳", 4),
                ("Case Register", "📁", 5),
                ("GST Handbook", "📘", 6),
                ("Mail Merge", "📧", 7),
                ("Templates", "📝", 8),
                ("Developer", "🛠️", 9)
            ]
            for text, icon, idx in items:
                self.add_button(text, icon, idx, self.handle_global_click)
                
        elif mode == "case":
            self.title_lbl.setText("CASE WORK")
            # Add "Back to Global" button
            self.add_button("Back to Home", "⬅️", -1, self.handle_back_click)
            
            items = [
                ("Summary", "📋", "summary"),
                ("DRC-01A", "📝", "drc01a"),
                ("SCN", "📜", "scn"),
                ("PH Intimation", "📅", "ph"),
                ("Order", "⚖️", "order"),
                ("Documents", "📂", "documents"),
                ("Timeline", "⏱️", "timeline")
            ]
            for text, icon, action in items:
                self.add_button(text, icon, action, self.handle_case_click)
        
        # Re-apply collapsed state if needed
        if not self.is_expanded:
            self.is_expanded = True # Reset to expand to apply changes properly
            self.toggle_sidebar() # Then collapse again

    def add_button(self, text, icon, index, callback):
        btn = SidebarButton(text, icon, index, callback)
        self.content_layout.addWidget(btn)
        self.buttons.append(btn)

    def handle_global_click(self, index):
        self.set_active_btn(index)
        self.navigate_signal.emit(index)

    def handle_case_click(self, action):
        self.set_active_btn(action)
        self.action_signal.emit(action)
        
    def handle_back_click(self, _):
        self.set_mode("global")
        self.navigate_signal.emit(0) # Go to Home

    def set_active_btn(self, index_or_action):
        for btn in self.buttons:
            if btn.index == index_or_action:
                btn.setChecked(True)
            else:
                btn.setChecked(False)
