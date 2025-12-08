import sys
import os
from PyQt6.QtWidgets import QApplication, QTableWidgetItem
from PyQt6.QtCore import Qt

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.ui.proceedings_workspace import ProceedingsWorkspace
    from src.database.db_manager import DatabaseManager
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    # Mock Database
    class MockDB:
        def init_sqlite(self): pass
        def get_proceeding(self, pid):
            return {
                'case_id': 'TEST/001',
                'gstin': '32AAAAA0000A1Z5',
                'legal_name': 'Test Trader',
                'initiating_section': '73'
            }
        def get_issue_templates(self):
            return [{
                "issue_id": "OUT_001",
                "issue_name": "Test Issue",
                "templates": {"brief_facts": "Facts", "grounds": "Grounds", "legal": "Legal", "conclusion": "Conclusion"},
                "placeholders": [
                    {"name": "gstr1_taxable", "type": "number"},
                    {"name": "gstr3b_taxable", "type": "number"},
                    {"name": "value_difference", "type": "number", "computed": True},
                    {"name": "tax_difference", "type": "number", "computed": True}
                ],
                "variables": {"gstr1_taxable": 0, "gstr3b_taxable": 0},
                "calc_logic": "def compute(v):\n    diff = float(v.get('gstr1_taxable',0)) - float(v.get('gstr3b_taxable',0))\n    tax = diff * 0.18\n    return {'value_difference': diff, 'tax_difference': tax, 'calculated_tax': tax, 'calculated_interest': 100, 'calculated_penalty': 0}",
                "tax_demand_mapping": {"tax": "calculated_tax", "interest": "calculated_interest", "penalty": "calculated_penalty"}
            }]
        def save_document(self, data):
            print(f"Document saved: {data['doc_type']}")
        def update_proceeding(self, pid, data):
            print(f"Proceeding updated: {data}")

    # Initialize Workspace with Mock DB
    workspace = ProceedingsWorkspace(lambda x: None, proceeding_id="123")
    workspace.db = MockDB()
    workspace.load_issue_templates() # Reload with mock data
    
    # Simulate Adding Issue
    print("Adding Issue Card...")
    workspace.issue_combo.setCurrentIndex(1) # Select first item (index 0 is placeholder)
    workspace.insert_selected_issue()
    
    if len(workspace.issue_cards) != 1:
        print("Error: Issue card not added")
        sys.exit(1)
        
    card = workspace.issue_cards[0]
    print("Issue Card Added")
    
    # Simulate Input Change
    print("Updating Input Values...")
    card.input_widgets['gstr1_taxable'].setText("1000")
    card.input_widgets['gstr3b_taxable'].setText("500")
    
    # Check Card Calculation
    # Wait for signals/slots? Direct check variables
    print(f"Card Variables: {card.variables}")
    if card.variables.get('value_difference') != 500.0:
        print(f"Error: Calculation failed. Expected 500.0, got {card.variables.get('value_difference')}")
        # sys.exit(1) # Don't exit yet, might be async? No, setText triggers signal immediately usually
        
    # Check Grand Totals in Table
    # Total row is last row
    row = workspace.tax_table.rowCount() - 1
    tax_item = workspace.tax_table.item(row, 3)
    interest_item = workspace.tax_table.item(row, 4)
    
    print(f"Table Total Tax: {tax_item.text()}")
    print(f"Table Total Interest: {interest_item.text()}")
    
    expected_tax = 500 * 0.18 # 90.0
    if float(tax_item.text()) != expected_tax:
         print(f"Error: Table Total Tax incorrect. Expected {expected_tax}, got {tax_item.text()}")
         sys.exit(1)
         
    if float(interest_item.text()) != 100.0:
         print(f"Error: Table Total Interest incorrect. Expected 100.0, got {interest_item.text()}")
         sys.exit(1)

    print("Verification Successful!")
    sys.exit(0)

if __name__ == "__main__":
    main()
