import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager
import json

def simulate():
    print("--- Simulating UI Data Enrichtment ---")
    try:
        db = DatabaseManager()
    except Exception as e:
        print(f"FAIL: DatabaseManager init failed: {e}")
        return

    # Check if get_issue exists
    if not hasattr(db, 'get_issue'):
        print("FAIL: db.get_issue method missing!")
        return

    # Test with a known ID from Kaitharan data
    # Inspect output showed: LIABILITY_3B_R1
    test_id = "LIABILITY_3B_R1"
    print(f"Fetching {test_id}...")
    
    issue = db.get_issue(test_id)
    if not issue:
        print("FAIL: Issue not found in DB (Result is None).")
        return
        
    print("Success! Issue retrieved.")
    print(f"ID: {issue.get('issue_id')}")
    print(f"Keys returned: {list(issue.keys())}")
    print(f"SOP Point from key: {issue.get('sop_point')} (Type: {type(issue.get('sop_point'))})")
    
    if issue.get('sop_point') == 1:
        print("VERIFIED: SOP Point is correct (1).")
    else:
        print(f"WARNING: SOP Point output mismatch: {issue.get('sop_point')}")

if __name__ == "__main__":
    simulate()
