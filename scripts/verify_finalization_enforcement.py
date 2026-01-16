import sys
import os
import json
import uuid
import sqlite3

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db_manager import DatabaseManager

def test_strict_listing():
    print("\n--- Test 1: Strict Adjudication Listing ---")
    db = DatabaseManager()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    # 1. Create Mock Scrutiny Cases
    scrutiny_finalised_id = str(uuid.uuid4())
    scrutiny_draft_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO proceedings (id, case_id, gstin, legal_name, financial_year, initiating_section, status, asmt10_status)
        VALUES (?, 'CASE/SCR/001', 'GSTIN001', 'Valid Scrutiny', '2024-25', '61', 'Closed', 'Finalised')
    """, (scrutiny_finalised_id,))
    
    cursor.execute("""
        INSERT INTO proceedings (id, case_id, gstin, legal_name, financial_year, initiating_section, status, asmt10_status)
        VALUES (?, 'CASE/SCR/002', 'GSTIN002', 'Draft Scrutiny', '2024-25', '61', 'In Progress', 'Draft')
    """, (scrutiny_draft_id,))
    
    # 2. Create Adjudication Cases
    # Case A: Valid (Linked to Finalised Scrutiny)
    adj_valid_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO adjudication_cases (id, source_scrutiny_id) VALUES (?, ?)", (adj_valid_id, scrutiny_finalised_id))
    
    # Case B: Orphan/Invalid (Linked to Draft Scrutiny)
    adj_invalid_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO adjudication_cases (id, source_scrutiny_id) VALUES (?, ?)", (adj_invalid_id, scrutiny_draft_id))
    
    # Case C: Direct Adjudication (No Link)
    adj_direct_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO adjudication_cases (id, source_scrutiny_id) VALUES (?, NULL)", (adj_direct_id,))
    
    conn.commit()
    conn.close()
    
    # 3. Fetch Valid Cases
    results = db.get_valid_adjudication_cases()
    result_ids = [r['id'] for r in results]
    
    print(f"Found {len(results)} valid cases.")
    
    if adj_valid_id in result_ids:
        print("PASS: Valid Scrutiny-Origin Case included.")
    else:
        print("FAIL: Valid Scrutiny-Origin Case missing!")
        
    if adj_direct_id in result_ids:
        print("PASS: Direct Adjudication Case included.")
    else:
        print("FAIL: Direct Adjudication Case missing!")
        
    if adj_invalid_id not in result_ids:
        print("PASS: Draft Scrutiny-Origin Case excluded (Ghost prevention).")
    else:
        print("FAIL: Draft Scrutiny-Origin Case included (Ghost leak)!")

def test_scn_flag_persistence():
    print("\n--- Test 2: SCN Flag Persistence ---")
    db = DatabaseManager()
    
    # 1. Setup Mock Proceeding
    pid = str(uuid.uuid4())
    db.create_proceeding({
        'gstin': 'GSTIN_FLAG_TEST',
        'legal_name': 'Flag Test',
        'financial_year': '2024-25',
        'selected_issues': [{'issue': 'Test Issue', 'category': 'Tax'}]
    })
    
    # Manually update ID to match our PID for easier tracking (create_proceeding generates random ID)
    # Actually create_proceeding returns 'CASE/...' ID string, not PID. 
    # Let's just manually insert a proceeding to control the ID.
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proceedings WHERE gstin = 'GSTIN_FLAG_TEST'") # Cleanup
    cursor.execute("""
        INSERT INTO proceedings (id, case_id, gstin, legal_name, financial_year, selected_issues, additional_details)
        VALUES (?, 'CASE/TEST/FLAG', 'GSTIN_FLAG_TEST', 'Flag Test', '2024-25', ?, '{}')
    """, (pid, json.dumps([{'description': 'Test', 'category': 'Tax'}])))
    conn.commit()
    conn.close()
    
    # 2. Simulate init_scn_from_asmt10 logic (Copy-paste logic from UI since we can't instantiate UI easily)
    # But wait, we can reuse the logic we just verified in the UI by importing the class? 
    # Or just replicate the DB persistence part which is what we care about here.
    
    # Simulate step: Save issues and update flag
    print("Simulating SCN Init...")
    issues_list = [{'issue_id': 'GENERIC', 'data': {'issue': 'test'}}]
    db.save_case_issues(pid, issues_list, stage='SCN')
    
    # Update Flag (Logic from init_scn_from_asmt10)
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT additional_details FROM proceedings WHERE id = ?", (pid,))
    row = cursor.fetchone()
    curr_details = json.loads(row[0]) if row and row[0] else {}
    curr_details['scn_initialized_from_asmt10'] = True
    cursor.execute("UPDATE proceedings SET additional_details = ? WHERE id = ?", (json.dumps(curr_details), pid))
    conn.commit()
    conn.close()
    
    # 3. Verify Flag Persistence
    proc = db.get_proceeding(pid)
    details = proc.get('additional_details', {})
    if isinstance(details, str): details = json.loads(details)
    
    if details.get('scn_initialized_from_asmt10') is True:
        print("PASS: Flag 'scn_initialized_from_asmt10' persisted as True.")
    else:
        print(f"FAIL: Flag not found or False. Details: {details}")

if __name__ == "__main__":
    try:
        test_strict_listing()
        test_scn_flag_persistence()
        print("\nAll Tests Completed.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
