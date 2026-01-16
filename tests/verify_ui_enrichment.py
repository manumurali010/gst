import sqlite3
import json

db_path = 'C:/Users/manum/.gemini/antigravity/scratch/gst/data/adjudication.db'

def verify_sop5_master_data():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT grid_data FROM issues_master WHERE issue_id = 'TDS_TCS_MISMATCH'")
    row = c.fetchone()
    conn.close()
    
    if not row:
        print("FAIL: SOP-5 not found in issues_master")
        return False
        
    grid_data = json.loads(row[0])
    if grid_data != []:
        print(f"FAIL: SOP-5 grid_data is not empty! Found: {grid_data}")
        return False
    
    print("PASS: SOP-5 grid_data is empty in DB.")
    return True

def simulate_enrichment(issue):
    """
    Simulates the corrected logic from ScrutinyTab.enrich_issues_with_templates
    """
    # Mock DB Fetch
    if issue['issue_id'] == 'TDS_TCS_MISMATCH':
        # Even if DB returned junk (simulating race condition or old DB), the Code Guard should protect it.
        # Let's pretend DB *still* had RCM data to test the Code Guard.
        master_json = {
            "grid_data": [{"fake": "RCM_DATA"}] 
        }
    else:
        master_json = {}
        
    # LOGIC UNDER TEST
    if "summary_table" in issue or "tables" in issue:
        print(f"DEBUG: Skipping legacy grid injection for {issue['issue_id']} because summary_table/tables is present.")
    else:
        # Legacy Path (Bad)
        issue['grid_data'] = master_json.get('grid_data')
        print("DEBUG: Legacy Path Taken (Overwrite happened)")

    return issue

def verify_logic_guard():
    print("\n--- Verifying Code Guard ---")
    
    # Case 1: Issue with 'tables' (SOP-5 Phase 2)
    issue_good = {
        "issue_id": "TDS_TCS_MISMATCH",
        "description": "SOP-5",
        "tables": [{"title": "TDS", "rows": []}]
    }
    
    print("Testing Issue with 'tables'...")
    simulate_enrichment(issue_good)
    
    if "grid_data" in issue_good:
        print("FAIL: 'grid_data' was injected/overwritten despite 'tables' presence.")
    else:
        print("PASS: 'grid_data' was NOT injected. Guard works.")

    # Case 2: Issue without 'tables' (Legacy Fallback scenario)
    issue_bad = {
        "issue_id": "TDS_TCS_MISMATCH",
        "description": "SOP-5 Legacy"
    }
    print("\nTesting Issue WITHOUT 'tables'...")
    simulate_enrichment(issue_bad)
    
    if "grid_data" in issue_bad and issue_bad['grid_data'] is not None:
         print("PASS: 'grid_data' WAS injected (Legacy Fallback behavior correct).")
    else:
         print("FAIL: 'grid_data' NOT injected for legacy case.")

if __name__ == "__main__":
    db_ok = verify_sop5_master_data()
    if db_ok:
        verify_logic_guard()
    else:
        print("Skipping logic test due to DB failure.")
