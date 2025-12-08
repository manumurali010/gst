from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QListWidget, QStackedWidget, QSplitter, QScrollArea, QTextEdit, 
                             QMessageBox, QFrame, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QComboBox, QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QPixmap
from src.database.db_manager import DatabaseManager
from src.utils.preview_generator import PreviewGenerator
from src.ui.collapsible_box import CollapsibleBox
from src.ui.rich_text_editor import RichTextEditor
from src.ui.components.modern_card import ModernCard
from src.ui.issue_card import IssueCard
import os
import json
from jinja2 import Template, Environment, FileSystemLoader
import datetime

class ProceedingsWorkspace(QWidget):
    def __init__(self, navigate_callback, proceeding_id=None):
        super().__init__()
        print("ProceedingsWorkspace: init start")
        self.navigate_callback = navigate_callback
        self.db = DatabaseManager()
        self.db.init_sqlite()
        print("ProceedingsWorkspace: DB initialized")
        
        self.proceeding_id = proceeding_id
        self.proceeding_data = {}
        
        # Debounce Timer
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(500)
        self.preview_timer.timeout.connect(self.update_preview)
        
        print("ProceedingsWorkspace: calling init_ui")
        self.init_ui()
        print("ProceedingsWorkspace: init_ui done")
        
        if self.proceeding_id:
            self.load_proceeding(self.proceeding_id)

    def init_ui(self):
        print("ProceedingsWorkspace: init_ui start")
        self.setObjectName("ProceedingsWorkspace")
        
        # Load Stylesheet
        try:
            style_path = os.path.join(os.path.dirname(__file__), "styles", "proceedings.qss")
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading stylesheet: {e}")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. Center Pane: Content (Stacked)
        self.content_stack = QStackedWidget()
        
        # Tab 0: Summary
        print("ProceedingsWorkspace: creating summary tab")
        self.summary_tab = self.create_summary_tab()
        self.content_stack.addWidget(self.summary_tab)
        
        # Tab 1: DRC-01A Editor
        print("ProceedingsWorkspace: creating drc01a tab")
        self.drc01a_tab = self.create_drc01a_tab()
        self.content_stack.addWidget(self.drc01a_tab)
        
        # Tab 2: SCN (Show Cause Notice)
        print("ProceedingsWorkspace: creating scn tab")
        self.scn_tab = self.create_scn_tab()
        self.content_stack.addWidget(self.scn_tab)
        
        # Tab 3: PH Intimation (Personal Hearing)
        print("ProceedingsWorkspace: creating ph_intimation tab")
        self.ph_tab = self.create_ph_intimation_tab()
        self.content_stack.addWidget(self.ph_tab)
        
        # Tab 4: Order
        print("ProceedingsWorkspace: creating order_tab")
        self.order_tab = self.create_order_tab()
        self.content_stack.addWidget(self.order_tab)
        print("ProceedingsWorkspace: order_tab added")
        
        # Placeholders for Documents and Timeline
        for i, name in enumerate(["Documents", "Timeline"]):
            lbl = QLabel(f"{name} - Coming Soon")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 16px; color: #7f8c8d;")
            self.content_stack.addWidget(lbl)
            
        self.layout.addWidget(self.content_stack, 65) # 65% width
        
        # 3. Right Pane: Preview
        print("ProceedingsWorkspace: creating preview_pane")
        self.create_preview_pane()
        print("ProceedingsWorkspace: preview_pane created")
        self.layout.addWidget(self.preview_container, 35) # 35% width

    def handle_sidebar_action(self, action):
        """Switch tabs based on sidebar action"""
        action_map = {
            "summary": 0,
            "drc01a": 1,
            "scn": 2,
            "ph": 3,
            "order": 4,
            "documents": 5,
            "timeline": 6
        }
        
        if action in action_map:
            index = action_map[action]
            self.content_stack.setCurrentIndex(index)
            
            # Auto-load issues when switching to SCN tab
            if action == "scn":
                self.load_scn_issues()
            
            # Trigger preview update if needed
            self.trigger_preview()

    def load_proceeding(self, pid):
        self.proceeding_id = pid
        self.proceeding_data = self.db.get_proceeding(pid)
        if not self.proceeding_data:
            QMessageBox.critical(self, "Error", "Proceeding not found!")
            return
            
        # Fetch associated documents
        self.documents = self.db.get_documents(pid)
            
        # Update UI
        self.update_summary_tab()
        
        # Restore Draft State (Issues, Amounts, etc.)
        self.restore_draft_state()
        
        # Check for existing generated documents to toggle View Mode
        self.check_existing_documents()
        
        self.trigger_preview()

    def create_preview_pane(self):
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_header = QHBoxLayout()
        preview_label = QLabel("Live Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        preview_header.addWidget(preview_label)
        
        self.show_letterhead_cb = QCheckBox("Show Letterhead")
        self.show_letterhead_cb.setChecked(True)
        self.show_letterhead_cb.stateChanged.connect(self.trigger_preview)
        preview_header.addWidget(self.show_letterhead_cb)
        
        preview_header.addStretch()
        preview_layout.addLayout(preview_header)
        
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_container = QWidget()
        self.preview_container_layout = QVBoxLayout(self.preview_container)
        self.preview_container_layout.setSpacing(20)  # Space between pages
        self.preview_container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.preview_scroll.setWidget(self.preview_container)
        preview_layout.addWidget(self.preview_scroll)
        
        self.preview_container = preview_widget # Assign widget to variable expected by splitter


    def create_summary_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        card = ModernCard("Case Summary")
        
        self.summary_title = QLabel("Case Summary")
        self.summary_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        # card.addWidget(self.summary_title) # Title already in card header
        
        self.summary_info = QLabel("Loading...")
        card.addWidget(self.summary_info)
        
        layout.addWidget(card)
        layout.addStretch()
        return widget

    def update_summary_tab(self):
        if not self.proceeding_data:
            return
            
        legal_name = self.proceeding_data.get('legal_name', 'Unknown')
        # self.summary_title.setText(f"Case Summary: {legal_name}") # Card title is static for now
        
        # Format Taxpayer Details
        tp_details = self.proceeding_data.get('taxpayer_details', {})
        if isinstance(tp_details, str):
            import json
            try: 
                tp_details = json.loads(tp_details)
            except: 
                tp_details = {}
            
        info_text = f"""<b>Case ID:</b> {self.proceeding_data.get('case_id', 'Pending')}<br>
<b>GSTIN:</b> {self.proceeding_data.get('gstin')}<br>
<b>Legal Name:</b> {legal_name}<br>
<b>Trade Name:</b> {self.proceeding_data.get('trade_name', 'N/A')}<br>
<b>Address:</b> {self.proceeding_data.get('address', 'N/A')}<br>
<b>Financial Year:</b> {self.proceeding_data.get('financial_year')}<br>
<b>Section:</b> {self.proceeding_data.get('initiating_section')}<br>
<b>Form Type:</b> {self.proceeding_data.get('form_type')}<br>
<b>Status:</b> {self.proceeding_data.get('status')}"""
        
        self.summary_info.setText(info_text)

    def create_drc01a_tab(self):
        print("ProceedingsWorkspace: create_drc01a_tab start")
        # Initialize list of issue cards
        self.issue_cards = []
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- DRAFT CONTAINER ---
        self.drc01a_draft_container = QWidget()
        draft_layout = QVBoxLayout(self.drc01a_draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("<b>Drafting DRC-01A</b>")
        title.setStyleSheet("font-size: 18px; margin-bottom: 10px; color: #2c3e50;")
        draft_layout.addWidget(title)
        
        # 0. Reference Details (OC No)
        print("ProceedingsWorkspace: creating ref_card")
        ref_card = ModernCard("Reference Details", collapsible=True)
        ref_layout = QHBoxLayout()
        
        oc_label = QLabel("OC No:")
        self.oc_number_input = QLineEdit()
        self.oc_number_input.setPlaceholderText("Enter OC Number (Optional)")
        self.oc_number_input.textChanged.connect(self.trigger_preview)
        
        ref_layout.addWidget(oc_label)
        ref_layout.addWidget(self.oc_number_input)
        
        oc_date_label = QLabel("OC Date:")
        self.oc_date_input = QDateEdit()
        self.oc_date_input.setCalendarPopup(True)
        self.oc_date_input.setDate(QDate.currentDate())
        self.oc_date_input.dateChanged.connect(self.trigger_preview)
        ref_layout.addWidget(oc_date_label)
        ref_layout.addWidget(self.oc_date_input)
        
        self.oc_date_input.dateChanged.connect(self.trigger_preview)
        ref_layout.addWidget(oc_date_label)
        ref_layout.addWidget(self.oc_date_input)

        
        ref_layout.addStretch()
        ref_card.addLayout(ref_layout)
        draft_layout.addWidget(ref_card)
        
        # 1. Issues Involved (Collapsible)
        print("ProceedingsWorkspace: creating issues_card")
        issues_card = ModernCard("Issues Involved", collapsible=True)
        
        # Issue Selection
        issue_selection_layout = QHBoxLayout()
        issue_label = QLabel("Select Issue:")
        self.issue_combo = QComboBox()
        self.issue_combo.addItem("Select an issue...", None)
        print("ProceedingsWorkspace: loading issue templates")
        self.load_issue_templates()
        print("ProceedingsWorkspace: issue templates loaded")
        
        refresh_issues_btn = QPushButton("🔄")
        refresh_issues_btn.setToolTip("Refresh issue list")
        refresh_issues_btn.clicked.connect(self.load_issue_templates)
        
        insert_issue_btn = QPushButton("Insert Issue Template")
        insert_issue_btn.setProperty("class", "primary")
        insert_issue_btn.clicked.connect(self.insert_selected_issue)
        
        issue_selection_layout.addWidget(issue_label)
        issue_selection_layout.addWidget(self.issue_combo)
        issue_selection_layout.addWidget(refresh_issues_btn)
        issue_selection_layout.addWidget(insert_issue_btn)
        issue_selection_layout.addStretch()
        issues_card.addLayout(issue_selection_layout)
        
        self.issues_container = QWidget()
        self.issues_layout = QVBoxLayout(self.issues_container)
        self.issues_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.issues_container)
        scroll.setMinimumHeight(300)
        
        issues_card.addWidget(scroll)
        draft_layout.addWidget(issues_card)

        # 2. Sections Violated (Collapsible)
        print("ProceedingsWorkspace: creating sections_card")
        sections_card = ModernCard("Sections Violated", collapsible=True)
        
        # Section Selection
        section_selection_layout = QHBoxLayout()
        section_label = QLabel("Select Section:")
        self.section_combo = QComboBox()
        self.section_combo.addItem("Select a section...", None)
        print("ProceedingsWorkspace: loading sections")
        self.load_sections()
        print("ProceedingsWorkspace: sections loaded")
        
        add_section_btn = QPushButton("Add Section")
        add_section_btn.setProperty("class", "primary")
        add_section_btn.clicked.connect(self.add_section_to_editor)
        
        section_selection_layout.addWidget(section_label)
        section_selection_layout.addWidget(self.section_combo)
        section_selection_layout.addWidget(add_section_btn)
        section_selection_layout.addStretch()
        sections_card.addLayout(section_selection_layout)
        
        print("ProceedingsWorkspace: creating sections_editor")
        self.sections_editor = RichTextEditor("Enter the sections of law that were violated...")
        print("ProceedingsWorkspace: sections_editor created")
        self.sections_editor.setMinimumHeight(100)
        self.sections_editor.textChanged.connect(self.trigger_preview)
        sections_card.addWidget(self.sections_editor)
        
        draft_layout.addWidget(sections_card)
        print("ProceedingsWorkspace: sections_card added")
        
        # 3. Tax Demand Details (Collapsible)
        print("ProceedingsWorkspace: creating tax_card")
        tax_card = ModernCard("Tax Demand Details", collapsible=True)
        
        # Act Selection
        act_label = QLabel("Select Acts:")
        act_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        tax_card.addWidget(act_label)
        
        act_selection_layout = QHBoxLayout()
        self.act_checkboxes = {}
        for act in ["CGST", "SGST", "IGST", "Cess"]:
            cb = QCheckBox(act)
            cb.stateChanged.connect(lambda state, a=act: self.toggle_act_row(a, state))
            self.act_checkboxes[act] = cb
            act_selection_layout.addWidget(cb)
        act_selection_layout.addStretch()
        tax_card.addLayout(act_selection_layout)
        
        # Tax Demand Table
        print("ProceedingsWorkspace: creating tax table")
        self.tax_table = QTableWidget()
        self.tax_table.setColumnCount(7)
        self.tax_table.setHorizontalHeaderLabels([
            "Act", "Tax Period From", "Tax Period To", "Tax (₹)", "Interest (₹)", "Penalty (₹)", "Total (₹)"
        ])
        self.tax_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tax_table.setMinimumHeight(200)
        tax_card.addWidget(self.tax_table)
        
        # Add Total Row initially
        print("ProceedingsWorkspace: adding total row")
        self.add_total_row()
        
        draft_layout.addWidget(tax_card)
        print("ProceedingsWorkspace: tax_card added")

        # 4. Dates (Collapsible)
        print("ProceedingsWorkspace: creating dates_card")
        dates_card = ModernCard("Dates", collapsible=True)
        dates_layout = QHBoxLayout()
        
        # Last Date for Reply
        reply_layout = QVBoxLayout()
        reply_label = QLabel("Last Date for Reply")
        self.reply_date = QDateEdit()
        self.reply_date.setCalendarPopup(True)
        self.reply_date.setDate(QDate.currentDate().addDays(30))
        self.reply_date.setMinimumDate(QDate.currentDate()) # Prevent past dates
        self.reply_date.dateChanged.connect(self.trigger_preview)
        reply_layout.addWidget(reply_label)
        reply_layout.addWidget(self.reply_date)
        dates_layout.addLayout(reply_layout)
        
        # Last Date for Payment
        payment_layout = QVBoxLayout()
        payment_label = QLabel("Last Date for Payment")
        self.payment_date = QDateEdit()
        self.payment_date.setCalendarPopup(True)
        self.payment_date.setDate(QDate.currentDate().addDays(30))
        self.payment_date.setMinimumDate(QDate.currentDate()) # Prevent past dates
        self.payment_date.dateChanged.connect(self.trigger_preview)
        payment_layout.addWidget(payment_label)
        payment_layout.addWidget(self.payment_date)
        
        print("ProceedingsWorkspace: create_drc01a_tab done")
        dates_layout.addLayout(payment_layout)
        
        dates_layout.addStretch()
        
        dates_layout.addStretch()
        dates_card.addLayout(dates_layout)
        draft_layout.addWidget(dates_card)
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Draft")
        save_btn.clicked.connect(self.save_drc01a)
        buttons_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setProperty("class", "danger")
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setProperty("class", "primary")
        docx_btn.clicked.connect(self.generate_docx)
        buttons_layout.addWidget(docx_btn)
        
        finalize_btn = QPushButton("Finalize")
        finalize_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        finalize_btn.clicked.connect(self.show_drc01a_finalization_panel)
        buttons_layout.addWidget(finalize_btn)
        
        buttons_layout.addStretch()
        
        # Letterhead Checkbox
        self.show_letterhead_cb = QCheckBox("Include Letterhead")
        self.show_letterhead_cb.setChecked(True)
        self.show_letterhead_cb.stateChanged.connect(self.trigger_preview)
        buttons_layout.addWidget(self.show_letterhead_cb)
        
        draft_layout.addLayout(buttons_layout)
        
        draft_layout.addStretch()
        
        # --- FINALIZATION CONTAINER (Initially Hidden) ---
        self.drc01a_finalization_container = self.create_drc01a_finalization_panel()
        self.drc01a_finalization_container.hide()
        
        # --- VIEW CONTAINER (Initially Hidden) ---
        self.drc01a_view_container = QWidget()
        self.drc01a_view_container.hide()
        view_layout = QVBoxLayout(self.drc01a_view_container)
        
        view_title = QLabel("<b>DRC-01A Generated</b>")
        view_title.setStyleSheet("font-size: 18px; color: #27ae60; margin-bottom: 20px;")
        view_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_title)
        
        view_msg = QLabel("A DRC-01A document has already been generated for this case.")
        view_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_msg)
        
        # Placeholder for Preview Image (Removed as per user request)
        # self.drc01a_view_preview = QLabel()
        # self.drc01a_view_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.drc01a_view_preview.setStyleSheet("border: 1px solid #ccc; background: white; min-height: 400px;")
        # view_layout.addWidget(self.drc01a_view_preview)
        
        # Add a simple summary placeholder instead
        summary_lbl = QLabel("Document Generated Successfully.\nClick 'Edit / Revise Draft' to make changes.")
        summary_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_lbl.setStyleSheet("color: #7f8c8d; font-size: 14px; margin: 20px;")
        view_layout.addWidget(summary_lbl)
        
        # Edit Button
        edit_btn = QPushButton("Edit / Revise Draft")
        edit_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; font-weight: bold;")
        edit_btn.clicked.connect(lambda: self.toggle_view_mode("drc01a", False))
        view_layout.addWidget(edit_btn)
        
        view_layout.addStretch()

        # Add both containers to main layout
        layout.addWidget(self.drc01a_draft_container)
        layout.addWidget(self.drc01a_finalization_container)
        layout.addWidget(self.drc01a_view_container)
        
        # Wrap in a centered container to constrain width
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        container_layout.addWidget(widget)
        
        # Set max width for the form content
        widget.setMaximumWidth(850) 
        
        # Wrap in Scroll Area
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setWidget(container)
        
        return main_scroll

    def create_drc01a_finalization_panel(self):
        """Create the Finalization Summary Panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Confirm Finalization")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; margin-bottom: 20px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # 1. Summary Card
        summary_card = ModernCard("Document Summary")
        
        # Date of Issue
        self.fin_date_lbl = QLabel("Date of Issue: -")
        self.fin_date_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        summary_card.addWidget(self.fin_date_lbl)
        
        # Amounts Summary Table
        self.fin_amounts_table = QTableWidget()
        self.fin_amounts_table.setColumnCount(4)
        self.fin_amounts_table.setHorizontalHeaderLabels(["Act", "Tax", "Interest", "Penalty"])
        self.fin_amounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fin_amounts_table.setMaximumHeight(150)
        summary_card.addWidget(self.fin_amounts_table)
        
        # Sections
        self.fin_sections_lbl = QLabel("Sections Applied: -")
        summary_card.addWidget(self.fin_sections_lbl)
        
        layout.addWidget(summary_card)
        
        # 2. Impact Card
        impact_card = ModernCard("System Updates")
        impact_lbl = QLabel("Proceeding with finalization will perform the following actions:")
        impact_lbl.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        impact_card.addWidget(impact_lbl)
        
        actions_list = [
            "✅ Update Proceeding Status to 'DRC-01A Issued'",
            "✅ Create Entry in Review / Order Register",
            "✅ Generate Permanent Document Number",
            "✅ Lock this Draft"
        ]
        
        for action in actions_list:
            lbl = QLabel(action)
            lbl.setStyleSheet("margin-left: 20px; color: #27ae60;")
            impact_card.addWidget(lbl)
            
        layout.addWidget(impact_card)
        
        # 3. Remarks
        remarks_card = ModernCard("Remarks (Optional)")
        self.fin_remarks = QTextEdit()
        self.fin_remarks.setPlaceholderText("Enter any internal remarks for this finalization...")
        self.fin_remarks.setMaximumHeight(80)
        remarks_card.addWidget(self.fin_remarks)
        layout.addWidget(remarks_card)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back to Edit")
        back_btn.setStyleSheet("padding: 10px;")
        back_btn.clicked.connect(self.hide_drc01a_finalization_panel)
        btn_layout.addWidget(back_btn)
        
        confirm_btn = QPushButton("Confirm & Finalize")
        confirm_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 10px 20px; font-weight: bold; font-size: 14px;")
        confirm_btn.clicked.connect(self.confirm_drc01a_finalization)
        btn_layout.addWidget(confirm_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        return widget

    def show_drc01a_finalization_panel(self):
        """Review and Show Finalization Panel"""
        # 1. Validate Inputs
        if not self.oc_number_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "OC Number is mandatory for finalization.")
            self.oc_number_input.setFocus()
            return

        # 2. Populate Summary Data
        self.fin_date_lbl.setText(f"Date of Issue: {self.oc_date_input.date().toString('dd-MM-yyyy')}")
        
        # Populate Table
        # Clone data from tax_table logic (simplified)
        self.fin_amounts_table.setRowCount(0)
        # Iterate tax table rows
        for row in range(self.tax_table.rowCount()):
            act_item = self.tax_table.item(row, 0)
            if act_item and act_item.text() != "Total":
                r = self.fin_amounts_table.rowCount()
                self.fin_amounts_table.insertRow(r)
                self.fin_amounts_table.setItem(r, 0, QTableWidgetItem(act_item.text()))
                # Tax, Int, Pen (Cols 3, 4, 5)
                self.fin_amounts_table.setItem(r, 1, QTableWidgetItem(self.tax_table.item(row, 3).text() if self.tax_table.item(row, 3) else "0"))
                self.fin_amounts_table.setItem(r, 2, QTableWidgetItem(self.tax_table.item(row, 4).text() if self.tax_table.item(row, 4) else "0"))
                self.fin_amounts_table.setItem(r, 3, QTableWidgetItem(self.tax_table.item(row, 5).text() if self.tax_table.item(row, 5) else "0"))

        # Sections
        # Just grab from DB since we selected one? Or parsing the text editor is hard.
        # Use the combo box selection for now as "Primary Section"
        sec_data = self.section_combo.currentData()
        sec_title = sec_data.get('title', 'Unknown') if sec_data else "Manual Entry"
        self.fin_sections_lbl.setText(f"Primary Section: {sec_title}")

        # 3. Switch View
        self.drc01a_draft_container.hide()
        self.drc01a_finalization_container.show()
        
    def hide_drc01a_finalization_panel(self):
        self.drc01a_finalization_container.hide()
        self.drc01a_draft_container.show()

    def confirm_drc01a_finalization(self):
        """Commit Finalization"""
        try:
            # 1. Save Document as Final
            self.save_drc01a() # Ensure latest draft is saved
            
            # Update Document is_final = 1
            # We need to get the doc_id or update all DRC-01A for this proceeding?
            # Ideally save_drc01a should handle "final" flag, but let's do an update query via DB manager 
            # or just rely on status update
            
            # 2. Update Proceeding Status
            self.db.update_proceeding(self.proceeding_id, {
                "status": "DRC-01A Issued"
            })
            
            # 3. Update Register (if needed)
            # The Save has already updated OC Register? 
            # We implemented add_oc_entry in DB manager but are we calling it?
            # Let's ensure OC entry is created now if not before
            oc_data = {
                'OC_Number': self.oc_number_input.text(),
                'OC_Date': self.oc_date_input.date().toString("yyyy-MM-dd"),
                'OC_Content': f"DRC-01A Issued. {self.fin_remarks.toPlainText()}",
                'OC_To': self.proceeding_data.get('legal_name', '')
            }
            self.db.add_oc_entry(self.proceeding_data['case_id'], oc_data)
            
            QMessageBox.information(self, "Success", "DRC-01A Finalized Successfully.")
            
            # 4. Switch to View Mode
            self.drc01a_finalization_container.hide()
            self.drc01a_view_container.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Finalization failed: {e}")
            import traceback
            traceback.print_exc()

    def load_issue_templates(self):
        """Load issue templates from DB (Active Issues)"""
        try:
            # Fetch active issues from DB
            issues = self.db.get_active_issues()
            
            # Convert list to dict keyed by issue_id
            self.issue_templates = {}
            self.issue_combo.clear()
            self.issue_combo.addItem("Select Issue...", None)
            
            for issue in issues:
                self.issue_templates[issue['issue_id']] = issue
                self.issue_combo.addItem(issue['issue_name'], issue['issue_id'])
                
        except Exception as e:
            print(f"Error loading issue templates: {e}")

    def load_sections(self):
        """Load CGST sections from DB"""
        try:
            sections = self.db.get_cgst_sections()
            self.section_combo.clear()
            self.section_combo.addItem("Select Section...", None)
            
            for section in sections:
                title = section.get('title', 'Unknown')
                # Store full content in user data if needed, or just title
                self.section_combo.addItem(title, section)
                
        except Exception as e:
            print(f"Error loading sections: {e}")

    def add_section_to_editor(self):
        """Insert selected section into the editor"""
        section_data = self.section_combo.currentData()
        if not section_data:
            return
            
        title = section_data.get('title', '')
        # content = section_data.get('content', '') # Optional: Add content too?
        
        # Append to editor
        current_html = self.sections_editor.toHtml()
        new_html = f"{current_html}<p><b>{title}</b></p>"
        self.sections_editor.setHtml(new_html)

    def insert_selected_issue(self):
        """Insert selected issue template as a new card"""
        issue_id = self.issue_combo.currentData()
        if not issue_id:
            return
            
        template = self.issue_templates.get(issue_id)
        if not template:
            return
            
        card = IssueCard(template)
        card.valuesChanged.connect(self.calculate_grand_totals)
        card.valuesChanged.connect(lambda: self.trigger_preview())  # Add preview trigger
        card.removeClicked.connect(lambda: self.remove_issue_card(card))
        
        self.issues_layout.addWidget(card)
        self.issue_cards.append(card)
        
        # Trigger initial calculation and preview
        self.calculate_grand_totals()
        self.trigger_preview()

    def remove_issue_card(self, card):
        self.issues_layout.removeWidget(card)
        card.deleteLater()
        if card in self.issue_cards:
            self.issue_cards.remove(card)
        self.calculate_grand_totals()

    def calculate_grand_totals(self, _=None):
        """Sum up totals from all issue cards and update main table"""
        # Initialize totals for each Act
        act_totals = {
            'CGST': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0},
            'SGST': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0},
            'IGST': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0},
            'Cess': {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0}
        }
        
        # Aggregate from all issue cards
        for card in self.issue_cards:
            if hasattr(card, 'get_tax_breakdown'):
                breakdown = card.get_tax_breakdown()
                for act, values in breakdown.items():
                    if act in act_totals:
                        act_totals[act]['tax'] += values.get('tax', 0.0)
                        act_totals[act]['interest'] += values.get('interest', 0.0)
                        act_totals[act]['penalty'] += values.get('penalty', 0.0)
        
        # Auto-select Acts based on non-zero totals
        # This ensures the rows exist in the table
        for act, totals in act_totals.items():
            has_liability = (totals['tax'] > 0 or totals['interest'] > 0 or totals['penalty'] > 0)
            if has_liability:
                # Find the checkbox for this act
                # keys in act_checkboxes match keys in act_totals (CGST, SGST, IGST, Cess)
                if act in self.act_checkboxes:
                    cb = self.act_checkboxes[act]
                    if not cb.isChecked():
                        # This will trigger toggle_act_row and create the row
                        cb.setChecked(True)
        
        # Update the Tax Table rows
        # We iterate through the table rows (excluding the last Total row)
        # and match the Act name in column 0
        
        # Temporarily block signals to prevent infinite loops
        self.tax_table.blockSignals(True)
        
        row_count = self.tax_table.rowCount()
        # The last row is "Total", so we iterate up to row_count - 1
        for row in range(row_count - 1):
            item = self.tax_table.item(row, 0)
            if not item: continue
            
            act_name = item.text().strip()
            
            # Map "Cess" variations if needed
            if act_name.lower() == 'cess': act_name = 'Cess'
            
            if act_name in act_totals:
                totals = act_totals[act_name]
                
                # Update Tax (Col 3)
                self.tax_table.setItem(row, 3, QTableWidgetItem(str(totals['tax'])))
                
                # Update Interest/Penalty if extracted (otherwise leave manual/default)
                if totals['interest'] > 0:
                    self.tax_table.setItem(row, 4, QTableWidgetItem(str(totals['interest'])))
                if totals['penalty'] > 0:
                    self.tax_table.setItem(row, 5, QTableWidgetItem(str(totals['penalty'])))
                    
        self.tax_table.blockSignals(False)
        
        # Recalculate row totals and grand total
        self.calculate_totals()
        
        # Trigger preview update
        self.trigger_preview()

    def create_scn_tab(self):
        print("ProceedingsWorkspace: create_scn_tab start")
        """Create Show Cause Notice tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # --- DRAFT CONTAINER ---
        self.scn_draft_container = QWidget()
        draft_layout = QVBoxLayout(self.scn_draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("<b>Drafting Show Cause Notice (SCN)</b>")
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        draft_layout.addWidget(title)
        
        # 0. Reference Details (SCN Specific)
        ref_card = ModernCard("Reference Details (SCN)", collapsible=True)
        ref_layout = QHBoxLayout()
        
        # SCN OC No
        oc_label = QLabel("SCN OC No:")
        self.scn_oc_input = QLineEdit()
        self.scn_oc_input.setPlaceholderText("Enter SCN OC Number")
        self.scn_oc_input.textChanged.connect(self.trigger_preview)
        
        # SCN Date
        date_label = QLabel("SCN Date:")
        self.scn_date_input = QDateEdit()
        self.scn_date_input.setCalendarPopup(True)
        self.scn_date_input.setDate(QDate.currentDate())
        self.scn_date_input.dateChanged.connect(self.trigger_preview)
        
        ref_layout.addWidget(oc_label)
        ref_layout.addWidget(self.scn_oc_input)
        ref_layout.addSpacing(20)
        ref_layout.addWidget(date_label)
        ref_layout.addWidget(self.scn_date_input)
        ref_layout.addStretch()
        ref_card.addLayout(ref_layout)

        draft_layout.addWidget(ref_card)
        
        # 1. Issues Involved (Collapsible) - SCN Specific
        self.scn_issue_cards = []
        scn_issues_card = ModernCard("Issues Involved", collapsible=True)
        
        # Issue Selection
        scn_issue_selection_layout = QHBoxLayout()
        scn_issue_label = QLabel("Select Issue:")
        self.scn_issue_combo = QComboBox()
        self.scn_issue_combo.addItem("Select an issue...", None)
        print("ProceedingsWorkspace: loading scn issue templates")
        self.load_scn_issue_templates()
        print("ProceedingsWorkspace: scn issue templates loaded")
        
        scn_refresh_issues_btn = QPushButton("🔄")
        scn_refresh_issues_btn.setToolTip("Refresh issue list")
        scn_refresh_issues_btn.clicked.connect(self.load_scn_issue_templates)
        
        scn_insert_issue_btn = QPushButton("Insert Issue Template")
        scn_insert_issue_btn.setProperty("class", "primary")
        scn_insert_issue_btn.clicked.connect(self.insert_scn_issue)
        
        scn_issue_selection_layout.addWidget(scn_issue_label)
        scn_issue_selection_layout.addWidget(self.scn_issue_combo)
        scn_issue_selection_layout.addWidget(scn_refresh_issues_btn)
        scn_issue_selection_layout.addWidget(scn_insert_issue_btn)
        scn_issue_selection_layout.addStretch()
        scn_issues_card.addLayout(scn_issue_selection_layout)
        
        self.scn_issues_container = QWidget()
        self.scn_issues_layout = QVBoxLayout(self.scn_issues_container)
        self.scn_issues_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scn_scroll = QScrollArea()
        scn_scroll.setWidgetResizable(True)
        scn_scroll.setWidget(self.scn_issues_container)
        scn_scroll.setMinimumHeight(300)
        
        scn_issues_card.addWidget(scn_scroll)
        draft_layout.addWidget(scn_issues_card)
        print("ProceedingsWorkspace: scn_issues_card added")

        print("ProceedingsWorkspace: creating reliance_card")
        rel_card = ModernCard("Reliance Placed on Documents", collapsible=True)
        self.reliance_editor = RichTextEditor("List documents here (e.g., 1. INS-01 dated...)")
        self.reliance_editor.setMinimumHeight(150)
        self.reliance_editor.textChanged.connect(self.trigger_preview)
        rel_card.addWidget(self.reliance_editor)
        draft_layout.addWidget(rel_card)
        print("ProceedingsWorkspace: reliance_card added")

        # 2. Copy Submitted To
        print("ProceedingsWorkspace: creating copy_card")
        copy_card = ModernCard("Copy Submitted To", collapsible=True)
        self.copy_to_editor = RichTextEditor("List authorities here...")
        self.copy_to_editor.setMinimumHeight(100)
        self.copy_to_editor.textChanged.connect(self.trigger_preview)
        copy_card.addWidget(self.copy_to_editor)
        draft_layout.addWidget(copy_card)
        print("ProceedingsWorkspace: copy_card added")
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Draft")
        save_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        save_btn.clicked.connect(lambda: self.save_document("SCN"))
        buttons_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        docx_btn.clicked.connect(self.generate_docx)
        buttons_layout.addWidget(docx_btn)
        
        buttons_layout.addStretch()
        draft_layout.addLayout(buttons_layout)
        
        draft_layout.addStretch()
        
        # --- VIEW CONTAINER (Initially Hidden) ---
        self.scn_view_container = QWidget()
        self.scn_view_container.hide()
        view_layout = QVBoxLayout(self.scn_view_container)
        
        view_title = QLabel("<b>SCN Generated</b>")
        view_title.setStyleSheet("font-size: 18px; color: #27ae60; margin-bottom: 20px;")
        view_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_title)
        
        view_msg = QLabel("A Show Cause Notice has already been generated for this case.")
        view_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_layout.addWidget(view_msg)
        
        # Placeholder for Preview Image
        self.scn_view_preview = QLabel()
        self.scn_view_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scn_view_preview.setStyleSheet("border: 1px solid #ccc; background: white; min-height: 400px;")
        view_layout.addWidget(self.scn_view_preview)
        
        # Edit Button
        edit_btn = QPushButton("Edit / Revise Draft")
        edit_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; font-weight: bold;")
        edit_btn.clicked.connect(lambda: self.toggle_view_mode("scn", False))
        view_layout.addWidget(edit_btn)
        
        view_layout.addStretch()

        # Add both containers to main layout
        layout.addWidget(self.scn_draft_container)
        layout.addWidget(self.scn_view_container)
        
        layout.addStretch()
        print("ProceedingsWorkspace: create_scn_tab done")
        return widget
        return widget

    def create_ph_intimation_tab(self):
        print("ProceedingsWorkspace: create_ph_intimation_tab start")
        """Create Personal Hearing Intimation tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("<b>Drafting Personal Hearing Intimation</b>")
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Rich Text Editor
        print("ProceedingsWorkspace: creating ph_editor")
        self.ph_editor = RichTextEditor("Enter the Personal Hearing Intimation content here...")
        print("ProceedingsWorkspace: ph_editor created")
        self.ph_editor.setMinimumHeight(400)
        self.ph_editor.textChanged.connect(self.trigger_preview)
        layout.addWidget(self.ph_editor)
        print("ProceedingsWorkspace: ph_editor added")
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Draft")
        save_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        save_btn.clicked.connect(lambda: self.save_document("PH"))
        buttons_layout.addWidget(save_btn)
        
        pdf_btn = QPushButton("Generate PDF")
        pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        pdf_btn.clicked.connect(self.generate_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        docx_btn = QPushButton("Generate DOCX")
        docx_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        docx_btn.clicked.connect(self.generate_docx)
        buttons_layout.addWidget(docx_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
        print("ProceedingsWorkspace: create_ph_intimation_tab done")
        return widget

    def create_order_tab(self):
        print("ProceedingsWorkspace: create_order_tab start")
        """Create Order tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("<b>Drafting Order</b>")
        title.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Rich Text Editor
        print("ProceedingsWorkspace: creating order_editor")
        self.order_editor = RichTextEditor("Enter the Order content here...")
        print("ProceedingsWorkspace: order_editor created")
        self.order_editor.setMinimumHeight(400)
        self.order_editor.textChanged.connect(self.trigger_preview)
        layout.addWidget(self.order_editor)
        print("ProceedingsWorkspace: order_editor added")
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Draft")
        save_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        save_btn.clicked.connect(lambda: self.save_document("Order"))
        buttons_layout.addWidget(save_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
        print("ProceedingsWorkspace: create_order_tab done")
        return widget

    def load_scn_issue_templates(self):
        """Load issue templates from DB for SCN tab"""
        try:
            issues = self.db.get_active_issues()
            self.scn_issue_templates = {}
            self.scn_issue_combo.clear()
            self.scn_issue_combo.addItem("Select Issue...", None)
            
            for issue in issues:
                self.scn_issue_templates[issue['issue_id']] = issue
                self.scn_issue_combo.addItem(issue['issue_name'], issue['issue_id'])
        except Exception as e:
            print(f"Error loading SCN issue templates: {e}")

    def insert_scn_issue(self):
        """Insert selected issue template into SCN tab"""
        issue_id = self.scn_issue_combo.currentData()
        if not issue_id:
            return
            
        template = self.scn_issue_templates.get(issue_id)
        if not template:
            return
            
        card = IssueCard(template)
        # Connect signals if needed (e.g., for preview updates)
        card.valuesChanged.connect(lambda: self.trigger_preview())
        card.removeClicked.connect(lambda: self.remove_scn_issue_card(card))
        
        self.scn_issues_layout.addWidget(card)
        self.scn_issue_cards.append(card)
        self.trigger_preview()

    def remove_scn_issue_card(self, card):
        self.scn_issues_layout.removeWidget(card)
        card.deleteLater()
        if card in self.scn_issue_cards:
            self.scn_issue_cards.remove(card)
        self.trigger_preview()

    def load_scn_issues(self):
        """Auto-load issues from DB into SCN tab"""
        try:
            # Clear existing cards
            for card in self.scn_issue_cards:
                card.setParent(None)
                self.scn_issues_layout.removeWidget(card)
                card.deleteLater()
            self.scn_issue_cards = []
            
            # Fetch issues from DB (Shared with DRC-01A)
            saved_issues = self.db.get_case_issues(self.proceeding_id)
            
            if saved_issues:
                all_templates = self.db.get_issue_templates()
                template_map = {t['issue_id']: t for t in all_templates}
                
                for issue_record in saved_issues:
                    issue_id = issue_record['issue_id']
                    data = issue_record['data']
                    
                    template = template_map.get(issue_id)
                    if not template:
                        template = {'issue_id': issue_id, 'issue_name': 'Unknown Issue', 'variables': {}}
                        
                    card = IssueCard(template, parent=self)
                    card.load_data(data)
                    
                    self.scn_issues_layout.addWidget(card)
                    self.scn_issue_cards.append(card)
            
            self.trigger_preview()
        except Exception as e:
            print(f"Error loading SCN issues: {e}")

    def save_document(self, doc_type):
        if doc_type == "SCN":
            try:
                # 1. Aggregate HTML for Document
                issues_html = ""
                issues_list = []
                
                for card in self.scn_issue_cards:
                    issues_html += card.generate_html()
                    issues_html += "<br><hr><br>"
                    
                    # Collect structured data for restoration
                    issues_list.append({
                        'issue_id': card.template.get('issue_id', 'UNKNOWN'),
                        'data': card.get_data()
                    })
                    
                # 2. Save Document HTML (for View Mode)
                doc_data = {
                    "proceeding_id": self.proceeding_id,
                    "doc_type": "Show Cause Notice",
                    "content_html": self.render_scn(), # Use render_scn to get full HTML
                    "is_final": 0
                }
                self.db.save_document(doc_data)
                
                # 3. Save Structured Draft Data to case_issues table
                # This ensures SCN issues are saved and shared with DRC-01A
                self.db.save_case_issues(self.proceeding_id, issues_list)
                
                # 4. Save Metadata
                metadata = {
                    "scn_oc_number": self.scn_oc_input.text(),
                    "scn_date": self.scn_date_input.date().toString("yyyy-MM-dd"),
                    "reliance_documents": self.reliance_editor.toHtml(),
                    "copy_submitted_to": self.copy_to_editor.toHtml()
                }
                
                # Update additional_details
                current_details = self.proceeding_data.get('additional_details', {})
                if isinstance(current_details, str):
                    try: current_details = json.loads(current_details)
                    except: current_details = {}
                    
                current_details.update(metadata)
                
                self.db.update_proceeding(self.proceeding_id, {
                    "status": "SCN Draft",
                    "additional_details": json.dumps(current_details)
                })
                
                # Update local data
                self.proceeding_data['additional_details'] = current_details
                
                QMessageBox.information(self, "Success", "Show Cause Notice draft saved successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving SCN: {e}")
                print(f"Error saving SCN: {e}")
                
        else:
            QMessageBox.information(self, "Success", f"{doc_type} draft saved.")

    def toggle_act_row(self, act_name, state):
        """Add or remove row for the selected act"""
        if state == Qt.CheckState.Checked.value:
            # Add Row before Total row
            total_row = self.tax_table.rowCount() - 1
            self.tax_table.insertRow(total_row)
            
            # Act Name (Read-only)
            item = QTableWidgetItem(act_name)
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.tax_table.setItem(total_row, 0, item)
            
            # Get months for the financial year
            fy = self.proceeding_data.get('financial_year', '')
            months = self.get_fy_months(fy)
            
            # Period From (Dropdown)
            from_combo = QComboBox()
            from_combo.addItems(months)
            from_combo.setStyleSheet("padding: 4px;")
            from_combo.currentTextChanged.connect(self.calculate_totals)
            self.tax_table.setCellWidget(total_row, 1, from_combo)
            
            # Period To (Dropdown)
            to_combo = QComboBox()
            to_combo.addItems(months)
            to_combo.setCurrentIndex(len(months) - 1)  # Default to last month
            to_combo.setStyleSheet("padding: 4px;")
            to_combo.currentTextChanged.connect(self.calculate_totals)
            self.tax_table.setCellWidget(total_row, 2, to_combo)
            
            # Editable cells for amounts
            for col in range(3, 7):
                self.tax_table.setItem(total_row, col, QTableWidgetItem("0"))
        else:
            # Remove Row
            for row in range(self.tax_table.rowCount() - 1):  # Exclude Total row
                item = self.tax_table.item(row, 0)
                if item and item.text() == act_name:
                    self.tax_table.removeRow(row)
                    break
        
        self.calculate_totals()
    
    def get_fy_months(self, fy_string):
        """Get list of months for a financial year (e.g., '2022-23' -> ['April 2022', 'May 2022', ...])"""
        if not fy_string or '-' not in fy_string:
            # Default to current FY
            import datetime
            year = datetime.date.today().year
            fy_string = f"{year}-{str(year+1)[-2:]}"
        
        try:
            start_year = int(fy_string.split('-')[0])
            end_year = int('20' + fy_string.split('-')[1])
        except:
            import datetime
            year = datetime.date.today().year
            start_year = year
            end_year = year + 1
        
        months = []
        month_names = ["April", "May", "June", "July", "August", "September", 
                      "October", "November", "December", "January", "February", "March"]
        
        for i, month in enumerate(month_names):
            if i < 9:  # April to December
                months.append(f"{month} {start_year}")
            else:  # January to March
                months.append(f"{month} {end_year}")
        
        return months

    def add_total_row(self):
        """Add Total row at the bottom"""
        row = self.tax_table.rowCount()
        self.tax_table.insertRow(row)
        
        # Total label
        item = QTableWidgetItem("Total")
        item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        item.setBackground(Qt.GlobalColor.lightGray)
        self.tax_table.setItem(row, 0, item)
        
        # Empty cells for periods
        for col in [1, 2]:
            item = QTableWidgetItem("-")
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.tax_table.setItem(row, col, item)
        
        # Total amounts
        for col in range(3, 7):
            item = QTableWidgetItem("0")
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.tax_table.setItem(row, col, item)

    def calculate_totals(self):
        """Calculate row totals and grand totals"""
        # Temporarily disconnect to avoid recursion
        try:
            self.tax_table.itemChanged.disconnect(self.calculate_totals)
        except:
            pass
        
        total_row = self.tax_table.rowCount() - 1
        if total_row < 0: return

        # Calculate each row's total (Tax + Interest + Penalty)
        for row in range(total_row):
            try:
                tax = float(self.tax_table.item(row, 3).text() or 0)
                interest = float(self.tax_table.item(row, 4).text() or 0)
                penalty = float(self.tax_table.item(row, 5).text() or 0)
                total = tax + interest + penalty
                self.tax_table.setItem(row, 6, QTableWidgetItem(str(total)))
            except (ValueError, AttributeError):
                pass
        
        # Calculate grand totals
        for col in range(3, 7):
            grand_total = 0
            for row in range(total_row):
                try:
                    value = float(self.tax_table.item(row, col).text() or 0)
                    grand_total += value
                except (ValueError, AttributeError):
                    pass
            
            item = QTableWidgetItem(str(grand_total))
            item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            item.setBackground(Qt.GlobalColor.lightGray)
            self.tax_table.setItem(total_row, col, item)
        
        # Reconnect signal
        self.tax_table.itemChanged.connect(self.calculate_totals)

    def change_tab(self, index):
        self.content_stack.setCurrentIndex(index)
        self.trigger_preview()

    def trigger_preview(self):
        self.preview_timer.start()

    def update_preview(self):
        # Determine what to preview based on active tab
        current_index = self.content_stack.currentIndex()
        
        html = ""
        if current_index == 1:  # DRC-01A
            html = self.generate_drc01a_html()
        elif current_index == 2: # SCN
            html = self.render_scn()
        else:
            html = "<h3>Select a document tab to view preview</h3>"
            
        # Generate Image
        images = PreviewGenerator.generate_preview_image(html, all_pages=True)
        
        # Clear previous preview
        while self.preview_container_layout.count():
            item = self.preview_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if images:
            for img_bytes in images:
                pixmap = PreviewGenerator.get_qpixmap_from_bytes(img_bytes)
                if pixmap:
                    # Scale to fit width (minus scrollbar/padding)
                    scaled_pixmap = pixmap.scaledToWidth(self.preview_scroll.width() - 40, Qt.TransformationMode.SmoothTransformation)
                    
                    lbl = QLabel()
                    lbl.setPixmap(scaled_pixmap)
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setStyleSheet("border: 1px solid #ccc; margin-bottom: 10px;") # Add border for page effect
                    self.preview_container_layout.addWidget(lbl)
        else:
            lbl = QLabel("Preview generation failed")
            self.preview_container_layout.addWidget(lbl)

    def generate_drc01a_html(self):
        # Load Template
        try:
            with open('templates/drc_01a.html', 'r', encoding='utf-8') as f:
                html = f.read()
        except:
            return "<h3>Template not found</h3>"
            
        # Replace Placeholders with data from DB + Editors
        html = html.replace("{{GSTIN}}", self.proceeding_data.get('gstin', '') or '')
        html = html.replace("{{LegalName}}", self.proceeding_data.get('legal_name', '') or '')
        html = html.replace("{{TradeName}}", self.proceeding_data.get('trade_name', '') or '')
        html = html.replace("{{Address}}", self.proceeding_data.get('address', '') or '')
        html = html.replace("{{CaseID}}", self.proceeding_data.get('case_id', '') or '')
        html = html.replace("{{OCNumber}}", self.oc_number_input.text())
        html = html.replace("{{FinancialYear}}", self.proceeding_data.get('financial_year', '') or '')
        html = html.replace("{{SelectedSection}}", self.proceeding_data.get('initiating_section', '') or '')
        html = html.replace("{{FormType}}", self.proceeding_data.get('form_type', '') or '')
        
        # Issue Date (Use OC Date)
        issue_date_str = self.oc_date_input.date().toString("dd/MM/yyyy")
        html = html.replace("{{IssueDate}}", issue_date_str)
        html = html.replace("{{CurrentDate}}", issue_date_str) # Fallback if template still has it
        
        # Conditional Section Text
        section = self.proceeding_data.get('initiating_section', '')
        if "73" in section:
            section_title = "section 73(5)"
            section_body = "73(5)"
        elif "74" in section:
            section_title = "section 74(5)"
            section_body = "74(5)"
        else:
            section_title = "section 73(5)/section 74(5)"
            section_body = "73(5) / 74(5)"
            
        html = html.replace("{{SectionTitle}}", section_title)
        html = html.replace("{{SectionBody}}", section_body)

        # The user's HTML has {{IssueDescription}} and {{SectionsViolated}} but NO {{GroundsContent}}?
        # Wait, looking at the user's HTML:
        # <div class="section-title">Issue:</div>
        # <div>{{IssueDescription}}</div>
        # <div class="section-title">Sections Violated:</div>
        # <div>{{SectionsViolated}}</div>
        
        # So I should map the "Issues Involved" editor to {{IssueDescription}} 
        # and "Sections Violated" editor to {{SectionsViolated}}
        
        # Aggregate HTML from all Issue Cards
        issues_html = ""
        for card in self.issue_cards:
            issues_html += card.generate_html()
            issues_html += "<br><hr><br>" # Separator between issues
            
        html = html.replace("{{IssueDescription}}", issues_html)
        html = html.replace("{{SectionsViolated}}", self.sections_editor.toHtml())
        
        # Generate Tax Table HTML
        tax_table_html = self.generate_tax_table_html()
        html = html.replace("{{TaxTableRows}}", tax_table_html)
        
        # Calculate Tax Period Range from Table
        period_from_list = []
        period_to_list = []
        for row in range(self.tax_table.rowCount()):
            # Check if row is valid (not total row)
            if self.tax_table.item(row, 0) and self.tax_table.item(row, 0).text() != "Total":
                # Get period from QComboBox widgets or items
                from_widget = self.tax_table.cellWidget(row, 1)
                to_widget = self.tax_table.cellWidget(row, 2)
                
                p_from = ""
                p_to = ""
                
                if isinstance(from_widget, QComboBox):
                    p_from = from_widget.currentText()
                elif self.tax_table.item(row, 1):
                    p_from = self.tax_table.item(row, 1).text()
                    
                if isinstance(to_widget, QComboBox):
                    p_to = to_widget.currentText()
                elif self.tax_table.item(row, 2):
                    p_to = self.tax_table.item(row, 2).text()
                
                if p_from: period_from_list.append(p_from)
                if p_to: period_to_list.append(p_to)
        
        # Simple logic: take first and last if available, otherwise empty
        tax_period_from = period_from_list[0] if period_from_list else ""
        tax_period_to = period_to_list[-1] if period_to_list else ""
        
        html = html.replace("{{TaxPeriodFrom}}", tax_period_from)
        html = html.replace("{{TaxPeriodTo}}", tax_period_to)
        
        # Get Last Date for Payment
        last_date_payment = self.payment_date.date().toString("dd/MM/yyyy")
        html = html.replace("{{LastDateForPayment}}", last_date_payment)
        
        # Get Last Date for Reply
        last_date_reply = self.reply_date.date().toString("dd/MM/yyyy")
        html = html.replace("{{LastDateForReply}}", last_date_reply)
        
        # Generate Conditional Advice Text based on Section
        section = self.proceeding_data.get('initiating_section', '')
        print(f"DEBUG: Section value = '{section}'")  # Debug output
        
        if "73" in section:
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."
            print(f"DEBUG: Using Section 73 advice text")  # Debug output
        elif "74" in section:
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."
            print(f"DEBUG: Using Section 74 advice text")  # Debug output
        else:
            advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest by {last_date_payment}, failing which Show Cause Notice will be issued."
            print(f"DEBUG: Using default advice text")  # Debug output
        
        print(f"DEBUG: Advice text = '{advice_text}'")  # Debug output
        html = html.replace("{{AdviceText}}", advice_text)
        
        # Inject letterhead if checkbox is checked
        if self.show_letterhead_cb.isChecked():
            try:
                from src.utils.config_manager import ConfigManager
                config = ConfigManager()
                letterhead_path = config.get_letterhead_path('pdf')
                with open(letterhead_path, 'r', encoding='utf-8') as f:
                    letterhead_html = f.read()
                html = html.replace('<div id="letterhead-placeholder"></div>', letterhead_html)
            except Exception as e:
                print(f"Error loading letterhead: {e}")
        
        # Clean up others
        for p in ["{{OCNumber}}", "{{SCNSection}}", "{{CurrentDate}}", "{{ComplianceDate}}", "{{TaxPeriodFrom}}", "{{TaxPeriodTo}}", "{{IssueDescription}}", "{{TaxAmount}}", "{{InterestAmount}}", "{{PenaltyAmount}}", "{{TotalAmount}}"]:
            html = html.replace(p, "_________________")
            
        return html

    def render_scn(self):
        """Render SCN HTML using Jinja2 template"""
        try:
            # 1. Gather Data
            data = self.proceeding_data.copy()
            
            # Format Dates
            # Use SCN specific date if available, else fallback to issue_date (which is DRC-01A date usually)
            # Actually, we added scn_date_input
            scn_date = self.scn_date_input.date()
            data['issue_date'] = scn_date.toString("dd/MM/yyyy")
            data['year'] = scn_date.year()
            
            # Financial Year
            fy = data.get('financial_year', '') or ''
            data['current_financial_year'] = fy
            
            # OC No (SCN Specific)
            data['oc_no'] = self.scn_oc_input.text() or "____"
            data['scn_no'] = "____" # Placeholder or auto-generated
            data['initiating_section'] = data.get('initiating_section', '') or "____"
            
            # Taxpayer Details (Already in data, but ensure keys match template)
            tp = data.get('taxpayer_details', {})
            if tp is None: tp = {}
            if isinstance(tp, str): 
                try:
                    tp = json.loads(tp)
                except:
                    tp = {}
            
            data['legal_name'] = tp.get('Legal Name', '') or data.get('legal_name', '')
            data['trade_name'] = tp.get('Trade Name', '') or data.get('trade_name', '')
            data['address'] = tp.get('Address', '') or data.get('address', '')
            data['gstin'] = data.get('gstin', '')
            data['constitution_of_business'] = tp.get('Constitution of Business', 'Registered')
            
            # Officer Details (Mock for now, should come from Settings/Auth)
            data['officer_name'] = "VISHNU V"
            data['officer_designation'] = "Superintendent"
            data['designation'] = "Superintendent"
            data['jurisdiction'] = "Paravur Range"
            
            # Issues & Demands
            # Issues & Demands
            issues_html = ""
            demand_html = ""
            
            total_tax = 0
            igst_total = 0
            cgst_total = 0
            sgst_total = 0
            
            # Generate Issues HTML (Same as DRC-01A but for SCN body)
            # Generate Issues HTML (Same as DRC-01A but for SCN body)
            # Always fetch from DB for consistency ("Source of Truth")
            saved_issues = self.db.get_case_issues(self.proceeding_id)
            
            # Load templates for titles if needed, but we can rely on saved data if we stored titles?
            # Actually, our new schema stores 'issue_id' and 'data_json'.
            # We need to look up the title from the template ID or store it in data_json.
            # Let's load templates to be safe.
            # Load templates using unified method
            print("DEBUG: Loading issue templates...")
            all_templates = self.db.get_issue_templates()
            print(f"DEBUG: Loaded {len(all_templates)} templates.")
            template_map = {t['issue_id']: t for t in all_templates if isinstance(t, dict) and 'issue_id' in t}

            if saved_issues:
                print(f"DEBUG: Found {len(saved_issues)} saved issues.")
                for i, issue_record in enumerate(saved_issues):
                    issue_id = issue_record['issue_id']
                    issue_data = issue_record['data']
                    
                    template = template_map.get(issue_id, {})
                    title = template.get('issue_name', 'Issue')
                    
                    # Issue Description
                    issues_html += f"<h3>Issue {i+1}: {title}</h3>"
                    issues_html += issue_data.get('content', '')
                    
                    # Generate Table HTML dynamically
                    try:
                        table_html = IssueCard.generate_table_html(template, issue_data.get('variables', {}))
                        issues_html += table_html
                    except Exception as e:
                        print(f"Error generating table for issue {issue_id}: {e}")
                        
                    issues_html += "<br><hr><br>"
                    
                    # Demand Summary
                    demand_html += f"<li>Demand for {title}...</li>"
                    
                    # Totals
                    breakdown = issue_data.get('tax_breakdown', {})
                    for act, vals in breakdown.items():
                        tax = vals.get('tax', 0)
                        total_tax += tax
                        if act == 'IGST': igst_total += tax
                        elif act == 'CGST': cgst_total += tax
                        elif act == 'SGST': sgst_total += tax
            else:
                 issues_html = "<p>No issues drafted yet.</p>"
            
            data['issues_content'] = issues_html
            data['issues_templates'] = issues_html # Keep for backward compat if needed
            data['issue_template_demand'] = demand_html
            
            # Generate Tax Table HTML (Reuse DRC-01A table logic)
            data['tax_table'] = self.generate_tax_table_html()
            
            data['total_amount'] = f"{total_tax:,.2f}"
            data['igst_total'] = f"{igst_total:,.2f}"
            data['cgst_total'] = f"{cgst_total:,.2f}"
            data['sgst_total'] = f"{sgst_total:,.2f}"
            
            # Reliance Documents
            rel_text = self.reliance_editor.toPlainText()
            data['reliance_documents'] = [line for line in rel_text.split('\\n') if line.strip()]
            data['reliance_documents_placeholder'] = "No documents listed"
            
            # Copy Submitted To
            copy_text = self.copy_to_editor.toPlainText()
            data['copy_submitted_to'] = [line for line in copy_text.split('\\n') if line.strip()]
            data['copy_submitted_to_placeholder'] = "No copies listed"
            
            data['show_letterhead'] = self.show_letterhead_cb.isChecked()
            
            # Letterhead Content
            if data['show_letterhead']:
                try:
                    from src.utils.config_manager import ConfigManager
                    config = ConfigManager()
                    letterhead_path = config.get_letterhead_path('pdf')
                    with open(letterhead_path, 'r', encoding='utf-8') as f:
                        data['letter_head'] = f.read()
                except Exception as e:
                    print(f"Error loading letterhead: {e}")
                    data['letter_head'] = ""
            else:
                data['letter_head'] = ""

            # Section Logic
            section = data.get('initiating_section', '')
            data['section'] = section
            
            # 2. Load Template
            template_dir = os.path.join(os.getcwd(), 'templates')
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template('scn.html')
            
            # 3. Render
            return template.render(**data)
            
        except Exception as e:
            print(f"Error rendering SCN: {e}")
            import traceback
            traceback.print_exc()
    def save_drc01a_metadata(self):
        """Save DRC-01A Metadata (OC No, Dates, etc.) to DB"""
        metadata = {
            "oc_number": self.oc_number_input.text(),
            "oc_date": self.oc_date_input.date().toString("yyyy-MM-dd"),
            "reply_date": self.reply_date.date().toString("yyyy-MM-dd"),
            "payment_date": self.payment_date.date().toString("yyyy-MM-dd"),
            "financial_year": self.proceeding_data.get('financial_year', ''),
            "initiating_section": self.proceeding_data.get('initiating_section', '')
        }
        
        # Tax Period Logic
        period_from_list = []
        period_to_list = []
        for row in range(self.tax_table.rowCount()):
            if self.tax_table.item(row, 0) and self.tax_table.item(row, 0).text() != "Total":
                from_widget = self.tax_table.cellWidget(row, 1)
                to_widget = self.tax_table.cellWidget(row, 2)
                
                p_from = ""
                p_to = ""
                
                if isinstance(from_widget, QComboBox): p_from = from_widget.currentText()
                elif self.tax_table.item(row, 1): p_from = self.tax_table.item(row, 1).text()
                    
                if isinstance(to_widget, QComboBox): p_to = to_widget.currentText()
                elif self.tax_table.item(row, 2): p_to = self.tax_table.item(row, 2).text()
                
                if p_from: period_from_list.append(p_from)
                if p_to: period_to_list.append(p_to)
                
        metadata['tax_period_from'] = period_from_list[0] if period_from_list else ""
        metadata['tax_period_to'] = period_to_list[-1] if period_to_list else ""
        
        # Update DB
        current_details = self.proceeding_data.get('additional_details', {})
        if isinstance(current_details, str):
            try: current_details = json.loads(current_details)
            except: current_details = {}
            
        current_details.update(metadata)
        
        self.db.update_proceeding(self.proceeding_id, {
            "initiating_section": metadata['initiating_section'],
            "last_date_to_reply": metadata['reply_date'],
            "additional_details": json.dumps(current_details)
        })
        
        # Update local data
        self.proceeding_data.update(metadata)
        self.proceeding_data['additional_details'] = current_details

    def save_drc01a(self):
        """Save DRC-01A Draft"""
        # 1. Aggregate HTML for Document
        issues_html = ""
        issues_list = []
        
        for card in self.issue_cards:
            issues_html += card.generate_html()
            issues_html += "<br><hr><br>"
            
            # Collect structured data for restoration
            issues_list.append({
                'issue_id': card.template.get('issue_id', 'UNKNOWN'),
                'data': card.get_data()
            })
            
        # 2. Save Document HTML (for View Mode)
        doc_data = {
            "proceeding_id": self.proceeding_id,
            "doc_type": "DRC-01A",
            "content_html": issues_html,
            "is_final": 0
        }
        self.db.save_document(doc_data)
        
        # 3. Save Structured Draft Data to case_issues table
        self.db.save_case_issues(self.proceeding_id, issues_list)
        
        # 4. Save Metadata
        self.save_drc01a_metadata()
        
        self.db.update_proceeding(self.proceeding_id, {
            "status": "DRC-01A Draft"
        })

        QMessageBox.information(self, "Success", "DRC-01A draft saved successfully!")

    def generate_tax_table_html(self):
        """Generate HTML table rows from tax_table widget"""
        rows_html = ""
        try:
            for row in range(self.tax_table.rowCount()):
                item_act = self.tax_table.item(row, 0)
                act = item_act.text() if item_act else ""
                
                # Get period from QComboBox widgets
                from_widget = self.tax_table.cellWidget(row, 1)
                to_widget = self.tax_table.cellWidget(row, 2)
                
                if isinstance(from_widget, QComboBox):
                    period_from = from_widget.currentText()
                else:
                    item_from = self.tax_table.item(row, 1)
                    period_from = item_from.text() if item_from else ""
                    
                if isinstance(to_widget, QComboBox):
                    period_to = to_widget.currentText()
                else:
                    item_to = self.tax_table.item(row, 2)
                    period_to = item_to.text() if item_to else ""
                
                item_tax = self.tax_table.item(row, 3)
                tax = item_tax.text() if item_tax else "0"
                
                item_int = self.tax_table.item(row, 4)
                interest = item_int.text() if item_int else "0"
                
                item_pen = self.tax_table.item(row, 5)
                penalty = item_pen.text() if item_pen else "0"
                
                item_tot = self.tax_table.item(row, 6)
                total = item_tot.text() if item_tot else "0"
                
                rows_html += f"""
                <tr>
                    <td style="border: 1px solid black; padding: 8px;">{act}</td>
                    <td style="border: 1px solid black; padding: 8px;">{period_from}</td>
                    <td style="border: 1px solid black; padding: 8px;">{period_to}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{tax}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{interest}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{penalty}</td>
                    <td style="border: 1px solid black; padding: 8px; text-align: right;">{total}</td>
                </tr>
                """
        except Exception as e:
            print(f"Error generating tax table HTML: {e}")
            return "<tr><td colspan='7'>Error loading tax details</td></tr>"
    
        return rows_html

    def generate_pdf(self):
        """Generate PDF for current tab"""
        try:
            current_index = self.content_stack.currentIndex()
            
            # Determine content based on tab
            html_content = ""
            filename_prefix = "Document"
            doc_type = "Document"
            
            if current_index == 1: # DRC-01A
                # AUTO-SAVE: Ensure DB is up to date before generation
                self.save_drc01a_metadata()
                
                html_content = self.generate_drc01a_html()
                oc_no = self.oc_number_input.text() or "DRAFT"
                # Sanitize OC No for filename
                safe_oc = "".join([c for c in oc_no if c.isalnum() or c in ('-','_')])
                default_filename = f"DRC-01A_{safe_oc}.pdf"
                doc_type = "DRC 01A"
            elif current_index == 2: # SCN
                html_content = self.render_scn()
                case_id = self.proceeding_data.get('case_id', 'DRAFT').replace('/', '_')
                default_filename = f"SCN_{case_id}.pdf"
                doc_type = "Show Cause Notice"
            else:
                QMessageBox.warning(self, "Error", "PDF generation not supported for this tab yet.")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save PDF As",
                default_filename,
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Generate PDF using the correct method
                import shutil
                from src.utils.document_generator import DocumentGenerator
                
                # Extract just the filename without extension
                filename_only = os.path.splitext(os.path.basename(file_path))[0]
                
                doc_gen = DocumentGenerator()
                generated_path = doc_gen.generate_pdf_from_html(html_content, filename_only)
                
                if generated_path and os.path.exists(generated_path):
                    # Move the file to user-selected location
                    try:
                        shutil.move(generated_path, file_path)
                        
                        # 2. Auto-Register in OC Register
                        oc_data = {
                            'OC_Number': oc_no if current_index == 1 else self.scn_oc_input.text(),
                            'OC_Content': doc_type,
                            'OC_Date': self.oc_date_input.date().toString("yyyy-MM-dd"), # DB format
                            'OC_To': self.proceeding_data.get('legal_name', '')
                        }
                        self.db.add_oc_entry(self.proceeding_data.get('case_id'), oc_data)
                        
                        # 3. Save Document Record to DB (for View Mode)
                        doc_data = {
                            'proceeding_id': self.proceeding_data.get('id'),
                            'doc_type': doc_type,
                            'content_html': html_content,
                            'template_id': None, # Could link to template if needed
                            'template_version': 1,
                            'version_no': 1,
                            'is_final': 1,
                            'snapshot_path': file_path # Using PDF path as snapshot for now
                        }
                        self.db.save_document(doc_data)
                        
                        QMessageBox.information(self, "Success", f"PDF generated and OC Registered successfully!\n\nSaved to: {file_path}")
                        
                        # Open the file
                        try:
                            os.startfile(file_path)
                        except Exception as e:
                            print(f"Could not open file: {e}")
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"PDF was generated but could not be moved to selected location.\n\nGenerated at: {generated_path}\nError: {str(e)}")
                else:
                    QMessageBox.warning(self, "Error", "Failed to generate PDF. Check console for errors.")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating PDF: {str(e)}")
            print(f"PDF Generation Error: {e}")
            import traceback
            traceback.print_exc()

    def generate_docx(self):
        """Generate DOCX document for DRC-01A"""
        try:
            # Check Tab
            if self.content_stack.currentIndex() != 1:
                QMessageBox.information(self, "Info", "DOCX generation is currently only available for DRC-01A.")
                return

            # Check if proceeding is loaded
            if not self.proceeding_data or not isinstance(self.proceeding_data, dict):
                QMessageBox.warning(self, "Error", "No proceeding loaded. Please open a case first.")
                return

            # Save Metadata first!
            self.save_drc01a_metadata()

            # 1. Validate OC No (Mandatory)
            oc_no = self.oc_number_input.text().strip()
            if not oc_no:
                QMessageBox.warning(self, "Validation Error", "OC Number is mandatory. Please enter it in the Reference Details section.")
                return
                
            from PyQt6.QtWidgets import QFileDialog
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from bs4 import BeautifulSoup
            import os
            
            # Ask user for save location
            case_id = self.proceeding_data.get('case_id', 'DRAFT')
            if case_id and isinstance(case_id, str):
                case_id = case_id.replace('/', '_')
            else:
                case_id = 'DRAFT'
            default_filename = f"DRC-01A_{case_id}.docx"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save DOCX As",
                default_filename,
                "Word Documents (*.docx)"
            )
            
            if file_path:
                # Create DOCX document
                doc = Document()
                
                # Set margins
                sections = doc.sections
                for section in sections:
                    section.top_margin = Inches(1)
                    section.bottom_margin = Inches(1)
                    section.left_margin = Inches(1)
                    section.right_margin = Inches(1)
                
                # Add title
                title = doc.add_paragraph()
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = title.add_run("FORM DRC-01A")
                run.bold = True
                run.font.size = Pt(16)
                
                # Add case details
                doc.add_paragraph(f"Case ID: {self.proceeding_data.get('case_id', 'N/A')}")
                doc.add_paragraph(f"GSTIN: {self.proceeding_data.get('gstin', 'N/A')}")
                doc.add_paragraph(f"Legal Name: {self.proceeding_data.get('legal_name', 'N/A')}")
                doc.add_paragraph(f"Address: {self.proceeding_data.get('address', 'N/A')}")
                doc.add_paragraph()
                
                # Add Tax Demand Table
                if self.tax_table.rowCount() > 0:
                    heading = doc.add_paragraph()
                    run = heading.add_run("Tax Demand Details:")
                    run.bold = True
                    run.font.size = Pt(14)
                    
                    # Create table
                    table = doc.add_table(rows=self.tax_table.rowCount(), cols=7)
                    table.style = 'Light Grid Accent 1'
                    
                    # Add headers
                    headers = ["Act", "Tax Period From", "Tax Period To", "Tax (₹)", "Interest (₹)", "Penalty (₹)", "Total (₹)"]
                    for col, header in enumerate(headers):
                        cell = table.rows[0].cells[col]
                        cell.text = header
                        cell.paragraphs[0].runs[0].bold = True
                    
                    # Add data
                    for row in range(self.tax_table.rowCount()):
                        # Handle QComboBox widgets for periods in DOCX
                        from_widget = self.tax_table.cellWidget(row, 1)
                        to_widget = self.tax_table.cellWidget(row, 2)
                        
                        p_from = ""
                        p_to = ""
                        
                        if isinstance(from_widget, QComboBox):
                            p_from = from_widget.currentText()
                        elif self.tax_table.item(row, 1):
                            p_from = self.tax_table.item(row, 1).text()
                            
                        if isinstance(to_widget, QComboBox):
                            p_to = to_widget.currentText()
                        elif self.tax_table.item(row, 2):
                            p_to = self.tax_table.item(row, 2).text()

                        # Act
                        if self.tax_table.item(row, 0):
                            table.rows[row].cells[0].text = self.tax_table.item(row, 0).text()
                        
                        # Periods
                        table.rows[row].cells[1].text = p_from
                        table.rows[row].cells[2].text = p_to
                        
                        # Amounts
                        for col in range(3, 7):
                            item = self.tax_table.item(row, col)
                            if item:
                                table.rows[row].cells[col].text = item.text()
                    
                    doc.add_paragraph()
                
                # Add Issue (Mapped from Issues Editor)
                heading = doc.add_paragraph()
                run = heading.add_run("Issue:")
                run.bold = True
                run.font.size = Pt(14)
                doc.add_paragraph(self.issues_editor.toPlainText())
                doc.add_paragraph()

                # Add Sections Violated
                heading = doc.add_paragraph()
                run = heading.add_run("Sections Violated:")
                run.bold = True
                run.font.size = Pt(14)
                doc.add_paragraph(self.sections_editor.toPlainText())
                
                # Add Conditional Advice Text
                last_date_payment = self.payment_date.date().toString("dd/MM/yyyy")
                section = self.proceeding_data.get('initiating_section', '')
                
                if "73" in section:
                    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest in full by {last_date_payment}, failing which Show Cause Notice will be issued under section 73(1)."
                elif "74" in section:
                    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest and penalty under section 74(5) by {last_date_payment}, failing which Show Cause Notice will be issued under section 74(1)."
                else:
                    advice_text = f"You are hereby advised to pay the amount of tax as ascertained above alongwith the amount of applicable interest by {last_date_payment}, failing which Show Cause Notice will be issued."
                
                p = doc.add_paragraph()
                p.add_run(advice_text)

                # Add Submission Instructions
                last_date_reply = self.reply_date.date().toString("dd/MM/yyyy")
                p = doc.add_paragraph()
                p.add_run(f"In case you wish to file any submissions against the above ascertainment, the same may be furnished by {last_date_reply} in Part B of this Form.")
                
                # Add Signature Block
                doc.add_paragraph()
                doc.add_paragraph()
                
                sig = doc.add_paragraph()
                sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = sig.add_run("Proper Officer")
                run.bold = True
                
                doc.save(file_path)
                
                # 2. Auto-Register in OC Register
                oc_data = {
                    'OC_Number': oc_no,
                    'OC_Content': 'DRC 01A',
                    'OC_Date': self.oc_date_input.date().toString("yyyy-MM-dd"), # DB format
                    'OC_To': self.proceeding_data.get('legal_name', '')
                }
                self.db.add_oc_entry(self.proceeding_data.get('case_id'), oc_data)
                
                QMessageBox.information(self, "Success", f"DOCX generated and OC Registered successfully!\n\nSaved to: {file_path}")
                
                # Open the file
                try:
                    os.startfile(file_path)
                except Exception as e:
                    print(f"Could not open file: {e}")
                sig = doc.add_paragraph()
                sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                run = sig.add_run("Proper Officer\n(Signature)\nName: ____________________\nDesignation: ____________________\nJurisdiction: ____________________")
                run.bold = True
                
                # Save document
                doc.save(file_path)
                
                QMessageBox.information(self, "Success", f"DOCX generated successfully!\n\nSaved to: {file_path}")
                
                # Open the file
                os.startfile(file_path)
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating DOCX: {str(e)}")

    def check_existing_documents(self):
        """Check if documents exist and toggle view mode"""
        drc01a_exists = False
        scn_exists = False
        
        for doc in self.documents:
            if doc['doc_type'] == 'DRC 01A':
                drc01a_exists = True
                # Update preview image if available (Removed as per user request)
                # if doc.get('snapshot_path') and os.path.exists(doc['snapshot_path']):
                #     pixmap = QPixmap(doc['snapshot_path'])
                #     self.drc01a_view_preview.setPixmap(pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation))
                # else:
                #     self.drc01a_view_preview.setText("Preview not available")
                    
        self.toggle_view_mode("drc01a", drc01a_exists)
        self.toggle_view_mode("scn", scn_exists)

    def toggle_view_mode(self, doc_type, show_view):
        """Toggle between Draft and View containers"""
        if doc_type == "drc01a":
            if show_view:
                self.drc01a_draft_container.hide()
                self.drc01a_view_container.show()
            else:
                self.drc01a_view_container.hide()
                self.drc01a_draft_container.show()
                
        elif doc_type == "scn":
            if show_view:
                self.scn_draft_container.hide()
                self.scn_view_container.show()
            else:
                self.scn_view_container.hide()
                self.scn_draft_container.show()

    def restore_draft_state(self):
        """Restore UI state from proceeding data"""
        try:
            # 1. Restore Issues
            # Check for structured data in proceedings table
            add_details = self.proceeding_data.get('additional_details', {})
            # 1. Restore Issues from case_issues table
            saved_issues = self.db.get_case_issues(self.proceeding_id)
            
            # Clear existing cards first
            for card in self.issue_cards:
                card.setParent(None)
                self.issues_layout.removeWidget(card)
                card.deleteLater()
            self.issue_cards = []
            
            if saved_issues:
                # Load templates to reconstruct cards
                all_templates = self.db.get_issue_templates()
                    
                template_map = {t['issue_id']: t for t in all_templates}
                
                for issue_record in saved_issues:
                    issue_id = issue_record['issue_id']
                    data = issue_record['data']
                    
                    template = template_map.get(issue_id)
                    if not template:
                        print(f"WARNING: Template not found for issue_id: {issue_id}. Using fallback.")
                        # Fallback for unknown template
                        template = {'issue_id': issue_id, 'issue_name': 'Unknown Issue', 'variables': {}}
                    else:
                        print(f"SUCCESS: Restoring issue {issue_id} with template.")
                        
                    from src.ui.issue_card import IssueCard
                    card = IssueCard(template, parent=self)
                    
                    # Restore state using robust load_data method
                    card.load_data(data)
                    
                    # Add to layout
                    self.issues_layout.addWidget(card)
                    self.issue_cards.append(card)
                    
                    # Connect signals
                    card.removeClicked.connect(lambda c=card: self.remove_issue_card(c))
                    card.valuesChanged.connect(self.calculate_grand_totals)
                    card.valuesChanged.connect(lambda _: self.trigger_preview())
                    
                    # Trigger calculation to update totals based on restored variables
                    card.calculate_values()
            
            # 2. Restore Metadata from additional_details
            if add_details:
                if 'oc_number' in add_details: 
                    self.oc_number_input.setText(add_details['oc_number'])
                if 'oc_date' in add_details: 
                    self.oc_date_input.setDate(QDate.fromString(add_details['oc_date'], "yyyy-MM-dd"))
                if 'reply_date' in add_details: 
                    self.reply_date.setDate(QDate.fromString(add_details['reply_date'], "yyyy-MM-dd"))
                
        except Exception as e:
            print(f"Error restoring draft state: {e}")
            import traceback
            traceback.print_exc()
