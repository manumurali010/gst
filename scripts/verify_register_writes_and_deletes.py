
import sys
import os
import sqlite3
import datetime
import uuid

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db_manager import DatabaseManager

def verify_registers():
    print("Initializing DB Manager...")
    db = DatabaseManager()
    db.init_sqlite()
    
    # 1. Setup Data
    gstin = "TEST_GSTIN_999"
    fy = "2024-25"
    created_id = db.create_proceeding({
        "gstin": gstin,
        "financial_year": fy,
        "legal_name": "Register Test Corp",
        "status": "Initiated"
    })
    print(f"Created Proceeding: {created_id}")
    
    oc_num = "1/2026" # Legit format
    issue_date = datetime.date.today().isoformat()
    
    oc_data = {
        'OC_Number': oc_num,
        'OC_Date': issue_date,
        'OC_Content': "Finalization Test OC",
        'OC_To': "Register Test Corp"
    }
    
    asmt_data = {
        'gstin': gstin,
        'financial_year': fy,
        'issue_date': issue_date,
        'case_id': created_id,
        'oc_number': oc_num
    }
    
    adj_data = {
        'source_scrutiny_id': created_id,
        'gstin': gstin,
        'legal_name': "Register Test Corp",
        'financial_year': fy
    }
    
    # 2. Test Finalization (Legit Write)
    print("\ntesting finalize_proceeding_transaction with '1/2026'...")
    success, adj_id = db.finalize_proceeding_transaction(created_id, oc_data, asmt_data, adj_data)
    
    if not success:
        print(f"FAIL: Finalization failed: {adj_id}")
        return False
    print(f"Finalization Success. Adj ID: {adj_id}")
    
    # 3. Verify Writes
    conn = db._get_conn()
    cursor = conn.cursor()
    
    # Check OC Register
    cursor.execute("SELECT id, oc_number FROM oc_register WHERE case_id = ?", (created_id,))
    oc_entry = cursor.fetchone()
    if oc_entry and oc_entry[1] == oc_num:
        print(f"PASS: OC Register Write Confirmed. ID: {oc_entry[0]}, OC: {oc_entry[1]}")
    else:
        print(f"FAIL: OC Register missing or incorrect. Found: {oc_entry}")
        return False

    # Check ASMT-10 Register
    cursor.execute("SELECT id, oc_number FROM asmt10_register WHERE case_id = ?", (created_id,))
    asmt_entry = cursor.fetchone()
    if asmt_entry and asmt_entry[1] == oc_num:
        print(f"PASS: ASMT-10 Register Write Confirmed. ID: {asmt_entry[0]}, OC: {asmt_entry[1]}")
    else:
        print(f"FAIL: ASMT-10 Register missing or incorrect. Found: {asmt_entry}")
        return False
        
    conn.close()
    
    # 4. Test Deletion (Issue 2)
    print("\nTesting Deletion Logic...")
    
    # Delete OC Entry
    print(f"Deleting OC Entry ID: {oc_entry[0]}")
    del_success = db.delete_oc_entry(oc_entry[0])
    if not del_success:
        print("FAIL: delete_oc_entry returned False")
        return False
        
    # Verify Gone
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM oc_register WHERE id = ?", (oc_entry[0],))
    gone = cursor.fetchone()
    conn.close()
    
    if gone is None:
        print("PASS: OC Entry permanently deleted from DB.")
    else:
        print("FAIL: OC Entry still exists in DB!")
        return False

    # Delete ASMT-10 Entry
    print(f"Deleting ASMT-10 Entry ID: {asmt_entry[0]}")
    del_success_2 = db.delete_asmt10_entry(asmt_entry[0])
    
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM asmt10_register WHERE id = ?", (asmt_entry[0],))
    gone_2 = cursor.fetchone()
    conn.close()
    
    if gone_2 is None:
        print("PASS: ASMT-10 Entry permanently deleted from DB.")
    else:
        print("FAIL: ASMT-10 Entry still exists!")
        return False

    # 5. Negative Test (Delete non-existent)
    print("\nTesting Delete Non-Existent Entry...")
    fake_id = 999999
    # This should return False now and print a warning
    fail_res = db.delete_oc_entry(fake_id)
    if not fail_res:
         print(f"PASS: Correctly failed to delete non-existent ID {fake_id}")
    else:
         print(f"FAIL: delete_oc_entry returned True for non-existent ID {fake_id}!")
         return False

    print("\nALL TESTS PASSED.")
    return True

if __name__ == "__main__":
    verify_registers()
