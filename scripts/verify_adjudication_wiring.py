import sys
import os
import uuid
import datetime

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

def verify_wiring():
    print("--- Verifying Adjudication Wiring Logic ---")
    db = DatabaseManager()
    
    # 1. Create Mock Scrutiny Case
    print("[Step 1] Creating Mock Scrutiny Case...")
    case_create_data = {
        'gstin': "99AAAAA0000A1Z5",
        'financial_year': "2023-24",
        'legal_name': "Test Trader"
    }
    pid = db.create_proceeding(case_create_data)
    print(f"Created Scrutiny Case: {pid}")
    
    # 2. Finalize it to get Adjudication ID
    print("[Step 2] Finalizing Case...")
    oc_data = {
        'OC_Number': f"TEST/OC/{uuid.uuid4().hex[:4]}",
        'OC_Content': "Test Content",
        'OC_Date': datetime.date.today().strftime("%Y-%m-%d"),
        'OC_To': "Test User"
    }
    asmt_data = {
        'gstin': "99AAAAA0000A1Z5",
        'financial_year': "2023-24",
        'issue_date': datetime.date.today().strftime("%Y-%m-%d"),
        'case_id': "CASE/TEST/001",
        'oc_number': oc_data['OC_Number']
    }
    adj_data = {
        'source_scrutiny_id': pid,
        'gstin': "99AAAAA0000A1Z5", 
        'legal_name': "Test Trader",
        'financial_year': "2023-24"
    }
    
    success, adj_id = db.finalize_proceeding_transaction(pid, oc_data, asmt_data, adj_data)
    if not success:
        print(f"[ERROR] Finalization failed: {adj_id}")
        return
        
    print(f"[SUCCESS] Finalized. Adjudication ID: {adj_id}")
    
    # 3. Test retrieval via get_proceeding using Adj ID
    print("[Step 3] Testing get_proceeding(adj_id)...")
    data = db.get_proceeding(adj_id)
    
    if not data:
        print("[ERROR] get_proceeding returned None for Adj ID!")
        sys.exit(1)
        
    print(f"[INFO] Retrieved Data ID: {data.get('id')}")
    print(f"[INFO] Retrieved Scrutiny ID: {data.get('scrutiny_id')}")
    print(f"[INFO] Is Adjudication Flag: {data.get('is_adjudication')}")
    
    if data.get('id') == adj_id and data.get('scrutiny_id') == pid and data.get('is_adjudication'):
        print("[SUCCESS] Wiring Logic Verified: Adjudication ID correctly loads merged data.")
    else:
        print("[ERROR] Data mismatch.")
        print(data)
        sys.exit(1)

if __name__ == "__main__":
    verify_wiring()
