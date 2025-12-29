import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QFrame, QPushButton, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize

# Mock CompliancePointCard (Copy-pasted relevant parts or importing if possible)
# For isolation, I will redefine it to ensure I am testing the Logic I wrote.

class CompliancePointCard(QFrame):
    def __init__(self, number, title, description, parent=None):
        super().__init__(parent)
        self.number = number
        self.main_layout = QVBoxLayout(self)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        
        # Details Box
        self.details_box = QFrame()
        details_layout = QVBoxLayout(self.details_box)
        
        self.details_lbl = QLabel("No detailed analysis performed yet.")
        self.details_lbl.setVisible(True)
        details_layout.addWidget(self.details_lbl)
        
        self.table_widget = QTableWidget()
        self.table_widget.setVisible(False)
        details_layout.addWidget(self.table_widget)
        
        self.content_layout.addWidget(self.details_box)
        self.main_layout.addWidget(self.content_area)
        
        self.resize(600, 400)

    def set_status(self, status, value_text=None, details=None):
        print(f"DEBUG: set_status called with status={status}, details_keys={details.keys() if details else None}")
        
        if details:
            # Check if details is structured table data
            if isinstance(details, dict) and "summary_table" in details:
                print("DEBUG: summary_table found! Rendering table...")
                tbl_data = details["summary_table"]
                headers = tbl_data.get("headers", [])
                rows = tbl_data.get("rows", [])
                
                print(f"DEBUG: Headers: {headers}")
                print(f"DEBUG: Row Count: {len(rows)}")
                
                self.table_widget.setColumnCount(len(headers))
                self.table_widget.setRowCount(len(rows))
                self.table_widget.setHorizontalHeaderLabels(headers)
                
                # self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                
                for r, row_data in enumerate(rows):
                    self.table_widget.setItem(r, 0, QTableWidgetItem(str(row_data.get("col0", ""))))
                    for c in range(1, 4): 
                        val = row_data.get(f"col{c}", 0)
                        self.table_widget.setItem(r, c, QTableWidgetItem(str(val)))
                        
                self.table_widget.setVisible(True)
                self.details_lbl.setVisible(False)
            else:
                print("DEBUG: No summary_table in details.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Payload from previous debug step
    payload = {
      "category": "Output Liability",
      "description": "Outward Liability Mismatch (GSTR-1 vs 3B)",
      "total_shortfall": 0,
      "summary_table": {
        "headers": ["Description", "CGST", "SGST", "IGST"],
        "rows": [
          { "col0": "3B", "col1": 9760645, "col2": 9760645, "col3": 2311132 },
          { "col0": "GSTR-1", "col1": 0, "col2": 0, "col3": 0 },
          { "col0": "Diff", "col1": 0, "col2": 0, "col3": 0 }
        ]
      }
    }

    card = CompliancePointCard(1, "Test Point", "Test Description")
    card.show()
    
    print("Setting status...")
    card.set_status("pass", "Matched", details=payload)
    
    sys.exit(app.exec())
