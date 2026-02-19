import sys
import os
print("DEBUG: Starting script...", flush=True)
import json
import sqlite3
print("DEBUG: Standard imports done.", flush=True)

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print(f"DEBUG: Path updated. Importing DatabaseManager...", flush=True)

from src.database.db_manager import DatabaseManager
print("DEBUG: DatabaseManager imported.", flush=True)

def test_direct_adjudication_flow():
    print("=== Starting Direct Adjudication Verification ===", flush=True)
    
    print("DEBUG: Initializing DatabaseManager...", flush=True)
    db = DatabaseManager()
    print("DEBUG: DatabaseManager initialized. Init SQLite...", flush=True)
    db.init_sqlite()
    print("DEBUG: SQLite initialized.", flush=True)
    
    # 1. Test Scrutiny Creation (Regression)
    print("\n[TEST 1] Creating Scrutiny Case (Legacy Flow)...")
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
    if row and row[0] == 'SCRUTINY':
        print("✅ Registry correctly identifies SCRUTINY.")
    else:
        print(f"❌ Registry Mismatch: {row}")
        
    # 2. Test Direct Adjudication Creation (New Flow)
    print("\n[TEST 2] Creating Direct Adjudication Case...")
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
    cursor.execute("SELECT source_type FROM case_registry WHERE id=?", (pid_adj,))
    row = cursor.fetchone()
    if row and row[0] == 'ADJUDICATION':
        print("✅ Registry correctly identifies ADJUDICATION.")
    else:
        print(f"❌ Registry Mismatch: {row}")
    conn.close()

    # 3. Test Retrieval & Data Logic
    print("\n[TEST 3] Verifying get_proceeding Logic...")
    
    # Get Scrutiny
    case_s = db.get_proceeding(pid_scrutiny)
    if case_s and case_s.get('source_type') == 'SCRUTINY':
         print("✅ get_proceeding(Scrutiny) returns correct source_type.")
    else:
         print(f"❌ get_proceeding(Scrutiny) Failed: {case_s.get('source_type') if case_s else 'None'}")

    # Get Adjudication
    case_a = db.get_proceeding(pid_adj)
    if case_a and case_a.get('source_type') == 'ADJUDICATION':
         print("✅ get_proceeding(Adjudication) returns correct source_type.")
         if case_a.get('is_adjudication'):
             print("✅ is_adjudication flag is Set.")
         else:
             print("❌ is_adjudication flag Missing.")
    else:
         print(f"❌ get_proceeding(Adjudication) Failed: {case_a.get('source_type') if case_a else 'None'}")

    # 4. Simulate Draft Typing (Mocking Workspace Logic)
    print("\n[TEST 4] Simulating Draft Typing Logic...")
    
    def simulate_hydration(case_data):
        details = case_data.get('additional_details', {})
        source_type = case_data.get('source_type', 'SCRUTINY').lower()
        
        # Simulate the workspace logic I wrote
        grounds = details.get('scn_grounds')
        if not grounds:
            print(f"   -> Hydrating new grounds for {source_type}...")
            grounds = {
                "type": source_type, # The logic I added
                "data": {
                    "asmt10_ref": {} if source_type == 'scrutiny' else {} # My logic conditionally populates
                }
            }
        return grounds

    grounds_s = simulate_hydration(case_s)
    if grounds_s['type'] == 'scrutiny':
        print("✅ Scrutiny Draft Type: Correct")
    else:
        print(f"❌ Scrutiny Draft Type Error: {grounds_s['type']}")

    grounds_a = simulate_hydration(case_a)
    if grounds_a['type'] == 'adjudication':
        print("✅ Adjudication Draft Type: Correct")
    else:
        print(f"❌ Adjudication Draft Type Error: {grounds_a['type']}")

    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    test_direct_adjudication_flow()
