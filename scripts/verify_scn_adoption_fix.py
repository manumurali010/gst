
import sys
import os
import json
from PyQt6.QtWidgets import QApplication

# Setup Path
sys.path.append(os.getcwd())

# Mock DB and ProceedingsWorkspace for isolation
from unittest.mock import MagicMock
from src.ui.proceedings_workspace import ProceedingsWorkspace

def test_scn_adoption_logic():
    print("--- [TEST] SCN Adoption Logic (ASMT-10 Table Persistence) ---")
    
    # 1. Setup Mock Workspace
    # We need to subclass to bypass __init__ UI creation which requires full app
    class TestWorkspace(ProceedingsWorkspace):
        def __init__(self):
            self.db = MagicMock()
            self.proceeding_data = {'id': 'TEST_CASE', 'source_scrutiny_id': 'SCR_001'}
            self.proceeding_id = 'TEST_CASE'
            
    app = QApplication(sys.argv)
    workspace = TestWorkspace()
    
    # 2. Simulate ASMT-10 Record with Summary Table
    # A typical 3-row summary table from Scrutiny
    summary_table = [
        {"description": "Tax Liability Declared", "cgst": 5000, "sgst": 5000, "igst": 0, "cess": 0},
        {"description": "Tax Liability GSTR-3B", "cgst": 4000, "sgst": 4000, "igst": 0, "cess": 0},
        {"description": "Difference", "cgst": 1000, "sgst": 1000, "igst": 0, "cess": 0}
    ]
    
    asmt_record = {
        'issue_id': 'LIABILITY_MISMATCH',
        'data': {
            'issue': 'Liability Mismatch',
            'summary_table': summary_table,
            'grid_data': None, # Critical: Master grid_data is usually None or empty in this scenario
            'tables': None
        }
    }
    
    print(f"INPUT: Summary Table with {len(summary_table)} rows.")
    
    # 3. Run the Adapter
    try:
        # Mock DB issue lookup to return empty or basic template
        workspace.db.get_issue.return_value = None
        workspace.db.get_issue_by_name.return_value = None
        
        result = workspace.build_scn_issue_from_asmt10(asmt_record)
        
        # 4. Inspect Output
        template = result['template']
        grid_data = template.get('grid_data')
        
        if grid_data:
            rows = grid_data.get('rows', [])
            print(f"OUTPUT: grid_data present with {len(rows)} rows.")
            
            # Check content
            if len(rows) == 3:
                print("PASS: Row count matches input.")
                print("SUCCESS: Fix Verified.")
            else:
                print(f"FAIL: Row count mismatch. Expected 3, got {len(rows)}.")
        else:
            print("FAIL: grid_data is None or Empty! (Bug Reproduced)")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_regression_issue_card_binding():
    print("\n--- [TEST] Regression: IssueCard Canonicalization (String Columns) ---")
    from src.ui.issue_card import IssueCard
    
    # Simulate the crash condition: grid_data with columns as list of strings
    bad_grid_data = {
        'columns': ['Tax', 'Interest', 'Penalty'], 
        'rows': [{'Tax': 100, 'Interest': 10, 'Penalty': 0}]
    }
    
    template = {
        'issue_id': 'REGRESSION_TEST',
        'grid_data': bad_grid_data
    }
    
    try:
        # data needs to match structure or be empty. 
        # IssueCard uses data['table_data'] or template['grid_data']
        # We rely on template['grid_data'] here as per report
        card = IssueCard(template, data={}, mode="SCN")
        
        # If we reach here, no crash in __init__ -> init_ui -> bind_grid_data
        print("PASS: IssueCard instantiated without crash.")
        
        # Verify normalization happened internally
        # We can check internal table column count
        if hasattr(card, 'table'):
            cols = card.table.columnCount()
            print(f"OUTPUT: Table created with {cols} columns.")
            if cols == 3:
                print("SUCCESS: Regression Fix Verified.")
            else:
                print(f"FAIL: Expected 3 columns, got {cols}.")
        else:
             print("FAIL: Table widget not created.")
             
    except Exception as e:
        print(f"FAIL: Crashed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scn_adoption_logic()
    test_regression_issue_card_binding()
