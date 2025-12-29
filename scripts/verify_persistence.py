import sys
import os
import sqlite3
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db_manager import DatabaseManager

def test_persistence():
    db = DatabaseManager()
    
    # 1. Create a dummy proceeding
    data = {
        "gstin": "24ABCDE1234F1Z5",
        "legal_name": "Test Taxpayer",
        "financial_year": "2023-24",
        "status": "Initiated",
        "additional_details": {"existing_key": "existing_val"}
    }
    pid = db.create_proceeding(data)
    print(f"Created proceeding with ID: {pid}")
    
    # 2. Simulate saving findings with file paths
    file_paths = {
        "tax_liability": "C:/data/tax_liab.xlsx",
        "gstr_2b": "C:/data/gstr2b.xlsx"
    }
    updates = {
        "selected_issues": [{"id": "1", "desc": "Mismatch"}],
        "oc_number": "123/2025",
        "notice_date": "2025-01-01",
        "last_date_to_reply": "2025-02-01",
        "additional_details": {
            "file_paths": file_paths
        }
    }
    
    success = db.update_proceeding(pid, updates)
    print(f"Update status: {success}")
    
    # 3. Retrieve and verify
    proc = db.get_proceeding(pid)
    print("Retrieved proceeding data:")
    print(json.dumps(proc, indent=2))
    
    saved_paths = proc.get('additional_details', {}).get('file_paths', {})
    if saved_paths == file_paths:
        print("\nSUCCESS: File paths persisted correctly!")
    else:
        print("\nFAILURE: File paths not persisted correctly.")
        print(f"Expected: {file_paths}")
        print(f"Actual: {saved_paths}")

    # Cleanup
    db.delete_proceeding(pid)

if __name__ == "__main__":
    test_persistence()
