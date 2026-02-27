import sys
import os

# Ensure the src module is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from src.ui.scrutiny_tab import ComplianceDashboard
from src.database.db_manager import DatabaseManager

def test_dashboard():
    app = QApplication(sys.argv)
    db = DatabaseManager()
    
    print("--- Initializing ComplianceDashboard ---")
    dashboard = ComplianceDashboard(db_manager=db)
    
    print("\n--- Current Keys in Dashboard ---")
    for k in dashboard.cards.keys():
        print(f"Key: {k}, Type: {type(k)}")
        
    print("\n--- Simulating update_point(1, 'pass', 'Rs. 0') ---")
    dashboard.update_point(1, "pass", "Rs. 0")
    
    # Also simulate what the backend used to do before the fix (if it somehow sends a string)
    # print("\n--- Simulating update_point('1', 'pass', 'Rs. 0') ---")
    # dashboard.update_point('1', "pass", "Rs. 0")

if __name__ == '__main__':
    test_dashboard()
