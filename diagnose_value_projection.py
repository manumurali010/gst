
import sys
import os
from PyQt6.QtWidgets import QApplication

# Setup path
sys.path.append(os.getcwd())

from src.ui.issue_card import IssueCard

# Mock Schema
MOCK_SCHEMA = {
    "columns": [
        {"id": "desc", "label": "Description"},
        {"id": "cgst", "label": "CGST"}
    ],
    "rows": [
        {"desc": {"var": "row1_desc", "type": "static"}, "cgst": {"var": "row1_cgst", "type": "input"}}
    ]
}

# Mock Snapshot (Scrutiny Legacy Style - List of Lists)
MOCK_SNAPSHOT_DATA = {
    "issue_id": "SOP-TEST",
    "origin": "ASMT10",
    "table_data": [
        ["Header Desc", "Header CGST"], # Row 0 (Skip)
        ["Taxable Supply", 5000]        # Row 1 (Value)
    ],
    # Crucially, checks if 'variables' is empty or present in snapshot
    "variables": {} 
}

class DiagnosticIssueCard(IssueCard):
    """
    Subclass to intercept init_grid_ui and inspect state
    without modifying the actual codebase.
    """
    def init_grid_ui(self, layout, data=None):
        print("\n[DIAGNOSTIC] === Intercepting init_grid_ui ===")
        print(f"[DIAGNOSTIC] self.variables keys: {list(self.variables.keys())}")
        print(f"[DIAGNOSTIC] 'row1_cgst' present?: {'row1_cgst' in self.variables}")
        if 'row1_cgst' in self.variables:
            print(f"[DIAGNOSTIC] 'row1_cgst' value: {self.variables['row1_cgst']}")
        
        # Check source
        # We can't easily prove source *here* except by inference, 
        # but we can check if it was in the input snapshot's 'variables'.
        
        super().init_grid_ui(layout, data)

def run_diagnostic():
    app = QApplication(sys.argv)
    
    print("--- Starting Value Projection Diagnosis ---")
    
    # 1. Restore Snapshot (Factory simulation)
    # We manually simulate what restore_snapshot does
    # by passing the schema and data to constructor.
    
    print("\n1. Instantiating IssueCard (HYDRATION mode)...")
    try:
        card = DiagnosticIssueCard(
            token=IssueCard._FACTORY_TOKEN,
            template={'grid_data': MOCK_SCHEMA, 'issue_id': 'SOP-TEST'}, 
            data=MOCK_SNAPSHOT_DATA, 
            lifecycle_stage="HYDRATION",
            schema=MOCK_SCHEMA # Factory passes resolved schema
        )
        
        print("\n[DIAGNOSTIC] Instantiation Complete.")
        print(f"[DIAGNOSTIC] Final Variables: {card.variables}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()
