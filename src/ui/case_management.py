from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTabWidget, QSplitter, QFrame, QMessageBox, QComboBox, QCompleter, QTextBrowser, QGridLayout, QSizePolicy, QMenu)
from PyQt6.QtCore import Qt, QStringListModel
import os
import json
from src.database.db_manager import DatabaseManager
from src.utils.formatting import format_indian_number

class CaseManagement(QWidget):
    def __init__(self, wizard_callback):
        super().__init__()
        self.wizard_callback = wizard_callback # Callback to launch wizard with data
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        # Header
        header_frame = QFrame()
        header_frame.setFixedHeight(50)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 2px solid #3498db;
                border-radius: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        header_label = QLabel("Case Lifecycle Management")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; border: none;")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        self.layout.addWidget(header_frame)

        # Main Content Card
        content_card = QFrame()
        content_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(0, 0, 0, 0) # Splitter handles margins

        # Splitter for Search/List (Left) and Details (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")
        
        # Left Panel: Search & List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)
        
        # Search Bar Area
        search_container = QWidget()
        search_container.setStyleSheet("background: transparent; border: none;")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)
        
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setPlaceholderText("Search by GSTIN or Trade Name...")
        self.search_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QComboBox { 
                padding: 5px 10px; 
                border-radius: 5px; 
                border: 1px solid #bdc3c7; 
                font-size: 13px;
                background: #fdfefe;
            }
            QComboBox:focus { border: 1px solid #3498db; }
            QComboBox::drop-down { border: none; width: 0px; }
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
        search_btn.setFixedSize(100, 40)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; 
                color: white; 
                border-radius: 5px; 
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #2573a7; }
        """)
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)
        left_layout.addWidget(search_container)
        
        # Case List Table
        self.case_table = QTableWidget()
        # New Columns: GSTIN | Legal Name | Section | FY | Status
        columns = ["GSTIN", "Legal Name", "Section", "FY", "Status"]
        self.case_table.setColumnCount(len(columns))
        self.case_table.setHorizontalHeaderLabels(columns)
        
        # Table Styling
        self.case_table.verticalHeader().setVisible(False)
        self.case_table.setShowGrid(False)
        self.case_table.setAlternatingRowColors(True)
        self.case_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.case_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.case_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.case_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
                height: 40px;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #d6eaf8;
                color: #2c3e50;
            }
        """)
        
        header = self.case_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents) # Adjust based on content
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Legal Name gets extra space
        
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
        
        # Note: Previous Metadata Label and Tabs are now created dynamically in load_case_details
        
        splitter.addWidget(self.details_widget)
        splitter.setStretchFactor(1, 2) # Give more space to details
        
        content_layout.addWidget(splitter)
        self.layout.addWidget(content_card)

    def load_gstin_suggestions(self):
        """Load unique GSTINs and Trade Names for auto-complete"""
        try:
            suggestions = set()
            
            # CSV Cases
            csv_cases = self.db.get_all_case_files()
            for c in csv_cases:
                if c.get('GSTIN'): suggestions.add(str(c.get('GSTIN')))
                if c.get('Legal Name'): suggestions.add(str(c.get('Legal Name')))
            
            # SQLite Cases
            sqlite_cases = self.db.get_all_proceedings()
            for c in sqlite_cases:
                if c.get('gstin'): suggestions.add(str(c.get('gstin')))
                if c.get('legal_name'): suggestions.add(str(c.get('legal_name')))
            
            sorted_suggestions = sorted(list(suggestions))
            
            self.search_input.clear()
            self.search_input.addItems(sorted_suggestions)
            self.search_input.setCurrentIndex(-1)
            
            model = QStringListModel(sorted_suggestions)
            self.completer.setModel(model)
            
        except Exception as e:
            print(f"Error loading suggestions: {e}")

    def perform_search(self):
        query = self.search_input.currentText().strip().lower()
        
        all_cases = []
        
        # 1. Get CSV Cases
        csv_cases = self.db.get_all_case_files()
        for c in csv_cases:
            c['source'] = 'csv'
        all_cases.extend(csv_cases)
        
        # 2. Get SQLite Cases
        sqlite_cases = self.db.get_all_proceedings()
        for c in sqlite_cases:
            c['source'] = 'sqlite'
            # Normalize keys
            c['CaseID'] = c.get('id')
            c['Section'] = c.get('initiating_section')
            c['Financial_Year'] = c.get('financial_year')
            c['Status'] = c.get('status')
            c['GSTIN'] = c.get('gstin')
            c['Legal Name'] = c.get('legal_name')
            
        all_cases.extend(sqlite_cases)

        # 3. Get Adjudication Cases (Linked + Direct)
        adj_cases = self.db.get_valid_adjudication_cases()
        for c in adj_cases:
            c['source'] = 'sqlite'
            # Normalize keys
            c['CaseID'] = c.get('id')
            c['Section'] = c.get('adjudication_section') or "Not Set"
            # Fallback for source fields if linked
            c['Financial_Year'] = c.get('financial_year') or c.get('source_fy')
            c['Status'] = c.get('status')
            c['GSTIN'] = c.get('gstin') or c.get('source_gstin')
            c['Legal Name'] = c.get('legal_name') or c.get('source_legal_name')
            
        all_cases.extend(adj_cases)
        
        # Filter if query exists
        if query:
            filtered_cases = []
            for c in all_cases:
                gstin = str(c.get('GSTIN', '')).lower()
                name = str(c.get('Legal Name', '')).lower()
                
                if query in gstin or query in name:
                    filtered_cases.append(c)
            self.populate_table(filtered_cases)
        else:
            self.populate_table(all_cases)

    def populate_table(self, cases):
        self.case_table.setRowCount(len(cases))
        for row, case in enumerate(cases):
            gstin_item = QTableWidgetItem(str(case.get('GSTIN', 'N/A')))
            name_item = QTableWidgetItem(str(case.get('Legal Name', 'N/A')))
            section_item = QTableWidgetItem(str(case.get('Section', 'N/A')))
            fy_item = QTableWidgetItem(str(case.get('Financial_Year', 'N/A')))
            
            status_text = str(case.get('Status', 'Unknown'))
            status_item = QTableWidgetItem(status_text)
            
            # Status Color Coding
            if "Draft" in status_text:
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            elif "Issued" in status_text:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            
            self.case_table.setItem(row, 0, gstin_item)
            self.case_table.setItem(row, 1, name_item)
            self.case_table.setItem(row, 2, section_item)
            self.case_table.setItem(row, 3, fy_item)
            self.case_table.setItem(row, 4, status_item)
            
            # Store full case data in first item
            self.case_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, case)

    def get_safe_val(self, data, keys, default="N/A"):
        """Robustly fetch value using multiple key variations"""
        for k in keys:
            if k in data and data[k] and str(data[k]).strip() != "":
                return str(data[k])
        return default

    def create_info_widget(self, label, value, bold_val=True):
        """Helper to create styled info labels"""
        v_layout = QVBoxLayout()
        l = QLabel(label)
        l.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        v = QLabel(value)
        style = "font-size: 13px; color: #2c3e50;"
        if bold_val: style += " font-weight: bold;"
        v.setStyleSheet(style)
        v_layout.addWidget(l)
        v_layout.addWidget(v)
        return v_layout

    def hydrate_sqlite_case(self, case_data):
        """Fetch and populate missing details for SQLite cases from other tables"""
        try:
            pid = case_data.get('id')
            if not pid: return case_data
            
            # 1. Parse JSON Fields (if not already dicts)
            
            # Demand Details -> Tax Aggregates
            demands = case_data.get('demand_details', [])
            if isinstance(demands, str):
                try: demands = json.loads(demands)
                except: demands = []
            
            cgst = sgst = igst = cess = total = 0.0
            for d in demands:
                breakdown = d.get('tax_breakdown', {})
                
                def safe_float(val):
                    if not val: return 0.0
                    try: return float(val)
                    except: return 0.0

                cgst += safe_float(breakdown.get('CGST', {}).get('tax', 0))
                sgst += safe_float(breakdown.get('SGST', {}).get('tax', 0))
                igst += safe_float(breakdown.get('IGST', {}).get('tax', 0))
                cess += safe_float(breakdown.get('Cess', {}).get('tax', 0))
            
            total = cgst + sgst + igst + cess
            
            case_data["CGST_Demand"] = cgst
            case_data["SGST_Demand"] = sgst
            case_data["IGST_Demand"] = igst
            case_data["Cess_Demand"] = cess
            case_data["Total_Demand"] = total
            
            # Selected Issues -> Description
            issues = case_data.get('selected_issues', [])
            if isinstance(issues, str):
                try: issues = json.loads(issues)
                except: issues = []
            
            if issues:
                issue_titles = [i.get('issue_name', 'Unknown Issue') for i in issues]
                case_data["Issue_Description"] = ", ".join(issue_titles)
            
            # --- NEW: Check additional_details (JSON) for OC Data (Primary) ---
            add_details = case_data.get('additional_details', {})
            if isinstance(add_details, str):
                try: add_details = json.loads(add_details)
                except: add_details = {}
                
            if add_details.get('oc_number'):
                case_data["OC_Number"] = add_details.get('oc_number')
            if add_details.get('oc_date'):
                case_data["OC_Date"] = add_details.get('oc_date')

            # 2. Fetch OC Details from oc_register (Secondary / For older schema)
            try:
                conn = self.db._get_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM oc_register WHERE case_id = ?", (pid,))
                oc_row = cursor.fetchone()
                if oc_row:
                    # SQLite Row to dict
                    cols = [c[0] for c in cursor.description]
                    oc_dict = dict(zip(cols, oc_row))
                    # Only overwrite if not already found in additional_details
                    if not case_data.get("OC_Number"):
                        case_data["OC_Number"] = oc_dict.get('oc_number')
                    if not case_data.get("OC_Date"):
                        case_data["OC_Date"] = oc_dict.get('oc_date')
                conn.close()
            except Exception as e:
                # Table might not exist or connection error, ignore
                pass

                
            # 3. Fetch Document Details (SCN, Order)
            docs = self.db.get_documents(pid)
            if not isinstance(docs, list):
                print(f"Warning: get_documents returned non-list: {type(docs)}")
                docs = []

            for doc in docs:
                if isinstance(doc, str):
                    print(f"Warning: Unexpected string in docs list: {doc}")
                    continue
                    
                doc_type = doc.get('doc_type')
                path = doc.get('snapshot_path')
                updated_at = doc.get('updated_at')
                
                # We need to extract Date/No from somewhere if it's not in the doc record
                # Usually it's in the doc content or a separate register.
                # For now, let's assume we can map the path.
                
                if doc_type == 'SCN':
                    case_data["SCN_HTML_Path"] = path
                    # SCN Date/No might be complex to get if not stored separately.
                    # Fallback to updated_at if needed, or check if we store it in metadata
                elif doc_type == 'Order':
                    case_data["Order_Path"] = path

            return case_data
            
        except Exception as e:
            print(f"Error hydrating case: {e}")
            return case_data

    def load_case_details(self, item):
        row = item.row()
        case_data = self.case_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Hydrate if SQLite
        if case_data.get('source') == 'sqlite':
            case_data = self.hydrate_sqlite_case(case_data)
            
        self.current_case = case_data
        
        # Clear previous details layout
        while self.details_layout.count():
            child = self.details_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # --- 1. GLOBAL HEADER CARD ---
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-left: 5px solid #2980b9;
                border-radius: 4px;
            }
        """)
        header_layout = QVBoxLayout(header_card)
        
        # Extract Data with Fallbacks
        gstin = self.get_safe_val(case_data, ["GSTIN", "gstin"])
        legal_name = self.get_safe_val(case_data, ["Legal Name", "LegalName", "legal_name"])
        trade_name = self.get_safe_val(case_data, ["Trade Name", "TradeName", "trade_name"])
        section = self.get_safe_val(case_data, ["Section", "section", "initiating_section"])
        fy = self.get_safe_val(case_data, ["Financial_Year", "financial_year", "FY"])
        status = self.get_safe_val(case_data, ["Status", "status"], default="Unknown")
        
        # Top Row: Taxpayer Identity
        id_row = QHBoxLayout()
        
        id_row.addLayout(self.create_info_widget("GSTIN", gstin))
        id_row.addLayout(self.create_info_widget("Legal Name", legal_name))
        id_row.addLayout(self.create_info_widget("Trade Name", trade_name))
        id_row.addStretch()
        header_layout.addLayout(id_row)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #ecf0f1;")
        header_layout.addWidget(line)
        
        # Bottom Row: Context
        ctx_row = QHBoxLayout()
        ctx_row.addLayout(self.create_info_widget("Section", section))
        ctx_row.addLayout(self.create_info_widget("Financial Year", fy))
        
        # Status Badge
        status_layout = QVBoxLayout()
        sl = QLabel("Current Status")
        sl.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        sv = QLabel(status)
        
        # Status Color Logic
        bg_col = "#95a5a6" # Grey default
        if "Issued" in status: bg_col = "#27ae60" # Green
        elif "Draft" in status: bg_col = "#f39c12" # Orange
        
        sv.setStyleSheet(f"""
            background-color: {bg_col}; 
            color: white; 
            font-weight: bold; 
            padding: 4px 10px; 
            border-radius: 10px;
        """)
        status_layout.addWidget(sl)
        status_layout.addWidget(sv)
        
        ctx_row.addLayout(status_layout)
        ctx_row.addStretch()
        header_layout.addLayout(ctx_row)
        
        self.details_layout.addWidget(header_card)
        
        # --- 2. TABS ---
        self.doc_tabs = QTabWidget()
        self.details_layout.addWidget(self.doc_tabs)
        
        # Populate Tabs
        self.setup_tab("DRC-01A", case_data)
        self.setup_tab("SCN", case_data)
        self.setup_tab("PH Intimation", case_data)
        self.setup_tab("Order", case_data)
        
        # --- 3. ACTION BUTTON (Bottom) ---
        self.action_btn = QPushButton("Proceed to Next Action")
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980b9; color: white; padding: 12px; 
                font-weight: bold; border-radius: 4px;
            }
            QPushButton:hover { background-color: #3498db; }
        """)
        self.action_btn.clicked.connect(self.handle_next_action)
        self.details_layout.addWidget(self.action_btn)
        
        # Update Button Text based on Status - STRICTER LOGIC
        self.action_btn.setEnabled(True)
        # Check specific Issued states first
        if "DRC-01A Issued" in status: 
             self.action_btn.setText("Draft SCN")
        elif "SCN Issued" in status: 
             self.action_btn.setText("Issue PH Intimation")
        elif "PH Issued" in status: 
             self.action_btn.setText("Draft Final Order")
        
        # Check Draft states
        elif "SCN" in status: # SCN Draft or similar
             self.action_btn.setText("Resume SCN Draft")
        elif "Order" in status:
             self.action_btn.setText("Resume Order Draft")
        elif "Draft" in status:
             self.action_btn.setText("Resume Draft")
        else: 
             self.action_btn.setText("View / Edit Case")

        self.details_widget.setVisible(True)

    def setup_tab(self, title, data):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Check if Document is Issued/Finalized
        is_issued = False
        status = self.get_safe_val(data, ["Status", "status"])
        
        # Determine specific paths/refs
        doc_path = None
        doc_ref = "N/A"
        doc_date = "N/A"
        oc_no = self.get_safe_val(data, ["OC_Number", "oc_number"])
        
        if title == "DRC-01A":
            if "DRC-01A Issued" in status or "SCN" in status or "Order" in status: is_issued = True
            doc_ref = oc_no # For DRC-01A, OC No is the ref
            doc_date = self.get_safe_val(data, ["OC_Date", "oc_date"])
            doc_path = self.get_safe_val(data, ["DRC01A_HTML_Path", "DRC01A_Path"], default="")
            
        elif title == "SCN":
            if "SCN Issued" in status or "Order" in status: is_issued = True
            doc_ref = self.get_safe_val(data, ["SCN_Number", "scn_number"])
            doc_date = self.get_safe_val(data, ["SCN_Date", "scn_date"])
            doc_path = self.get_safe_val(data, ["SCN_HTML_Path", "SCN_Path"], default="")
            
        elif title == "Order":
            if "Order Issued" in status: is_issued = True
            doc_ref = self.get_safe_val(data, ["OIO_Number", "oio_number"])
            doc_date = self.get_safe_val(data, ["OIO_Date", "oio_date"])
            doc_path = self.get_safe_val(data, ["DRC07_Path", "Order_Path"], default="")

        # RENDER CONTENT
        if not is_issued:
            # Placeholder State
            ph_layout = QVBoxLayout()
            msg = QLabel(f"{title} is not yet issued.")
            msg.setStyleSheet("color: #7f8c8d; font-size: 14px; font-style: italic;")
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ph_layout.addWidget(msg)
            
            if title == "DRC-01A" and "Draft" in status:
                btn = QPushButton("Resume Draft")
                btn.setStyleSheet("background-color: #2ecc71; color: white;")
                btn.clicked.connect(lambda: self.wizard_callback("workspace", self.current_case))
                ph_layout.addWidget(btn)
                
            ph_layout.addStretch()
            layout.addLayout(ph_layout)
            self.doc_tabs.addTab(tab_widget, title)
            return

        # --- IS ISSUED: SHOW DETAILS ---
        
        # A. Reference Row
        ref_frame = QFrame()
        ref_frame.setStyleSheet("background: #f8f9fa; border-radius: 4px; padding: 5px;")
        ref_layout = QHBoxLayout(ref_frame)
        
        def add_ref(label, val):
            v_box = QVBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("font-size: 10px; color: #7f8c8d;")
            v = QLabel(val)
            v.setStyleSheet("font-weight: bold; color: #2c3e50;")
            v_box.addWidget(l)
            v_box.addWidget(v)
            ref_layout.addLayout(v_box)
            
        add_ref("OC No.", oc_no)
        add_ref(f"{title} No.", doc_ref)
        add_ref("Issue Date", doc_date)
        ref_layout.addStretch()
        
        # View PDF Button
        if doc_path and os.path.exists(doc_path):
            view_btn = QPushButton("View Document")
            view_btn.setStyleSheet("background: white; border: 1px solid #3498db; color: #3498db;")
            view_btn.clicked.connect(lambda: os.startfile(doc_path) if os.path.exists(doc_path) else None)
            ref_layout.addWidget(view_btn)
            
        layout.addWidget(ref_frame)
        
        # B. Issues List
        try:
            cgst = float(self.get_safe_val(data, ["CGST_Demand"], "0"))
            sgst = float(self.get_safe_val(data, ["SGST_Demand"], "0"))
            igst = float(self.get_safe_val(data, ["IGST_Demand"], "0"))
            cess = float(self.get_safe_val(data, ["Cess_Demand"], "0"))
            total = float(self.get_safe_val(data, ["Total_Demand"], "0"))
        except:
            cgst=sgst=igst=cess=total=0.0
            
        issues_title = QLabel("Issues Involved")
        issues_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(issues_title)
        
        issue_desc = self.get_safe_val(data, ["Issue_Description"], "Details available in document")
        issue_row = QHBoxLayout()
        bullet = QLabel("•")
        lbl = QLabel(f"{issue_desc}")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #34495e;")
        issue_row.addWidget(bullet)
        issue_row.addWidget(lbl)
        
        demand_lbl = QLabel(f"(Total Demand: {format_indian_number(total, prefix_rs=True)})")
        demand_lbl.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        issue_row.addWidget(demand_lbl)
        
        layout.addLayout(issue_row)
        
        # C. Summary Tax Table
        table_title = QLabel("Summary of Tax Demand")
        table_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(table_title)
        
        tax_table = QTableWidget()
        tax_table.setColumnCount(5)
        tax_table.setHorizontalHeaderLabels(["Act", "Tax", "Interest", "Penalty", "Total"])
        tax_table.verticalHeader().setVisible(False)
        tax_table.setFixedHeight(120)
        
        h = tax_table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tax_table.setStyleSheet("QHeaderView::section { background: #ecf0f1; font-weight: bold; border: none; }")
        
        acts = [("CGST", cgst), ("SGST", sgst), ("IGST", igst), ("Cess", cess)]
        tax_table.setRowCount(0)
        row_idx = 0
        for act, amt in acts:
            if amt > 0:
                tax_table.insertRow(row_idx)
                tax_table.setItem(row_idx, 0, QTableWidgetItem(act))
                tax_table.setItem(row_idx, 1, QTableWidgetItem(format_indian_number(amt)))
                tax_table.setItem(row_idx, 2, QTableWidgetItem(format_indian_number(0))) 
                tax_table.setItem(row_idx, 3, QTableWidgetItem(format_indian_number(0))) 
                tax_table.setItem(row_idx, 4, QTableWidgetItem(format_indian_number(amt)))
                row_idx += 1
                
        layout.addWidget(tax_table)
        
        # D. Critical Dates (DRC-01A Only)
        if title == "DRC-01A":
            dates_frame = QFrame()
            dates_frame.setStyleSheet("background: #fdf2e9; border: 1px solid #fae5d3; border-radius: 4px; margin-top: 10px;")
            df_layout = QHBoxLayout(dates_frame)
            
            # Calculate Reply Date
            reply_date = "N/A"
            if doc_date != "N/A":
                try:
                    from datetime import datetime, timedelta
                    # Clean date string (remove time if present)
                    doc_date_clean = doc_date.split(' ')[0]
                    
                    if '/' in doc_date_clean:
                        fmt = "%d/%m/%Y"
                    else:
                        fmt = "%Y-%m-%d" # SQLite default
                        
                    d = datetime.strptime(doc_date_clean, fmt)
                    reply_date = (d + timedelta(days=30)).strftime("%d/%m/%Y")
                except Exception as e:
                    print(f"Date parse error: {e}")
                
            df_layout.addLayout(self.create_info_widget("Last Date to Reply", reply_date))
            df_layout.addLayout(self.create_info_widget("Last Date for Payment", reply_date)) # Usually same
            df_layout.addStretch()
            layout.addWidget(dates_frame)
            
        layout.addStretch()
        self.doc_tabs.addTab(tab_widget, title)

    def handle_next_action(self):
        if not hasattr(self, 'current_case'):
            return
            
        action = self.action_btn.text()
        if action == "Open Workspace":
            self.wizard_callback("workspace", self.current_case)
        elif action == "Draft SCN":
            self.wizard_callback("SCN", self.current_case)
        elif action == "Resume SCN Draft":
            self.wizard_callback("SCN", self.current_case)
        elif action == "Draft Final Order":
             self.wizard_callback("Order", self.current_case)
        elif action == "View / Edit Case":
             self.wizard_callback("View", self.current_case)
        else:
             self.wizard_callback("View", self.current_case)

    def show_context_menu(self, position):
        """Show context menu for table items"""
        menu = QMenu()
        
        item = self.case_table.itemAt(position)
        if item and not item.isSelected():
            self.case_table.clearSelection()
            self.case_table.selectRow(item.row())
        
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
        
        reply = QMessageBox.question(
            self, 'Confirm Deletion', 
            f"Are you sure you want to delete {count} selected case(s)?\\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            fail_count = 0
            
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
            
            if fail_count == 0:
                QMessageBox.information(self, "Success", f"Successfully deleted {success_count} case(s).")
            else:
                QMessageBox.warning(self, "Partial Success", f"Deleted {success_count} cases.\\nFailed to delete {fail_count} cases.")
                
            self.perform_search() # Refresh table
            self.details_widget.setVisible(False) # Hide details
