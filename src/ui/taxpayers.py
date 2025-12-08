from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                             QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from src.database.db_manager import DatabaseManager

class TaxpayersTab(QWidget):
    def __init__(self, home_callback):
        super().__init__()
        self.home_callback = home_callback
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Taxpayers Database")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(header)

        # Actions
        btn_layout = QVBoxLayout()
        import_btn = QPushButton("Import / Update Taxpayers (CSV/Excel)")
        import_btn.setStyleSheet("background-color: #3498db; color: white; padding: 10px; font-size: 14px;")
        import_btn.clicked.connect(self.import_data)
        btn_layout.addWidget(import_btn)
        layout.addLayout(btn_layout)

        # Search
        # (Can add search bar here later)

        # Table Preview (Show first 50 or search results)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["GSTIN", "Legal Name", "Trade Name", "Address", "State", "Email", "Mobile", "Constitution"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)
        
        self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        try:
            # Load all data
            # Note: In a real app with large data, we should paginate or limit this.
            # For now, we load all as requested.
            import pandas as pd
            from src.utils.constants import TAXPAYERS_FILE
            import os
            
            if not os.path.exists(TAXPAYERS_FILE):
                return

            df = pd.read_csv(TAXPAYERS_FILE)
            # Ensure new columns exist in display even if not in file yet
            for col in ["Email", "Mobile", "Constitution"]:
                if col not in df.columns:
                    df[col] = ""
                    
            df = df.fillna("")
            
            self.table.setRowCount(len(df))
            for row, record in df.iterrows():
                self.table.setItem(row, 0, QTableWidgetItem(str(record['GSTIN'])))
                self.table.setItem(row, 1, QTableWidgetItem(str(record['Legal Name'])))
                self.table.setItem(row, 2, QTableWidgetItem(str(record['Trade Name'])))
                self.table.setItem(row, 3, QTableWidgetItem(str(record['Address'])))
                self.table.setItem(row, 4, QTableWidgetItem(str(record['State'])))
                self.table.setItem(row, 5, QTableWidgetItem(str(record.get('Email', ''))))
                self.table.setItem(row, 6, QTableWidgetItem(str(record.get('Mobile', ''))))
                self.table.setItem(row, 7, QTableWidgetItem(str(record.get('Constitution', ''))))
        except Exception as e:
            print(f"Error loading data: {e}")

    def import_data(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv);;Excel Files (*.xlsx *.xls)")
        if fname:
            success, msg = self.db.import_taxpayers(fname)
            if success:
                QMessageBox.information(self, "Success", msg)
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", msg)
