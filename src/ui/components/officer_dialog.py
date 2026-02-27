from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt

class OfficerDialog(QDialog):
    def __init__(self, parent=None, officer_data=None):
        super().__init__(parent)
        self.officer_data = officer_data
        self.is_edit = bool(officer_data)
        
        title = "Edit Officer" if self.is_edit else "Add New Officer"
        self.setWindowTitle(title)
        self.setFixedSize(450, 300)
        self.init_ui()
        
        if self.is_edit:
            self.populate_data()
            
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Officer Details")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., John Doe")
        self.name_input.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.designation_input = QLineEdit()
        self.designation_input.setPlaceholderText("e.g., Assistant Commissioner")
        self.designation_input.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.jurisdiction_input = QLineEdit()
        self.jurisdiction_input.setPlaceholderText("e.g., Ernakulam")
        self.jurisdiction_input.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.office_input = QLineEdit()
        self.office_input.setPlaceholderText("e.g., State GST Bhavan")
        self.office_input.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        form_layout.addRow("Name *:", self.name_input)
        form_layout.addRow("Designation :", self.designation_input)
        form_layout.addRow("Jurisdiction :", self.jurisdiction_input)
        form_layout.addRow("Office Address :", self.office_input)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Save Officer")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet('''
            QPushButton {
                background-color: #27ae60; color: white; padding: 8px 16px; 
                border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2ecc71; }
        ''')
        self.btn_save.clicked.connect(self.validate_and_accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        
    def populate_data(self):
        self.name_input.setText(self.officer_data.get('name', ''))
        self.designation_input.setText(self.officer_data.get('designation', ''))
        self.jurisdiction_input.setText(self.officer_data.get('jurisdiction', ''))
        self.office_input.setText(self.officer_data.get('office_address', ''))
        
    def validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Officer Name is required.")
            return
            
        self.accept()
        
    def get_data(self):
        """Returns the dictionary payload for DB operations"""
        return {
            "name": self.name_input.text().strip(),
            "designation": self.designation_input.text().strip() or None,
            "jurisdiction": self.jurisdiction_input.text().strip() or None,
            "office_address": self.office_input.text().strip() or None
        }
