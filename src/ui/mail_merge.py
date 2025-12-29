from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTextEdit, QSplitter, QFrame, QHeaderView, QCheckBox, 
                             QAbstractItemView, QMessageBox, QProgressBar, QFileDialog)
from PyQt6.QtCore import Qt, QDate
from src.database.db_manager import DatabaseManager
from src.ui.rich_text_editor import RichTextEditor
from src.utils.config_manager import ConfigManager
from src.services.asmt10_generator import ASMT10Generator
import datetime
import os

class MailMergeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.db.init_sqlite() # Ensure DB is ready
        self.config = ConfigManager()
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
        self.oc_number_input.setPlaceholderText("Format: No./Year")
        
        self.oc_suggest_btn = QPushButton("Get Next")
        self.oc_suggest_btn.setStyleSheet("padding: 2px 8px; background-color: #3498db; color: white; border-radius: 4px; font-size: 10px;")
        self.oc_suggest_btn.clicked.connect(lambda: self.suggest_next_oc(self.oc_number_input))
        
        oc_row.addWidget(QLabel("OC No:"))
        oc_row.addWidget(self.oc_number_input)
        oc_row.addWidget(self.oc_suggest_btn)
        
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
        btn_row = QHBoxLayout()
        load_btn = QPushButton("Reload Taxpayers")
        load_btn.clicked.connect(self.load_taxpayers)
        btn_row.addWidget(load_btn)
        
        self.select_all_chk = QCheckBox("Select All")
        self.select_all_chk.stateChanged.connect(self.toggle_select_all)
        btn_row.addWidget(self.select_all_chk)
        left_layout.addLayout(btn_row)
        
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
        self.editor = RichTextEditor(placeholder="Draft your communication here...")
        right_layout.addWidget(self.editor)
        
        # Output Folder Selection
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select output folder...")
        if not os.path.exists(os.path.join(os.getcwd(), "output", "mail_merge")):
            os.makedirs(os.path.join(os.getcwd(), "output", "mail_merge"), exist_ok=True)
        self.folder_input.setText(os.path.join(os.getcwd(), "output", "mail_merge"))
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(QLabel("Output Folder:"))
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_btn)
        right_layout.addLayout(folder_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        right_layout.addWidget(self.progress_bar)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview (First Recipient)")
        self.preview_btn.clicked.connect(self.preview_document)
        self.preview_btn.setMinimumHeight(35)
        action_layout.addWidget(self.preview_btn)
        
        action_layout.addStretch()
        
        self.generate_btn = QPushButton("Generate & Save to OC Register")
        self.generate_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px 20px; font-size: 14px;")
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
            
    def toggle_select_all(self, state):
        """Select/deselect all visible taxpayers"""
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.taxpayer_table.rowCount()):
            if not self.taxpayer_table.isRowHidden(row):
                cell_widget = self.taxpayer_table.cellWidget(row, 0)
                if cell_widget:
                    chk = cell_widget.findChild(QCheckBox)
                    if chk:
                        chk.setChecked(checked)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.folder_input.setText(folder)

    def insert_placeholder(self, text):
        """Insert placeholder at cursor position"""
        self.editor.insertHtml(f"<b>{text}</b>")
        self.editor.setFocus()

    def load_template(self, comm_type):
        """Load template for communication type from DB or fallbacks"""
        try:
            # Query templates from SQLite
            with self.db._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT content FROM templates WHERE type = ? OR name LIKE ? LIMIT 1", 
                             (comm_type, f"%{comm_type}%"))
                row = cursor.fetchone()
                if row:
                    self.editor.setHtml(row[0])
                    return
        except Exception as e:
            print(f"Error loading template from DB: {e}")

        # Fallback Hardcoded Templates
        templates = {
            "Letter": "To,<br>{{Legal Name}}<br>{{Address}}<br><br>Subject: General Correspondence<br><br>Dear Sir/Madam,<br><br>[Content Here]<br><br>Yours Faithfully,<br>Superintendent",
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
<p>1. Please refer to the above mentioned SCN number issued by Office of the [Office Name].</p>
<p>2. In this connection, it is to inform you that personal hearing in this case will be held at [Time] on [Date] before the [Officer Designation], [Office Address].</p>
<p>3. You may therefore appear in person or through an authorized representative for the personal hearing on the above mentioned date and time as per your convenience, at the above mentioned address, without fail along with records/documents/evidences, you wish to rely upon in support of your case.</p>
<br>
<br>
<p>Copy submitted to:</p>
<p>[Copy To]</p>
""",
            "Reminder": "To,<br>{{Legal Name}}<br><br>Subject: Reminder<br><br>This is to remind you regarding...",
            "Trade Notice": "TRADE NOTICE<br><br>To All Taxpayers,<br><br>...",
            "Public Notice": "PUBLIC NOTICE<br><br>...",
            "Summon": "SUMMON<br>To,<br>{{Legal Name}}<br><br>Whereas your attendance is required..."
        }
        self.editor.setHtml(templates.get(comm_type, ""))

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
        """Show preview for the first selected taxpayer using the professional generator"""
        selected = self.get_selected_taxpayers()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one taxpayer.")
            return
            
        recipient = selected[0]
        # 1. Get Editor Content
        content = self.editor.toHtml()
        
        # 2. Fill Placeholders
        filled_content = self.fill_placeholders(content, recipient)
        
        # 3. Inject Letterhead
        lh_path = self.config.get_letterhead_path('pdf')
        lh_content = ""
        if os.path.exists(lh_path):
            with open(lh_path, 'r', encoding='utf-8') as f:
                import re
                full_lh = f.read()
                match = re.search(r"<body[^>]*>(.*?)</body>", full_lh, re.DOTALL | re.IGNORECASE)
                lh_content = match.group(1) if match else full_lh

        # 4. Wrap with letterhead and A4 styling (like ASMT10Generator)
        final_html = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 15mm; }}
                body {{ font-family: 'Bookman Old Style', serif; font-size: 11pt; }}
                .page-container {{ width: 210mm; margin: 0 auto; background: white; }}
                .justify-text {{ text-align: justify; }}
            </style>
        </head>
        <body>
            <div class="page-container">
                <div class="letterhead">{lh_content}</div>
                <div class="content" style="margin-top:20px;">
                    {filled_content}
                </div>
            </div>
        </body>
        </html>
        """
        
        # 5. Show in a professional preview (using internal mechanism)
        from src.utils.preview_generator import PreviewGenerator
        img_bytes = PreviewGenerator.generate_preview_image(final_html)
        if img_bytes:
            pixmap = PreviewGenerator.get_qpixmap_from_bytes(img_bytes)
            preview_dialog = QLabel()
            preview_dialog.setPixmap(pixmap)
            preview_dialog.setWindowTitle(f"Preview: {recipient.get('Legal Name')}")
            preview_dialog.show()
            self._preview = preview_dialog
        else:
            QMessageBox.critical(self, "Error", "Failed to generate preview.")

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
        """Generate Actual PDF documents and save to OC Register"""
        selected = self.get_selected_taxpayers()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one taxpayer.")
            return
            
        oc_no_base = self.oc_number_input.text()
        if not oc_no_base:
            QMessageBox.warning(self, "Missing OC No", "Please enter an OC Number.")
            return
            
        output_dir = self.folder_input.text()
        if not output_dir or not os.path.exists(output_dir):
            if not os.path.exists(output_dir):
                 os.makedirs(output_dir, exist_ok=True)
            else:
                QMessageBox.warning(self, "Invalid Folder", "Please select a valid output folder.")
                return

        comm_type = self.comm_type_combo.currentText()
        content_template = self.editor.toHtml()
        
        # UI Feedback
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)
        
        count = 0
        errors = []
        
        # Load Letterhead
        lh_path = self.config.get_letterhead_path('pdf')
        lh_content = ""
        if os.path.exists(lh_path):
            with open(lh_path, 'r', encoding='utf-8') as f:
                import re
                full_lh = f.read()
                match = re.search(r"<body[^>]*>(.*?)</body>", full_lh, re.DOTALL | re.IGNORECASE)
                lh_content = match.group(1) if match else full_lh

        for i, recipient in enumerate(selected):
            try:
                # 1. Generate OC No (If multiple, we might want to suffix or just use same)
                current_oc_no = oc_no_base
                if len(selected) > 1 and "/" in oc_no_base:
                    # Optional: Could add automatic numbering here
                    pass

                # 2. Fill Placeholders
                filled_content = self.fill_placeholders(content_template, recipient)
                
                # 3. Final HTML
                final_html = f"""
                <html>
                <head>
                    <style>
                        @page {{ size: A4; margin: 15mm; }}
                        body {{ font-family: 'Bookman Old Style', serif; font-size: 11pt; }}
                        .page-container {{ width: 100%; }}
                        .justify-text {{ text-align: justify; }}
                    </style>
                </head>
                <body>
                    <div class="page-container">
                        <div class="letterhead">{lh_content}</div>
                        <div class="content" style="margin-top:20px;">
                            {filled_content}
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # 4. Generate PDF
                filename = f"{comm_type.replace(' ', '_')}_{recipient.get('GSTIN')}_{datetime.datetime.now().strftime('%H%M%S')}.pdf"
                filepath = os.path.join(output_dir, filename)
                
                success, msg = ASMT10Generator.save_pdf(final_html, filepath)
                if not success:
                    errors.append(f"Failed for {recipient.get('GSTIN')}: {msg}")
                    continue

                # 5. Save to OC Register
                entry_data = {
                    "OC_Number": current_oc_no,
                    "OC_Content": comm_type,
                    "OC_Date": self.oc_date_input.text(),
                    "OC_To": f"{recipient.get('Legal Name')}, {recipient.get('GSTIN')}",
                    "GSTIN": recipient.get('GSTIN', ''),
                    "Legal Name": recipient.get('Legal Name', ''),
                    "Trade Name": recipient.get('Trade Name', ''),
                    "Status": "Generated (Mail Merge)",
                    "Section": "General", 
                    "Remarks": f"Generated PDF: {filename}"
                }
                
                # Use SQLite entry
                # We need a case_id. For mail merge, we can either create a new proceeding 
                # or just add to register without one (if the DB allows)
                # Let's try to find an active case first
                case = self.db.find_active_case(recipient.get('GSTIN'), "General")
                case_id = case.get('CaseID') if case else None
                
                self.db.add_oc_entry(case_id, entry_data)
                count += 1
                
            except Exception as e:
                errors.append(f"Error for {recipient.get('GSTIN')}: {str(e)}")
            
            self.progress_bar.setValue(i + 1)
            # Process UI events to keep it responsive
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

        self.progress_bar.setVisible(False)
        
        if errors:
            err_msg = "\n".join(errors[:5]) + ("\n..." if len(errors) > 5 else "")
            QMessageBox.warning(self, "Completed with Errors", f"Generated {count} documents.\n\nErrors:\n{err_msg}")
        else:
            QMessageBox.information(self, "Success", f"Successfully generated {count} documents in:\n{output_dir}")

    def suggest_next_oc(self, input_field: QLineEdit):
        """Fetch next available OC number and set it to input"""
        try:
            import datetime
            current_year = datetime.date.today().year
            
            # Fetch next number from DB
            next_num = self.db.get_next_oc_number(str(current_year))
            
            formatted_oc = f"{next_num}/{current_year}"
            input_field.setText(formatted_oc)
            
        except Exception as e:
            print(f"Error suggesting OC: {e}")
