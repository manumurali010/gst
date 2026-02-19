from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QLineEdit, QStackedWidget, QMessageBox, QFrame, QGridLayout, QCompleter, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, pyqtSignal
from src.database.db_manager import DatabaseManager
import datetime

class CaseInitiationWizard(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        self.navigate_callback = navigate_callback
        self.db = DatabaseManager()
        self.db.init_sqlite()
        
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Start New Proceeding")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)
        
        # Main Content Area (Split into Form and Preview)
        content_layout = QHBoxLayout()
        
        # Left Side: Form
        form_container = QFrame()
        form_container.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #e0e0e0;")
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. GSTIN Input (Top for auto-fetch)
        gstin_group = QVBoxLayout()
        gstin_lbl = QLabel("GSTIN")
        gstin_lbl.setStyleSheet("font-weight: bold; color: #34495e;")
        self.gstin_input = QLineEdit()
        self.gstin_input.setPlaceholderText("Enter 15-digit GSTIN")
        self.gstin_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")
        
        # 1.5 Case Type Selection (New for Direct Adjudication)
        type_group = QVBoxLayout()
        type_lbl = QLabel("Case Type")
        type_lbl.setStyleSheet("font-weight: bold; color: #34495e;")
        
        self.type_btn_group = QButtonGroup(self)
        self.radio_scrutiny = QRadioButton("Scrutiny (ASMT-10)")
        self.radio_adjudication = QRadioButton("Direct Adjudication")
        self.radio_scrutiny.setChecked(True) # Default
        
        self.type_btn_group.addButton(self.radio_scrutiny)
        self.type_btn_group.addButton(self.radio_adjudication)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(self.radio_scrutiny)
        type_layout.addWidget(self.radio_adjudication)
        type_layout.addStretch()
        
        type_group.addWidget(type_lbl)
        type_group.addLayout(type_layout)
        form_layout.addLayout(type_group)
        
        # Auto-complete
        all_gstins = self.db.get_all_gstins()
        completer = QCompleter(all_gstins)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.gstin_input.setCompleter(completer)
        
        self.gstin_input.textChanged.connect(self.on_gstin_changed)
        gstin_group.addWidget(gstin_lbl)
        gstin_group.addWidget(self.gstin_input)
        form_layout.addLayout(gstin_group)
        
        # 2. Financial Year
        fy_group = QVBoxLayout()
        fy_lbl = QLabel("Financial Year")
        fy_lbl.setStyleSheet("font-weight: bold; color: #34495e;")
        self.fy_combo = QComboBox()
        self.fy_combo.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")
        current_year = datetime.date.today().year
        self.fy_combo.addItem("Select FY", "")
        for i in range(2017, current_year + 1):
            self.fy_combo.addItem(f"{i}-{str(i+1)[-2:]}")
        fy_group.addWidget(fy_lbl)
        fy_group.addWidget(self.fy_combo)
        form_layout.addLayout(fy_group)
        
        # 3. Section
        sec_group = QVBoxLayout()
        sec_lbl = QLabel("Initiating Section")
        sec_lbl.setStyleSheet("font-weight: bold; color: #34495e;")
        self.section_combo = QComboBox()
        self.section_combo.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px;")
        self.section_combo.addItems(["Select Section", "73", "74", "74A", "122", "125", "Other"])
        self.section_combo.currentTextChanged.connect(self.on_section_changed)
        sec_group.addWidget(sec_lbl)
        sec_group.addWidget(self.section_combo)
        
        self.other_section_input = QLineEdit()
        self.other_section_input.setPlaceholderText("Enter Section manually")
        self.other_section_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px; margin-top: 5px;")
        self.other_section_input.setVisible(False)
        sec_group.addWidget(self.other_section_input)
        form_layout.addLayout(sec_group)
        
        
        form_layout.addStretch()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create Proceeding")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; 
                color: white; 
                font-weight: bold; 
                padding: 10px 20px; 
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.create_btn.clicked.connect(self.create_proceeding)
        btn_layout.addStretch()
        btn_layout.addWidget(self.create_btn)
        form_layout.addLayout(btn_layout)
        
        content_layout.addWidget(form_container, 1) # Stretch factor 1
        
        # Right Side: Taxpayer Preview
        self.preview_container = QFrame()
        self.preview_container.setStyleSheet("background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e0e0e0;")
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        
        preview_title = QLabel("Taxpayer Details")
        preview_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
        preview_layout.addWidget(preview_title)
        
        self.tp_details_lbl = QLabel("Enter GSTIN to fetch details...")
        self.tp_details_lbl.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        self.tp_details_lbl.setWordWrap(True)
        self.tp_details_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        preview_layout.addWidget(self.tp_details_lbl)
        
        preview_layout.addStretch()
        
        content_layout.addWidget(self.preview_container, 1) # Stretch factor 1
        
        self.layout.addLayout(content_layout)
        
        # State
        self.taxpayer_data = {}

    def on_section_changed(self, text):
        self.other_section_input.setVisible(text == "Other")

    def on_gstin_changed(self, text):
        text = text.strip().upper()
        if len(text) == 15:
            self.fetch_gstin_details(text)
        else:
            self.taxpayer_data = {}
            self.tp_details_lbl.setText("Enter valid 15-digit GSTIN...")
            
    def fetch_gstin_details(self, gstin):
        taxpayer = self.db.get_taxpayer(gstin)
        if taxpayer:
            self.taxpayer_data = taxpayer
            info = f"""
            <div style='font-size: 14px; line-height: 1.6;'>
                <b>Legal Name:</b><br>{taxpayer.get('Legal Name', 'N/A')}<br><br>
                <b>Trade Name:</b><br>{taxpayer.get('Trade Name', 'N/A')}<br><br>
                <b>Address:</b><br>{taxpayer.get('Address', 'N/A')}<br><br>
                <b>Status:</b><br><span style='color: green;'>Active</span>
            </div>
            """
            self.tp_details_lbl.setText(info)
        else:
            self.taxpayer_data = {}
            self.tp_details_lbl.setText(f"<span style='color: red;'>Taxpayer not found for GSTIN: {gstin}</span><br>Please enter details manually in the workspace.")

    def create_proceeding(self):
        # Validation
        gstin = self.gstin_input.text().strip().upper()
        if not gstin or len(gstin) != 15:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid 15-digit GSTIN.")
            return
            
        fy = self.fy_combo.currentText()
        if not fy or fy == "Select FY":
            QMessageBox.warning(self, "Validation Error", "Please select a Financial Year.")
            return
            
        section = self.section_combo.currentText()
        if section == "Select Section":
            QMessageBox.warning(self, "Validation Error", "Please select an Initiating Section.")
            return
        if section == "Other":
            section = self.other_section_input.text().strip()
            if not section:
                QMessageBox.warning(self, "Validation Error", "Please enter the Section manually.")
                return
                
        # Form type is not needed - user will select document type later in workspace

        # Prepare Data
        source_type = 'SCRUTINY' if self.radio_scrutiny.isChecked() else 'ADJUDICATION'
        
        data = {
            "gstin": gstin,
            "financial_year": fy,
            "initiating_section": section,
            "section": section, # Mapped for Adjudication
            "taxpayer_details": self.taxpayer_data,
            "status": "Draft",
            "legal_name": self.taxpayer_data.get('Legal Name', ''),
            "trade_name": self.taxpayer_data.get('Trade Name', ''),
            "address": self.taxpayer_data.get('Address', '')
        }
        
        # Create in DB
        pid = self.db.create_proceeding(data, source_type=source_type)
        
        if pid:
            QMessageBox.information(self, "Success", "Case initiated successfully!")
            self.navigate_callback("workspace", pid)
        else:
            QMessageBox.critical(self, "Error", "Failed to initiate case.")
