from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QGridLayout, QCheckBox, 
                             QAbstractItemView, QGraphicsOpacityEffect, QTableWidget, 
                             QTableWidgetItem, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
import copy
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
    
    from src.ui.developer.grid_adapter import GridAdapter
    
    # [CONST] Idempotency Contract
    CANONICAL_PLACEHOLDER = "[Enter Brief Facts here]"

    def __init__(self, template, data=None, parent=None, mode="DRC-01A", content_key="content", save_template_callback=None, issue_number=None):
        super().__init__(parent)
        # [STATE OWNERSHIP] Enforce Immutability
        self.template = copy.deepcopy(template)
        print(f"[IssueCard DIAG] __init__ start for {self.template.get('issue_id')}")
        
        self.mode = mode
        self.content_key = content_key
        # [STATE OWNERSHIP] Capture persisted content for strict restoration
        self.saved_content = data.get(content_key) if data else None
        
        self.issue_number = issue_number
        self.save_template_callback = save_template_callback
        
        # [IDENTITY BOOTSTRAP] Minimal state for init_ui
        self.issue_id = self.template.get('issue_id', 'unknown')
        
        # [INVARIANT] 1. Header Title Derivation (Computed ONCE)
        # Priority: issue_name > formatted(issue_id)
        raw_name = self.template.get('issue_name', '')
        if not raw_name or raw_name == 'Issue':
             # Fallback to ID title-cased (e.g. IMPORT_ITC_MISMATCH -> Import Itc Mismatch)
             self.display_title = self.issue_id.replace('_', ' ').title()
        else:
             self.display_title = raw_name
             
        self.variables = self.template.get('variables', {}).copy()
        self.calc_logic = self.template.get('calc_logic', "")
        self.tax_mapping = self.template.get('tax_demand_mapping', {})
        
        # [STATE OWNERSHIP] Instance-Owned Content
        self.grid_data = None
        
        self.data_snapshot = {}
        self.is_read_only = False
        self.source_text = ""
        self.is_included = True
        self.source_type = None
        self.source_issue_id = data.get('source_issue_id') if data else None
        self.drop_reason = data.get('drop_reason') if data else None
        self.origin = data.get('origin', "SCN") if data else "SCN"
        self.status = data.get('status', "ACTIVE") if data else "ACTIVE"
        self.is_adopted = True
        self.last_rendered_html = ""
        self._is_bootstrapping = True # [GUARD] Prevent destructive sync during init
        self.cell_widgets = {}       # [MULTI-TABLE] Aggregate rather than reassign

        # [STATE OWNERSHIP] 2. Grid Data Resolution & Normalization (Single Pass)
        # Priority 1: Hydrated/Adopted Data (Run-time State)
        # Priority 2: Template Static Data (Design-time Structure)
        
        raw_grid_data = None
        if data and 'table_data' in data and data['table_data']:
             raw_grid_data = data['table_data']
             print(f"[IssueCard DIAG] Resolving grid_data from Runtime Identity (Adopted)")
        elif self.template.get('grid_data'):
             raw_grid_data = self.template['grid_data']
             print(f"[IssueCard DIAG] Resolving grid_data from Template Default")
             
        if raw_grid_data:
             # Canonical Lock: Assert normalization happened upstream.
             # [STRICT CONTRACT] IssueCard expects pre-normalized data.
             if isinstance(raw_grid_data, dict) and 'columns' in raw_grid_data and len(raw_grid_data['columns']) > 0:
                 if not isinstance(raw_grid_data['columns'][0], dict):
                     print(f"[IssueCard CRITICAL] Non-canonical columns detected! {raw_grid_data['columns'][0]}")
                     # raise ValueError("IssueCard received non-canonical grid data") 
                     # For now, print critical error but allow proceed if empty

             self.grid_data = raw_grid_data
             print(f"[IssueCard DIAG] Canonical Grid Locked. Rows: {len(self.grid_data.get('rows', []))}")
             
             # [BOOTSTRAP] Variable Extraction (Read-Only)
             for row in self.grid_data.get('rows', []):
                  for cell in row.values():
                      if isinstance(cell, dict) and cell.get('var'):
                           val = cell.get('value')
                           if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','',1).isdigit()):
                                self.variables[cell['var']] = val

        # [MANDATORY] 1. Unconditional UI Construction First
        # Decoupled from hydration, table_data, and routing logic.
        self.init_ui()


             
             # template['grid_data'] is authoritative structural skeleton.
        pass # Block 1 removed
             
        # DISABLED
        if False: # self.template.get('grid_data'):
                  self.bind_grid_data(self.template['grid_data'], self.grid_container)

                  # [MANDATORY FIX] Unconditional Variable Bootstrap
                  # Override template defaults (0) with adopted grid values immediately.
                  print(f"[IssueCard DIAG] Running Bootstrap for {self.template.get('issue_id')}")
                  normalized = self.GridAdapter.normalize_to_schema(self.template['grid_data'])
                  for row in normalized.get('rows', []):
                      for cell in row.values():
                          if isinstance(cell, dict) and cell.get('var'):
                              val = cell.get('value')
                              # Strict Numeric Check as per user request
                              if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','',1).isdigit()):
                                   self.variables[cell['var']] = val

        # [HYDRATION] 3. Value Restoration
        if data and 'variables' in data:
            self.variables.update(data['variables'])

        # [CALCULATION] 4. Bootstrapping state
        self.set_classification(self.origin, self.status)
        self.calculate_values() 
        
        # [SYNC] 5. Final UI Sync
        self._is_bootstrapping = False # Release guard
        self.sync_ui_with_variables()


    def init_ui(self):
        """
        Structural Restoration (STRICT)
        - Top-Level: ModernCard (Collapsed by default)
        - Nested: Issue Data Card + Draft Content Card
        - Persistence: Create once, show/hide only
        """
        # Base container styling
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent;")
        
        # [FIX] Layout Safety: Check existing before creating
        if self.layout():
            self.main_layout = self.layout()
        else:
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(0,0,0,0)
        
        # 1. Top-Level Card (Host)
        # [FIX] UI Header Title logic
        # Constraint: init_ui must NOT compute title, only decorate it.
        title_text = self.display_title
        
        if self.mode == "SCN":
             # Ensure we don't duplicate if title already has it (unlikely but safe)
             if "(SCN Draft)" not in title_text:
                 title_text += " (SCN Draft)"
        
        if self.issue_number:
            title_text = f"Issue {self.issue_number} – {title_text}"

        self.card = ModernCard(title_text, collapsible=True)
        self.card.toggle_btn.setChecked(False) # Default Collapsed
        self.card.content_widget.setVisible(False)
        self.card.line.setVisible(False)
        
        # 2. Header Components (Moved to Card Header)
        # We access the card's header layout directly to inject controls
        header_layout = self.card.header_layout
        
        # Insert Badge after title
        self.source_badge = QLabel("")
        self.source_badge.hide()
        self.source_badge.setStyleSheet("""
            QLabel {
                background-color: #e8f0fe;
                color: #1a73e8;
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 8pt;
                font-weight: bold;
                border: 1px solid #d2e3fc;
            }
        """)
        header_layout.insertWidget(2, self.source_badge)

        self.card.header_layout.addStretch()

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
        
        # 3. Body Structure (Nested Cards)
        # [FIX] Simplified Layout (No StackAll)
        # Directly use the ModernCard's content layout (Strict API usage)
        
        main_card_layout = self.card.content_layout
        
        # [DEBUG] Hierarchy Check
        print(f"[IssueCard DIAG] main_card_layout type: {type(main_card_layout)}")
        print(f"[IssueCard DIAG] main_card_layout parent: {main_card_layout.parentWidget()}")
        
        p = main_card_layout.parentWidget()
        while p:
            print(f"[IssueCard DIAG] Ancestor: {p} | Layout: {type(p.layout()) if p.layout() else 'None'}")
            p = p.parentWidget()

        # 3.1 Issue Data Card
        self.data_card = ModernCard("Issue Data", collapsible=True)
        
        # [PART B DIAG] LOG: UI Branch Selection
        issue_id = self.template.get('issue_id')
        if issue_id == 'IMPORT_ITC_MISMATCH':
             print(f"[SOP-10 UI DIAG] init_ui: Issue ID={issue_id}")
             # ... (keep logs)

        print(f"[IssueCard DIAG] init_ui: Checking UI branches for {issue_id}")
        self.grid_container = self.data_card # Store for late-binding
        
        # Check if we have grid_data...
        if 'grid_data' in self.template:
             # ... (init_grid_ui calls)
             self.init_grid_ui(self.grid_container)
        elif self.template.get('summary_table'):
             self.init_grid_ui(self.data_card, data=self.template['summary_table'])
        elif 'tables' in self.template and isinstance(self.template['tables'], list):
            for tbl in self.template['tables']:
                if tbl.get('title'):
                    t_lbl = QLabel(f"<b>{tbl.get('title')}</b>")
                    t_lbl.setStyleSheet("color: #34495e; margin-top: 10px; margin-bottom: 5px;")
                    self.data_card.addWidget(t_lbl)
                self.init_grid_ui(self.data_card, data=tbl)
        elif isinstance(self.template.get('tables'), dict):
            self.init_excel_table_ui(self.data_card)
        
        if self.template.get('placeholders'):
            self.init_legacy_ui(self.data_card)
            
        main_card_layout.addWidget(self.data_card)
            
        # 3.2 Draft Content Card
        self.draft_card = ModernCard("Draft Content", collapsible=True)
        self.editor = RichTextEditor()
        self.editor.setMinimumHeight(200)
        self.update_editor_content()
        self.editor.textChanged.connect(self.contentChanged.emit)
        self.draft_card.addWidget(self.editor)
        
        # Connect Draft Focus Mode
        # [FIX] Removed Focus Mode (Opacity) as it caused visual artifacts ("Grey" card) 
        # and potential z-order compositing errors.
        # self.draft_card.toggle_btn.clicked.connect(self._on_draft_focus_changed)
        
        # Mini Totals (Inside Data Card)
        totals_layout = QHBoxLayout()
        self.lbl_tax = QLabel("Tax: Rs. 0")
        self.lbl_interest = QLabel("Interest: Rs. 0")
        self.lbl_penalty = QLabel("Penalty: Rs. 0")
        
        for lbl in [self.lbl_tax, self.lbl_interest, self.lbl_penalty]:
            lbl.setStyleSheet("background-color: #f8f9fa; padding: 5px; border-radius: 3px; border: 1px solid #e9ecef; color: #555;")
            totals_layout.addWidget(lbl)
        totals_layout.addStretch()
        self.data_card.addLayout(totals_layout)
        
        # Sync Warning
        self.sync_warning = QLabel("⚠️ Narration out of sync with Table (Manual edits detected)")
        self.sync_warning.setStyleSheet("color: #e67e22; font-size: 9pt; font-weight: bold; margin-bottom: 5px;")
        self.sync_warning.hide()
        self.draft_card.addWidget(self.sync_warning)
        
        main_card_layout.addWidget(self.draft_card)
        
        # Add Main Card to Layout
        self.main_layout.addWidget(self.card)
        
    def _on_inclusion_changed(self, state):
        if self.origin == "ASMT10":
            # RE-ENFORCE: Include/Exclude forbidden for derived issues
            self.include_cb.setChecked(True)
            return

        self.is_included = (state == 2) # Qt.CheckState.Checked
        
        # GUARD: Visual Muting Only (No blocking overlay)
        # self.overlay.setVisible(not self.is_included) 
        
        # [FIX] Simplified Inclusion Feedback (No Opacity)
        # opacity = 1.0 if self.is_included else 0.5
        # self._set_opacity(self.card, opacity)
            
        self.valuesChanged.emit(self.get_tax_breakdown())
        
    def _on_draft_focus_changed(self):
        """Focus Mode: Deprecated to prevent layout/z-order artifacts."""
        pass
 
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
        if hasattr(self.card, 'title_label'):
             self.card.title_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        
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
        """Initialize structural QTableWidget. Supports idempotent setup and skeleton mode."""
        grid_id = self.template.get('issue_id')
        print(f"[IssueCard DIAG] init_grid_ui: Start for {grid_id}")
        
        # [STATE OWNERSHIP] 1. Resolve Data Source
        # Prefer instance-owned canonical data if available (Single Source of Truth)
        canonical_data = self.grid_data if self.grid_data else None
        
        # Fallback to arguments only if not yet initialized (e.g. skeleton mode first pass)
        if not canonical_data:
             raw_source = data if data else self.template.get('grid_data')
             if not raw_source:
                 print("[IssueCard DIAG] init_grid_ui: ABORT - No grid_data available")
                 return
             # Normalize on the fly (should have been done in init, but safe fallback)
             canonical_data = self.GridAdapter.normalize_to_schema(raw_source)

        # [PHASE A] Mandatory Skeleton Rendering
        # DRAFTING RULE: Always render structural skeleton, even if values empty
        
        # 3. Structure (Idempotent Widget Creation)
        if not hasattr(self, "table"):
            self.table = QTableWidget()
            self.table.setMinimumHeight(200)
            self.table.setMaximumHeight(800)
            
            # Connect signal ONCE
            self.table.itemChanged.connect(self.on_grid_item_changed)
            
            # Layout Bind
            if hasattr(layout, 'addWidget'):
                layout.addWidget(self.table)
            elif hasattr(layout, 'addLayout'):
                layout.addLayout(self.table)

        # 4. Mandatory Bind
        # Remove guards that hid table on empty rows. Data might be empty but structure exists.
        if canonical_data:
            self.bind_grid_data(canonical_data)
            self.table.show()
        else:
            # Should not happen given step 1, but safety fallback
            print("[IssueCard] No canonical data to bind")

    def bind_grid_data(self, grid_data, layout=None, sub_data=None):
        """Strictly UI-only binding. Idempotent and reversible. Expects CANONICAL data."""
        # [ARCH INVARIANT] Grid Normalization MUST NOT happen here.
        # Function expects already-canonical data.
        
        # 1. Strict Schema Assertion
        if not isinstance(grid_data, dict) or 'rows' not in grid_data:
             print(f"[IssueCard CRITICAL] bind_grid_data received INVALID schema for {self.issue_id}. Aborting bind.")
             # We do NOT try to fix it. We fail safe.
             return

        # 2. Schema is valid -> Proceed
        normalized = grid_data 

        # [MANDATORY] Late-Initialization Gate: Ensure self.table exists
        if not hasattr(self, 'table'):
             if layout:
                  self.init_grid_ui(layout, data=grid_data)
             return

        grid_id = self.template.get('issue_id')
        # normalized = self.GridAdapter.normalize_to_schema(grid_data) # Redundant now
        rows = normalized.get('rows', [])
        
        if not rows:
            return
            
        # REVERSIBILITY: Show table if it was hidden
        self.table.show()
        print(f"[IssueCard DIAG] BINDING real grid_data. Rows={len(rows)}")
        
        self.cell_widgets = {} # Reset for fresh bind
        new_widgets = render_grid_to_table_widget(self.table, normalized, interactive=True)
        for var, item in new_widgets.items():
            if var not in self.cell_widgets:
                self.cell_widgets[var] = []
            self.cell_widgets[var].append(item)
        
        # [Visual Polish] 
        from PyQt6.QtWidgets import QHeaderView, QSizePolicy
        
        # Define layout_to_check early to avoid NameError in branches
        layout_to_check = layout.content_layout if hasattr(layout, 'content_layout') else layout
        
        if grid_id in ['EXPANDED_TABLE', 'IMPORT_ITC_MISMATCH']:
            self.table.setMinimumHeight(400)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        else:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            self.table.setShowGrid(True)
            
        # [FIX] SOP-5/SOP-7 UI WIDTH & LAYOUT
        # Determine if this is a 'tables' payload (SOP-5/7) or legacy grid_data
        # 'sub_data' argument is populated only when iterating over 'tables'
        is_expanded_table = (sub_data is not None) or (grid_id in ['TDS_TCS_MISMATCH', 'CANCELLED_SUPPLIERS'])
        
        if is_expanded_table and layout:
             # Force expansion for Detailed Tables
             self.table.setMinimumWidth(850)
             self.table.setMaximumWidth(900)
             self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
             
             # Force Header Stretch
             header = self.table.horizontalHeader()
             header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
             
             # Apply layout stretch
             # Check if already in layout to avoid double adding
             if hasattr(layout_to_check, 'indexOf') and layout_to_check.indexOf(self.table) == -1:
                  if hasattr(layout_to_check, 'addWidget'):
                       layout_to_check.addWidget(self.table, stretch=1)
        elif layout:
             # Legacy Behavior for SOP-2/3/4/etc
             self.table.setMaximumWidth(850)
             self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
             if hasattr(layout_to_check, 'indexOf') and layout_to_check.indexOf(self.table) == -1:
                  if hasattr(layout_to_check, 'addWidget'):
                       layout_to_check.addWidget(self.table)
        
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
                           if layout and hasattr(layout, 'addWidget'):
                               layout.addWidget(note)
                           break # Only show once

        # [DYNAMIC ROW SUPPORT]
        # Check policy from schema
        policy = grid_data.get('row_policy', 'fixed')
        
        if policy == 'dynamic':
            # 1. Create Toolbar if missing
            # We treat this as part of the grid lifecycle
            if not hasattr(self, 'row_controls'):
                self.row_controls = QFrame()
                h_layout = QHBoxLayout(self.row_controls)
                h_layout.setContentsMargins(0, 5, 0, 5)
                
                self.add_btn = QPushButton("+ Add Row")
                self.add_btn.setStyleSheet("text-align: left; color: #1a73e8; border: none; font-weight: bold; padding: 4px;")
                self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.add_btn.clicked.connect(self.add_dynamic_row)
                
                self.del_btn = QPushButton("Delete Selected Row")
                self.del_btn.setStyleSheet("color: #e74c3c; border: none; margin-left: 10px; padding: 4px;")
                self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.del_btn.clicked.connect(self.delete_dynamic_row)
                
                h_layout.addWidget(self.add_btn)
                h_layout.addWidget(self.del_btn)
                h_layout.addStretch()
                
                # Add to layout immediately after table
                # We need to find where table is
                if layout:
                     if hasattr(layout, 'addWidget'):
                          layout.addWidget(self.row_controls)
                     elif hasattr(layout, 'addLayout'):
                          layout.addWidget(self.row_controls)
            
            self.row_controls.show()
        else:
            # Fixed Mode: Hide controls if they exist
            if hasattr(self, 'row_controls'):
                self.row_controls.hide()

    def add_dynamic_row(self):
        """Adds a new row to the dynamic grid and refreshes UI."""
        if not self.grid_data: return
        
        columns = self.grid_data.get('columns', [])
        if not columns: return
        
        # 1. Create New Row
        import time
        new_id = f"r_dyn_{int(time.time()*1000)}" 
        row_obj = {"id": new_id}
        
        for col in columns:
            # Default to input type
            row_obj[col['id']] = {"value": "", "type": "input"}
            
        # 2. Update Data
        if 'rows' not in self.grid_data: self.grid_data['rows'] = []
        self.grid_data['rows'].append(row_obj)
        
        # 3. Refresh UI (Full Re-bind to ensure consistency)
        # This is safe because bind_grid_data is idempotent-ish
        # We assume self.table already exists
        self.bind_grid_data(self.grid_data)
        
        # 4. Scroll to bottom
        self.table.scrollToBottom()

    def delete_dynamic_row(self):
        """Deletes the currently selected row."""
        if not self.grid_data: return
        
        rows = self.grid_data.get('rows', [])
        if not rows: return
        
        # 1. Get Selection
        current_row = self.table.currentRow()
        if current_row < 0: return # No selection
        
        # 2. Safety Check (Don't allow deleting header/magic rows? 
        # GridAdapter renders headers as QTableWidget headers, so row 0 is data row 0.
        if current_row >= len(rows): return
        
        # 3. Update Data
        del rows[current_row]
        
        # 4. Refresh UI
        self.bind_grid_data(self.grid_data)

    def on_grid_data_adopted(self):
        """
        Called exactly once when REAL grid_data is attached to the template.
        Responsible for exiting Skeleton Mode and binding data to the UI.
        UI must never infer data readiness from dict truthiness.
        """
        grid_data = self.template.get('grid_data')
        if not grid_data:
            return

        # [FIX] Normalize BEFORE binding to satisfy strict invariant
        normalized = self.GridAdapter.normalize_to_schema(grid_data)
        rows = normalized.get('rows', [])
        
        if rows:
            print(f"[IssueCard DIAG] EXITING SKELETON MODE – binding real grid_data (Rows={len(rows)})")
            # Pass NORMALIZED data, not raw grid_data
            self.bind_grid_data(normalized, self.grid_container)
            if hasattr(self, 'table'):
                 self.table.show()

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
        
        # [FIX] Sync to Canonical Grid Data Source (Robust via Index)
        try:
            if self.grid_data and 'rows' in self.grid_data:
                row_idx = item.row()
                col_idx = item.column()
                
                rows = self.grid_data.get('rows', [])
                cols = self.grid_data.get('columns', [])
                
                if 0 <= row_idx < len(rows) and 0 <= col_idx < len(cols):
                    # Resolve Column ID from Schema Order
                    col_id = cols[col_idx].get('id')
                    if col_id:
                        # Locate cell dict in canonical source
                        row_dict = rows[row_idx]
                        if col_id in row_dict:
                            if isinstance(row_dict[col_id], dict):
                                row_dict[col_id]['value'] = val
                            else:
                                # Auto-repair: convert raw value to cell dict if needed
                                row_dict[col_id] = {'value': val, 'type': 'static'}
        except Exception as e:
            print(f"[IssueCard ERROR] Failed to sync grid edit: {e}")
            
        # 1. Update numeric totals
        self.calculate_values()
        
        # 2. Narration Sync: Auto-refresh brief-facts/draft content
        self.update_editor_content(is_recalculation=True)

    def update_variable(self, name, value):
        self.variables[name] = value
        self.calculate_values()

    def calculate_values(self):
        # 1. Handle Excel Grid Calculation
        if 'grid_data' in self.template:
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
        """Evaluate formulas in the grid with explicit variable binding precedence"""
        grid_data = data if data else self.template.get('grid_data')
        if not grid_data: return
        
        # [FIX] Normalize before calculation
        grid_data = self.GridAdapter.normalize_to_schema(grid_data)
        rows = grid_data['rows']

        # Pass 1: Bound Variable Bootstrap (Static & Input)
        # We extract all values into variables map if they have a 'var' tag.
        # This ensures values like 'tax_igst' provided by normalization aren't lost.
        for row_data in rows:
            cells = row_data.values() if isinstance(row_data, dict) else row_data
            for cell_info in cells:
                if isinstance(cell_info, dict):
                    var_name = cell_info.get('var')
                    if var_name:
                        # [BOOTSTRAP CORRECTION] Override 0 if grid contains non-zero value
                        current_val = self.variables.get(var_name)
                        grid_val = cell_info.get('value')
                        
                        is_empty = current_val in (None, "")
                        is_zero = current_val in (0, 0.0)
                        has_priority_data = grid_val not in (None, "", 0, 0.0)

                        if is_empty or (is_zero and has_priority_data):
                            try:
                                self.variables[var_name] = float(grid_val) if grid_val not in (None, "") else 0.0
                            except:
                                self.variables[var_name] = grid_val # String fallback
                                
                        # Diagnostic Tracking
                        if has_priority_data and current_val == 0:
                             print(f"[IssueCard BOOTSTRAP] Overrode 0 for '{var_name}' with grid value: {grid_val}")

        # Pass 2: Formula Evaluation (Overrides Bootstrap)
        for r, row_data in enumerate(rows):
            cells = row_data.values() if isinstance(row_data, dict) else row_data
            for cell_info in cells:
                if isinstance(cell_info, dict) and cell_info.get('type') == 'formula':
                        formula = cell_info.get('python_formula')
                        if not formula: continue
                        
                        try:
                            context = {
                                'v': self.variables,
                                'round': round, 'max': max, 'min': min, 'abs': abs
                            }
                            result = eval(formula, {}, context)
                            
                            var_name = cell_info.get('var')
                            if var_name:
                                self.variables[var_name] = result
                                
                                # Update UI [MULTI-TABLE SAFE]
                                items = self.cell_widgets.get(var_name, [])
                                if not isinstance(items, list): items = [items]
                                
                                for item in items:
                                    tbl = item.tableWidget()
                                    if tbl: tbl.blockSignals(True)
                                    item.setText(str(result))
                                    if tbl: tbl.blockSignals(False)
                                    
                        except Exception as e:
                            print(f"[IssueCard] Formula Error {formula}: {e}")

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
        
        if not hasattr(self, 'editor'): return
        
        # SAFEGUARD: Detection of manual edits
        current_html = self.editor.toHtml()
        if is_recalculation and hasattr(self, 'last_rendered_html') and self.last_rendered_html:
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
            # [FIX] Strict Idempotency Logic (Iter 2)
            # Priority 1: Restored Content (User Edits)
            # Priority 2: Template Authoritative (template['templates']['brief_facts_scn'])
            # Priority 3: Canonical Placeholder
            
            check_content = self.saved_content
            
            # Simple validity check
            has_saved_content = check_content and len(check_content.strip()) > 0 and check_content != self.CANONICAL_PLACEHOLDER
            
            if has_saved_content:
                brief_facts = self.extract_html_body(check_content)
                if not brief_facts.strip(): has_saved_content = False
            
            if has_saved_content:
                 brief_facts = self.extract_html_body(check_content)
            else:
                 # Adoption Mode: Strictly fetch from authoritative template location
                 # No guessing. No probing root keys.
                 brief_facts = t.get('brief_facts_scn')
                 
                 if not brief_facts:
                     brief_facts = self.CANONICAL_PLACEHOLDER
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
            
        # 2. Inject Display-Only Fallbacks for unresolved placeholders (NO state mutation)
        for var_name in unresolved:
            # [DISPLAY FALLBACK] Default to "0" or "-" based on heuristic or just clean "0"
            fallback_val = "0"
            
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in html:
                html = html.replace(placeholder, fallback_val)
            
            # Also handle spaced version
            placeholder_spaced = f"{{{{ {var_name} }}}}"
            if placeholder_spaced in html:
                html = html.replace(placeholder_spaced, fallback_val)
            
        self.editor.setHtml(html)
        self.last_rendered_html = html # Update baseline

    # Removed duplicate generate_html

                

    @staticmethod
    def generate_table_html(template, variables):
        """Generate HTML for the table portion of the card"""
        html = ""
        
        # 0. Grid Data Support (Excel Import) - High Priority check
        # [FIX] Check both template and variables for grid_data to ensure table renders
        grid_source = None
        if 'grid_data' in template:
            grid_source = template['grid_data']
        elif 'grid_data' in variables:
            grid_source = variables['grid_data']
            
        if grid_source:
            grid_data = grid_source
            print(f"[IssueCard DIAG] Found grid_source type: {type(grid_source)}")
            
            # [FIX] Robust Normalization for Canonical Grid (List vs Dict)
            # The new IssueCard enforces {'columns': ..., 'rows': ...} but legacy data might be List[List].
            # We must normalize to List[List] for HTML generation.
            rows_data = []
            if isinstance(grid_data, dict):
                rows_data = grid_data.get('rows', [])
            elif isinstance(grid_data, list):
                rows_data = grid_data
            
            print(f"[IssueCard DIAG] Normalized rows_data length: {len(rows_data)}")
            if len(rows_data) > 0:
                print(f"[IssueCard DIAG] Sample row_data[0] type: {type(rows_data[0])}")
                print(f"[IssueCard DIAG] Sample row_data[0] keys/content: {rows_data[0]}")
            
            # [CRITICAL FIX] Overwrite variables context so downstream logic sees a List
            # This prevents KeyError: 0 when Jinja/Legacy logic tries to index it numerically
            if 'grid_data' in variables:
                 variables['grid_data'] = rows_data
                 
            rows = len(rows_data)
            
            # [FIX] Generate Table HTML manually to ensure it appears
            # ... (Rest of existing logic, but we need to see the loop below)
            
            html += """
            <div style="margin-bottom: 20px; margin-top: 15px;">
                <p style="font-weight: bold; margin-bottom: 8px; font-size: 11pt;">Calculation Table</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 10pt; font-family: 'Bookman Old Style', serif; border: 2px solid #000;">
            """
            
            # Attempt to get header columns if possible
            if isinstance(grid_data, dict) and 'columns' in grid_data:
                columns = grid_data['columns']
                print(f"[IssueCard DIAG] columns data: {columns}")
                html += "<tr>"
                for col in columns:
                    col_name = col.get('name', 'Column') if isinstance(col, dict) else str(col)
                    html += f'<th style="border: 1px solid black; padding: 5px; text-align: center; background-color: #f0f0f0;">{col_name}</th>'
                html += "</tr>"
            
            for r, row_data in enumerate(rows_data):
                html += "<tr>"
                
                # Ensure row_data is iterable (List)
                cells = []
                if isinstance(row_data, list):
                     cells = row_data
                elif isinstance(row_data, dict):
                    if 'cells' in row_data:
                         cells = row_data['cells']
                    else:
                        # Fallback: maybe it's a direct dict of values? 
                        cells = list(row_data.values())

                for c, cell_info in enumerate(cells):
                    val = ""
                    var_name = None
                    ctype = 'empty'
                    
                    if isinstance(cell_info, dict):
                        val = cell_info.get('value', '')
                        var_name = cell_info.get('var')
                        ctype = cell_info.get('type', 'empty')
                    else:
                        val = str(cell_info)
                        ctype = 'static' # Assume static if just a value
                    
                    # Resolve Value
                    if var_name:
                        if var_name in variables:
                            val = variables[var_name]
                        else:
                            # [DISPLAY FALLBACK] Unresolved variables default to 0 in HTML view
                            val = 0
                    
                    # Styling
                    style = "border: 1px solid #000; padding: 6px; word-wrap: break-word; vertical-align: top;"
                    
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
                            # Check if it looks like currency/tax
                            s_var = str(var_name).lower() if var_name else ""
                            if 'tax' in s_var or 'int' in s_var or 'pen' in s_var or val > 1000:
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
            'issue_id': self.template.get('issue_id', 'unknown'),
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
        if self.grid_data:
             data['table_data'] = self.grid_data
        elif 'grid_data' in self.template:
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
        
        # 1.1 Restore Table Data (Non-Destructive Adoption)
        if 'table_data' in data and data['table_data']:
            # [ROUTING PRECEDENCE] template['grid_data'] is authoritative.
            # Only adopt snapshot structure if template's existing structure is missing.
            has_structure = bool(self.template.get('grid_data') or self.template.get('tables'))
            
            if not has_structure:
                if isinstance(data['table_data'], list):
                     self.template['grid_data'] = data['table_data']
                elif isinstance(data['table_data'], dict):
                     # Check for Canonical Grid Schema (rows/columns)
                     if 'rows' in data['table_data'] and 'columns' in data['table_data']:
                          self.template['grid_data'] = data['table_data']
                     else:
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

        # 3. Restore Narration
        # For SCN mode, content_key is 'scn_content' or similar
        content = data.get(self.content_key) or data.get('scn_narration') or data.get('content')
        if content:
            self.editor.setHtml(content)
            
        # 4. Final Verification: Sync structural changes if real grid data just arrived
        if ('table_data' in data and data['table_data']):
             print(f"[IssueCard DIAG] load_data: Final Bind check for {self.template.get('issue_id')}")
             # Ensure template has the structure
             if self.template.get('grid_data'):
                  self.bind_grid_data(self.template['grid_data'], self.grid_container)
        else:
            # Strictly use SCN template if no manual draft exists
            self.update_editor_content()
            
        # 4. Synchronize UI
        self.set_classification(self.origin, self.status, self.drop_reason)
        self.calculate_values()
        self.update_editor_content()
        
        # Update inputs/tables with variables
        self._is_bootstrapping = False
        self.sync_ui_with_variables()
        self.calculate_values()

    def sync_ui_with_variables(self):
        """Helper to sync UI widgets with self.variables"""
        # [NON-DESTRUCTIVE GUARD] Prevent overwriting UI values during bootstrap
        if getattr(self, '_is_bootstrapping', False):
             return

        # A. Legacy Inputs
        if hasattr(self, 'input_widgets'):
            for name, widget in self.input_widgets.items():
                if name in self.variables:
                    widget.blockSignals(True)
                    widget.setText(str(self.variables[name]))
                    widget.blockSignals(False)
                    
        # B. Grid Table
        if hasattr(self, 'cell_widgets'):
            for var_name, items in self.cell_widgets.items():
                if var_name in self.variables:
                    val = self.variables[var_name]
                    # Support both list and single-item for robustness
                    widget_list = items if isinstance(items, list) else [items]
                    for item in widget_list:
                        tbl = item.tableWidget()
                        if tbl: tbl.blockSignals(True)
                        item.setText(str(val))
                        if tbl: tbl.blockSignals(False)
                    
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

        # [FIX] Canonical-First Logic: Strict Adherence to tax_demand_mapping
        if self.tax_mapping:
            has_mapped_data = False
            for act in ['IGST', 'CGST', 'SGST', 'Cess']:
                var_name = self.tax_mapping.get(act)
                if var_name:
                    # Mapped variable exists in template contract
                    val = get_v(var_name)
                    # We populate the breakdown even if 0, to respect the contract
                    # But we only flag has_mapped_data if we found a valid mapping instruction
                    has_mapped_data = True
                    
                    if act not in breakdown:
                        breakdown[act] = {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0}
                    
                    breakdown[act]['tax'] = val
                    
                    # Optional: Look for sibling interest/penalty variables if conventional names used
                    # (This part remains heuristic or requires extended mapping, but tax is the priority)
            
            if has_mapped_data:
                return breakdown

        # 2. Smart Detection for Grid Tables (if mapping is missing)
        # Support both Legacy 'tables' and Modern 'grid_data'
        target_tables = []
        if isinstance(self.template.get('tables'), dict) and self.template['tables'].get('rows', 0) > 0:
            target_tables.append(('legacy', self.template['tables']))
        
        # [FIX] Add grid_data support for heuristics
        # We look at self.grid_data which is the runtime state, or template default
        current_grid = self.grid_data if hasattr(self, 'grid_data') and self.grid_data else self.template.get('grid_data')
        if current_grid and isinstance(current_grid, dict) and 'rows' in current_grid:
            target_tables.append(('grid', current_grid))

        if target_tables:
            try:
                for t_type, table_data in target_tables:
                    if t_type == 'legacy':
                        # ... Existing Legacy Logic (Preserved) ...
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
                        for r in range(rows - 1, 0, -1):
                            row_label = str(cells[r][0]).upper() if len(cells[r]) > 0 else ""
                            if 'DIFFERENCE' in row_label or 'TAX' in row_label or 'TOTAL' in row_label:
                                for act, col_idx in header_map.items():
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
                                if breakdown: return breakdown

                    elif t_type == 'grid':
                        # [NEW] Grid Data Heuristic
                        # 1. Map Columns by Label
                        columns = table_data.get('columns', [])
                        col_map = {} # 'CGST': 'col2'
                        
                        for col in columns:
                            if isinstance(col, dict):
                                label = str(col.get('label', '')).upper()
                                cid = col.get('id')
                                if 'CGST' in label: col_map['CGST'] = cid
                                elif 'SGST' in label: col_map['SGST'] = cid
                                elif 'IGST' in label: col_map['IGST'] = cid
                                elif 'CESS' in label: col_map['Cess'] = cid
                        
                        if not col_map: continue
                        
                        # 2. Iterate Rows and Sum (Assumption: All rows contribute to liability unless labeled otherwise?)
                        # Or should we look for Total row?
                        # Start by Summing ALL numeric values in these columns (Safe for simple lists)
                        # If we find a "Total" row, we might double count? 
                        # GridAdapter usually doesn't have "Total" rows unless static.
                        
                        temp_totals = {k: 0.0 for k in col_map.keys()}
                        
                        rows = table_data.get('rows', [])
                        for row in rows:
                            # Skip Header-like rows if any (usually handled by columns)
                            # Check Row Label if exists
                            # In GridAdapter, row is dict: {col_id: cell_obj}
                            
                            is_total_row = False
                            # Heuristic: Check ALL string cells for "Total" or "Difference"
                            # This is safer than assuming first col is always the label (e.g. checkbox cols)
                            for cell in row.values():
                                if isinstance(cell, dict) and 'value' in cell:
                                    val_str = str(cell['value']).strip().upper()
                                    if val_str == "TOTAL" or "TOTAL " in val_str or " TOTAL" in val_str:
                                        is_total_row = True
                                        break
                                    if "DIFFERENCE" in val_str:
                                        is_total_row = True 
                                        break
                            
                            if is_total_row: continue

                            for act, cid in col_map.items():
                                cell = row.get(cid)
                                if isinstance(cell, dict):
                                    # Try 'var' first (bound value)
                                    val = 0.0
                                    raw_val = None
                                    if 'var' in cell and cell['var']:
                                         raw_val = get_v(cell['var'])
                                         val = raw_val
                                    else:
                                         # Try static/input value
                                         try: 
                                             raw_val = cell.get('value', 0)
                                             # Handle "Rs. 1,000" or "1000.00"
                                             if isinstance(raw_val, str):
                                                 clean_val = raw_val.replace(',', '').replace('Rs.', '').strip()
                                                 if clean_val:
                                                     val = float(clean_val)
                                             else:
                                                 val = float(raw_val)
                                         except: val = 0.0
                                    
                                    if val > 0:
                                        temp_totals[act] += val
                        
                        # Transfer to breakdown
                        has_val = False
                        for act, total in temp_totals.items():
                            if total > 0:
                                if act not in breakdown: breakdown[act] = {'tax': 0.0, 'interest': 0.0, 'penalty': 0.0}
                                breakdown[act]['tax'] = total
                                has_val = True
                        
                        if has_val: return breakdown

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
