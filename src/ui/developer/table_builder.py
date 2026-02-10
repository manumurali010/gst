from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QMenu, 
                             QMessageBox, QInputDialog, QLabel, QStyledItemDelegate, QLineEdit,
                             QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QAction, QColor, QFont

class FormulaDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_widget = parent

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            self.table_widget.current_editor = editor
            # Install app-level event filter to catch clicks before focus change
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().installEventFilter(self.table_widget)
        return editor

    def destroyEditor(self, editor, index):
        if editor == self.table_widget.current_editor:
            self.table_widget.current_editor = None
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().removeEventFilter(self.table_widget)
        super().destroyEditor(editor, index)

class TableBuilderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_editor = None # Track active editor
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_row_btn = QPushButton("+ Row")
        add_row_btn.clicked.connect(self.add_row)
        toolbar.addWidget(add_row_btn)
        
        add_col_btn = QPushButton("+ Column")
        add_col_btn.clicked.connect(self.add_column)
        toolbar.addWidget(add_col_btn)
        
        del_row_btn = QPushButton("- Row")
        del_row_btn.clicked.connect(self.remove_row)
        toolbar.addWidget(del_row_btn)
        
        del_col_btn = QPushButton("- Column")
        del_col_btn.clicked.connect(self.remove_column)
        toolbar.addWidget(del_col_btn)
        
        toolbar.addStretch()
        
        help_btn = QPushButton("?")
        help_btn.setToolTip("Help: Use =A1+B1 for formulas. First row/col are headers.")
        help_btn.clicked.connect(self.show_help)
        toolbar.addWidget(help_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget(4, 4)
        self.table.setItemDelegate(FormulaDelegate(self)) # Set Custom Delegate
        self.table.setHorizontalHeaderLabels(["A", "B", "C", "D"])
        self.table.setVerticalHeaderLabels(["1", "2", "3", "4"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Enable context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)
        
        # Note: We use App-level event filter installed by Delegate now
        
        # Status Tip
        self.status_lbl = QLabel("Tip: Enter formulas starting with '=' (e.g., =A2*B2)")
        self.status_lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_lbl)

    # ... (add_row, add_column, etc. unchanged) ...
    def add_row(self):
        self.table.insertRow(self.table.rowCount())
        self.update_headers()

    def add_column(self):
        self.table.insertColumn(self.table.columnCount())
        self.update_headers()

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.update_headers()

    def remove_column(self):
        col = self.table.currentColumn()
        if col >= 0:
            self.table.removeColumn(col)
            self.update_headers()
            
    def update_headers(self):
        # Update vertical headers (1, 2, 3...)
        self.table.setVerticalHeaderLabels([str(i+1) for i in range(self.table.rowCount())])
        
        # Update horizontal headers (A, B, C...)
        labels = []
        for i in range(self.table.columnCount()):
            labels.append(self.get_col_label(i))
        self.table.setHorizontalHeaderLabels(labels)

    def get_col_label(self, idx):
        # 0 -> A, 25 -> Z, 26 -> AA
        res = ""
        while idx >= 0:
            res = chr(ord('A') + (idx % 26)) + res
            idx = (idx // 26) - 1
        return res

    def show_context_menu(self, pos):
        menu = QMenu()
        add_r_action = QAction("Add Row", self)
        add_r_action.triggered.connect(self.add_row)
        menu.addAction(add_r_action)
        
        add_c_action = QAction("Add Column", self)
        add_c_action.triggered.connect(self.add_column)
        menu.addAction(add_c_action)
        
        menu.addSeparator()
        
        del_r_action = QAction("Delete Row", self)
        del_r_action.triggered.connect(self.remove_row)
        menu.addAction(del_r_action)
        
        del_c_action = QAction("Delete Column", self)
        del_c_action.triggered.connect(self.remove_column)
        menu.addAction(del_c_action)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def show_help(self):
        QMessageBox.information(self, "Table Builder Help", 
            "1. First Row is typically used for Headers.\n"
            "2. Enter text or numbers normally.\n"
            "3. For calculations, start with '='.\n"
            "   Example: =A2 * B2\n"
            "   Supported: +, -, *, /, (, )\n"
            "   References: A1, B2, etc.")

    def get_data(self):
        """Serialize table data to JSON"""
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        data = {
            "rows": rows,
            "cols": cols,
            "cells": []
        }
        
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self.table.item(r, c)
                txt = item.text() if item else ""
                row_data.append(txt)
            data["cells"].append(row_data)
            
        return data

    def set_data(self, data):
        """Load data from JSON"""
        if not data: return
        
        rows = data.get("rows", 4)
        cols = data.get("cols", 4)
        
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.update_headers()
        
        cells = data.get("cells", [])
        for r, row_data in enumerate(cells):
            if r >= rows: break
            for c, txt in enumerate(row_data):
                if c >= cols: break
                self.table.setItem(r, c, QTableWidgetItem(txt))

    def eventFilter(self, source, event):
        # Debug event order
        # if self.current_editor:
        #    print(f"DEBUG: Event {event.type()} on {source}")

        # Check if we are currently editing a cell using our tracked editor
        if self.current_editor:
            if event.type() == QEvent.Type.MouseButtonPress:
                # Check if the click is on the table viewport
                viewport = self.table.viewport()
                
                # Let's use global pos to be safe
                global_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                viewport_pos = viewport.mapFromGlobal(global_pos)
                
                if viewport.rect().contains(viewport_pos):
                    # print("DEBUG: Click inside viewport")
                    try:
                        text = self.current_editor.text()
                        # print(f"DEBUG: Editor text: '{text}'")
                        # Check if it looks like a formula (allow spaces)
                        if text.strip().startswith('='):
                            # Get the cell under the mouse
                            index = self.table.indexAt(viewport_pos)
                            # print(f"DEBUG: Index: {index.row()}, {index.column()}")
                            if index.isValid():
                                # Get cell address (e.g. A1)
                                col_label = self.get_col_label(index.column())
                                row_label = str(index.row() + 1)
                                ref = f"{col_label}{row_label}"
                                
                                # Insert into editor
                                self.current_editor.insert(ref)
                                # print(f"DEBUG: Inserted {ref}")
                                
                                # Consume event to prevent selection change
                                return True
                    except Exception as e:
                        pass
                        # print(f"DEBUG: Exception in eventFilter: {e}")
            
            elif event.type() == QEvent.Type.FocusOut and source == self.current_editor:
                 # print("DEBUG: FocusOut on editor")
                 pass
                        
        return super().eventFilter(source, event)

class TableBuilderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_editor = None # Track active editor
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_row_btn = QPushButton("+ Row")
        add_row_btn.clicked.connect(self.add_row)
        toolbar.addWidget(add_row_btn)
        
        add_col_btn = QPushButton("+ Column")
        add_col_btn.clicked.connect(self.add_column)
        toolbar.addWidget(add_col_btn)
        
        del_row_btn = QPushButton("- Row")
        del_row_btn.clicked.connect(self.remove_row)
        toolbar.addWidget(del_row_btn)
        
        del_col_btn = QPushButton("- Column")
        del_col_btn.clicked.connect(self.remove_column)
        toolbar.addWidget(del_col_btn)
        
        toolbar.addStretch()
        
        help_btn = QPushButton("?")
        help_btn.setToolTip("Help: Use =A1+B1 for formulas. First row/col are headers.")
        help_btn.clicked.connect(self.show_help)
        toolbar.addWidget(help_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget(4, 4)
        self.table.setItemDelegate(FormulaDelegate(self)) # Set Custom Delegate
        self.table.setHorizontalHeaderLabels(["A", "B", "C", "D"])
        self.table.setVerticalHeaderLabels(["1", "2", "3", "4"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Enable context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)
        
        # Install event filter for interactive formula building
        self.table.viewport().installEventFilter(self)
        
        # Status Tip
        self.status_lbl = QLabel("Tip: Enter formulas starting with '=' (e.g., =A2*B2)")
        self.status_lbl.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.status_lbl)

    def add_row(self):
        self.table.insertRow(self.table.rowCount())
        self.update_headers()

    def add_column(self):
        self.table.insertColumn(self.table.columnCount())
        self.update_headers()

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.update_headers()

    def remove_column(self):
        col = self.table.currentColumn()
        if col >= 0:
            self.table.removeColumn(col)
            self.update_headers()
            
    def update_headers(self):
        # Update vertical headers (1, 2, 3...)
        self.table.setVerticalHeaderLabels([str(i+1) for i in range(self.table.rowCount())])
        
        # Update horizontal headers (A, B, C...)
        labels = []
        for i in range(self.table.columnCount()):
            labels.append(self.get_col_label(i))
        self.table.setHorizontalHeaderLabels(labels)

    def get_col_label(self, idx):
        # 0 -> A, 25 -> Z, 26 -> AA
        res = ""
        while idx >= 0:
            res = chr(ord('A') + (idx % 26)) + res
            idx = (idx // 26) - 1
        return res

    def show_context_menu(self, pos):
        menu = QMenu()
        add_r_action = QAction("Add Row", self)
        add_r_action.triggered.connect(self.add_row)
        menu.addAction(add_r_action)
        
        add_c_action = QAction("Add Column", self)
        add_c_action.triggered.connect(self.add_column)
        menu.addAction(add_c_action)
        
        menu.addSeparator()
        
        del_r_action = QAction("Delete Row", self)
        del_r_action.triggered.connect(self.remove_row)
        menu.addAction(del_r_action)
        
        del_c_action = QAction("Delete Column", self)
        del_c_action.triggered.connect(self.remove_column)
        menu.addAction(del_c_action)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def show_help(self):
        QMessageBox.information(self, "Table Builder Help", 
            "1. First Row is typically used for Headers.\n"
            "2. Enter text or numbers normally.\n"
            "3. For calculations, start with '='.\n"
            "   Example: =A2 * B2\n"
            "   Supported: +, -, *, /, (, )\n"
            "   References: A1, B2, etc.")

    def get_data(self):
        """Serialize table data to JSON"""
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        data = {
            "rows": rows,
            "cols": cols,
            "cells": []
        }
        
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = self.table.item(r, c)
                txt = item.text() if item else ""
                row_data.append(txt)
            data["cells"].append(row_data)
            
        return data

        return super().eventFilter(source, event)

    def set_read_only(self, read_only):
        """
        [PHASE A] Enforce Read-Only Mode for Semantic Tables.
        - Disables editing triggers.
        - Disables toolbar buttons.
        - Disables context menu.
        - [SAFEGUARD] Blocks signals to preventing accidental mutation events during setup.
        """
        self.table.blockSignals(True) # [SAFEGUARD]
        
        if read_only:
            # Disable Editing
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
            
            # Disable Toolbar Buttons
            for i in range(self.layout().itemAt(0).layout().count()):
                widget = self.layout().itemAt(0).layout().itemAt(i).widget()
                if isinstance(widget, QPushButton) and widget.text() != "?":
                    widget.setEnabled(False)
                    
            # Visual Indicator
            self.status_lbl.setText("🔒 Read-Only: Semantic Table (Edit in Codebase)")
            self.status_lbl.setStyleSheet("color: #e67e22; font-weight: bold;")
        else:
            # Re-enable Editing
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.AnyKeyPressed)
            self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            
            # Re-enable Toolbar
            for i in range(self.layout().itemAt(0).layout().count()):
                widget = self.layout().itemAt(0).layout().itemAt(i).widget()
                if isinstance(widget, QPushButton):
                    widget.setEnabled(True)
            
            self.status_lbl.setText("Tip: Enter formulas starting with '=' (e.g., =A2*B2)")
            self.status_lbl.setStyleSheet("color: gray; font-style: italic;")
            
        self.table.blockSignals(False) # [SAFEGUARD]

    def set_data(self, data):
        """Load data from JSON. Handles both simple (Spreadsheet) and Semantic (Read-Only) formats."""
        if not data: return
        
        is_semantic = data.get("is_semantic_view", False)
        
        rows = data.get("rows", 4)
        cols = data.get("cols", 4)
        
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        self.update_headers()
        
        cells = data.get("cells", [])
        
        # [PHASE A] UX Hardening
        if is_semantic:
            # 1. Container Constraints
            self.table.setMaximumWidth(950) # Approx 850-900px + padding
            self.table.setSizePolicy(self.table.sizePolicy().horizontalPolicy(), 
                                   self.table.sizePolicy().verticalPolicy().Expanding)
            
            # 2. visual polish
            self.table.setShowGrid(True)
            self.table.setWordWrap(True)
            self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        else:
            self.table.setMaximumWidth(16777215) # Reset to max
            
        header_font = QFont()
        header_font.setBold(True)
        header_bg = QColor("#f0f0f0")
        
        for r, row_data in enumerate(cells):
            if r >= rows: break
            for c, txt in enumerate(row_data):
                if c >= cols: break
                
                item = QTableWidgetItem(txt)
                
                if is_semantic:
                    # Generic Semantic Styling
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                    
                    # Row 0 (Headers)
                    if r == 0:
                        item.setFont(header_font)
                        item.setBackground(header_bg)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # Col 0 (Row Labels / Description)
                    if c == 0:
                        item.setFont(header_font)
                        item.setBackground(header_bg)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                        # Min width handled by header interaction below loop? 
                        # Actually set strictly here if possible, but easier on the column
                        
                self.table.setItem(r, c, item)
        
            # 3. Column Sizing
            # Col 0 needs min width for readability
            self.table.setColumnWidth(0, 300) # Minimum width for description
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Allow resize but start wide
            
            # Other columns stretch
            for i in range(1, cols):
                 self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

            # [PHASE A] Full-Height Rendering (Mandatory)
            # Must be visible without vertical scrolling whenever possible.
            self.table.resizeRowsToContents()
            
            total_height = self.table.horizontalHeader().height() + (self.table.frameWidth() * 2)
            for r in range(self.table.rowCount()):
                total_height += self.table.rowHeight(r)
            
            # Add small buffer for borders/grid
            total_height += 2 
            
            # Apply Height & Scroll Policy
            self.table.setFixedHeight(total_height)
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        else:
            # Spreadsheet Mode: Reset to default sizing behavior
            self.table.setMaximumHeight(16777215) # Max
            self.table.setMinimumHeight(0)
            self.table.setSizePolicy(self.table.sizePolicy().horizontalPolicy(), 
                                   self.table.sizePolicy().verticalPolicy().Expanding)
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def eventFilter(self, source, event):
        # Check if we are currently editing a cell using our tracked editor
        if self.current_editor:
            if event.type() == QEvent.Type.MouseButtonPress:
                # Check if the click is on the table viewport
                viewport = self.table.viewport()
                
                # Let's use global pos to be safe
                global_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                viewport_pos = viewport.mapFromGlobal(global_pos)
                
                if viewport.rect().contains(viewport_pos):
                    try:
                        text = self.current_editor.text()
                        # Check if it looks like a formula (allow spaces)
                        if text.strip().startswith('='):
                            # Get the cell under the mouse
                            index = self.table.indexAt(viewport_pos)
                            if index.isValid():
                                # Get cell address (e.g. A1)
                                col_label = self.get_col_label(index.column())
                                row_label = str(index.row() + 1)
                                ref = f"{col_label}{row_label}"
                                
                                # Insert into editor
                                self.current_editor.insert(ref)
                                
                                # Consume event to prevent selection change
                                return True
                    except Exception:
                        pass
            
            elif event.type() == QEvent.Type.FocusOut and source == self.current_editor:
                 # Check if we are clicking on the viewport
                 from PyQt6.QtGui import QCursor
                 viewport = self.table.viewport()
                 cursor_pos = QCursor.pos()
                 viewport_pos = viewport.mapFromGlobal(cursor_pos)
                 
                 if viewport.rect().contains(viewport_pos):
                     # If clicking on viewport while editing formula, ignore focus out
                     try:
                         text = self.current_editor.text()
                         if text.strip().startswith('='):
                             return True
                     except:
                         pass
                        
        return super().eventFilter(source, event)
