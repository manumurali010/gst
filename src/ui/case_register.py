from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QPushButton, QHBoxLayout, QAbstractItemView, 
                             QTabWidget, QLineEdit, QFrame, QMenu, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from src.database.db_manager import DatabaseManager

class CaseRegister(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header Section
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Case File Registers")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in current register...")
        self.search_input.setFixedWidth(300)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        self.search_input.textChanged.connect(self.filter_current_table)
        header_layout.addWidget(self.search_input)
        
        # Refresh Button
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        refresh_btn.clicked.connect(self.load_all_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addWidget(header_widget)
        
        # Tab Widget
        self.tabs = QTabWidget()
        # Styling is now handled globally in proceedings.qss

        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # OC Register Tab
        self.oc_widget = QWidget()
        self.oc_table = self.create_oc_table()
        oc_layout = QVBoxLayout(self.oc_widget)
        oc_layout.setContentsMargins(0, 0, 0, 0)
        oc_layout.addWidget(self.oc_table)
        self.tabs.addTab(self.oc_widget, "OC Register")
        
        # DRC-01A Register Tab
        self.drc01a_widget = QWidget()
        self.drc01a_table = self.create_drc01a_table()
        drc01a_layout = QVBoxLayout(self.drc01a_widget)
        drc01a_layout.setContentsMargins(0, 0, 0, 0)
        drc01a_layout.addWidget(self.drc01a_table)
        self.tabs.addTab(self.drc01a_widget, "DRC-01A Register")
        
        # SCN Register Tab
        self.scn_widget = QWidget()
        self.scn_table = self.create_scn_table()
        scn_layout = QVBoxLayout(self.scn_widget)
        scn_layout.setContentsMargins(0, 0, 0, 0)
        scn_layout.addWidget(self.scn_table)
        self.tabs.addTab(self.scn_widget, "SCN Register")
        
        # OIO Register Tab
        self.oio_widget = QWidget()
        self.oio_table = self.create_oio_table()
        oio_layout = QVBoxLayout(self.oio_widget)
        oio_layout.setContentsMargins(0, 0, 0, 0)
        oio_layout.addWidget(self.oio_table)
        self.tabs.addTab(self.oio_widget, "OIO Register")
        
        # ASMT-10 Register Tab (NEW)
        self.asmt10_widget = QWidget()
        self.asmt10_table = self.create_asmt10_table()
        asmt_layout = QVBoxLayout(self.asmt10_widget)
        asmt_layout.setContentsMargins(0, 0, 0, 0)
        asmt_layout.addWidget(self.asmt10_table)
        self.tabs.addTab(self.asmt10_widget, "ASMT-10 Register")
        
        layout.addWidget(self.tabs)

        self.setLayout(layout)
        self.load_all_data()

    def setup_table_style(self, table):
        """Apply modern styling to table"""
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        
        # Header Style
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        
        # Table Style
        table.setStyleSheet("""
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
        """)
        
        # Enable Context Menu
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)

    def create_oc_table(self):
        """Create OC Register table with 6 columns"""
        table = QTableWidget()
        table.setColumnCount(6)
        headers = ["Sl. No.", "OC No.", "Content", "Date", "To", "Copy To"]
        table.setHorizontalHeaderLabels(headers)
        
        self.setup_table_style(table)
        
        # Set specific column widths
        table.setColumnWidth(0, 60)   # Sl. No.
        table.setColumnWidth(1, 120)  # OC No.
        table.setColumnWidth(2, 200)  # Content
        table.setColumnWidth(3, 100)  # Date
        table.setColumnWidth(4, 250)  # To
        # Copy To stretches
        
        return table

    def create_scn_table(self):
        """Create SCN Register table with 14 columns"""
        table = QTableWidget()
        table.setColumnCount(14)
        headers = [
            "Sl. No.", "GSTIN", "Legal Name", "Issue", "Financial Year", 
            "Section Proceeding", "Issue (Section Violated)", "SCN No.", "SCN Date",
            "Demand (CGST)", "Demand (SGST)", "Demand (IGST)", "Demand (Total)", "Remarks"
        ]
        table.setHorizontalHeaderLabels(headers)
        
        self.setup_table_style(table)
        
        # Set specific column widths
        table.setColumnWidth(0, 60)   # Sl. No.
        table.setColumnWidth(1, 140)  # GSTIN
        table.setColumnWidth(2, 200)  # Legal Name
        table.setColumnWidth(3, 200)  # Issue
        table.setColumnWidth(4, 100)  # FY
        table.setColumnWidth(5, 120)  # Section
        table.setColumnWidth(6, 150)  # Section Violated
        table.setColumnWidth(7, 120)  # SCN No
        table.setColumnWidth(8, 100)  # Date
        # Demands default width is fine
        
        return table

    def create_oio_table(self):
        """Create OIO Register table with 16 columns"""
        table = QTableWidget()
        table.setColumnCount(16)
        headers = [
            "Sl. No.", "GSTIN", "Legal Name", "Issue", "Financial Year", 
            "Section Proceeding", "Issue (Section Violated)", "SCN No.", "SCN Date",
            "OIO No.", "OIO Date",
            "Demand (CGST)", "Demand (SGST)", "Demand (IGST)", "Demand (Total)", "Remarks"
        ]
        table.setHorizontalHeaderLabels(headers)
        
        self.setup_table_style(table)
        
        # Set specific column widths
        table.setColumnWidth(0, 60)   # Sl. No.
        table.setColumnWidth(1, 140)  # GSTIN
        table.setColumnWidth(2, 200)  # Legal Name
        table.setColumnWidth(3, 200)  # Issue
        table.setColumnWidth(4, 100)  # FY
        table.setColumnWidth(5, 120)  # Section
        table.setColumnWidth(6, 150)  # Section Violated
        table.setColumnWidth(7, 120)  # SCN No
        table.setColumnWidth(8, 100)  # SCN Date
        table.setColumnWidth(9, 120)  # OIO No
        table.setColumnWidth(10, 100) # OIO Date
        
        return table

    def create_drc01a_table(self):
        """Create DRC-01A Register table with 13 columns (No SCN No)"""
        table = QTableWidget()
        table.setColumnCount(13)
        headers = [
            "Sl. No.", "GSTIN", "Legal Name", "Issue", "Financial Year", 
            "Section Proceeding", "Issue (Section Violated)", "DRC-01A Date",
            "Demand (CGST)", "Demand (SGST)", "Demand (IGST)", "Demand (Cess)", "Demand (Total)", "Remarks"
        ]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        self.setup_table_style(table)
        
        # Set specific column widths
        table.setColumnWidth(0, 60)   # Sl. No.
        table.setColumnWidth(1, 140)  # GSTIN
        table.setColumnWidth(2, 200)  # Legal Name
        table.setColumnWidth(3, 200)  # Issue
        table.setColumnWidth(4, 100)  # FY
        table.setColumnWidth(5, 120)  # Section
        table.setColumnWidth(6, 150)  # Section Violated
        table.setColumnWidth(7, 100)  # Date
        # Demands default width is fine
        
        return table

    def load_all_data(self):
        """Load data for all registers"""
        self.load_oc_register()
        self.load_drc01a_register()
        self.load_scn_register()
        self.load_scn_register()
        self.load_oio_register()
        self.load_asmt10_register()
        
        # Re-apply filter if text exists

        if self.search_input.text():
            self.filter_current_table(self.search_input.text())

    def load_oc_register(self):
        """Load OC Register data"""
        entries = self.db.get_oc_register_entries()
        self.oc_table.setRowCount(len(entries))
        
        for i, entry in enumerate(entries):
            self.oc_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.oc_table.setItem(i, 1, QTableWidgetItem(str(entry.get('OC_Number', ''))))
            self.oc_table.setItem(i, 2, QTableWidgetItem(str(entry.get('OC_Content', ''))))
            self.oc_table.setItem(i, 3, QTableWidgetItem(str(entry.get('OC_Date', ''))))
            self.oc_table.setItem(i, 4, QTableWidgetItem(str(entry.get('OC_To', ''))))
            self.oc_table.setItem(i, 5, QTableWidgetItem(str(entry.get('OC_Copy_To', ''))))
            
            # Store data for deletion
            self.oc_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, entry)

    def load_drc01a_register(self):
        """Load DRC-01A Register data"""
        cases = self.db.get_drc01a_register_cases()
        self.drc01a_table.setRowCount(len(cases))
        
        for i, case in enumerate(cases):
            self.drc01a_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.drc01a_table.setItem(i, 1, QTableWidgetItem(str(case.get('GSTIN', ''))))
            self.drc01a_table.setItem(i, 2, QTableWidgetItem(str(case.get('Legal Name', ''))))
            self.drc01a_table.setItem(i, 3, QTableWidgetItem(str(case.get('Issue_Description', ''))))
            self.drc01a_table.setItem(i, 4, QTableWidgetItem(str(case.get('Financial_Year', ''))))
            self.drc01a_table.setItem(i, 5, QTableWidgetItem(str(case.get('Section', ''))))
            self.drc01a_table.setItem(i, 6, QTableWidgetItem(str(case.get('Issue_Description', ''))))
            self.drc01a_table.setItem(i, 7, QTableWidgetItem(str(case.get('OC_Date', ''))))
            self.drc01a_table.setItem(i, 8, QTableWidgetItem(str(case.get('CGST_Demand', ''))))
            self.drc01a_table.setItem(i, 9, QTableWidgetItem(str(case.get('SGST_Demand', ''))))
            self.drc01a_table.setItem(i, 10, QTableWidgetItem(str(case.get('IGST_Demand', ''))))
            self.drc01a_table.setItem(i, 11, QTableWidgetItem(str(case.get('Cess_Demand', ''))))
            self.drc01a_table.setItem(i, 12, QTableWidgetItem(str(case.get('Total_Demand', ''))))
            self.drc01a_table.setItem(i, 13, QTableWidgetItem(str(case.get('Remarks', ''))))
            
            # Store data for deletion
            self.drc01a_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, case)

    def load_scn_register(self):
        """Load SCN Register data"""
        cases = self.db.get_scn_register_cases()
        self.scn_table.setRowCount(len(cases))
        
        for i, case in enumerate(cases):
            self.scn_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.scn_table.setItem(i, 1, QTableWidgetItem(str(case.get('GSTIN', ''))))
            self.scn_table.setItem(i, 2, QTableWidgetItem(str(case.get('Legal Name', ''))))
            self.scn_table.setItem(i, 3, QTableWidgetItem(str(case.get('Issue_Description', ''))))
            self.scn_table.setItem(i, 4, QTableWidgetItem(str(case.get('Financial_Year', ''))))
            self.scn_table.setItem(i, 5, QTableWidgetItem(str(case.get('Section', ''))))
            self.scn_table.setItem(i, 6, QTableWidgetItem(str(case.get('Issue_Description', ''))))
            self.scn_table.setItem(i, 7, QTableWidgetItem(str(case.get('SCN_Number', ''))))
            self.scn_table.setItem(i, 8, QTableWidgetItem(str(case.get('SCN_Date', ''))))
            self.scn_table.setItem(i, 9, QTableWidgetItem(str(case.get('CGST_Demand', ''))))
            self.scn_table.setItem(i, 10, QTableWidgetItem(str(case.get('SGST_Demand', ''))))
            self.scn_table.setItem(i, 11, QTableWidgetItem(str(case.get('IGST_Demand', ''))))
            self.scn_table.setItem(i, 12, QTableWidgetItem(str(case.get('Total_Demand', ''))))
            self.scn_table.setItem(i, 13, QTableWidgetItem(str(case.get('Remarks', ''))))
            
            # Store data for deletion
            self.scn_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, case)

    def load_oio_register(self):
        """Load OIO Register data"""
        cases = self.db.get_oio_register_cases()
        self.oio_table.setRowCount(len(cases))
        
        for i, case in enumerate(cases):
            self.oio_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.oio_table.setItem(i, 1, QTableWidgetItem(str(case.get('GSTIN', ''))))
            self.oio_table.setItem(i, 2, QTableWidgetItem(str(case.get('Legal Name', ''))))
            self.oio_table.setItem(i, 3, QTableWidgetItem(str(case.get('Issue_Description', ''))))
            self.oio_table.setItem(i, 4, QTableWidgetItem(str(case.get('Financial_Year', ''))))
            self.oio_table.setItem(i, 5, QTableWidgetItem(str(case.get('Section', ''))))
            self.oio_table.setItem(i, 6, QTableWidgetItem(str(case.get('Issue_Description', ''))))
            self.oio_table.setItem(i, 7, QTableWidgetItem(str(case.get('SCN_Number', ''))))
            self.oio_table.setItem(i, 8, QTableWidgetItem(str(case.get('SCN_Date', ''))))
            self.oio_table.setItem(i, 9, QTableWidgetItem(str(case.get('OIO_Number', ''))))
            self.oio_table.setItem(i, 10, QTableWidgetItem(str(case.get('OIO_Date', ''))))
            self.oio_table.setItem(i, 11, QTableWidgetItem(str(case.get('CGST_Demand', ''))))
            self.oio_table.setItem(i, 12, QTableWidgetItem(str(case.get('SGST_Demand', ''))))
            self.oio_table.setItem(i, 13, QTableWidgetItem(str(case.get('IGST_Demand', ''))))
            self.oio_table.setItem(i, 14, QTableWidgetItem(str(case.get('Total_Demand', ''))))
            self.oio_table.setItem(i, 15, QTableWidgetItem(str(case.get('Remarks', ''))))
            
            # Store data for deletion
            self.oio_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, case)

    def create_asmt10_table(self):
        """Create ASMT-10 Register table"""
        table = QTableWidget()
        table.setColumnCount(7)
        headers = ["Sl. No.", "GSTIN", "Financial Year", "Issue Date", "O.C. No.", "Case ID", "Actions"]
        table.setHorizontalHeaderLabels(headers)
        
        self.setup_table_style(table)
        
        table.setColumnWidth(0, 60)
        table.setColumnWidth(1, 140) # GSTIN
        table.setColumnWidth(2, 100) # FY
        table.setColumnWidth(3, 100) # Date
        table.setColumnWidth(4, 120) # OC No
        table.setColumnWidth(5, 120) # Case ID
        # Actions stretch
        
        return table

    def load_asmt10_register(self):
        """Load ASMT-10 Register data"""
        entries = self.db.get_asmt10_register_entries()
        self.asmt10_table.setRowCount(len(entries))
        
        for i, entry in enumerate(entries):
            self.asmt10_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.asmt10_table.setItem(i, 1, QTableWidgetItem(str(entry.get('gstin', ''))))
            self.asmt10_table.setItem(i, 2, QTableWidgetItem(str(entry.get('financial_year', ''))))
            self.asmt10_table.setItem(i, 3, QTableWidgetItem(str(entry.get('issue_date', ''))))
            self.asmt10_table.setItem(i, 4, QTableWidgetItem(str(entry.get('oc_number', ''))))
            self.asmt10_table.setItem(i, 5, QTableWidgetItem(str(entry.get('case_id', ''))))
            
            # Action Button (Placeholder for now, or View)
            btn = QPushButton("View")
            btn.setStyleSheet("padding: 2px 8px; background: transparent; color: #3b82f6; border: 1px solid #3b82f6; border-radius: 4px;")
            self.asmt10_table.setCellWidget(i, 6, btn)
            
            # Store data for deletion/actions
            self.asmt10_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, entry)

    def on_tab_changed(self, index):

        """Handle tab change"""
        # Clear search when switching tabs or re-apply?
        # Let's re-apply filter to the new table
        self.filter_current_table(self.search_input.text())

    def filter_current_table(self, text):
        """Filter the currently visible table"""
        current_widget = self.tabs.currentWidget()
        # Find the table inside the widget
        table = current_widget.findChild(QTableWidget)
        
        if not table:
            return
            
        text = text.lower()
        for row in range(table.rowCount()):
            match = False
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            table.setRowHidden(row, not match)

    def show_context_menu(self, position):
        """Show context menu for table items"""
        # Identify sender table
        sender_table = self.sender()
        if not isinstance(sender_table, QTableWidget):
            return

        menu = QMenu()
        
        # Handle right-click on unselected row
        item = sender_table.itemAt(position)
        if item and not item.isSelected():
            sender_table.clearSelection()
            sender_table.selectRow(item.row())
        
        selection = sender_table.selectionModel().selectedRows()
        count = len(selection)
        
        if count > 0:
            label = "Delete Entry" if count == 1 else f"Delete {count} Entries"
            delete_action = menu.addAction(label)
            action = menu.exec(sender_table.viewport().mapToGlobal(position))
            
            if action == delete_action:
                self.delete_selected_entries(sender_table)

    def delete_selected_entries(self, table):
        """Delete selected entries from the given table"""
        selection = table.selectionModel().selectedRows()
        if not selection:
            return
            
        count = len(selection)
        
        reply = QMessageBox.question(
            self, 'Confirm Deletion', 
            f"Are you sure you want to delete {count} selected entr(ies)?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            fail_count = 0
            
            for index in selection:
                row = index.row()
                case_data = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                
                if not case_data:
                    continue
                
                # Special Logic per Register Type
                res = False
                
                if table == self.oc_table:
                    # OC Register: Delete by Entry ID
                    entry_id = case_data.get('id')
                    if entry_id:
                        res = self.db.delete_oc_entry(entry_id)
                        
                elif table == self.asmt10_table:
                    # ASMT-10 Register: Delete by Entry ID
                    entry_id = case_data.get('id')
                    if entry_id:
                        res = self.db.delete_asmt10_entry(entry_id)
                        
                else:
                    # Default/Legacy: Delete by Case ID (CSV/Proceeding)
                    # This logic assumes the entry represents a Case
                    case_id = case_data.get('CaseID') or case_data.get('id')
                    
                    if case_id:
                        # Try deleting as CSV case first
                        res = self.db.delete_csv_case(case_id)
                        # If failed, try SQLite Proceeding
                        if not res:
                            res = self.db.delete_proceeding(case_id)
                
                if res:
                    success_count += 1
                else:
                    fail_count += 1
            
            if fail_count == 0:
                QMessageBox.information(self, "Success", f"Successfully deleted {success_count} entr(ies).")
            else:
                QMessageBox.warning(self, "Partial Success", f"Deleted {success_count} entries.\nFailed to delete {fail_count} entries.")
                
            self.load_all_data() # Refresh all tables
