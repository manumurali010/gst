import os
import sqlite3
import json
from src.database.db_manager import DatabaseManager
from src.utils.constants import WorkflowStage
from src.ui.proceedings_workspace import ProceedingsWorkspace
from PyQt6.QtWidgets import QApplication
import sys

def test_scn_flow():
    # Setup PyQt for testing UI logic
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'adjudication.db')
    db = DatabaseManager(db_path=db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- 1. INJECT DEMO OFFICER ---")
    cursor.execute("SELECT id FROM officers WHERE is_active=1 LIMIT 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute('''INSERT INTO officers (name, designation, jurisdiction, office_address, is_active)
                          VALUES ('Jane Smith', 'Assistant Commissioner', 'Division A', 'HQ', 1)''')
        conn.commit()
        officer_id = cursor.lastrowid
        print(f"Inserted demo officer ID: {officer_id}")
    else:
        officer_id = row[0]
        print(f"Using existing officer ID: {officer_id}")
        
    print("\n--- 2. CREATE TEST PROCEEDING ---")
    pid = db.create_proceeding({
        "gstin": "29BABCU9898K1ZT", 
        "legal_name": "TEST CO SCN"
    }, source_type="SCRUTINY")
    if not pid:
        print("Failed to create proceeding.")
        return
    print(f"Created Scrutiny proceeding: {pid}")
    
    cursor.execute("UPDATE proceedings SET workflow_stage=?, initiating_section='73(1)' WHERE id=?", (WorkflowStage.SCN_DRAFT.value, pid))
    conn.commit()
    
    print("\n--- 3. INITIALIZE WORKSPACE & TRIGGER SCN SAVE ---")
    workspace = ProceedingsWorkspace(navigate_callback=lambda x, y=None: None)
    workspace.load_proceeding(pid)
    
    print("Calling save_scn_metadata...")
    # Force reload case from DB so that proceeding_data has proper base details
    workspace.load_proceeding(pid)
    
    # Simulate UI inputs for SCN Step 1 AFTER reload
    workspace.scn_no_input.setText("SCN/2026/002")
    workspace.scn_oc_input.setText("111/2026")
    
    # The combo index is 1 because 0 is "Select Officer..." and we added a single officer
    workspace.scn_officer_combo.setCurrentIndex(1)
    workspace.save_scn_metadata()
    # Verify the snapshot and ID were stored in the database
    cursor.execute("SELECT issuing_officer_id, issuing_officer_snapshot FROM proceedings WHERE id=?", (pid,))
    db_row = cursor.fetchone()
    print(f"After Save -> DB Officer ID: {db_row[0]}")
    try:
         snap = json.loads(db_row[1])
         officer_name = snap.get('SCN', {}).get('name') if 'SCN' in snap else snap.get('name')
         print(f"After Save -> DB Officer Name in Snapshot: {officer_name}")
         # Manually inject into workspace.proceeding_data to simulate UI reload for the render step
         workspace.proceeding_data['issuing_officer_id'] = db_row[0]
         workspace.proceeding_data['issuing_officer_snapshot'] = db_row[1]
    except:
         print("After Save -> Snapshot parsing failed or is None.")
         
    print("\n--- 4. MOCK SCN ISSUE INJECTION ---")
    # Need to give it an issue to bypass validation if requested, or just mock the render directly
    model = workspace._get_scn_model()
    print("Generated Model Keys:", list(model.keys()))
    print("Model extracted Officer Name:", model.get('officer_name'))
    
    print("\n--- 5. TEMPLATE ENGINE RENDERING ---")
    html = workspace.render_scn(is_preview=True)
    if model.get('officer_name') in html:
         print(f"PASS: Officer name '{model.get('officer_name')}' found in generated HTML.")
    else:
         print("FAIL: Officer name NOT found in HTML output.")
         
    if len(html) > 1000:
         print("PASS: HTML appears fully formed.")

    print("\n--- 6. MOCK FINALIZATION & TEST LOCK ---")
    cursor.execute("UPDATE proceedings SET workflow_stage=?, status='SCN Issued' WHERE id=?", (WorkflowStage.SCN_ISSUED.value, pid))
    conn.commit()
    
    try:
        db.update_proceeding(pid, {"financial_year": "2024-25"})
        print("FAIL: Backend lock did not prevent update!")
    except RuntimeError as e:
        print(f"PASS: Backend lock successfully prevented update. Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    test_scn_flow()
