from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QGridLayout, QCheckBox, QAbstractItemView)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from src.ui.rich_text_editor import RichTextEditor
from src.ui.components.modern_card import ModernCard
from src.ui.ui_helpers import render_grid_to_table_widget
from src.utils.formatting import format_indian_number

class IssueCard(QFrame):
    # Signal emitted when any value changes, passing the calculated totals
    valuesChanged = pyqtSignal(dict)
    # Signal emitted when remove button is clicked
    removeClicked = pyqtSignal()
    # Signal emitted when editor content changes
    contentChanged = pyqtSignal()

    def __init__(self, template, data=None, parent=None, mode="DRC-01A", content_key="content", save_template_callback=None, issue_number=None):

        super().__init__(parent)
        self.template = template
        if data and 'table_data' in data:
             # Force injection into template so init_ui picks it up
             if isinstance(data['table_data'], list):
                 self.template['grid_data'] = data['table_data']
             elif isinstance(data['table_data'], dict):
                 if 'tables' not in self.template:
                     self.template['tables'] = {}
                 self.template['tables'].update(data['table_data'])
        
        self.mode = mode
        self.content_key = content_key
        
        # Merge variables from template and data
        self.variables = template.get('variables', {}).copy()
        if data and 'variables' in data:
            self.variables.update(data['variables'])
            
        self.calc_logic = template.get('calc_logic', "")
        self.tax_mapping = template.get('tax_demand_mapping', {})
        self.data_snapshot = {} # To preserve other data (like DRC-01A content when in SCN mode)
        
        self.save_template_callback = save_template_callback # Store callback
        self.issue_number = issue_number
        self.is_read_only = False
        self.source_text = ""
        self.is_included = True
        self.source_type = None
        self.source_issue_id = None
        
        # --- Authoritative Model Fields ---
        self.origin = data.get('origin', "SCN") if data else "SCN"
        self.status = data.get('status', "ACTIVE") if data else "ACTIVE"
        self.drop_reason = data.get('drop_reason') if data else None
        self.source_issue_id = data.get('source_issue_id') if data else None
        self.is_adopted = True # SCN Workflow State Authority
        
        # Narrative-Numeric Consistency Safeguard
        self.last_rendered_html = "" # Detection baseline
        
        self.init_ui()
        
        # Initial calculation and classification
        self.set_classification(self.origin, self.status)
        self.calculate_values() 


    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("IssueCard { background-color: #ffffff; border: 1px solid #bdc3c7; border-radius: 5px; margin-bottom: 10px; }")
        
        layout = QVBoxLayout(self)
        
        # Wrapper for Header + Body
        self.main_layout = QVBoxLayout()
        layout.addLayout(self.main_layout) # Use main_layout instead of adding directly to self
        
        # Header
        header_layout = QHBoxLayout()
        base_title = self.template.get('issue_name', 'Issue')
        # Also check 'category' if issue_name is generic or missing (common in scrutiny issues)
        if base_title == 'Issue' or not base_title:
             base_title = self.template.get('category', 'Issue')
             
        title_text = base_title
        if self.mode == "SCN":
             title_text += " (SCN Draft)"
             
        # "Issue <n> – <Name>" Format
        if self.issue_number:
            title_text = f"Issue {self.issue_number} – {title_text}"
            
        self.title = QLabel(f"<b>{title_text}</b>")
        self.title.setStyleSheet("font-size: 14px; color: #2c3e50;")
        header_layout.addWidget(self.title)

        # Source Badge
        self.source_badge = QLabel("")
        self.source_badge.hide()
        self.source_badge.setStyleSheet("""
            QLabel {
                background-color: #e8f0fe;
                color: #1a73e8;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid #d2e3fc;
            }
        """)
        header_layout.addWidget(self.source_badge)

        
        self.main_layout.addLayout(header_layout) # Add header to main layout
        header_layout.addStretch()
        
        # Inclusion Checkbox
        self.include_cb = QCheckBox("Include in SCN")
        self.include_cb.setChecked(True)
        self.include_cb.hide()
        self.include_cb.stateChanged.connect(self._on_inclusion_changed)
        header_layout.addWidget(self.include_cb)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 3px;")
        self.remove_btn.clicked.connect(self.handle_remove_or_drop)
        header_layout.addWidget(self.remove_btn)
        
        
        # --- Body Wrapper (Stacked for Overlay) ---
        from PyQt6.QtWidgets import QStackedLayout
        self.body_container = QWidget()
        self.body_stack = QStackedLayout(self.body_container)
        self.body_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Layer 1: Content
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0,0,0,0)
        
        # Section 1: Table (Collapsible)
        table_card = ModernCard("Table", collapsible=True)
        
        # [PART B DIAG] LOG: UI Branch Selection
        issue_id = self.template.get('issue_id')
        if issue_id == 'IMPORT_ITC_MISMATCH':
             print(f"[SOP-10 UI DIAG] init_ui: Issue ID={issue_id}")
             print(f"[SOP-10 UI DIAG] Template Keys: {list(self.template.keys())}")
             print(f"[SOP-10 UI DIAG] Has 'grid_data'? {bool(self.template.get('grid_data'))}")
             print(f"[SOP-10 UI DIAG] Has 'tables'? {bool(self.template.get('tables'))}")
             print(f"[SOP-10 UI DIAG] Has 'summary_table'? {bool(self.template.get('summary_table'))}")
             
             # [LOG 5] Explicitly Check Layout Clearing
             # Although init_ui creates new widgets, if re-used, we check if layout is clean.
             print(f"[SOP-10 DIAG] Clearing layout check: Layout count before add: {content_layout.count()}")

        # Check if we have grid_data (Excel Import) or legacy placeholders
        if 'grid_data' in self.template and self.template['grid_data']:
             if issue_id == 'IMPORT_ITC_MISMATCH': print("[SOP-10 UI DIAG] Branch: init_grid_ui (grid_data)")
             self.init_grid_ui(table_card)
        elif self.template.get('summary_table'):
             # SOP-10 / ASMT-10 Unified Schema Support
             if issue_id == 'IMPORT_ITC_MISMATCH': print("[SOP-10 UI DIAG] Branch: init_grid_ui (summary_table)")
             # Map 'summary_table' to 'grid_data' expected by renderer if grid_data is missing
             self.init_grid_ui(table_card, data=self.template['summary_table'])
        elif 'tables' in self.template and isinstance(self.template['tables'], list):
            # SOP-5 Multi-Table Support
            for tbl in self.template['tables']:
                if tbl.get('title'):
                    # Helper title - QLabel is already imported at module level
                    t_lbl = QLabel(f"<b>{tbl.get('title')}</b>")
                    t_lbl.setStyleSheet("color: #34495e; margin-top: 10px; margin-bottom: 5px;")
                    table_card.addWidget(t_lbl)
                self.init_grid_ui(table_card, data=tbl)
        elif isinstance(self.template.get('tables'), dict):
            self.init_excel_table_ui(table_card)
            
        # Also load legacy placeholders if they exist (Hybrid Mode)
        if self.template.get('placeholders'):
            self.init_legacy_ui(table_card)
            
        content_layout.addWidget(table_card)
            
        # Mini Totals (Read Only)
        totals_layout = QHBoxLayout()
        totals_layout.addWidget(QLabel("<b>Calculated Demand:</b>"))
        
        # Section 0: Demand Summary in Header
        self.tax_badge = QLabel("")
        self.tax_badge.setStyleSheet("""
            QLabel {
                background-color: #e8f8f5;
                color: #27ae60;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #d1f2eb;
            }
        """)
        self.tax_badge.hide()
        header_layout.insertWidget(2, self.tax_badge) # After title and source badge
        
        self.lbl_tax = QLabel("Tax: Rs. 0")
        self.lbl_interest = QLabel("Interest: Rs. 0")
        self.lbl_penalty = QLabel("Penalty: Rs. 0")
        
        for lbl in [self.lbl_tax, self.lbl_interest, self.lbl_penalty]:
            lbl.setStyleSheet("background-color: #ecf0f1; padding: 5px; border-radius: 3px; border: 1px solid #bdc3c7;")
            totals_layout.addWidget(lbl)
            
        totals_layout.addStretch()
        content_layout.addLayout(totals_layout)
        
        # Section 2: Brief Facts (Collapsible)
        label_text = "Draft Content" if self.mode == "SCN" else "Brief Facts & Grounds"
        facts_card = ModernCard(label_text, collapsible=True)
        self.editor = RichTextEditor()
        self.editor.setMinimumHeight(150)
        self.update_editor_content()
        self.editor.textChanged.connect(self.contentChanged.emit)
        facts_card.addWidget(self.editor)
        
        # Narration Sync Warning
        self.sync_warning = QLabel("⚠️ Narration out of sync with Table (Manual edits detected)")
        self.sync_warning.setStyleSheet("color: #e67e22; font-size: 11px; font-weight: bold; margin-bottom: 5px;")
        self.sync_warning.hide()
        facts_card.addWidget(self.sync_warning)
        
        content_layout.addWidget(facts_card)
        
        # Add Content to Stack
        self.body_stack.addWidget(self.content_widget)
        
        # Layer 2: Blocking Overlay (Only covers body)
        self.overlay = QFrame()
        self.overlay.setStyleSheet("background-color: rgba(255, 255, 255, 180); border-radius: 5px;")
        self.overlay.hide()
        self.body_stack.addWidget(self.overlay)
        
        # Add Body to Main Layout
        self.main_layout.addWidget(self.body_container)
        
    def _on_inclusion_changed(self, state):
        if self.origin == "ASMT10":
            # RE-ENFORCE: Include/Exclude forbidden for derived issues
            self.include_cb.setChecked(True)
            return
 
        self.is_included = (state == 2) # Qt.CheckState.Checked
        self.overlay.setVisible(not self.is_included)
        if not self.is_included:
            self.overlay.raise_()
        self.valuesChanged.emit(self.get_tax_breakdown())
 
    def set_classification(self, origin="SCN", status="ACTIVE", drop_reason=None):
        """Flexible Classification Setter (Informational)"""
        self.origin = origin
        self.status = status
        
        # 1. Informational Badge (Strict DECLARATIVE Mapping)
        # origin -> (Text, BgColor, TextColor, BorderColor)
        
        # Normalize origin for mapping
        canonical_origin = origin.upper() if origin else "SCN"
        if canonical_origin == "ASMT10": canonical_origin = "SCRUTINY"
        
        if canonical_origin == "SCRUTINY":
            self.set_source("Adopted from ASMT-10")
            # Style: Muted Blue
            self.source_badge.setStyleSheet("""
                QLabel { background-color: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; border: 1px solid #d2e3fc; }
            """)
        elif canonical_origin == "MANUAL_SOP":
            self.set_source("Manual – SOP")
            # Style: Muted Grey
            self.source_badge.setStyleSheet("""
                QLabel { background-color: #f1f3f4; color: #5f6368; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; border: 1px solid #dadce0; }
            """)
        else:
            self.set_source("New Issue (SCN)")
            # Default Style: Red
            self.source_badge.setStyleSheet("""
                QLabel { background-color: #fce8e6; color: #c5221f; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold; border: 1px solid #fad2cf; }
            """)

        # 2. Universal Flexibility
        self.include_cb.show()
        self.remove_btn.setText("Remove")
        self.remove_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 3px;")
        
        # Reset visual styles to standard
        self.setStyleSheet("IssueCard { background-color: #ffffff; border: 1px solid #bdc3c7; border-radius: 5px; margin-bottom: 10px; }")
        self.title.setStyleSheet("span { color: #2c3e50; font-weight: bold; }")
        
        # Ensure interactive state
        if hasattr(self, 'editor'):
            self.editor.set_read_only(False)
            self.editor.setStyleSheet("") # Clear any custom dashed borders
 
    def handle_remove_or_drop(self):
        """Handle issue removal with optional confirmation for derived issues"""
        if self.origin == "ASMT10":
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(self, "Confirm Removal", 
                                       "This issue was derived from ASMT-10. Are you sure you want to remove it from the SCN proposal?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.removeClicked.emit()
        else:
            self.removeClicked.emit()
 
    def set_source(self, source_text):
        """Set source badge text (e.g., 'From ASMT-10')"""
        self.source_text = source_text
        if source_text:
            self.source_badge.setText(source_text)
            self.source_badge.show()
        else:
            self.source_badge.hide()

    def set_adoption_mode(self, enabled):
        """Legacy placeholder - redirected to set_classification"""
        if enabled:
            self.set_classification("ASMT10", "ACTIVE")
        else:
            self.set_classification("SCN", "ACTIVE")

    def set_source_metadata(self, source_type, source_issue_id):
        """Store source metadata for persistence"""
        self.source_type = source_type
        self.source_issue_id = source_issue_id
        label = f"From {source_type}"
        self.set_source(label)

    def set_read_only(self, read_only):
        self.is_read_only = read_only
        
        # Simple, universal application for Flexible model
        if hasattr(self, 'editor'):
            if hasattr(self.editor, "set_read_only"):
                 self.editor.set_read_only(read_only)
            else:
                 self.editor.setEnabled(not read_only)
        
        # Table
        if hasattr(self, 'table'):
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers if read_only else QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
            # Do NOT disable the table entirely if you want scrolling/selection, just triggers
            # self.table.setEnabled(not read_only)
            
        # Legacy inputs
        if hasattr(self, 'input_widgets'):
            for widget in self.input_widgets.values():
                widget.setReadOnly(read_only)
                widget.setEnabled(not read_only)

    def init_excel_table_ui(self, layout):
        """Initialize UI from Excel-like Table Builder Data"""
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        import re
        
        table_data = self.template['tables']
        rows = table_data.get('rows', 4)
        cols = table_data.get('cols', 4)
        cells = table_data.get('cells', [])
        
        self.table = QTableWidget(rows, cols)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.cell_formulas = {} # (row, col) -> formula_string
        
        for r in range(rows):
            row_data = cells[r] if r < len(cells) else []
            for c in range(cols):
                txt = row_data[c] if c < len(row_data) else ""
                item = QTableWidgetItem(txt)
                
                # Check for formula
                if txt.startswith('='):
                    self.cell_formulas[(r, c)] = txt[1:] # Store without '='
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setForeground(Qt.GlobalColor.blue)
                    item.setText("0") # Initial value
                elif r == 0 or c == 0:
                    # Headers (First row/col)
                    item.setBackground(Qt.GlobalColor.lightGray)
                    item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                
                self.table.setItem(r, c, item)
        
        self.table.itemChanged.connect(self.on_excel_table_changed)
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(400)
        # Prevent table from forcing window width too wide
        from PyQt6.QtWidgets import QSizePolicy
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.table)
        
        # Initial Calc will be triggered by calculate_values in __init__

    def on_excel_table_changed(self, item):
        # Avoid recursion
        if self.table.signalsBlocked(): return
        self.calculate_excel_table()

    def calculate_excel_table(self):
        """Evaluate formulas in the Excel-like table"""
        import re
        
        # Helper to get cell value
        def get_cell_val(ref):
            # ref is like "A1", "B2"
            # Parse ref
            match = re.match(r"([A-Z]+)([0-9]+)", ref.upper())
            if not match: return 0
            
            col_str, row_str = match.groups()
            
            # Convert col_str to index (A=0, B=1, AA=26)
            col = 0
            for char in col_str:
                col = col * 26 + (ord(char) - ord('A') + 1)
            col -= 1
            
            row = int(row_str) - 1
            
            if row < 0 or row >= self.table.rowCount() or col < 0 or col >= self.table.columnCount():
                return 0
                
            item = self.table.item(row, col)
            if not item: return 0
            
            try:
                return float(item.text())
            except:
                return 0

        # Iterate formulas
        # Simple 2-pass for dependencies
        for _ in range(2):
            for (r, c), formula in self.cell_formulas.items():
                try:
                    # Replace references with values
                    # Regex to find A1, B2 etc.
                    # We use a callback to replace
                    def replace_ref(match):
                        return str(get_cell_val(match.group(0)))
                    
                    eval_expr = re.sub(r"[A-Z]+[0-9]+", replace_ref, formula.upper())
                    
                    # Safe Eval
                    allowed_names = {"abs": abs, "min": min, "max": max, "round": round}
                    res = eval(eval_expr, {"__builtins__": {}}, allowed_names)
                    
                    # Update Item
                    item = self.table.item(r, c)
                    if item:
                        self.table.blockSignals(True)
                        item.setText(str(res))
                        self.table.blockSignals(False)
                        
                except Exception as e:
                    print(f"Formula Error {formula}: {e}")
                    pass
        
        # Populate variables with all cell values for placeholders
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        for r in range(rows):
            for c in range(cols):
                item = self.table.item(r, c)
                if item:
                    val = item.text()
                    # Get address
                    col_label = ""
                    temp = c
                    while temp >= 0:
                        col_label = chr(ord('A') + (temp % 26)) + col_label
                        temp = (temp // 26) - 1
                    
                    addr = f"{col_label}{r+1}"
                    self.variables[addr] = val
                    
        # Trigger update of editor content to reflect new variable values
        self.update_editor_content()
        self.calculate_values() # Centralized badge and signal update

    # Removed duplicate get_tax_breakdown


    def init_grid_ui(self, layout, data=None):
        """Initialize UI from Excel Grid Data"""
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        
        # [SOP-10 EXPAND] Checkpoint
        # We hook here because this renders the table content
        if self.template.get('issue_id') == 'IMPORT_ITC_MISMATCH':
             import hashlib
             import json
             def _safe_hash(d):
                 try:
                     s = json.dumps(d, sort_keys=True, default=str)
                     return hashlib.sha1(s.encode()).hexdigest()
                 except: return "HASH_ERR"
                 
             print(f"\n[SOP-10 EXPAND] Issue ID: {self.template.get('issue_id')}")
             print(f"[SOP-10 EXPAND] Template Type: {self.template.get('template_type')}")
             print(f"[SOP-10 EXPAND] Summary Table: {self.template.get('summary_table')}")
             st = self.template.get('summary_table')
             print(f"[SOP-10 EXPAND] ID(Summary Table): {id(st)}")
             print(f"[SOP-10 EXPAND] ID(Summary Rows): {id(st.get('rows')) if st else 'N/A'}")
             print(f"[SOP-10 EXPAND] Hash: {_safe_hash(self.template)}")

        grid_data = data if data else self.template.get('grid_data')
        if not grid_data:
            return
            
        self.table = QTableWidget()
        self.table.itemChanged.connect(self.on_grid_item_changed)
        
        # Unified Renderer (Interactive Mode)
        # Helper handles columns/rows/style/flags and returns widgets map
        self.cell_widgets = render_grid_to_table_widget(self.table, grid_data, interactive=True)

        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(400)
        from PyQt6.QtWidgets import QSizePolicy
        
        # [FIX] SOP-5/SOP-7 UI WIDTH & LAYOUT
        # Determine if this is a 'tables' payload (SOP-5/7) or legacy grid_data
        # 'data' argument is populated only when iterating over 'tables'
        is_expanded_table = (data is not None) or (self.template.get('issue_id') in ['TDS_TCS_MISMATCH', 'CANCELLED_SUPPLIERS'])
        
        if is_expanded_table:
             # Force expansion for Detailed Tables
             self.table.setMinimumWidth(900)
             self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
             
             # Force Header Stretch
             header = self.table.horizontalHeader()
             header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             
             # Apply layout stretch
             layout.addWidget(self.table, stretch=1)
        else:
             # Legacy Behavior for SOP-2/3/4/etc
             self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
             layout.addWidget(self.table)
        
        # Provenance Note (Dict Schema Safe)
        rows = grid_data.get('rows', [])
        columns = grid_data.get('columns', [])
        
        if rows and columns:
             for col in columns:
                  col_id = col.get('id')
                  if not col_id: continue
                  
                  first_cell = rows[0].get(col_id, {})
                  if isinstance(first_cell, dict):
                       source = first_cell.get('source')
                       if source:
                           origin = source.get("origin", "ASMT10")
                           asmt_id = source.get("asmt_id", "N/A")
                           dt = source.get("converted_on", "")
                           if dt and "T" in dt: dt = dt.split("T")[0]
                  
                           note = QLabel(f"<i>Source: Adopted from {origin} (Case: {asmt_id}) | Date: {dt}</i>")
                           note.setStyleSheet("color: #7f8c8d; font-size: 10px; padding-left: 5px;")
                           layout.addWidget(note)
                           break # Only show once

    def init_legacy_ui(self, layout):
        """Initialize UI from legacy placeholders"""
        inputs_layout = QGridLayout()
        self.input_widgets = {}
        
        placeholders = self.template.get('placeholders', [])
        row = 0
        col = 0
        
        for p in placeholders:
            if p.get('computed'):
                continue
                
            label = QLabel(p['name'].replace('_', ' ').title() + ":")
            inputs_layout.addWidget(label, row, col)
            
            inp = QLineEdit()
            inp.setText(str(self.variables.get(p['name'], '')))
            inp.textChanged.connect(lambda val, name=p['name']: self.update_variable(name, val))
            self.input_widgets[p['name']] = inp
            inputs_layout.addWidget(inp, row, col + 1)
            
            col += 2
            if col > 2:
                col = 0
                row += 1
                
        layout.addLayout(inputs_layout)

    def on_grid_item_changed(self, item):
        """Handle changes in grid table"""
        cell_info = item.data(Qt.ItemDataRole.UserRole)
        if not cell_info:
            return
            
        # Update variable
        var_name = cell_info.get('var')
        text = item.text()
        
        try:
            val = float(text)
        except ValueError:
            val = text
            
        self.variables[var_name] = val
        
        # 1. Update numeric totals
        self.calculate_values()
        
        # 2. Narration Sync: Auto-refresh brief-facts/draft content
        self.update_editor_content(is_recalculation=True)

    def update_variable(self, name, value):
        self.variables[name] = value
        self.calculate_values()

    def calculate_values(self):
        # 1. Handle Excel Grid Calculation
        if 'grid_data' in self.template and self.template['grid_data']:
            self.calculate_grid()
        
        # SOP-5 Multi-Table Support
        if 'tables' in self.template and isinstance(self.template['tables'], list):
            for tbl in self.template['tables']:
                 self.calculate_grid(data=tbl)

        elif isinstance(self.template.get('tables'), dict) and self.template['tables'].get('rows', 0) > 0:
            self.calculate_excel_table()
            
        # 2. Handle Legacy Python Logic
        # (Execute legacy logic even if grid exists, to allow hybrid calcs)
        if self.calc_logic:
            try:
                local_scope = {}
                exec(self.calc_logic, {}, local_scope)
                compute_func = local_scope.get('compute')
                
                if compute_func:
                    results = compute_func(self.variables)
                    self.variables.update(results)
            except Exception as e:
                print(f"Legacy Calculation Error: {e}")

        # 3. Update UI
        self.refresh_totals_ui()

    def refresh_totals_ui(self):
        """Update Tax/Interest/Penalty labels and signals based on current variables"""
        tax = 0
        interest = 0
        penalty = 0
        
        mapping = self.tax_mapping
        
        # Helper to get value from mapping
        def get_val(key):
            ref_var = mapping.get(key)
            if not ref_var: return 0
            val = self.variables.get(ref_var, 0)
            try: return float(val)
            except: return 0
                
        if 'grid_data' in self.template or isinstance(self.template.get('tables'), list):
            tax = get_val('tax_cgst') + get_val('tax_sgst') + get_val('tax_igst') + get_val('tax_cess')
            if not tax: tax = get_val('tax')
            interest = get_val('interest')
            penalty = get_val('penalty')
        else:
            tax = self.variables.get(mapping.get('tax', 'calculated_tax'), 0)
            interest = self.variables.get(mapping.get('interest', 'calculated_interest'), 0)
            penalty = self.variables.get(mapping.get('penalty', 'calculated_penalty'), 0)

        # Update header badge
        if hasattr(self, 'tax_badge'):
            formatted_tax = format_indian_number(tax, prefix_rs=True)
            self.tax_badge.setText(f"Tax: {formatted_tax}")
            self.tax_badge.show()

        self.valuesChanged.emit({
            'tax': tax,
            'interest': interest,
            'penalty': penalty
        })

    def calculate_grid(self, data=None):
        """Evaluate formulas in the grid"""
        # Simple iterative pass (can be improved to topological sort)
        # We do 2 passes to handle simple forward references
        
        grid_data = data if data else self.template.get('grid_data')
        if not grid_data: return
        
        for _ in range(2): 
            for r, row_data in enumerate(grid_data):
                for c, cell_info in enumerate(row_data):
                    if cell_info.get('type') == 'formula':
                        formula = cell_info.get('python_formula')
                        if not formula: continue
                        
                        try:
                            # Evaluate formula using current variables
                            # We expose 'v' as the variables dict
                            # Also expose 'round', 'max', 'min' etc.
                            context = {
                                'v': self.variables,
                                'round': round,
                                'max': max,
                                'min': min,
                                'abs': abs
                            }
                            
                            result = eval(formula, {}, context)
                            
                            # Update variable
                            var_name = cell_info.get('var')
                            self.variables[var_name] = result
                            
                            # Update UI
                            item = self.cell_widgets.get(var_name)
                            if item:
                                # Block signal to prevent recursion
                                self.table.blockSignals(True)
                                item.setText(str(result))
                                self.table.blockSignals(False)
                                
                        except Exception as e:
                            print(f"Formula Error {formula}: {e}")
                            # pass

    # Removed duplicate empty calculate_excel_table


    def extract_html_body(self, html):
        """Extract content from body tag to avoid nested html document issues"""
        import re
        if not html: return ""
        match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return html

    def _validate_template_variables(self, template_text: str, variables: dict) -> list:
        """Extract all {{ placeholders }} and check if they exist in variables."""
        import re
        placeholders = re.findall(r'\{\{\s*(.*?)\s*\}\}', template_text)
        unresolved = [p for p in placeholders if p not in variables]
        return unresolved

    def update_editor_content(self, is_recalculation=False):
        """Populate editor with template text. Syncs with variables."""
        import re
        t = self.template.get('templates', {})
        
        # SAFEGUARD: Detection of manual edits
        current_html = self.editor.toHtml()
        if is_recalculation and self.last_rendered_html:
            # Check if user modified the text since last render
            # (Strip whitespace for robust comparison)
            if self.extract_html_body(current_html).strip() != self.extract_html_body(self.last_rendered_html).strip():
                if hasattr(self, 'sync_warning'):
                    self.sync_warning.show()
                return
        
        if hasattr(self, 'sync_warning'):
            self.sync_warning.hide()

        def get_content(key):
            raw = t.get(key, '')
            return self.extract_html_body(raw)
        
        # 1. Determine Brief Facts content based on mode
        if self.mode == "SCN":
            brief_facts = get_content('brief_facts_scn')
            if not brief_facts:
                brief_facts = get_content('scn') # Legacy fallback
            if not brief_facts:
                brief_facts = get_content('brief_facts') # Absolute fallback
            
            # User Requirement: Alert if template is empty
            if not brief_facts:
                from PyQt6.QtWidgets import QMessageBox
                issue_name = self.template.get('issue_name', 'Issue')
                QMessageBox.warning(self, "No Template Available", 
                                   f"No SCN template found for '{issue_name}'.\n\nPlease enter the facts manually.")
                brief_facts = "[Enter Brief Facts here]"
        else:
            brief_facts = get_content('brief_facts')

        # 2. Check optional sections
        include_grounds = t.get('include_grounds', True)
        include_conclusion = t.get('include_conclusion', True)

        # 3. Build structured HTML
        html_sections = []
        
        # Brief Facts
        html_sections.append(f"""
        <div style="margin-bottom: 15px;">
            <b>Brief Facts:</b><br>
            {brief_facts}
        </div>
        """)
        
        # Grounds (Optional)
        if include_grounds:
            html_sections.append(f"""
            <div style="margin-bottom: 15px;">
                <b>Grounds:</b><br>
                {get_content('grounds')}
            </div>
            """)
            
        # Legal (Always)
        html_sections.append(f"""
        <div style="margin-bottom: 15px;">
            <b>Legal Provisions:</b><br>
            {get_content('legal')}
        </div>
        """)
        
        # Conclusion (Optional)
        if include_conclusion:
            html_sections.append(f"""
            <div style="margin-bottom: 15px;">
                <b>Conclusion:</b><br>
                {get_content('conclusion')}
            </div>
            """)
            
        html = "".join(html_sections)
        
        # CLAIM 2 FIX: Placeholder Audit & Enforced Resolution
        unresolved = self._validate_template_variables(html, self.variables)
        if unresolved:
            print(f"DEBUG: Unresolved variables in {self.template.get('issue_id')}: {unresolved}")
            # Log to a potential UI console or debug log if available
        
        # 1. Replace valid placeholders
        for var_name, var_val in self.variables.items():
            # Format numbers with commas
            if isinstance(var_val, (int, float)):
                val_str = f"{var_val:,.2f}" if var_val != 0 else "0"
            else:
                val_str = str(var_val)
            html = html.replace(f"{{{{{var_name}}}}}", val_str)
            html = html.replace(f"{{{{ {var_name} }}}}", val_str) # Handle spacing
            
        # 2. Inject markers for unresolved placeholders (NO silent blanks)
        for var_name in unresolved:
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in html:
                html = html.replace(placeholder, f"<b style='color:red;'>[[UNRESOLVED: {var_name}]]</b>")
            
            # Also handle spaced version
            placeholder_spaced = f"{{{{ {var_name} }}}}"
            if placeholder_spaced in html:
                html = html.replace(placeholder_spaced, f"<b style='color:red;'>[[UNRESOLVED: {var_name}]]</b>")
            
        self.editor.setHtml(html)
        self.last_rendered_html = html # Update baseline

    # Removed duplicate generate_html

                

    @staticmethod
    def generate_table_html(template, variables):
        """Generate HTML for the table portion of the card"""
        html = ""
        
        # 0. Grid Data Support (Excel Import) - High Priority check
        if 'grid_data' in template:
            grid_data = template['grid_data']
            rows = len(grid_data)
            cols = len(grid_data[0]) if rows > 0 else 0
            
            html += """
            <div style="margin-bottom: 20px; margin-top: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px; font-size: 11pt;">Calculation Table</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 10pt; font-family: 'Bookman Old Style', serif; border: 2px solid #000;">
            """
            
            for r, row_data in enumerate(grid_data):
                html += "<tr>"
                for c, cell_info in enumerate(row_data):
                    val = cell_info.get('value', '')
                    var_name = cell_info.get('var')
                    ctype = cell_info.get('type', 'empty')
                    
                    # Resolve Value
                    if var_name and var_name in variables:
                        val = variables[var_name]
                    
                    # Styling
                    style = "border: 1px solid #000; padding: 6px; word-wrap: break-word; vertical-align: top;"
                    
                    # Header detection (heuristic: static and row 0 or 1, or bold/gray in cell_info?)
                    # For now, we assume imported Excel uses row 0-10 as header? No, 'grid_data' is just the table part.
                    # The importer sets 'table_start_row' but only grid_data starting from there is saved.
                    # So row 0 of grid_data is the first data row (headers were potentially skipped or included?).
                    # Check importer:
                    # current_row = table_start_row + 2
                    # grid_data does NOT include headers currently based on importer logic!
                    # Wait, importer loop: for r in range(current_row, max_row + 1): ... grid_data.append(row_data)
                    # So grid_data is DATA ONLY.
                    # This means we might be missing headers in the HTML if we only render grid_data.
                    # But the User said "table appeared perfectly". In the Form UI, init_grid_ui renders grid_data.
                    # Does init_grid_ui add headers?
                    # self.table.horizontalHeader().setVisible(False)
                    # It renders exactly what is in grid_data.
                    # So if the import logic skipped headers, the form has no headers?
                    # Unless `static` cells in row 0 are headers.
                    
                    if ctype == 'static':
                        style += "background-color: #f2f2f2; font-weight: bold;"
                    else:
                        # Align numbers
                        try:
                            float(str(val).replace(',', '').replace('₹', '').strip())
                            style += "text-align: right;"
                        except:
                            style += "text-align: left;"
                            
                    # Format float
                    try:
                        if isinstance(val, (int, float)):
                            if 'tax' in str(var_name).lower() or 'int' in str(var_name).lower() or 'pen' in str(var_name).lower() or val > 1000:
                                val = f"{val:,.2f}"
                            else:
                                val = str(val)
                    except:
                        pass
                        
                    html += f"<td style='{style}'>{val}</td>"
                html += "</tr>"
                
            html += """
                </table>
            </div>
            """
            return html

        # New Schema Table Support (Excel-like Dict)
        if isinstance(template.get('tables'), dict) and template['tables'].get('rows', 0) > 0:
            table_data = template['tables']
            rows = table_data.get('rows', 0)
            cols = table_data.get('cols', 0)
            
            html += """
            <div style="margin-bottom: 20px; margin-top: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px; font-size: 11pt;">Calculation Table</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 10pt; font-family: 'Bookman Old Style', serif; border: 2px solid #000;">
            """
            
            # Reconstruct grid from variables (A1, B1, etc.)
            for r in range(rows):
                html += "<tr>"
                for c in range(cols):
                    # Calculate address (A1, B1...)
                    col_label = ""
                    temp = c
                    while temp >= 0:
                        col_label = chr(ord('A') + (temp % 26)) + col_label
                        temp = (temp // 26) - 1
                    addr = f"{col_label}{r+1}"
                    
                    # Get value
                    val = variables.get(addr, "")
                    
                    # Basic Styling
                    style = "border: 1px solid #000; padding: 8px; word-wrap: break-word; vertical-align: top;"
                    
                    # Heuristic: First row is usually header
                    if r == 0:
                        style += "background-color: #f2f2f2; font-weight: bold; text-align: center;"
                        
                        # Set Column Widths
                        if cols > 1:
                            if c == 0:
                                style += "width: 40%;"
                            else:
                                width_pct = 60 // (cols - 1)
                                style += f"width: {width_pct}%;"
                    else:
                        # Check if numeric
                        try:
                            float(str(val).replace(',', '').replace('₹', '').strip())
                            style += "text-align: right;"
                        except:
                            style += "text-align: left;"
                            
                    html += f"<td style='{style}'>{val}</td>"
                html += "</tr>"
                
            html += """
                </table>
            </div>
            """

        # Legacy Table Support (Single Table)
        elif 'table' in template:
            table = template['table']
            html += f"""
            <div style="margin-bottom: 20px; margin-top: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px; font-size: 11pt;">{table.get('title', 'Table')}</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 10pt; font-family: 'Bookman Old Style', serif; border: 2px solid #000;">
                    <thead>
                        <tr>
            """
            
            for col in table['columns']:
                html += f"<th style='border: 1px solid #000; padding: 8px; background-color: #f2f2f2; text-align: center; font-weight: bold;'>{col['label']}</th>"
                
            html += """
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for row in table['rows']:
                html += "<tr>"
                for col in table['columns']:
                    key = col['key']
                    val_template = row.get(key, "")
                    val = str(val_template)
                    for var_name, var_val in variables.items():
                        val = val.replace(f"{{{{{var_name}}}}}", str(var_val))
                    
                    # Align numbers to right
                    align = "left"
                    try:
                        float(val.replace(',', '').replace('₹', '').strip())
                        align = "right"
                    except:
                        pass
                        
                    html += f"<td style='border: 1px solid #000; padding: 8px; text-align: {align};'>{val}</td>"
                html += "</tr>"
                
            html += """
                    </tbody>
                </table>
            </div>
            """
            
        return html

    def generate_html(self):
        """Generate HTML for preview/PDF"""
        # 1. Get Editor Content
        html = self.editor.toHtml()
        
        # 2. Append Table
        html += self.generate_table_html(self.template, self.variables)
            
        return html

    def get_data(self):
        """Return current state for saving using the authoritative schema"""
        data = self.data_snapshot.copy()
        
        # 1. Base Issue Data
        data.update({
            'issue_id': self.template['issue_id'],
            'issue': self.template.get('issue_name', ''),
            'variables': self.variables,
            self.content_key: self.editor.toHtml() if hasattr(self, 'editor') else "",
            'tax_breakdown': self.get_tax_breakdown(),
            'is_included': self.is_included,
            'source_type': self.source_type,
            'source_issue_id': self.source_issue_id,
            
            # 2. Structural Classification (Mandatory)
            'origin': self.origin,
            'status': self.status,
            'drop_reason': self.drop_reason
        })
        
        # 3. Data slots (Flexible Schema)
        data['facts'] = self.variables.copy()
        data['scn_narration'] = data.get(self.content_key, "")
        
        # 4. Table Data Persistence (CRITICAL for ad-hoc conversions)
        if 'grid_data' in self.template:
             data['table_data'] = self.template['grid_data']

        # Legacy compatibility (optional)
        if self.origin == "ASMT10":
            data['frozen_facts'] = self.variables.copy()

        return data

    def load_data(self, data):
        """Restore state from authoritative schema"""
        self.data_snapshot = data.copy()
        
        # 1. Restore Classification
        self.origin = data.get('origin', 'SCN')
        self.status = data.get('status', 'ACTIVE')
        self.drop_reason = data.get('drop_reason')
        self.source_issue_id = data.get('source_issue_id')
        
        # 1.1 Restore Table Data (Essential for Adoptions)
        if 'table_data' in data:
            if isinstance(data['table_data'], list):
                 self.template['grid_data'] = data['table_data']
            elif isinstance(data['table_data'], dict):
                 if 'tables' not in self.template:
                     self.template['tables'] = {}
                 self.template['tables'].update(data['table_data'])

        # 2. Restore Variables/Facts
        # If origin is ASMT10 (fresh adoption), facts might be empty, so we must 
        # pull from table_data to ensure sync_ui_with_variables works.
        if 'facts' in data:
            self.variables = data['facts'].copy()
        elif 'variables' in data:
            self.variables = data['variables'].copy()

        # Verbatim Table Carry-Forward: Extract variables from table_data
        if self.origin == "ASMT10" and 'table_data' in data:
             if isinstance(data['table_data'], list): # grid_data style
                 for row in data['table_data']:
                     for cell in row:
                         if isinstance(cell, dict):
                             var = cell.get('var')
                             if var and 'value' in cell:
                                 self.variables[var] = cell['value']
            
        # 3. Restore Narration
        # For SCN mode, content_key is 'scn_content' or similar
        content = data.get(self.content_key) or data.get('scn_narration') or data.get('content')
        if content:
            self.editor.setHtml(content)
        else:
            # Strictly use SCN template if no manual draft exists
            self.update_editor_content()
            
        # 4. Synchronize UI
        self.set_classification(self.origin, self.status, self.drop_reason)
        self.calculate_values()
        self.update_editor_content()
        
        # Update inputs/tables with variables
        self.sync_ui_with_variables()
        self.calculate_values()

    def sync_ui_with_variables(self):
        """Helper to sync UI widgets with self.variables"""
        # A. Legacy Inputs
        if hasattr(self, 'input_widgets'):
            for name, widget in self.input_widgets.items():
                if name in self.variables:
                    widget.blockSignals(True)
                    widget.setText(str(self.variables[name]))
                    widget.blockSignals(False)
                    
        # B. Grid Table
        if hasattr(self, 'cell_widgets'):
            for var_name, item in self.cell_widgets.items():
                if var_name in self.variables:
                    self.table.blockSignals(True)
                    item.setText(str(self.variables[var_name]))
                    self.table.blockSignals(False)
                    
        # C. Manual Table
        if hasattr(self, 'table') and not hasattr(self, 'cell_widgets'):
            rows = self.table.rowCount()
            cols = self.table.columnCount()
            for r in range(rows):
                for c in range(cols):
                    col_label = ""
                    temp = c
                    while temp >= 0:
                        col_label = chr(ord('A') + (temp % 26)) + col_label
                        temp = (temp // 26) - 1
                    addr = f"{col_label}{r+1}"
                    
                    if addr in self.variables:
                        item = self.table.item(r, c)
                        if item and item.flags() & Qt.ItemFlag.ItemIsEditable:
                            self.table.blockSignals(True)
                            item.setText(str(self.variables[addr]))
                            self.table.blockSignals(False)

    def get_tax_breakdown(self):
        """Return tax breakdown by Act"""
        breakdown = {}
        
        # Helper to safely get float
        def get_v(key):
            try: return float(self.variables.get(key, 0))
            except: return 0.0

        # 1. Try explicit Act variables first (if defined in template/variables)
        igst = get_v('tax_igst') or get_v('igst_tax')
        cgst = get_v('tax_cgst') or get_v('cgst_tax')
        sgst = get_v('tax_sgst') or get_v('sgst_tax')
        cess = get_v('tax_cess') or get_v('cess_tax')
        
        if igst or cgst or sgst or cess:
            if igst: breakdown['IGST'] = {'tax': igst, 'interest': get_v('interest_igst'), 'penalty': get_v('penalty_igst')}
            if cgst: breakdown['CGST'] = {'tax': cgst, 'interest': get_v('interest_cgst'), 'penalty': get_v('penalty_cgst')}
            if sgst: breakdown['SGST'] = {'tax': sgst, 'interest': get_v('interest_sgst'), 'penalty': get_v('penalty_sgst')}
            if cess: breakdown['Cess'] = {'tax': cess, 'interest': get_v('interest_cess'), 'penalty': get_v('penalty_cess')}
            return breakdown

        # 2. Smart Detection for Grid Tables (if mapping is missing)
        if isinstance(self.template.get('tables'), dict) and self.template['tables'].get('rows', 0) > 0:
            try:
                table_data = self.template['tables']
                rows = table_data.get('rows', 0)
                cols = table_data.get('cols', 0)
                cells = table_data.get('cells', [])
                
                # Find Header Row (usually row 0)
                header_map = {} # 'CGST': col_index
                if rows > 0 and len(cells) > 0:
                    for c, val in enumerate(cells[0]):
                        val_str = str(val).upper()
                        if 'CGST' in val_str: header_map['CGST'] = c
                        elif 'SGST' in val_str: header_map['SGST'] = c
                        elif 'IGST' in val_str: header_map['IGST'] = c
                        elif 'CESS' in val_str: header_map['Cess'] = c
                
                # Find Data Row (Difference, Tax, Total)
                # We search from bottom up as totals are usually at the bottom
                for r in range(rows - 1, 0, -1):
                    row_label = str(cells[r][0]).upper() if len(cells[r]) > 0 else ""
                    if 'DIFFERENCE' in row_label or 'TAX' in row_label or 'TOTAL' in row_label:
                        # Found a candidate row
                        # Extract values based on header map
                        for act, col_idx in header_map.items():
                            # Reconstruct address (e.g., B4)
                            col_label = ""
                            temp = col_idx
                            while temp >= 0:
                                col_label = chr(ord('A') + (temp % 26)) + col_label
                                temp = (temp // 26) - 1
                            addr = f"{col_label}{r+1}"
                            
                            val = get_v(addr)
                            if val > 0:
                                if act not in breakdown:
                                    breakdown[act] = {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0}
                                breakdown[act]['tax'] = val
                        
                        if breakdown:
                            return breakdown
            except Exception as e:
                print(f"Smart Tax Detection Error: {e}")

        # 3. Fallback to mapped totals (Legacy)
        # If we only have total tax, we don't know the Act.
        # We default to IGST to ensure it appears in the table.
        tax = get_v(self.tax_mapping.get('tax', 'calculated_tax'))
        interest = get_v(self.tax_mapping.get('interest', 'calculated_interest'))
        penalty = get_v(self.tax_mapping.get('penalty', 'calculated_penalty'))
        
        if tax or interest or penalty:
            breakdown['IGST'] = {'tax': tax, 'interest': interest, 'penalty': penalty}
            
        return breakdown
