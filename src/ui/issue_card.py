from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QGridLayout, QCheckBox, 
                             QAbstractItemView, QGraphicsOpacityEffect, QTableWidget, 
                             QTableWidgetItem, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
import copy
from src.ui.rich_text_editor import RichTextEditor
from src.ui.components.modern_card import ModernCard
from src.ui.ui_helpers import render_grid_to_table_widget, MonetaryDelegate
from src.utils.formatting import format_indian_number
from src.utils.number_utils import safe_int
from src.ui.styles import Theme

class CollapsibleSection(QWidget):
    def __init__(self, title, content_widget, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header
        self.header = QFrame()
        self.header.setStyleSheet("background-color: transparent;") 
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(0, 5, 0, 5)
        self.header_layout.setSpacing(8)
        
        self.toggle_btn = QLabel("▼") # Simple text label for chevron
        self.toggle_btn.setStyleSheet(f"color: {Theme.NEUTRAL_500}; font-size: 10px;")
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"font-size: {Theme.FONT_BODY}; font-weight: {Theme.WEIGHT_SEMIBOLD}; color: {Theme.NEUTRAL_500}; text-transform: uppercase; letter-spacing: 0.5px;")
        
        self.header_layout.addWidget(self.toggle_btn)
        self.header_layout.addWidget(self.title_lbl)
        self.header_layout.addStretch()
        
        # Click event on header
        self.header.mousePressEvent = self.toggle_content
        
        self.layout.addWidget(self.header)
        
        # Content
        self.content_area = content_widget
        self.layout.addWidget(self.content_area)
        
        # Separator (Optional)
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setStyleSheet(f"color: {Theme.NEUTRAL_200};")
        self.layout.addWidget(self.line)

    def toggle_content(self, event=None):
        visible = self.content_area.isVisible()
        self.content_area.setVisible(not visible)
        self.toggle_btn.setText("▶" if visible else "▼")

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

    def init_ui(self):
        """
        Refactored UI: Clean minimal design with right-aligned actions and no heavy nesting.
        """
        # Base container styling (Clean Card)
        self.setObjectName("IssueCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self.setStyleSheet(f"""
            #IssueCard {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.NEUTRAL_200};
                border-radius: {Theme.RADIUS_MD};
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.setSpacing(0)
        
        # --- 1. Header Section ---
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(f"border-bottom: 1px solid {Theme.NEUTRAL_200}; background-color: {Theme.NEUTRAL_100}; border-top-left-radius: {Theme.RADIUS_MD}; border-top-right-radius: {Theme.RADIUS_MD};")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        header_layout.setSpacing(10)
        
        # Toggle Button (Chevron)
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(28, 28)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.NEUTRAL_200};
                color: {Theme.NEUTRAL_900};
                border: none;
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                background-color: {Theme.NEUTRAL_500};
                color: {Theme.SURFACE};
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_content)
        header_layout.addWidget(self.toggle_btn)

        # Include Checkbox (For DRC-01A Soft Delete / Inclusion)
        self.include_cb = QCheckBox()
        self.include_cb.setChecked(self.is_included)
        self.include_cb.setStyleSheet(f"QCheckBox::indicator {{ width: 22px; height: 22px; }}")
        self.include_cb.stateChanged.connect(lambda: self.handle_remove_or_drop() if self.include_cb.isChecked() != self.is_included else None)
        header_layout.addWidget(self.include_cb)

        # Title Column
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        
        # Title
        title_text = self.display_title
        if self.issue_number:
            title_text = f"{self.issue_number}. {title_text}"
            
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setStyleSheet(f"font-size: {Theme.FONT_CARD}; font-weight: {Theme.WEIGHT_SEMIBOLD}; color: {Theme.NEUTRAL_900}; border: none;")
        title_col.addWidget(self.title_lbl)
        
        # Metadata Row (Source badge + text)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        
        self.source_badge = QLabel("")
        self.source_badge.hide()
        # Badge style handled in set_classification
        meta_row.addWidget(self.source_badge)
        
        self.meta_lbl = QLabel("Origin: SCN") # Placeholder
        self.meta_lbl.setStyleSheet(f"font-size: {Theme.FONT_META}; color: {Theme.NEUTRAL_500}; border: none;")
        meta_row.addWidget(self.meta_lbl)
        
        meta_row.addStretch()
        title_col.addLayout(meta_row)
        
        header_layout.addLayout(title_col, stretch=1)
        
        # Actions Column (Right Aligned)
        from src.ui.ui_helpers import create_secondary_button, create_danger_button
        
        # Remove Button
        self.remove_btn = create_danger_button("Remove", self.handle_remove_or_drop)
        # Compact Danger Button
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.SURFACE};
                color: {Theme.DANGER};
                border: 1px solid {Theme.NEUTRAL_200};
                border-radius: {Theme.RADIUS_MD};
                padding: 4px 12px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #fee2e2;
                border-color: {Theme.DANGER};
                color: {Theme.DANGER_HOVER};
            }}
        """)
        header_layout.addWidget(self.remove_btn)
        
        self.main_layout.addWidget(self.header_frame)
        
        # --- 2. Body Section ---
        self.body_container = QWidget()
        self.body_container.setObjectName("BodyContainer")
        body_layout = QVBoxLayout(self.body_container)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(20)
        
        # 2.1 Calculated Totals (Mini Dashboard)
        totals_panel = QFrame()
        totals_panel.setStyleSheet(f"background-color: {Theme.NEUTRAL_100}; border-radius: {Theme.RADIUS_MD};")
        t_layout = QHBoxLayout(totals_panel)
        t_layout.setContentsMargins(15, 10, 15, 10)
        
        self.lbl_igst = QLabel("IGST: ₹ 0")
        self.lbl_cgst = QLabel("CGST: ₹ 0")
        self.lbl_sgst = QLabel("SGST: ₹ 0")
        
        for lbl in [self.lbl_igst, self.lbl_cgst, self.lbl_sgst]:
            lbl.setStyleSheet(f"font-weight: {Theme.WEIGHT_SEMIBOLD}; color: {Theme.NEUTRAL_900}; border: none;")
            t_layout.addWidget(lbl)
            t_layout.addSpacing(20)
            
        t_layout.addStretch()
        body_layout.addWidget(totals_panel)
        
        # 2.2 Issue Data (Grid)
        self.grid_container = QWidget()
        g_layout = QVBoxLayout(self.grid_container)
        g_layout.setContentsMargins(0, 10, 0, 10)
        
        # Loading Logic
        if 'grid_data' in self.template:
             self.init_grid_ui(g_layout)
        elif self.template.get('summary_table'):
             self.init_grid_ui(g_layout, data=self.template['summary_table'])
        elif 'tables' in self.template and isinstance(self.template['tables'], list):
            for tbl in self.template['tables']:
                if tbl.get('title'):
                    t_lbl = QLabel(f"{tbl.get('title')}")
                    t_lbl.setStyleSheet(f"color: {Theme.NEUTRAL_900}; font-weight: bold; margin-top: 5px;")
                    g_layout.addWidget(t_lbl)
                self.init_grid_ui(g_layout, data=tbl)
        elif isinstance(self.template.get('tables'), dict):
            self.init_excel_table_ui(g_layout)
        
        if self.template.get('placeholders'):
            self.init_legacy_ui(g_layout)
            
        # Wrap Grid
        self.grid_section = CollapsibleSection("Issue Details", self.grid_container)
        body_layout.addWidget(self.grid_section)
        
        # 2.3 Brief Facts & Legal Provisions (Consolidated Editor)
        self.editor = RichTextEditor()
        self.editor.setMinimumHeight(200)
        self.editor.set_toolbar_visible(False) 
        self.editor.textChanged.connect(self.contentChanged.emit)
        
        self.draft_section = CollapsibleSection("Brief Facts & Legal Provisions", self.editor)
        body_layout.addWidget(self.draft_section)

        self.main_layout.addWidget(self.body_container)

    def toggle_content(self):
        """Toggles the visibility of the body content."""
        is_visible = self.body_container.isVisible()
        self.body_container.setVisible(not is_visible)
        # Update chevron
        self.toggle_btn.setText("▶" if not is_visible else "▼")


    def __init__(self, template, data=None, parent=None, mode="DRC-01A", content_key="content", save_template_callback=None, issue_number=None):
        super().__init__(parent)
        # [STATE OWNERSHIP] Enforce Immutability
        self.template = copy.deepcopy(template)
        
        self.mode = mode
        self.content_key = content_key
        # [STATE OWNERSHIP] Capture persisted content for strict restoration
        self.saved_content = data.get(content_key) if data else None
        
        self.issue_number = issue_number
        self.save_template_callback = save_template_callback
        
        # [IDENTITY BOOTSTRAP] Minimal state for init_ui
        self.issue_id = self.template.get('issue_id', 'unknown')
        
        # [INVARIANT] 1. Header Title Derivation (Computed ONCE)
        # Priority: issue_name > human-readable formatted string
        raw_name = self.template.get('issue_name', '')
        if not raw_name or raw_name == 'Issue':
             # Clean human-readable fallback (No underscore IDs)
             self.display_title = "Issue Concerning Tax Liability" 
        else:
             self.display_title = raw_name
             
        self.variables = self.template.get('variables', {}).copy()
        self.calc_logic = self.template.get('calc_logic', "")
        self.tax_mapping = self.template.get('tax_demand_mapping') or {}
        
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
        elif self.template.get('grid_data'):
             raw_grid_data = self.template['grid_data']
             
        if raw_grid_data:
             # Canonical Lock: Assert normalization happened upstream.
             # [STRICT CONTRACT] IssueCard expects pre-normalized data.
             if isinstance(raw_grid_data, dict) and 'columns' in raw_grid_data and len(raw_grid_data['columns']) > 0:
                 if not isinstance(raw_grid_data['columns'][0], dict):
                     print(f"[IssueCard CRITICAL] Non-canonical columns detected! {raw_grid_data['columns'][0]}")
                     # raise ValueError("IssueCard received non-canonical grid data") 
                     # For now, print critical error but allow proceed if empty

             self.grid_data = raw_grid_data
             
             # [FIX] Canonical Column IDs
             if isinstance(self.grid_data, dict) and 'columns' in self.grid_data:
                 cols = self.grid_data['columns']
                 for i, col in enumerate(cols):
                     if not isinstance(col, dict):
                         cols[i] = {"id": str(col).lower().replace(" ", "_"), "label": str(col)}


             
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
            # Style: Primary Blue
            self.source_badge.setStyleSheet(f"""
                QLabel {{ 
                    background-color: {Theme.NEUTRAL_100}; 
                    color: {Theme.PRIMARY}; 
                    padding: 2px 8px; 
                    border-radius: {Theme.RADIUS_MD}; 
                    font-size: {Theme.FONT_META}; 
                    font-weight: 600; 
                    border: 1px solid {Theme.NEUTRAL_200}; 
                }}
            """)
        elif canonical_origin == "MANUAL_SOP":
            self.set_source("Manual – SOP")
            # Style: Muted Gray
            self.source_badge.setStyleSheet(f"""
                QLabel {{ 
                    background-color: {Theme.NEUTRAL_100}; 
                    color: {Theme.NEUTRAL_500}; 
                    padding: 2px 8px; 
                    border-radius: {Theme.RADIUS_MD}; 
                    font-size: {Theme.FONT_META}; 
                    font-weight: 600; 
                    border: 1px solid {Theme.NEUTRAL_200}; 
                }}
            """)
        else:
            # Context-Aware Default
            if hasattr(self, 'mode') and self.mode == "DRC-01A":
                 self.set_source("DRC-01A Issue")
                 # Style: Warning/Orange (Distinct from SCN Red)
                 self.source_badge.setStyleSheet(f"""
                    QLabel {{ 
                        background-color: #fff7ed; 
                        color: #c2410c; 
                        padding: 2px 8px; 
                        border-radius: {Theme.RADIUS_MD}; 
                        font-size: {Theme.FONT_META}; 
                        font-weight: 600; 
                        border: 1px solid #fed7aa; 
                    }}
                """)
            else:
                self.set_source("New Issue (SCN)")
                # Default Style: Danger/Red
                self.source_badge.setStyleSheet(f"""
                    QLabel {{ 
                        background-color: #fee2e2; 
                        color: {Theme.DANGER}; 
                        padding: 2px 8px; 
                        border-radius: {Theme.RADIUS_MD}; 
                        font-size: {Theme.FONT_META}; 
                        font-weight: 600; 
                        border: 1px solid #fecaca; 
                    }}
                """)
            
        # [FIX] Visual Consistency: Update the text label too
        if hasattr(self, 'meta_lbl'):
            display_text = "SCN"
            if canonical_origin == "SCRUTINY":
                display_text = "ASMT-10"
            elif canonical_origin == "MANUAL_SOP":
                 display_text = "SOP"
            self.meta_lbl.setText(f"Origin: {display_text}")

        # 2. Universal Flexibility
        # 2. Universal Flexibility
        # self.include_cb.show()  <-- REMOVED to fix AttributeError
        
        # Ensure interactive state
        # self.remove_btn style is set in init_ui, no need to reset here unless changing state
        
        # Reset visual styles to standard
        # self.setStyleSheet(...) - Handled in init_ui with ID selector
        
        # Ensure interactive state
        if hasattr(self, 'editor'):
            self.editor.set_read_only(False)
            self.editor.setStyleSheet("") # Clear any custom dashed borders
 
    def handle_remove_or_drop(self):
        """Handle issue removal based on Origin:
           - SCN/Manual: Hard Delete (Emit removeClicked)
           - Scrutiny/ASMT-10: Soft Delete (Toggle Include/Exclude)
        """
        # Normalize origin check
        canonical_origin = self.origin.upper() if self.origin else "SCN"
        is_manual = canonical_origin in ["SCN", "MANUAL_SOP"]

        if is_manual:
            # HARD DELETE PATH
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, 
                "Confirm Delete", 
                "Are you sure you want to permanently delete this issue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.removeClicked.emit()
            return

        # SOFT DELETE PATH (Hydrated Issues)
        # Toggle state
        self.is_included = not self.is_included
        
        # Update Visuals
        self.update_visual_state()
        
        # Notifying Parent to recalculate (Excluded items return 0 tax)
        self.valuesChanged.emit(self.get_tax_breakdown())

    def update_visual_state(self):
        """Updates visual appearance based on inclusion state (Soft Delete)"""
        if self.is_included:
            # Active State
            self.include_cb.blockSignals(True)
            self.include_cb.setChecked(True)
            self.include_cb.blockSignals(False)
            
            self.body_container.setEnabled(True)
            self.setGraphicsEffect(None) # Remove opacity effect
            
            # Button: Action to Remove
            canonical_origin = self.origin.upper() if self.origin else "SCN"
            is_manual = canonical_origin in ["SCN", "MANUAL_SOP"]
            
            self.remove_btn.setText("Delete" if is_manual else "Exclude")
            self.remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.SURFACE};
                    color: {Theme.DANGER};
                    border: 1px solid {Theme.NEUTRAL_200};
                    border-radius: {Theme.RADIUS_MD};
                    padding: 4px 12px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: #fee2e2;
                    border-color: {Theme.DANGER};
                    color: {Theme.DANGER_HOVER};
                }}
            """)
        else:
            # Soft Deleted State
            self.include_cb.blockSignals(True)
            self.include_cb.setChecked(False)
            self.include_cb.blockSignals(False)
            
            self.body_container.setEnabled(False) 
            
            # Visual Greying Out
            opacity = QGraphicsOpacityEffect(self)
            opacity.setOpacity(0.6)
            self.setGraphicsEffect(opacity)
            
            # Button: Action to Restore
            self.remove_btn.setText("Restore")
            self.remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Theme.SURFACE};
                    color: {Theme.SUCCESS};
                    border: 1px solid {Theme.NEUTRAL_200};
                    border-radius: {Theme.RADIUS_MD};
                    padding: 4px 12px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: #dcfce7;
                    border-color: {Theme.SUCCESS};
                    color: {Theme.SUCCESS_HOVER};
                }}
            """)
 
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
                return safe_int(item.text())
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
    
        
        # [STATE OWNERSHIP] 1. Resolve Data Source
        # Prefer instance-owned canonical data if available (Single Source of Truth)
        canonical_data = self.grid_data if self.grid_data else None
        
        # Fallback to arguments only if not yet initialized (e.g. skeleton mode first pass)
        if not canonical_data:
             raw_source = data if data else self.template.get('grid_data')
             if not raw_source:
    
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
            
            # Enforce Integer standard at UI level
            self.table.setItemDelegate(MonetaryDelegate(self.table))
            
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
        
        # Modern Table Styling
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Theme.SURFACE};
                border: 1px solid {Theme.NEUTRAL_200};
                gridline-color: {Theme.NEUTRAL_200};
                font-size: {Theme.FONT_BODY};
                color: {Theme.NEUTRAL_900};
            }}
            QHeaderView::section {{
                background-color: {Theme.NEUTRAL_100};
                color: {Theme.NEUTRAL_900};
                font-weight: {Theme.WEIGHT_SEMIBOLD};
                border: none;
                border-bottom: 2px solid {Theme.NEUTRAL_200};
                padding: 6px;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {Theme.NEUTRAL_100};
            }}
            QTableWidget::item:selected {{
                background-color: {Theme.PRIMARY};
                color: white;
            }}
        """)
        
        self.table.verticalHeader().setVisible(False)
        # Ensure header text is visible and wraps if needed, but primarily legible
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # Adaptive Column Sizing
        col_count = self.table.columnCount()
        if col_count > 5:
             self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
             self.table.horizontalHeader().setStretchLastSection(True)
        else:
             self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
        # [FIX] SOP-5/SOP-7 UI WIDTH & LAYOUT
        # Determine if this is a 'tables' payload (SOP-5/7) or legacy grid_data
        # 'sub_data' argument is populated only when iterating over 'tables'
        is_expanded_table = (sub_data is not None) or (grid_id in ['TDS_TCS_MISMATCH', 'CANCELLED_SUPPLIERS', 'ITC_3B_2B_OTHER', 'ITC_3B_2B_9X4', 'NON_FILER_SUPPLIERS'])
        
        if is_expanded_table and layout:
             # Force expansion for Detailed Tables
             self.table.setMinimumWidth(850)
             self.table.setMaximumWidth(16777215) # MAX_WIDGET_SIZE
             self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
             self.table.setMinimumHeight(400) # Give it height
             
             
             # Force Header Stretch logic override for big tables
             header = self.table.horizontalHeader()
             
             # [FIX] PROFESSIONAL VISIBILITY: Auto-size first, then allow interaction
             # This ensures full headers ("GSTR 2A Period", "Invoice Number") are visible by default.
             self.table.resizeColumnsToContents()
             
             # Add buffer to columns for breathing room
             for c in range(self.table.columnCount()):
                 w = self.table.columnWidth(c)
                 self.table.setColumnWidth(c, w + 20)

             header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
             header.setStretchLastSection(True)
             
             # Apply layout stretch
             # Check if already in layout to avoid double adding
             if hasattr(layout_to_check, 'indexOf') and layout_to_check.indexOf(self.table) == -1:
                  if hasattr(layout_to_check, 'addWidget'):
                       layout_to_check.addWidget(self.table, stretch=1)
        elif layout:
             # Legacy Behavior for SOP-2/3/4/etc
             self.table.setMaximumWidth(850)
             self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
             # Adjust height to content
             row_h = self.table.rowHeight(0) if self.table.rowCount() > 0 else 30
             total_h = (row_h * self.table.rowCount()) + self.table.horizontalHeader().height() + 20
             self.table.setMinimumHeight(min(total_h, 400))
             
             if hasattr(layout_to_check, 'indexOf') and layout_to_check.indexOf(self.table) == -1:
                  if hasattr(layout_to_check, 'addWidget'):
                       layout_to_check.addWidget(self.table)
        
        # Provenance Note (Dict Schema Safe)
        rows = grid_data.get('rows', [])
        columns = grid_data.get('columns', [])
        
        if rows and columns:
             for i, col in enumerate(columns):
                  col_id = col.get('id') if isinstance(col, dict) else str(col).lower().replace(" ", "_")
                  if not col_id: continue
                  
                  # Support both Dict Rows (Modern) and List Rows (Legacy)
                  first_row = rows[0]
                  if isinstance(first_row, dict):
                       first_cell = first_row.get(col_id, {})
                  elif isinstance(first_row, list) and i < len(first_row):
                       first_cell = first_row[i]
                  else:
                       first_cell = {}
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
        
        issue_id = self.template.get('issue_id', '')
        is_sop_dynamic = issue_id.startswith('SOP-07') or issue_id.startswith('SOP-08') or issue_id.startswith('SOP-09')

        if policy == 'dynamic' or is_sop_dynamic:
            # [FIX] Integrated Toolbar (Word-like)
            if not hasattr(self, 'row_controls'):
                self.row_controls = QFrame(self) # Parented to self to avoid floating
                h_layout = QHBoxLayout(self.row_controls)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(10)
                
                # Add Row Action
                self.add_btn = QPushButton("+ Add Row")
                self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.add_btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {Theme.PRIMARY};
                        border: 1px solid {Theme.NEUTRAL_200};
                        border-radius: 4px;
                        padding: 4px 8px;
                        background-color: {Theme.SURFACE};
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {Theme.NEUTRAL_100};
                        border-color: {Theme.PRIMARY};
                    }}
                """)
                self.add_btn.clicked.connect(self.add_dynamic_row)
                
                # Delete Row Action
                self.del_btn = QPushButton("Delete Row")
                self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.del_btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {Theme.DANGER};
                        border: 1px solid {Theme.NEUTRAL_200};
                        border-radius: 4px;
                        padding: 4px 8px;
                        background-color: {Theme.SURFACE};
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: #fee2e2;
                        border-color: {Theme.DANGER};
                    }}
                """)
                self.del_btn.clicked.connect(self.delete_dynamic_row)
                
                h_layout.addWidget(self.add_btn)
                h_layout.addWidget(self.del_btn)
                h_layout.addStretch()
                
                h_layout.addStretch()
                
                # [FIX] Resolve Layout dynamically if not provided
                if not layout and hasattr(self, 'table') and self.table.parentWidget():
                    layout = self.table.parentWidget().layout()

                # Insert toolbar BELOW table
                # We need to find the table's index in the layout and insert after it
                if layout and hasattr(layout, 'indexOf'):
                    idx = layout.indexOf(self.table)
                    if idx != -1 and hasattr(layout, 'insertWidget'):
                        layout.insertWidget(idx + 1, self.row_controls)
                    else:
                        layout.addWidget(self.row_controls) # Fallback
                elif layout and hasattr(layout, 'addWidget'):
                     layout.addWidget(self.row_controls)
            
            self.row_controls.show()
            
            # [FIX] Context Menu for Table
            self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            try:
                self.table.customContextMenuRequested.disconnect() # Avoid duplicates
            except: pass
            self.table.customContextMenuRequested.connect(self.show_table_context_menu)
            
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

    def show_table_context_menu(self, pos):
        """Show context menu for table interactions (Word-like)"""
        if not self.grid_data: return
        
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        
        add_action = QAction("Add Row", self)
        add_action.triggered.connect(self.add_dynamic_row)
        menu.addAction(add_action)
        
        del_action = QAction("Delete Row", self)
        del_action.triggered.connect(self.delete_dynamic_row)
        menu.addAction(del_action)
        
        # Only enable delete if a row is selected or clicked
        item = self.table.itemAt(pos)
        if not item:
            del_action.setEnabled(False)
            
        menu.exec(self.table.viewport().mapToGlobal(pos))

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
        """Handle changes in grid table - Enforce Integers"""
        cell_info = item.data(Qt.ItemDataRole.UserRole)
        if not cell_info:
            return
            
        # Update variable
        var_name = cell_info.get('var')
        text = item.text().replace(',', '').replace('₹', '').strip()
        
        try:
            # Enforce Integer standard (Round Half Up)
            f = safe_int(text) if text else 0
            val = int(f + 0.5) if f >= 0 else int(f - 0.5)
            # Update UI text to integer string if it was float-like
            if '.' in text:
                item.tableWidget().blockSignals(True)
                item.setText(str(val))
                item.tableWidget().blockSignals(False)
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
                    col_obj = cols[col_idx]
                    col_id = col_obj.get('id') if isinstance(col_obj, dict) else str(col_obj).lower().replace(" ", "_")
                    
                    if col_id:
                        # Locate cell dict in canonical source
                        row_raw = rows[row_idx]
                        
                        # Scenario A: Dict-based Row
                        if isinstance(row_raw, dict):
                            if col_id in row_raw:
                                if isinstance(row_raw[col_id], dict):
                                    row_raw[col_id]['value'] = val
                                else:
                                    row_raw[col_id] = {'value': val, 'type': 'static'}
                            else:
                                # New Column in existing row
                                row_raw[col_id] = {'value': val, 'type': 'input'}
                                
                        # Scenario B: List-based Row
                        elif isinstance(row_raw, list) and col_idx < len(row_raw):
                            if isinstance(row_raw[col_idx], dict):
                                row_raw[col_idx]['value'] = val
                            else:
                                row_raw[col_idx] = val # Primitive storage
        except Exception as e:
            print(f"[IssueCard ERROR] Failed to sync grid edit: {e}")
            
        # 1. Update numeric totals
        self.calculate_values()
        
        # 2. Narration Sync: Auto-refresh brief-facts/draft content
        self.update_editor_content(is_recalculation=True)

    def update_variable(self, name, value):
        self.variables[name] = value
        self.calculate_values()

    def validate_tax_inputs(self, show_ui=True) -> bool:
        """
        [PHASE A] Financial Integrity Guard.
        Categorically block negative values in demand fields.
        Returns: True if valid, False if negative exists.
        """
        from PyQt6.QtGui import QColor
        is_valid = True
        if not hasattr(self, 'table'): return True
        
        # Reset background colors for numeric cells
        # (Assuming the grid uses standard numeric mapping)
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if not item: continue
                
                txt = item.text().replace(',', '').strip()
                try:
                    val = safe_int(txt)
                    if val < 0:
                        is_valid = False
                        if show_ui:
                            item.setBackground(QColor("#fecaca")) # Theme.DANGER light
                    else:
                        # Restore default if was previously bad
                        item.setBackground(Qt.GlobalColor.transparent)
                except ValueError:
                    pass
        
        return is_valid

    def calculate_values(self):
        """Centralized value calculation and UI sync."""
        if not hasattr(self, 'table'): return
        
        # Trigger validation
        valid = self.validate_tax_inputs(show_ui=True)
        # We don't block the calculation itself, just highlight the UI
        
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
        self.update_editor_content()

    def refresh_totals_ui(self):
        """Update IGST/CGST/SGST labels and signals based on current breakdown"""
        breakdown = self.get_tax_breakdown()
        
        # 1. Update Dashboard Labels
        igst = 0
        cgst = 0
        sgst = 0
        
        # Map acts to dashboard slots (Case Insensitive)
        for act, values in breakdown.items():
            tax_val = values.get('tax', 0)
            act_upper = str(act).upper()
            if 'IGST' in act_upper: igst += tax_val
            elif 'CGST' in act_upper: cgst += tax_val
            elif 'SGST' in act_upper or 'UGST' in act_upper: sgst += tax_val
            
        from src.utils.formatting import format_indian_number
        if hasattr(self, 'lbl_igst'):
            self.lbl_igst.setText(f"IGST: {format_indian_number(igst, prefix_rs=True)}")
        if hasattr(self, 'lbl_cgst'):
            self.lbl_cgst.setText(f"CGST: {format_indian_number(cgst, prefix_rs=True)}")
        if hasattr(self, 'lbl_sgst'):
            self.lbl_sgst.setText(f"SGST: {format_indian_number(sgst, prefix_rs=True)}")

        # 2. Update header badge (Total Tax)
        total_tax = sum(v.get('tax', 0) for v in breakdown.values())
        if hasattr(self, 'tax_badge'):
            formatted_tax = format_indian_number(total_tax, prefix_rs=True)
            self.tax_badge.setText(f"Tax: {formatted_tax}")
            self.tax_badge.show()

        # 3. Emit signals for summary persistence (Strict Integers)
        total_interest = sum(v.get('interest', 0) for v in breakdown.values())
        total_penalty = sum(v.get('penalty', 0) for v in breakdown.values())

        # Force integer conversion for safety
        self.valuesChanged.emit({
            'tax': int(total_tax),
            'interest': int(total_interest),
            'penalty': int(total_penalty)
        })
        

    def calculate_grid(self, data=None):
        """Evaluate formulas in the grid with explicit variable binding precedence"""
        # [FIX] Prioritize Instance Grid State over Static Template
        grid_data = data if data else self.grid_data
        if not grid_data: 
            grid_data = self.template.get('grid_data')
        
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
                                if grid_val not in (None, ""):
                                    # Standardize on Integer at bootstrap (Round Half Up)
                                    f = safe_int(grid_val)
                                    self.variables[var_name] = int(f + 0.5) if f >= 0 else int(f - 0.5)
                                else:
                                    self.variables[var_name] = 0
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


    def extract_html_body(self, html, allow_raw=True):
        """Extract content from body tag. If allow_raw is True and no body found, returns original."""
        import re
        if not html: return ""
        
        # Check if it's just an empty Qt paragraph
        plain_text = re.sub(r'<[^>]+>', '', html).strip()
        if not plain_text and "<br" not in html and "<img" not in html and "<table" not in html:
            return ""
            
        match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return html if allow_raw else ""

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
            if self.extract_html_body(current_html).strip() != self.extract_html_body(self.last_rendered_html).strip():
                if hasattr(self, 'sync_warning'):
                    self.sync_warning.show()
                return
        
        if hasattr(self, 'sync_warning'):
            self.sync_warning.hide()

        # [STRICT AUDIT LOGGING]
        print(f"\n--- Narrrative Sync Start: {self.issue_id} (Mode: {self.mode}) ---")

        def get_and_log(key, label, fallbacks=None):
            val = t.get(key)
            path = f"templates.{key}"
            
            if not val and fallbacks:
                for f_key in fallbacks:
                    val = t.get(f_key)
                    if val:
                        path = f"templates.{f_key} (fallback)"
                        break
            
            if not val:
                # Last resort: check root if requested (only for Brief Facts as per user)
                if label == "Brief Facts":
                    val = self.template.get('brief_facts')
                    if val: path = "root.brief_facts (fallback)"

            content = self.extract_html_body(str(val)) if val else ""
            if content:
                print(f"DEBUG: Found {label} via {path}")
            else:
                # [DIAGNOSTIC] Print raw value to see why it's considered missing
                raw_repr = repr(val)[:100] + ("..." if len(repr(val)) > 100 else "")
                print(f"DEBUG: Missing {label} (Tried {path}) | Raw Value: {raw_repr} | Type: {type(val)}")
            return content

        # 1. Resolve Sections
        if self.mode == "DRC-01A":
            brief_facts = get_and_log('brief_facts_drc01a', "Brief Facts", fallbacks=['brief_facts'])
            grounds = get_and_log('grounds', "Grounds")
            legal = get_and_log('legal', "Legal")
            conclusion = get_and_log('conclusion', "Conclusion")
        elif self.mode == "SCN":
            brief_facts = get_and_log('brief_facts_scn', "Brief Facts", fallbacks=['brief_facts'])
            grounds = get_and_log('grounds', "Grounds")
            legal = get_and_log('legal', "Legal")
            conclusion = get_and_log('conclusion', "Conclusion")
        else:
            brief_facts = get_and_log('brief_facts', "Brief Facts")
            grounds = get_and_log('grounds', "Grounds")
            legal = get_and_log('legal', "Legal")
            conclusion = get_and_log('conclusion', "Conclusion")

        # 2. Bypass visibility flags temporarily for raw testing
        include_grounds = True
        include_conclusion = True

        # 3. Build structured HTML
        html_sections = []
        
        if brief_facts.strip():
            html_sections.append(f'<div style="margin-bottom: 15px;"><b>Brief Facts:</b><br>{brief_facts}</div>')
        
        if include_grounds and grounds.strip():
            html_sections.append(f'<div style="margin-bottom: 15px;"><b>Grounds / Discussions:</b><br>{grounds}</div>')
        
        if legal.strip():
            html_sections.append(f'<div style="margin-bottom: 15px;"><b>Legal Provisions:</b><br>{legal}</div>')
        
        if include_conclusion and conclusion.strip():
            html_sections.append(f'<div style="margin-bottom: 15px;"><b>Conclusion:</b><br>{conclusion}</div>')
            
        html = "".join(html_sections)
        if not html:
            html = f"<i>{self.CANONICAL_PLACEHOLDER}</i>"

        print(f"--- Narrative Sync End: {self.issue_id} ---\n")
        
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
            
            # [FIX] Robust Normalization for Canonical Grid (List vs Dict)
            # The new IssueCard enforces {'columns': ..., 'rows': ...} but legacy data might be List[List].
            # We must normalize to List[List] for HTML generation.
            rows_data = []
            if isinstance(grid_data, dict):
                rows_data = grid_data.get('rows', [])
            elif isinstance(grid_data, list):
                rows_data = grid_data
            
            
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
            skip_first_col = False
            if isinstance(grid_data, dict) and 'columns' in grid_data:
                columns = grid_data['columns']
                
                # [POLISH] Suppress index column if present
                if columns:
                    first_col = columns[0]
                    first_label = ""
                    if isinstance(first_col, dict):
                        first_label = (first_col.get('label') or first_col.get('header') or first_col.get('name', '')).strip().lower()
                    else:
                        first_label = str(first_col).strip().lower()
                    
                    if first_label in ['sl no', 'sl no.', 'si no', 'si no.', 'sl.no', '#', 'no.']:
                        skip_first_col = True

                html += "<tr>"
                for c, col in enumerate(columns):
                    if c == 0 and skip_first_col: continue
                    # [FIX] Prioritize 'label' (canonical), then 'header', then 'name'
                    if isinstance(col, dict):
                        col_name = col.get('label') or col.get('header') or col.get('name', 'Column')
                    else:
                        col_name = str(col)
                    html += f'<th style="border: 1px solid black; padding: 6px; text-align: center; background-color: #f2f2f2; font-weight: bold; font-size: 10pt;">{col_name}</th>'
                html += "</tr>"
            
            for r, row_data in enumerate(rows_data):
                html += "<tr>"
                
                cells = []
                if isinstance(row_data, list):
                    cells = row_data
                elif isinstance(row_data, dict):
                    if 'cells' in row_data:
                        cells = row_data['cells']
                    elif isinstance(grid_data, dict) and 'columns' in grid_data:
                        columns = grid_data['columns']
                        for col in columns:
                            if isinstance(col, dict):
                                col_key = col.get('key') or col.get('id') or col.get('name', '')
                            else:
                                col_key = str(col)
                            cell_value = row_data.get(col_key, '')
                            cells.append(cell_value)
                    else:
                        cells = list(row_data.values())

                for c, cell_info in enumerate(cells):
                    if c == 0 and skip_first_col: continue
                    val = ""
                    var_name = None
                    
                    if isinstance(cell_info, dict):
                        val = cell_info.get('value', '')
                        var_name = cell_info.get('var')
                    else:
                        val = str(cell_info)
                    
                    # Resolve Value
                    if var_name:
                        if var_name in variables:
                            val = variables[var_name]
                        else:
                            # [DISPLAY FALLBACK] Unresolved variables default to 0 in HTML view
                            val = 0
                    
                    # [POLISH] Professional Table Cell Styling
                    style = "border: 1px solid black; padding: 4px 6px; font-size: 10pt;"
                    
                    # Alignment logic
                    if isinstance(val, (int, float)):
                        style += "text-align: right;"
                    else:
                        try:
                            clean_val = str(val).replace(',', '').replace('₹', '').strip()
                            if clean_val and all(c in '0123456789.-' for c in clean_val):
                                safe_int(clean_val)
                                style += "text-align: right;"
                            else:
                                style += "text-align: left;"
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
                            safe_int(val)
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
                        safe_int(val)
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
        # 1. Get Editor Content and extract just the body
        html = self.editor.toHtml()
        html = self.extract_html_body(html)
        
        # 2. Append Table
        html += self.generate_table_html(self.template, self.variables)
            
        return html

    # Authoritative get_data follows

    def get_data(self):
        """Return current state for saving using the authoritative schema"""
        import copy
        # Deepcopy to break any accidental references to self or UI objects
        data = copy.deepcopy(self.data_snapshot)
        
        # 1. Base Issue Data
        data.update({
            'issue_id': self.template.get('issue_id', 'unknown'),
            'issue': self.template.get('issue_name', ''),
            'variables': copy.deepcopy(self.variables), # Ensure clean copy
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
        data['facts'] = copy.deepcopy(self.variables)
        data['scn_narration'] = data.get(self.content_key, "")
        
        # 4. Table Data Persistence (CRITICAL for ad-hoc conversions)
        # Ensure we don't accidentally link to the template dict itself if it's mutable
        td = None
        if hasattr(self, 'grid_data') and self.grid_data:
             td = copy.deepcopy(self.grid_data)
        elif 'grid_data' in self.template and self.template['grid_data']:
             td = copy.deepcopy(self.template['grid_data'])
        
        data['table_data'] = td

        # Legacy compatibility (optional)
        if self.origin == "ASMT10":
            data['frozen_facts'] = copy.deepcopy(self.variables)

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
        
        # [VISUAL SYNC] Restore Soft Delete state
        self.update_visual_state()

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
        """Return tax breakdown by Act as integers"""
        # [SOFT DELETE] Excluded issues contribute 0 to tax
        if not self.is_included:
            return {}
            
        breakdown = {}
        
        def get_v(key):
            return safe_int(self.variables.get(key, 0))

        # [REORDERED] PRIORITY 1: Canonical-First Logic (Strict Adherence to tax_demand_mapping)
        if hasattr(self, 'tax_mapping') and self.tax_mapping:
            has_mapped_data = False
            for act in ['IGST', 'CGST', 'SGST', 'Cess']:
                var_name = self.tax_mapping.get(act)
                if var_name:
                    val = get_v(var_name)
                    has_mapped_data = True
                    if act not in breakdown:
                        breakdown[act] = {'tax': 0, 'interest': 0, 'penalty': 0}
                    breakdown[act]['tax'] = val
            
            if has_mapped_data:
                return breakdown

        # [REORDERED] PRIORITY 2: Structured Liability Config (Contract Mode)
        liability_config = self.template.get('liability_config')
        if liability_config:
            model = liability_config.get('model')
            heads = liability_config.get('column_heads', [])
            indices = liability_config.get('row_indices', [])
            
            def get_row_var(idx, head):
                return f"row{idx+1}_{head.lower()}"

            if model in ['single_row', 'single_column', 'multiple_rows']:
                for r_idx in indices:
                    for head in heads:
                        var_name = get_row_var(r_idx, head)
                        val = get_v(var_name)
                        act = head # CGST, SGST, IGST
                        if act == 'Amount': act = 'IGST' 
                        
                        if act not in breakdown:
                            breakdown[act] = {'tax': 0, 'interest': 0, 'penalty': 0}
                        breakdown[act]['tax'] += val
                
                if breakdown: 
                    return breakdown

            elif model == 'sum_of_rows':
                current_grid = self.grid_data if hasattr(self, 'grid_data') and self.grid_data else self.template.get('grid_data')
                if current_grid and isinstance(current_grid, dict):
                    columns = current_grid.get('columns', [])
                    col_map = {}
                    for col in columns:
                        if isinstance(col, dict):
                             lbl = str(col.get('label', '')).upper()
                             cid = col.get('id')
                             for head in heads:
                                 if head.upper() in lbl: col_map[head] = cid
                    
                    if col_map:
                        rows = current_grid.get('rows', [])
                        for row in rows:
                            is_total = False
                            for cell in row.values():
                                if isinstance(cell, dict) and 'value' in cell:
                                    if "TOTAL" in str(cell['value']).upper(): is_total = True; break
                            if is_total: continue

                            for head, cid in col_map.items():
                                cell = row.get(cid)
                                if isinstance(cell, dict):
                                    val = 0.0
                                    if cell.get('var'): val = get_v(cell['var'])
                                    else: val = safe_int(cell.get('value', 0))
                                    
                                    if head not in breakdown:
                                        breakdown[head] = {'tax': 0, 'interest': 0, 'penalty': 0}
                                    breakdown[head]['tax'] += val
                        
                        if breakdown: 
                            print("BREAKDOWN GENERATED:", breakdown)
                            return breakdown

        # [FALLBACK] Legacy / Explicit Act variables (High risk of hijacking)
        igst = get_v('tax_igst') or get_v('igst_tax')
        cgst = get_v('tax_cgst') or get_v('cgst_tax')
        sgst = get_v('tax_sgst') or get_v('sgst_tax')
        cess = get_v('tax_cess') or get_v('cess_tax')
        
        if igst or cgst or sgst or cess:
            if igst: breakdown['IGST'] = {'tax': igst, 'interest': get_v('interest_igst'), 'penalty': get_v('penalty_igst')}
            if cgst: breakdown['CGST'] = {'tax': cgst, 'interest': get_v('interest_cgst'), 'penalty': get_v('penalty_cgst')}
            if sgst: breakdown['SGST'] = {'tax': sgst, 'interest': get_v('interest_sgst'), 'penalty': get_v('penalty_sgst')}
            if cess: breakdown['Cess'] = {'tax': cess, 'interest': get_v('interest_cess'), 'penalty': get_v('penalty_cess')}
            print("BREAKDOWN GENERATED:", breakdown)
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
                                    val = 0
                                    raw_val = None
                                    if 'var' in cell and cell['var']:
                                         raw_val = get_v(cell['var'])
                                         val = raw_val
                                    else:
                                         # Try static/input value
                                         val = safe_int(cell.get('value', 0))
                                    
                                    if val > 0:
                                        temp_totals[act] += val
                        
                        # Transfer to breakdown
                        has_val = False
                        for act, total in temp_totals.items():
                            if total > 0:
                                if act not in breakdown: breakdown[act] = {'tax': 0, 'interest': 0, 'penalty': 0}
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
            
        print("BREAKDOWN GENERATED:", breakdown)
        return breakdown
