import os
import sqlite3
import json
from src.database.db_manager import DatabaseManager
from src.utils.constants import WorkflowStage

def test_drc01a_flow():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'adjudication.db')
    db = DatabaseManager(db_path=db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- 1. INJECT DEMO OFFICER ---")
    cursor.execute("SELECT id FROM officers WHERE is_active=1 LIMIT 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute('''INSERT INTO officers (name, designation, jurisdiction, office_address, is_active)
                          VALUES ('John Doe', 'Superintendent', 'Test Range', 'Test Office', 1)''')
        conn.commit()
        officer_id = cursor.lastrowid
        print(f"Inserted demo officer ID: {officer_id}")
    else:
        officer_id = row[0]
        print(f"Using existing officer ID: {officer_id}")
        
    print("\n--- 2. CREATE TEST PROCEEDING ---")
    pid = db.create_proceeding({
        "gstin": "29BABCU9898K1ZT", 
        "legal_name": "TEST CO"
    }, source_type="SCRUTINY")
    if not pid:
        print("Failed to create proceeding.")
        return
    print(f"Created Scrutiny proceeding: {pid}")
    
    # Initialize basic data so update_proceeding recognizes the source type
    cursor.execute("UPDATE proceedings SET workflow_stage=? WHERE id=?", (WorkflowStage.DRC01A_DRAFT.value, pid))
    conn.commit()
    
    print("\n--- 3. TEST UPDATE (Pre-Finalization) ---")
    officer_data = db.get_officer_by_id(officer_id)
    snapshot = json.dumps(officer_data)
    
    success = db.update_proceeding(pid, {
        "issuing_officer_id": officer_id,
        "issuing_officer_snapshot": snapshot,
        "status": "DRC-01A Draft"
    })
    print(f"Draft Update Success: {success is not False}")
    
    print("\n--- 4. MOCK FINALIZATION ---")
    cursor.execute("UPDATE proceedings SET workflow_stage=?, status='DRC-01A Issued' WHERE id=?", (WorkflowStage.DRC01A_ISSUED.value, pid))
    conn.commit()
    print("Workflow stage updated to DRC01A_ISSUED.")
    
    print("\n--- 5. TEST BACKEND LOCK ---")
    try:
        db.update_proceeding(pid, {"financial_year": "2024-25"})
        print("FAIL: Backend lock did not prevent update!")
    except RuntimeError as e:
        print(f"PASS: Backend lock successfully prevented update. Error: {e}")
        
    print("\n--- 6. VERIFY SCHEMA DUMP ---")
    cursor.execute("PRAGMA table_info(officers)")
    print("Officers Table Columns:")
    for col in cursor.fetchall():
        print(col)
        
    cursor.execute("PRAGMA table_info(proceedings)")
    print("\nProceedings Table Last 5 Columns:")
    for col in cursor.fetchall()[-5:]:
        print(col)
        
    conn.close()

if __name__ == "__main__":
    test_drc01a_flow()
