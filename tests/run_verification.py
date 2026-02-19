
import sys
import os
import functools

# Force flush for all prints to debug hangs
print = functools.partial(print, flush=True)

print("DEBUG: Starting run_verification.py")

# 1. Setup Path (Proven method from diagnostics)
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.append(cwd)
print(f"DEBUG: Path set to {cwd}")

# 2. Imports
import json
import uuid
import sqlite3
print("DEBUG: Standard libs imported")

# [Fix] Pre-import heavy libs to prevent loader locks
try:
    import pandas as pd
    print("DEBUG: Pandas pre-imported")
    from src.utils.constants import TAXPAYERS_FILE
    print("DEBUG: Constants pre-imported")
except ImportError as e:
    print(f"WARNING: Pre-import failed: {e}")

try:
    from src.database.db_manager import DatabaseManager
    print("DEBUG: DatabaseManager imported successfully")
except ImportError as e:
    print(f"ERROR: Could not import DatabaseManager: {e}")
    sys.exit(1)

# 3. Verification Logic
def run_tests():
    print("=== Starting Direct Adjudication Verification ===")
    
    print("DEBUG: Instantiating DatabaseManager...")
    db = DatabaseManager()
    print("DEBUG: Calling init_sqlite()...")
    db.init_sqlite()
    print("DEBUG: SQLite Initialized.")
    
    # ---------------------------------------------------------
    # TEST 1: Scrutiny Creation (Legacy Regression)
    # ---------------------------------------------------------
    print("\n[TEST 1] Creating Scrutiny Case (Legacy Flow)...")
    try:
        scrutiny_data = {
            "gstin": "29ABCDE1234F1Z5",
            "financial_year": "2017-18",
            "initiating_section": "61",
            "legal_name": "Test Trader Scrutiny",
            "status": "Draft"
        }
        pid_scrutiny = db.create_proceeding(scrutiny_data, source_type='SCRUTINY')
        
        if not pid_scrutiny:
            print("❌ FAILED: Could not create Scrutiny case.")
            return False
        
        print(f"✅ Created Scrutiny Case: {pid_scrutiny}")
        
        # Verify Registry
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT source_type FROM case_registry WHERE id=?", (pid_scrutiny,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == 'SCRUTINY':
            print("✅ Registry correctly identifies SCRUTINY.")
        else:
            print(f"❌ Registry Mismatch: {row}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 1 EXCEPTION: {e}")
        return False

    # ---------------------------------------------------------
    # TEST 2: Direct Adjudication Creation (New Flow)
    # ---------------------------------------------------------
    print("\n[TEST 2] Creating Direct Adjudication Case...")
    try:
        adj_data = {
            "gstin": "29ABCDE1234F1Z5",
            "financial_year": "2018-19",
            "section": "74", # Adjudication Section
            "legal_name": "Test Trader Adj",
            "status": "Pending"
        }
        pid_adj = db.create_proceeding(adj_data, source_type='ADJUDICATION')
        
        if not pid_adj:
            print("❌ FAILED: Could not create Adjudication case.")
            return False
            
        print(f"✅ Created Adjudication Case: {pid_adj}")
        
        # Verify Registry
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT source_type FROM case_registry WHERE id=?", (pid_adj,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == 'ADJUDICATION':
            print("✅ Registry correctly identifies ADJUDICATION.")
        else:
            print(f"❌ Registry Mismatch: {row}")
            return False
            
    except Exception as e:
        print(f"❌ TEST 2 EXCEPTION: {e}")
        return False

    # ---------------------------------------------------------
    # TEST 3: Retrieval & Branching Logic
    # ---------------------------------------------------------
    print("\n[TEST 3] Verifying Source Type Resolution...")
    try:
        # Get Scrutiny
        case_s = db.get_proceeding(pid_scrutiny)
        if case_s and case_s.get('source_type') == 'SCRUTINY':
             print("✅ get_proceeding(Scrutiny) returns correct source_type.")
        else:
             print(f"❌ get_proceeding(Scrutiny) Failed: {case_s.get('source_type') if case_s else 'None'}")
             return False

        # Get Adjudication
        case_a = db.get_proceeding(pid_adj)
        if case_a and case_a.get('source_type') == 'ADJUDICATION':
             print("✅ get_proceeding(Adjudication) returns correct source_type.")
             if case_a.get('is_adjudication'):
                 print("✅ is_adjudication flag is Set.")
             else:
                 print("❌ is_adjudication flag Missing.")
                 return False
        else:
             print(f"❌ get_proceeding(Adjudication) Failed: {case_a.get('source_type') if case_a else 'None'}")
             return False
             
    except Exception as e:
        print(f"❌ TEST 3 EXCEPTION: {e}")
        return False

    # ---------------------------------------------------------
    # TEST 4: Draft Engine Logic (Simulated)
    # ---------------------------------------------------------
    print("\n[TEST 4] Simulating Draft Typing Logic...")
    
    def simulate_hydration(case_data):
        details = case_data.get('additional_details', {})
        source_type = case_data.get('source_type', 'SCRUTINY').lower()
        
        # Simulate logic from hydrated_scn_grounds_data
        grounds = details.get('scn_grounds')
        if not grounds:
            print(f"   -> [Sim] Hydrating new grounds for {source_type}...")
            grounds = {
                "type": source_type, 
                "data": {
                    "asmt10_ref": {"exists": True} if source_type == 'scrutiny' else {} 
                }
            }
        return grounds

    grounds_s = simulate_hydration(case_s)
    if grounds_s['type'] == 'scrutiny' and grounds_s['data']['asmt10_ref']:
        print("✅ Scrutiny Draft Type: Correct (Has ASMT-10 Ref)")
    else:
        print(f"❌ Scrutiny Draft Fail: {grounds_s}")
        return False

    grounds_a = simulate_hydration(case_a)
    if grounds_a['type'] == 'adjudication' and not grounds_a['data'].get('asmt10_ref'):
        print("✅ Adjudication Draft Type: Correct (No ASMT-10 Ref)")
    else:
        print(f"❌ Adjudication Draft Fail: {grounds_a}")
        return False

    print("\n=== All Tests Passed Successfully ===")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
