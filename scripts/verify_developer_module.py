import sys
import os
import json
import sqlite3

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager
from src.ui.developer.logic_validator import LogicValidator

def test_db_operations():
    print("Testing DB Operations...")
    db = DatabaseManager()
    db.init_sqlite()
    
    # 1. Create Issue
    issue_data = {
        "issue_id": "TEST_001",
        "issue_name": "Test Issue",
        "category": "Test",
        "severity": "Low",
        "version": "1.0",
        "tags": ["test"],
        "templates": {"brief_facts": "Fact {{val}}"},
        "tables": [],
        "placeholders": [{"name": "val", "type": "number"}],
        "calc_logic": "def compute(v): return {'res': v.get('val', 0) * 2}",
        "active": True
    }
    
    success, msg = db.save_issue(issue_data)
    if success:
        print("[PASS] Save Issue: Success")
    else:
        print(f"[FAIL] Save Issue: Failed - {msg}")
        return

    # 2. Publish
    if db.publish_issue("TEST_001", True):
        print("[PASS] Publish Issue: Success")
    else:
        print("[FAIL] Publish Issue: Failed")

    # 3. Fetch Active
    active_issues = db.get_active_issues()
    found = any(i['issue_id'] == "TEST_001" for i in active_issues)
    if found:
        print("[PASS] Fetch Active Issues: Success")
    else:
        print("[FAIL] Fetch Active Issues: Failed (Issue not found)")

    # 4. Get Single Issue
    issue = db.get_issue("TEST_001")
    if issue and issue['issue_name'] == "Test Issue":
        print("[PASS] Get Issue: Success")
    else:
        print("[FAIL] Get Issue: Failed")

def test_logic_validator():
    print("\nTesting Logic Validator...")
    
    code = """
def compute(v):
    val = float(v.get('input', 0))
    return {"output": val * 2}
"""
    inputs = {"input": 10}
    
    valid, res = LogicValidator.validate_logic(code, inputs)
    
    if valid and res.get('output') == 20:
        print("[PASS] Logic Validation: Success")
    else:
        print(f"[FAIL] Logic Validation: Failed - {res}")

if __name__ == "__main__":
    test_db_operations()
    test_logic_validator()
