from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTabWidget, QSplitter, QFrame, QMessageBox, QComboBox, QCompleter, QTextBrowser, QGridLayout, QSizePolicy, QMenu)
from PyQt6.QtCore import Qt, QStringListModel
import os
from src.database.db_manager import DatabaseManager

class CaseManagement(QWidget):
    def __init__(self, wizard_callback):
        super().__init__()
        self.wizard_callback = wizard_callback # Callback to launch wizard with data
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        # Header
        header_frame = QFrame()
        header_frame.setFixedHeight(40) # Force compact height
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 1px solid #e0e0e0;
                border-radius: 5px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0) # Zero vertical padding
        
        header_label = QLabel("Case Lifecycle Management")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; border: none;") # Slightly smaller font
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        self.layout.addWidget(header_frame)

        # Splitter for Search/List (Left) and Details (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel: Search & List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        # Search Bar
        search_layout = QHBoxLayout()
        
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setPlaceholderText("Search by GSTIN...")
        self.search_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.search_input.setStyleSheet("""
            QComboBox { padding: 8px; border-radius: 4px; border: 1px solid #bdc3c7; }
            QComboBox::drop-down { border: none; }
        """)
        
        # Setup Completer
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_input.setCompleter(self.completer)
        
        # Load Suggestions
        self.load_gstin_suggestions()
        
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold;")
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)
        left_layout.addLayout(search_layout)
        
        # Case List Table
        self.case_table = QTableWidget()
        self.case_table.setColumnCount(4)
        self.case_table.setHorizontalHeaderLabels(["Case ID", "Section", "FY", "Status"])
        self.case_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.case_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.case_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.case_table.itemClicked.connect(self.load_case_details)
        
        # Context Menu
        self.case_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.case_table.customContextMenuRequested.connect(self.show_context_menu)
        
        left_layout.addWidget(self.case_table)
        
        splitter.addWidget(left_widget)
        
        # Right Panel: Case Details
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_widget.setVisible(False) # Hidden initially
        
        # Metadata Header
        self.meta_label = QLabel()
        self.meta_label.setStyleSheet("font-weight: bold; color: #34495e; padding: 10px; background: #ecf0f1; border-radius: 5px;")
        self.details_layout.addWidget(self.meta_label)
        
        # Document Tabs
        self.doc_tabs = QTabWidget()
        self.doc_tabs.addTab(QWidget(), "DRC-01A")
        self.doc_tabs.addTab(QWidget(), "SCN")
        self.doc_tabs.addTab(QWidget(), "PH Intimation")
        self.doc_tabs.addTab(QWidget(), "Order")
        self.details_layout.addWidget(self.doc_tabs)
        
        # Action Bar
        self.action_btn = QPushButton("Proceed to Next Action")
        self.action_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 12px; font-size: 16px; font-weight: bold; border-radius: 5px;")
        self.action_btn.clicked.connect(self.handle_next_action)
        self.details_layout.addWidget(self.action_btn)
        
        splitter.addWidget(self.details_widget)
        splitter.setStretchFactor(1, 2) # Give more space to details
        
        self.layout.addWidget(splitter)

    def load_gstin_suggestions(self):
        """Load unique GSTINs from case files (CSV + SQLite) for auto-complete"""
        try:
            # CSV Cases
            csv_cases = self.db.get_all_case_files()
            gstins = set([str(c.get('GSTIN', '')) for c in csv_cases if c.get('GSTIN')])
            
            # SQLite Cases
            sqlite_cases = self.db.get_all_proceedings()
            gstins.update([str(c.get('gstin', '')) for c in sqlite_cases if c.get('gstin')])
            
            sorted_gstins = sorted(list(gstins))
            
            self.search_input.clear()
            self.search_input.addItems(sorted_gstins)
            self.search_input.setCurrentIndex(-1) # Clear selection
            
            # Update completer model
            model = QStringListModel(sorted_gstins)
            self.completer.setModel(model)
            
        except Exception as e:
            print(f"Error loading GSTIN suggestions: {e}")

    def perform_search(self):
        gstin = self.search_input.currentText().strip()
        # If empty, show all (optional, but good for testing)
        
        all_cases = []
        
        # 1. Get CSV Cases
        csv_cases = self.db.get_cases_by_gstin(gstin) if gstin else self.db.get_all_case_files()
        for c in csv_cases:
            c['source'] = 'csv'
        all_cases.extend(csv_cases)
        
        # 2. Get SQLite Cases
        sqlite_cases = self.db.get_all_proceedings()
        if gstin:
            sqlite_cases = [c for c in sqlite_cases if c.get('gstin') == gstin]
        
        for c in sqlite_cases:
            c['source'] = 'sqlite'
            # Normalize keys for display
            c['CaseID'] = c.get('id')
            c['Section'] = c.get('initiating_section')
            c['Financial_Year'] = c.get('financial_year')
            c['Status'] = c.get('status')
            c['GSTIN'] = c.get('gstin')
            c['Legal Name'] = c.get('legal_name')
            
        all_cases.extend(sqlite_cases)
        
        self.populate_table(all_cases)

    def populate_table(self, cases):
        self.case_table.setRowCount(len(cases))
        for row, case in enumerate(cases):
            self.case_table.setItem(row, 0, QTableWidgetItem(str(case.get('CaseID', ''))))
            self.case_table.setItem(row, 1, QTableWidgetItem(str(case.get('Section', ''))))
            self.case_table.setItem(row, 2, QTableWidgetItem(str(case.get('Financial_Year', ''))))
            self.case_table.setItem(row, 3, QTableWidgetItem(str(case.get('Status', 'Unknown'))))
            
            # Store full case data in first item
            self.case_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, case)

    def load_case_details(self, item):
        row = item.row()
        case_data = self.case_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.current_case = case_data
        
        # Update Metadata
        meta_text = f"""
        GSTIN: {case_data.get('GSTIN')} | Legal Name: {case_data.get('Legal Name')}
        Case ID: {case_data.get('CaseID')} | Status: {case_data.get('Status')}
        """
        self.meta_label.setText(meta_text)
        
        # Update Tabs
        self.doc_tabs.clear()
        
        # Always add all tabs
        self.setup_tab("DRC-01A", case_data)
        self.setup_tab("SCN", case_data)
        self.setup_tab("PH Intimation", case_data)
        self.setup_tab("Order", case_data)

        # Update Action Button
        if case_data.get('source') == 'sqlite':
            self.action_btn.setText("Open Workspace")
            self.action_btn.setEnabled(True)
        else:
            status = case_data.get('Status', '')
            if "DRC-01A" in status:
                self.action_btn.setText("Draft SCN")
                self.action_btn.setEnabled(True)
            elif "SCN" in status:
                self.action_btn.setText("Issue PH Intimation")
                self.action_btn.setEnabled(True)
            elif "PH" in status:
                self.action_btn.setText("Draft Final Order")
                self.action_btn.setEnabled(True)
            else:
                self.action_btn.setText("View Case")
                self.action_btn.setEnabled(True)
            
        self.details_widget.setVisible(True)

    def setup_tab(self, title, data):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- 1. Detailed Summary Section ---
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(10)
        
        # Extract Data
        fy = str(data.get('Financial_Year', 'N/A') or 'N/A')
        section = str(data.get('Section', 'N/A') or 'N/A')
        issue = str(data.get('Issue_Description', 'N/A') or 'N/A')
        copy_to = str(data.get('OC_Copy_To', 'N/A') or 'N/A')
        remarks = str(data.get('Remarks', 'N/A') or 'N/A')
        
        # Determine Ref No & Dates based on Doc Type
        ref_no = "N/A"
        issue_date_str = "N/A"
        reply_date_str = "N/A"
        
        if title == "DRC-01A":
            ref_no = str(data.get('OC_Number', 'N/A') or 'N/A')
            issue_date_str = str(data.get('OC_Date', 'N/A') or 'N/A')
        elif title == "SCN":
            ref_no = str(data.get('SCN_Number', 'N/A') or 'N/A')
            issue_date_str = str(data.get('SCN_Date', 'N/A') or 'N/A')
        elif title == "Order":
            ref_no = str(data.get('OIO_Number', 'N/A') or 'N/A')
            issue_date_str = str(data.get('OIO_Date', 'N/A') or 'N/A')
        
        # Demands
        try:
            cgst = float(data.get('CGST_Demand') or 0)
            sgst = float(data.get('SGST_Demand') or 0)
            igst = float(data.get('IGST_Demand') or 0)
            cess = float(data.get('Cess_Demand') or 0)
            total = float(data.get('Total_Demand') or 0)
        except (ValueError, TypeError):
            cgst = sgst = igst = cess = total = 0.0
            
        cgst_str = f"₹ {cgst:,.2f}"
        sgst_str = f"₹ {sgst:,.2f}"
        igst_str = f"₹ {igst:,.2f}"
        cess_str = f"₹ {cess:,.2f}"
        total_str = f"₹ {total:,.2f}"
            
        # Calculate Last Date to Reply (+30 days)
        if issue_date_str != "N/A":
            try:
                from datetime import datetime, timedelta
                # Handle both / and . separators
                clean_date = issue_date_str.replace('.', '/')
                issue_date = datetime.strptime(clean_date, "%d/%m/%Y")
                reply_date = issue_date + timedelta(days=30)
                reply_date_str = reply_date.strftime("%d/%m/%Y")
            except:
                reply_date_str = "Invalid Date"

        # Group 1: Basic Details
        from PyQt6.QtWidgets import QGroupBox
        basic_group = QGroupBox("Case Details")
        basic_group.setStyleSheet("QGroupBox { font-weight: bold; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
        basic_layout = QGridLayout(basic_group)
        basic_layout.addWidget(QLabel("<b>Ref No:</b>"), 0, 0)
        basic_layout.addWidget(QLabel(ref_no), 0, 1)
        basic_layout.addWidget(QLabel("<b>Financial Year:</b>"), 0, 2)
        basic_layout.addWidget(QLabel(fy), 0, 3)
        basic_layout.addWidget(QLabel("<b>Section:</b>"), 1, 0)
        basic_layout.addWidget(QLabel(section), 1, 1)
        basic_layout.addWidget(QLabel("<b>Issue:</b>"), 1, 2)
        basic_layout.addWidget(QLabel(issue), 1, 3)
        summary_layout.addWidget(basic_group)

        # Group 2: Financials
        fin_group = QGroupBox("Financials")
        fin_group.setStyleSheet("QGroupBox { font-weight: bold; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
        fin_layout = QGridLayout(fin_group)
        fin_layout.addWidget(QLabel("<b>CGST:</b>"), 0, 0)
        fin_layout.addWidget(QLabel(cgst_str), 0, 1)
        fin_layout.addWidget(QLabel("<b>SGST:</b>"), 0, 2)
        fin_layout.addWidget(QLabel(sgst_str), 0, 3)
        fin_layout.addWidget(QLabel("<b>IGST:</b>"), 0, 4)
        fin_layout.addWidget(QLabel(igst_str), 0, 5)
        fin_layout.addWidget(QLabel("<b>Cess:</b>"), 1, 0)
        fin_layout.addWidget(QLabel(cess_str), 1, 1)
        fin_layout.addWidget(QLabel("<b>Total Demand:</b>"), 1, 2)
        fin_layout.addWidget(QLabel(total_str, styleSheet="font-weight: bold; color: #c0392b;"), 1, 3)
        summary_layout.addWidget(fin_group)

        # Group 3: Timeline & Others
        time_group = QGroupBox("Timeline & Remarks")
        time_group.setStyleSheet("QGroupBox { font-weight: bold; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }")
        time_layout = QGridLayout(time_group)
        time_layout.addWidget(QLabel("<b>Date of Issue:</b>"), 0, 0)
        time_layout.addWidget(QLabel(issue_date_str), 0, 1)
        time_layout.addWidget(QLabel("<b>Last Date to Reply:</b>"), 0, 2)
        time_layout.addWidget(QLabel(reply_date_str, styleSheet="font-weight: bold; color: #d35400;"), 0, 3)
        time_layout.addWidget(QLabel("<b>Copy To:</b>"), 1, 0)
        time_layout.addWidget(QLabel(copy_to), 1, 1)
        time_layout.addWidget(QLabel("<b>Remarks:</b>"), 1, 2)
        time_layout.addWidget(QLabel(remarks), 1, 3)
        summary_layout.addWidget(time_group)

        layout.addWidget(summary_widget)
        
        # --- 2. Document Preview Section ---
        
        # Determine path
        path = None
        if title == "DRC-01A":
            if data.get('DRC01A_HTML_Path') and os.path.exists(data.get('DRC01A_HTML_Path')):
                path = data['DRC01A_HTML_Path']
            elif data.get('DRC01A_Path'):
                path = data['DRC01A_Path']
        elif title == "SCN":
            if data.get('SCN_HTML_Path') and os.path.exists(data.get('SCN_HTML_Path')):
                path = data['SCN_HTML_Path']
            elif data.get('DRC01_Path'):
                path = data['DRC01_Path']
        elif title == "Order":
            if data.get('DRC07_Path'):
                path = data['DRC07_Path']
        
        # Preview Header (Open PDF Button)
        preview_header = QHBoxLayout()
        preview_label = QLabel("Document Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        preview_header.addWidget(preview_label)
        preview_header.addStretch()
        
        if path and path.endswith('.pdf') and os.path.exists(path):
            open_btn = QPushButton("Open PDF")
            open_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; padding: 5px 15px; border-radius: 4px;")
            open_btn.clicked.connect(lambda: os.startfile(path) if os.path.exists(path) else None)
            preview_header.addWidget(open_btn)
            
        layout.addLayout(preview_header)

        # Preview Area or Placeholder
        if not path or not os.path.exists(path):
            placeholder = QLabel(f"No {title} has been generated yet.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #95a5a6; font-size: 14px; font-style: italic; border: 1px dashed #bdc3c7; border-radius: 4px; background: #fdfefe;")
            placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(placeholder)
        else:
            preview = QTextBrowser()
            preview.setStyleSheet("border: 1px solid #bdc3c7; background-color: white;")
            
            if path.endswith('.html'):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    preview.setHtml(html_content)
                except Exception as e:
                    preview.setText(f"Error loading preview: {e}")
            else:
                preview.setText(f"Preview not available for this format.\nFile path: {path}")
                
            layout.addWidget(preview)
        
        self.doc_tabs.addTab(tab_widget, title)

    def handle_next_action(self):
        if not hasattr(self, 'current_case'):
            return
            
        action = self.action_btn.text()
        if action == "Open Workspace":
            self.wizard_callback("workspace", self.current_case)
        elif action == "Draft SCN":
            # Launch Wizard in SCN mode with pre-filled data
            self.wizard_callback("SCN", self.current_case)
        elif action == "Draft Final Order":
             self.wizard_callback("Order", self.current_case)
        else:
             self.wizard_callback("View", self.current_case)

    def show_context_menu(self, position):
        """Show context menu for table items"""
        menu = QMenu()
        
        # Handle right-click on unselected row
        item = self.case_table.itemAt(position)
        if item and not item.isSelected():
            # If clicking outside current selection, select the clicked row
            self.case_table.clearSelection()
            self.case_table.selectRow(item.row())
        
        # Check selection count
        selection = self.case_table.selectionModel().selectedRows()
        count = len(selection)
        
        if count > 0:
            label = "Delete Case" if count == 1 else f"Delete {count} Cases"
            delete_action = menu.addAction(label)
            action = menu.exec(self.case_table.viewport().mapToGlobal(position))
            
            if action == delete_action:
                self.delete_selected_cases()

    def delete_selected_cases(self):
        """Delete all selected cases"""
        selection = self.case_table.selectionModel().selectedRows()
        if not selection:
            return
            
        count = len(selection)
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 'Confirm Deletion', 
            f"Are you sure you want to delete {count} selected case(s)?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            fail_count = 0
            
            # Iterate in reverse order to avoid index issues if we were removing rows directly,
            # though here we just get data and refresh whole table later.
            for index in selection:
                row = index.row()
                case_data = self.case_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                
                if not case_data:
                    continue
                    
                res = False
                if case_data.get('source') == 'sqlite':
                    pid = case_data.get('id')
                    res = self.db.delete_proceeding(pid)
                elif case_data.get('source') == 'csv':
                    case_id = case_data.get('CaseID')
                    res = self.db.delete_csv_case(case_id)
                
                if res:
                    success_count += 1
                else:
                    fail_count += 1
            
            # Show result
            if fail_count == 0:
                QMessageBox.information(self, "Success", f"Successfully deleted {success_count} case(s).")
            else:
                QMessageBox.warning(self, "Partial Success", f"Deleted {success_count} cases.\nFailed to delete {fail_count} cases.")
                
            self.perform_search() # Refresh table
            self.details_widget.setVisible(False) # Hide details
