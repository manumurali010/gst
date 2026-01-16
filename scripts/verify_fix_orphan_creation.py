
import sys
import os
import json
import uuid
import datetime

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..')
sys.path.append(src_path)

from src.database.db_manager import DatabaseManager
print(f"DEBUG: Using db_manager from {DatabaseManager.__module__}")
import inspect
print(f"DEBUG: File: {inspect.getfile(DatabaseManager)}")

def green(text): return f"\033[92m{text}\033[0m"
def red(text): return f"\033[91m{text}\033[0m"
def yellow(text): return f"\033[93m{text}\033[0m"

def verify_fix():
    print(yellow("--- Starting Verification: ASMT-10 Finalisation & Orphan Logic ---"))
    
    db = DatabaseManager()
    db.init_sqlite()  # Ensure DB initialized

    # 1. Create a Fresh Scrutiny Case
    gstin = "32AABCL1984A1Z0" # Test GSTIN
    
    data = {
        "gstin": gstin,
        "legal_name": "Test Legal Name",
        "trade_name": "Test Trade Name",
        "address": "Test Address",
        "financial_year": "2023-24",
        "form_type": "ASMT-10",
        "initiating_section": "61",
        "status": "Initiated",
        "created_by": "Test Script"
    }

    print(f"\n[1] Creating Scrutiny Case for {gstin}...")
    pid = db.create_proceeding(data)
    
    if not pid:
        print(red("FAILED: Could not create proceeding"))
        return

    # 2. Assert Initial State (Draft, None, None)
    proc = db.get_proceeding(pid)
    
    asmt_status = proc.get('asmt10_status')
    adj_id = proc.get('adjudication_case_id')
    
    print(f"   Created Proceeding ID: {pid}")
    print(f"   Initial ASMT-10 Status: {asmt_status}")
    print(f"   Initial Adjudication ID: {adj_id}")
    
    if asmt_status == 'Draft' and adj_id is None:
        print(green("PASS: Initial state is clean (Draft, No Adjudication Link)"))
    else:
        print(red(f"FAIL: Initial state dirty. Status={asmt_status}, AdjID={adj_id}"))

    # 3. Simulate Finalisation
    print(f"\n[2] Simulating ASMT-10 Finalisation...")
    
    oc_data = {
        'OC_Number': "TEST/001/2026",
        'OC_Date': datetime.date.today().isoformat(),
        'OC_Content': "Test OC",
        'OC_To': "Taxpayer"
    }
    asmt_data = {
        'gstin': gstin,
        'financial_year': "2023-24",
        'issue_date': datetime.date.today().isoformat(),
        'case_id': pid,
        'oc_number': oc_data['OC_Number']
        
    }
    adj_data = {
        'source_scrutiny_id': pid,
        'gstin': gstin,
        'legal_name': "Test Legal Name",
        'financial_year': "2023-24"
    }
    
    success, result_adj_id = db.finalize_proceeding_transaction(pid, oc_data, asmt_data, adj_data)
    
    if success:
        print(green(f"   Finalised Successfully. Linked Adjudication ID: {result_adj_id}"))
    else:
        print(red(f"   Finalisation Failed: {result_adj_id}"))
        return

    # Verify updated state
    proc_final = db.get_proceeding(pid)
    print(f"   Final ASMT-10 Status: {proc_final.get('asmt10_status')}")
    print(f"   Final Adjudication ID: {proc_final.get('adjudication_case_id')}")

    if proc_final.get('asmt10_status') == 'finalised' and proc_final.get('adjudication_case_id') == result_adj_id:
         print(green("PASS: Proceeding updated correctly"))
    else:
         print(red("FAIL: Proceeding update mismatch"))

    # 4. Delete the Case & Verify Cleanup (Orphan Check)
    print(f"\n[3] Deleting Scrutiny Case {pid}...")
    del_success = db.delete_proceeding(pid)
    
    if del_success:
        print(green("   Scrutiny Case Deleted"))
    else:
        print(red("FAIL: Could not delete case"))
        return
        
    # Check if Adjudication Case still exists
    conn = db._get_conn()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM adjudication_cases WHERE id = ?", (result_adj_id,))
    count_adj = c.fetchone()[0]
    conn.close()
    
    if count_adj == 0:
        print(green("PASS: Linked Adjudication Case was DELETED (No Orphans left)"))
    else:
        print(red("FAIL: Linked Adjudication Case STILL EXISTS (Orphan detected!)"))

    # 5. Create NEW Case for SAME GSTIN
    print(f"\n[4] Creating NEW Scrutiny Case for {gstin} (Clean Slate Check)...")
    pid_new = db.create_proceeding(data) # Same data
    
    proc_new = db.get_proceeding(pid_new)
    new_status = proc_new.get('asmt10_status')
    new_adj_id = proc_new.get('adjudication_case_id')
    
    print(f"   New Proceeding ID: {pid_new}")
    print(f"   New ASMT-10 Status: {new_status}")
    print(f"   New Adjudication ID: {new_adj_id}")
    
    if new_status == 'Draft' and new_adj_id is None:
        print(green("PASS: New case started cleanly (No ghost finalisation)"))
    else:
        print(red(f"FAIL: New case inherited bad state. Status={new_status}, AdjID={new_adj_id}"))
    
    # Clean up new case
    db.delete_proceeding(pid_new)
    print(yellow("\n--- Verification Complete ---"))

if __name__ == "__main__":
    verify_fix()
