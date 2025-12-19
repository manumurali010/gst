
import sys
import os
import json
import sqlite3

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.database.db_manager import DatabaseManager
from src.database.schema import init_db

def test_isolation():
    print("Initializing DB...")
    db = DatabaseManager()
    db.init_sqlite()
    
    # Create a dummy proceeding
    proceeding_id = "TEST_CASE_ISOLATION_001"
    
    # Clean up previous test
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proceedings WHERE id = ?", (proceeding_id,))
    cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ?", (proceeding_id,))
    conn.commit()
    conn.close()
    
    print(f"Created/Cleaned proceeding: {proceeding_id}")
    
    # 1. Save DRC-01A Issues
    drc_issues = [
        {'issue_id': 'ISSUE_1', 'data': {'amount': 100}}
    ]
    print("Saving DRC-01A issues...")
    db.save_case_issues(proceeding_id, drc_issues, stage='DRC-01A')
    
    # Verify DB content
    issues_drc = db.get_case_issues(proceeding_id, stage='DRC-01A')
    print(f"DRC-01A Issues in DB: {len(issues_drc)}")
    assert len(issues_drc) == 1
    assert issues_drc[0]['issue_id'] == 'ISSUE_1'
    
    # Verify SCN issues don't exist yet
    issues_scn_pre = db.get_case_issues(proceeding_id, stage='SCN')
    print(f"SCN Issues in DB (Pre-Clone): {len(issues_scn_pre)}")
    assert len(issues_scn_pre) == 0
    
    # 2. Simulate SCN Open (Clone)
    print("Cloning issues for SCN...")
    success = db.clone_issues_for_scn(proceeding_id)
    assert success == True
    
    # Verify SCN content
    issues_scn = db.get_case_issues(proceeding_id, stage='SCN')
    print(f"SCN Issues in DB (Post-Clone): {len(issues_scn)}")
    assert len(issues_scn) == 1
    assert issues_scn[0]['issue_id'] == 'ISSUE_1'
    
    # 3. Modify SCN Issues (Add new one)
    scn_issues_new = [
        {'issue_id': 'ISSUE_1', 'data': {'amount': 100}},
        {'issue_id': 'ISSUE_2', 'data': {'amount': 500}}
    ]
    print("Saving modified SCN issues...")
    db.save_case_issues(proceeding_id, scn_issues_new, stage='SCN')
    
    # 4. Final Verification
    # Check DRC-01A (Should still be 1)
    final_drc = db.get_case_issues(proceeding_id, stage='DRC-01A')
    print(f"Final DRC-01A Issues: {len(final_drc)}")
    assert len(final_drc) == 1
    assert final_drc[0]['issue_id'] == 'ISSUE_1'
    
    # Check SCN (Should be 2)
    final_scn = db.get_case_issues(proceeding_id, stage='SCN')
    print(f"Final SCN Issues: {len(final_scn)}")
    assert len(final_scn) == 2
    
    print("\nSUCCESS: Data isolation verified!")

if __name__ == "__main__":
    test_isolation()
