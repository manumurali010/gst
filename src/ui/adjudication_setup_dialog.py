from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QRadioButton, 
                             QButtonGroup, QPushButton, QHBoxLayout, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt

class AdjudicationSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adjudication Case Setup")
        self.setFixedWidth(500)
        self.setModal(True)
        self.selected_section = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        lbl_title = QLabel("Initial Adjudication Setup")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel("This case originated from a finalised ASMT-10. Before proceeding with SCN drafting, please select the applicable section for adjudication.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #475569; margin-bottom: 10px;")
        layout.addWidget(lbl_desc)
        
        # Section Selection
        sec_group_box = QVBoxLayout()
        self.sec_group = QButtonGroup(self)
        
        self.rb_73 = QRadioButton("Section 73 (Non-Fraud / Normal Period)")
        self.rb_74 = QRadioButton("Section 74 (Fraud / Extended Period)")
        self.rb_74a = QRadioButton("Section 74A (Common Period - FY 2024-25 onwards)")
        
        self.sec_group.addButton(self.rb_73, 73)
        self.sec_group.addButton(self.rb_74, 74)
        self.sec_group.addButton(self.rb_74a, 740) # Use 740 as int ID
        
        sec_group_box.addWidget(self.rb_73)
        sec_group_box.addWidget(self.rb_74)
        sec_group_box.addWidget(self.rb_74a)
        layout.addLayout(sec_group_box)
        
        # Remarks (Optional)
        layout.addWidget(QLabel("Remarks (Optional):"))
        self.remarks_edit = QTextEdit()
        self.remarks_edit.setFixedHeight(60)
        self.remarks_edit.setPlaceholderText("Enter any internal notes regarding section selection...")
        layout.addWidget(self.remarks_edit)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_confirm = QPushButton("Confirm & Initialize Case")
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; color: white; border: none;
                padding: 8px 16px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.btn_confirm.clicked.connect(self.validate_and_accept)
        
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)
        
    def validate_and_accept(self):
        selected_id = self.sec_group.checkedId()
        if selected_id == -1:
            QMessageBox.warning(self, "Selection Required", "Please select an adjudication section.")
            return
            
        if selected_id == 73: self.selected_section = "73"
        elif selected_id == 74: self.selected_section = "74"
        elif selected_id == 740: self.selected_section = "74A"
        
        self.accept()
