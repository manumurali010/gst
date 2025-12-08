from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QLineEdit)
from PyQt6.QtCore import Qt, QDate
from src.database.db_manager import DatabaseManager
import pandas as pd
import os

class ReportsTab(QWidget):
    def __init__(self, home_callback):
        super().__init__()
        self.home_callback = home_callback
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Reports & Generated Notices")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(header)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Date From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("Date To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)
        
        filter_layout.addWidget(QLabel("GSTIN:"))
        self.gstin_filter = QLineEdit()
        filter_layout.addWidget(self.gstin_filter)
        
        refresh_btn = QPushButton("Apply Filters")
        refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export to Excel")
        export_btn.clicked.connect(self.export_data)
        filter_layout.addWidget(export_btn)
        
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "GSTIN", "Legal Name", "Form Type", "Status", "File Path"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.load_data()

    def load_data(self):
        all_cases = self.db.get_all_cases()
        
        # Apply filters (basic implementation)
        filtered_cases = []
        start_date = self.date_from.date().toString("yyyy-MM-dd")
        end_date = self.date_to.date().toString("yyyy-MM-dd")
        gstin_query = self.gstin_filter.text().strip().upper()
        
        for case in all_cases:
            case_date = str(case.get('Date', ''))
            case_gstin = str(case.get('GSTIN', '')).upper()
            
            if start_date <= case_date <= end_date:
                if not gstin_query or gstin_query in case_gstin:
                    filtered_cases.append(case)
        
        self.table.setRowCount(len(filtered_cases))
        for row, case in enumerate(filtered_cases):
            self.table.setItem(row, 0, QTableWidgetItem(str(case.get('Date', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(case.get('GSTIN', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(case.get('Legal Name', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(case.get('Form Type', ''))))
            self.table.setItem(row, 4, QTableWidgetItem(str(case.get('Status', ''))))
            self.table.setItem(row, 5, QTableWidgetItem(str(case.get('FilePath', ''))))

    def export_data(self):
        # Basic export logic
        try:
            path = "reports_export.xlsx" # Should ask user for path
            # For simplicity, just dump current filtered data
            # Re-fetch or iterate table
            pass
        except:
            pass
