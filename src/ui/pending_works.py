from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QListWidget, QListWidgetItem, QMessageBox)
from src.database.db_manager import DatabaseManager

class PendingWorksTab(QWidget):
    def __init__(self, home_callback, resume_callback):
        super().__init__()
        self.home_callback = home_callback
        self.resume_callback = resume_callback
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("Pending / Draft Cases")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(header)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.resume_item)
        layout.addWidget(self.list_widget)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(refresh_btn)
        
        self.load_data()

    def load_data(self):
        self.list_widget.clear()
        pending = self.db.get_pending_cases()
        
        if not pending:
            self.list_widget.addItem("No pending cases found.")
            return
            
        for case in pending:
            item_text = f"{case.get('Date')} - {case.get('GSTIN')} - {case.get('Form Type')}"
            item = QListWidgetItem(item_text)
            item.setData(32, case) # Store full case data
            self.list_widget.addItem(item)

    def resume_item(self, item):
        case_data = item.data(32)
        if case_data:
            # Logic to resume would go here
            # For now, just show info
            QMessageBox.information(self, "Resume Case", f"Resuming case for {case_data.get('GSTIN')}")
            # self.resume_callback(case_data) # If implemented
