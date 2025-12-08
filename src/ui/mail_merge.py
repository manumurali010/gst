from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTextEdit, QSplitter, QFrame, QHeaderView, QCheckBox, 
                             QAbstractItemView, QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QDate
from src.database.db_manager import DatabaseManager
import datetime

class MailMergeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Splitter for Left (Config) and Right (Content)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # ================= LEFT PANEL =================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # 1. Communication Type
        left_layout.addWidget(QLabel("<b>Form of Communication:</b>"))
        self.comm_type_combo = QComboBox()
        self.comm_type_combo.addItems([
            "Letter", "PH Intimation", "Reminder", "Trade Notice", "Public Notice", "Summon"
        ])
        self.comm_type_combo.currentTextChanged.connect(self.load_template)
        left_layout.addWidget(self.comm_type_combo)
        
        # 2. OC Details
        oc_group = QFrame()
        oc_group.setFrameShape(QFrame.Shape.StyledPanel)
        oc_layout = QVBoxLayout(oc_group)
        
        oc_layout.addWidget(QLabel("<b>OC Details:</b>"))
        
        oc_row = QHBoxLayout()
        self.oc_number_input = QLineEdit()
        self.oc_number_input.setPlaceholderText("OC Number")
        oc_row.addWidget(QLabel("OC No:"))
        oc_row.addWidget(self.oc_number_input)
        
        self.oc_date_input = QLineEdit()
        self.oc_date_input.setText(QDate.currentDate().toString("dd/MM/yyyy"))
        self.oc_date_input.setReadOnly(True)
        oc_row.addWidget(QLabel("Date:"))
        oc_row.addWidget(self.oc_date_input)
        
        oc_layout.addLayout(oc_row)
        left_layout.addWidget(oc_group)
        
        # 3. Taxpayer Selection
        left_layout.addWidget(QLabel("<b>Select Taxpayers:</b>"))
        
        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search GSTIN or Name...")
        self.search_input.textChanged.connect(self.filter_taxpayers)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        # Table
        self.taxpayer_table = QTableWidget()
        self.taxpayer_table.setColumnCount(4)
        self.taxpayer_table.setHorizontalHeaderLabels(["Select", "GSTIN", "Legal Name", "Trade Name"])
        self.taxpayer_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.taxpayer_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.taxpayer_table.verticalHeader().setVisible(False)
        self.taxpayer_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        left_layout.addWidget(self.taxpayer_table)
        
        # Load Taxpayers Button
        load_btn = QPushButton("Reload Taxpayers")
        load_btn.clicked.connect(self.load_taxpayers)
        left_layout.addWidget(load_btn)
        
        splitter.addWidget(left_widget)
        
        # ================= RIGHT PANEL =================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        # Editor Header
        right_layout.addWidget(QLabel("<b>Communication Content:</b>"))
        
        # Placeholders Toolbar
        placeholder_layout = QHBoxLayout()
        placeholders = ["{{Legal Name}}", "{{Trade Name}}", "{{GSTIN}}", "{{Address}}", "{{Email}}", "{{OC No}}", "{{Date}}"]
        for ph in placeholders:
            btn = QPushButton(ph)
            btn.setFlat(True)
            btn.setStyleSheet("color: #2980b9; font-weight: bold;")
            btn.clicked.connect(lambda checked, text=ph: self.insert_placeholder(text))
            placeholder_layout.addWidget(btn)
        placeholder_layout.addStretch()
        right_layout.addLayout(placeholder_layout)
        
        # Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Draft your communication here...")
        right_layout.addWidget(self.editor)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview (First Recipient)")
        self.preview_btn.clicked.connect(self.preview_document)
        action_layout.addWidget(self.preview_btn)
        
        action_layout.addStretch()
        
        self.generate_btn = QPushButton("Generate & Save to OC Register")
        self.generate_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        self.generate_btn.clicked.connect(self.generate_documents)
        action_layout.addWidget(self.generate_btn)
        
        right_layout.addLayout(action_layout)
        
        splitter.addWidget(right_widget)
        
        # Set Splitter Ratios (40% Left, 60% Right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        
        main_layout.addWidget(splitter)
        
        # Initial Load
        self.load_taxpayers()
        self.load_template("Letter") # Default template

    def load_taxpayers(self):
        """Load taxpayers from database into table"""
        taxpayers = self.db.search_taxpayers("") # Get all
        self.taxpayer_table.setRowCount(len(taxpayers))
        
        for i, tp in enumerate(taxpayers):
            # Checkbox
            chk = QCheckBox()
            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.addWidget(chk)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            self.taxpayer_table.setCellWidget(i, 0, cell_widget)
            
            self.taxpayer_table.setItem(i, 1, QTableWidgetItem(str(tp.get('GSTIN', ''))))
            self.taxpayer_table.setItem(i, 2, QTableWidgetItem(str(tp.get('Legal Name', ''))))
            self.taxpayer_table.setItem(i, 3, QTableWidgetItem(str(tp.get('Trade Name', ''))))
            
            # Store full data in user role of GSTIN item
            self.taxpayer_table.item(i, 1).setData(Qt.ItemDataRole.UserRole, tp)

    def filter_taxpayers(self, text):
        """Filter rows based on search text"""
        text = text.lower()
        for row in range(self.taxpayer_table.rowCount()):
            gstin = self.taxpayer_table.item(row, 1).text().lower()
            name = self.taxpayer_table.item(row, 2).text().lower()
            match = text in gstin or text in name
            self.taxpayer_table.setRowHidden(row, not match)

    def insert_placeholder(self, text):
        """Insert placeholder at cursor position"""
        self.editor.insertPlainText(text)
        self.editor.setFocus()

    def load_template(self, comm_type):
        """Load default template for communication type"""
        # TODO: Load actual HTML templates
        templates = {
            "Letter": "To,\n{{Legal Name}}\n{{Address}}\n\nSubject: General Correspondence\n\nDear Sir/Madam,\n\n[Content Here]\n\nYours Faithfully,\nSuperintendent",
            "PH Intimation": """
<p><strong>O.C.NO. {{OC No}} <span style="float:right">Date: {{Date}}</span></strong></p>
<p>To,</p>
<p>{{Legal Name}}</p>
<p>{{Trade Name}}</p>
<p>{{GSTIN}}</p>
<p>{{Address}}</p>
<br>
<p>Gentlemen/Sir/Madam,</p>
<br>
<p style="text-align:center"><strong>Subject: Intimation of Personal Hearings – reg</strong></p>
<br>
<p>References: 1. SCN reference number: [SCN No] dated [SCN Date]</p>
<br>
<ol>
<li>Please refer to the above mentioned SCN number issued by Office of the [Office Name].</li>
<li>In this connection, it is to inform you that personal hearing in this case will be held at [Time] on [Date] before the [Officer Designation], [Office Address].</li>
<li>You may therefore appear in person or through an authorized representative for the personal hearing on the above mentioned date and time as per your convenience, at the above mentioned address, without fail along with records/documents/evidences, you wish to rely upon in support of your case.</li>
</ol>
<br>
<br>
<p>Copy submitted to:</p>
<p>[Copy To]</p>
""",
            "Reminder": "To,\n{{Legal Name}}\n\nSubject: Reminder\n\nThis is to remind you regarding...",
            "Trade Notice": "TRADE NOTICE\n\nTo All Taxpayers,\n\n...",
            "Public Notice": "PUBLIC NOTICE\n\n...",
            "Summon": "SUMMON\nTo,\n{{Legal Name}}\n\nWhereas your attendance is required..."
        }
        self.editor.setText(templates.get(comm_type, ""))

    def get_selected_taxpayers(self):
        """Return list of selected taxpayer data"""
        selected = []
        for row in range(self.taxpayer_table.rowCount()):
            if self.taxpayer_table.isRowHidden(row):
                continue
                
            cell_widget = self.taxpayer_table.cellWidget(row, 0)
            chk = cell_widget.findChild(QCheckBox)
            if chk and chk.isChecked():
                # Retrieve data stored in GSTIN item
                data = self.taxpayer_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                selected.append(data)
        return selected

    def preview_document(self):
        """Show preview for the first selected taxpayer"""
        selected = self.get_selected_taxpayers()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one taxpayer.")
            return
            
        recipient = selected[0]
        content = self.editor.toPlainText() # Or toHtml()
        filled_content = self.fill_placeholders(content, recipient)
        
        # Simple preview dialog
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setText(filled_content)
        preview.setWindowTitle(f"Preview for {recipient.get('Legal Name')}")
        preview.resize(600, 800)
        preview.show()
        # Keep reference to avoid garbage collection
        self._preview_window = preview

    def fill_placeholders(self, content, data):
        """Replace placeholders with data"""
        replacements = {
            "{{Legal Name}}": data.get('Legal Name', ''),
            "{{Trade Name}}": data.get('Trade Name', ''),
            "{{GSTIN}}": data.get('GSTIN', ''),
            "{{Address}}": data.get('Address', ''),
            "{{Email}}": data.get('Email', ''),
            "{{OC No}}": self.oc_number_input.text(),
            "{{Date}}": self.oc_date_input.text()
        }
        
        for key, value in replacements.items():
            content = content.replace(key, str(value))
        return content

    def generate_documents(self):
        """Generate documents and save to OC Register"""
        selected = self.get_selected_taxpayers()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one taxpayer.")
            return
            
        oc_no = self.oc_number_input.text()
        if not oc_no:
            QMessageBox.warning(self, "Missing OC No", "Please enter an OC Number.")
            return
            
        comm_type = self.comm_type_combo.currentText()
        
        count = 0
        for recipient in selected:
            # 1. Generate Content (In real app, save PDF here)
            content = self.editor.toPlainText()
            filled_content = self.fill_placeholders(content, recipient)
            
            # 2. Save to OC Register
            # We use create_case_file to add a generic entry
            entry_data = {
                "OC_Number": oc_no,
                "OC_Content": comm_type,
                "OC_Date": self.oc_date_input.text(),
                "OC_To": f"{recipient.get('Legal Name')}, {recipient.get('GSTIN')}",
                "OC_Copy_To": "", # Could add input for this
                "GSTIN": recipient.get('GSTIN', ''),
                "Legal Name": recipient.get('Legal Name', ''),
                "Trade Name": recipient.get('Trade Name', ''),
                "Status": "Generated (Mail Merge)",
                "Section": "General", # Placeholder
                # Add other fields as empty
            }
            
            self.db.create_case_file(entry_data)
            count += 1
            
        QMessageBox.information(self, "Success", f"Successfully generated {count} documents and updated OC Register.")
