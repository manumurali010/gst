from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt
from src.ui.developer.issue_manager import IssueManager
from src.ui.developer.logic_lab import LogicLab
# from src.ui.developer.table_builder import TableBuilder # Uncomment when ready

class DeveloperConsole(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background: #2c3e50; border-radius: 5px;")
        header_layout = QHBoxLayout(header)
        
        title = QLabel("Developer Console")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; top: -1px; }
            QTabBar::tab {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                padding: 10px 20px;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                font-weight: bold;
            }
        """)
        
        # 1. Issue Manager
        self.issue_manager = IssueManager()
        self.tabs.addTab(self.issue_manager, "Issue Templates")
        
        # 2. Logic Lab (New)
        self.logic_lab = LogicLab()
        self.tabs.addTab(self.logic_lab, "Logic Lab")
        
        # 3. Table Builder (Placeholder/Existing)
        # self.tabs.addTab(TableBuilder(), "Table Builder")
        
        layout.addWidget(self.tabs)
