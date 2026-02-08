from PyQt6.QtWidgets import QApplication
import sys
import os

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.issue_card import IssueCard

def verify_boundary():
    app = QApplication(sys.argv)
    
    print("--- [TEST 1] Legacy List-Data Snapshot ---")
    legacy_snapshot = {
        'issue_id': 'LEGACY_001',
        'issue_name': 'Legacy Test Issue',
        'table_data': [
            [{'var': 'v1', 'value': 100}, {'var': 'v2', 'value': 200}],
            [{'var': 'v3', 'value': 300}, {'var': 'v4', 'value': 400}]
        ],
        # partial legacy structure
        'variables': {'v1': 100}
    }
    
    try:
        card = IssueCard.restore_snapshot(legacy_snapshot)
        print("SUCCESS: Legacy snapshot restored.")
        # Check internal structure
        if isinstance(card.template.get('grid_data'), dict):
            print("VERIFIED: grid_data is now a Dict.")
            rows = card.template['grid_data']['rows']
            print(f"VERIFIED: Converted {len(rows)} rows.")
            print(f"Sample Row 0: {rows[0]}")
        else:
            print("FAILURE: grid_data is NOT a dict!")
            
    except Exception as e:
        print(f"FAILURE during Legacy Restore: {e}")

    print("\n--- [TEST 2] Modern Grid-Data Snapshot ---")
    modern_snapshot = {
        'issue_id': 'MODERN_001',
        'issue_name': 'Modern Test Issue',
        'grid_data': {
            'headers': ['Col A', 'Col B'],
            'rows': [
                {'id': 'r0', 'c0': 10, 'c1': 20}
            ],
            'columns': ['c0', 'c1']
        },
        'table_data': [[1,2]] # LEAKAGE to be purged
    }
    
    try:
        card = IssueCard.restore_snapshot(modern_snapshot)
        print("SUCCESS: Modern snapshot restored.")
        passed_data = card.data_payload # sanitized data passed to init
        if 'table_data' not in passed_data:
             print("VERIFIED: Leaked 'table_data' was PURGED.")
        else:
             print("FAILURE: Leaked 'table_data' persisted!")
             
    except Exception as e:
        print(f"FAILURE during Modern Restore: {e}")

    print("\n--- [TEST 3] Constructor Guard (Direct Injection) ---")
    try:
        # Bypass factory to test constructor guard
        IssueCard(IssueCard._FACTORY_TOKEN, template={'grid_data': [[1,2]]}, lifecycle_stage="HYDRATION")
        print("FAILURE: Constructor accepted list data!")
    except ValueError as e:
        print(f"SUCCESS: Constructor caught invalid data: {e}")
    print("\n--- [TEST 4] Fatal Invariant (Empty Card) ---")
    try:
        # Pass empty grid_data to trigger Fatal Invariant
        IssueCard(IssueCard._FACTORY_TOKEN, template={'issue_id': 'EMPTY_001', 'grid_data': None}, lifecycle_stage="HYDRATION")
        print("FAILURE: Invariant failed to catch empty card!")
    except ValueError as e:
        if "FATAL" in str(e):
             print(f"SUCCESS: Caught Fatal Invariant: {e}")
        else:
             print(f"PARTIAL SUCCESS: Caught error but message differs: {e}")
    except Exception as e:
        print(f"Unknown Error in Test 4: {e}")

    print("\n--- [TEST 5] Narrative Only Restore (Supported) ---")
    try:
        # Narrative Only issue should pass invariant even without grid
        card = IssueCard(IssueCard._FACTORY_TOKEN, template={'issue_id': 'NARRATIVE_001', 'grid_data': None, 'narrative_only': True}, lifecycle_stage="HYDRATION")
        print(f"SUCCESS: Narrative Only card restored. Is Narrative? {card.template.get('narrative_only')}")
    except Exception as e:
        print(f"FAILURE: Narrative Only gave error: {e}")

if __name__ == "__main__":
    verify_boundary()
