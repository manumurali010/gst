
import sys
import os
import json
import sqlite3

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.database.db_manager import DatabaseManager

def repair_snapshots():
    print("--- STARTING SNAPSHOT REPAIR ---")
    db = DatabaseManager()
    
    conn = db._get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Schema Fix: The column is likely 'id' not 'proceeding_id'
    try:
        # Fetch selected_issues (Scrutiny Data) directly from proceedings
        cursor.execute("SELECT id as proceeding_id, legal_name, financial_year, selected_issues FROM proceedings")
    except sqlite3.OperationalError:
        # Fallback
        print("Schema Warning: Could not select columns explicitly. Using SELECT *")
        cursor.execute("SELECT * FROM proceedings")
        
    proceedings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    print(f"Found {len(proceedings)} proceedings.")
    
    fixed_count = 0
    
    for proc in proceedings:
        pid = proc.get('proceeding_id') or proc.get('id')
        name = proc.get('legal_name', 'Unknown')
        
        # 2. Fetch Source (SCRUTINY) from 'selected_issues' column
        raw_scrutiny = proc.get('selected_issues')
        scrutiny_issues = []
        if raw_scrutiny:
            if isinstance(raw_scrutiny, str):
                try: scrutiny_issues = json.loads(raw_scrutiny)
                except: scrutiny_issues = []
            elif isinstance(raw_scrutiny, list):
                scrutiny_issues = raw_scrutiny
                
        # 3. Fetch Target (DRC-01A) from case_issues table
        drc_issues = db.get_case_issues(pid, stage='DRC-01A')
        
        if not drc_issues:
            # Nothing to repair if no snapshot exists
            continue
            
        print(f"\nChecking Case: {name} ({pid})")
        print(f"  - Scrutiny Issues (Source): {len(scrutiny_issues)}")
        if scrutiny_issues:
             print(f"  Type of scrutiny_issues: {type(scrutiny_issues)}")
             
             # Normalize to list if it's a dict
             if isinstance(scrutiny_issues, dict):
                 print("  [INFO] Normalized dict to list.")
                 scrutiny_issues = list(scrutiny_issues.values())
                 
             if isinstance(scrutiny_issues, list) and len(scrutiny_issues) > 0:
                 print(f"  Type of first element: {type(scrutiny_issues[0])}")
                 # Handle list of strings (if double serialized or something)
                 if isinstance(scrutiny_issues[0], str):
                     print("  [INFO] Detected list of strings. Parsing inner JSON...")
                     refined_issues = []
                     for item in scrutiny_issues:
                         if isinstance(item, str):
                             try: refined_issues.append(json.loads(item))
                             except: pass
                         else:
                             refined_issues.append(item)
                     scrutiny_issues = refined_issues
        
        print(f"  - DRC-01A Issues (Target): {len(drc_issues)}")
        
        # Index Source by Issue ID for fast lookup
        # Note: In selected_issues, key is 'issue_id'. In case_issues, key is 'issue_id' column.
        source_map = {i.get('issue_id'): i for i in scrutiny_issues if isinstance(i, dict)}
        
        updates_needed = False
        repaired_issues = []
        
        for target_issue in drc_issues:
            tid = target_issue['issue_id']
            tdata = target_issue.get('data', {})
            
            # Check for corruption (missing summary_table)
            tsum = tdata.get('summary_table')
            trows = tsum.get('rows', []) if tsum else []
            
            # Check Source
            source = source_map.get(tid)
            if not source:
                print(f"  [WARN] Issue {tid} distinct in DRC-01A (no source match). Skipping.")
                repaired_issues.append({'issue_id': tid, 'data': tdata})
                continue
                
            # Scrutiny issues don't have 'data' wrapper usually, they ARE the data dict.
            # But check structure.
            sdata = source # Directly the issue dict
            ssum = sdata.get('summary_table')
            srows = ssum.get('rows', []) if ssum else []
            
            # Logic: If Target is empty but Source has data, REPAIR IT
            if (not tsum or not trows) and (srows):
                print(f"  [FIXING] {tid}: Target has 0 rows, Source has {len(srows)} rows.")
                tdata['summary_table'] = ssum
                # Also ensure grid_data is populated if missing
                if not tdata.get('grid_data') and sdata.get('grid_data'):
                     tdata['grid_data'] = sdata.get('grid_data')
                     print(f"  [FIXING] {tid}: Restored grid_data too.")
                     
                updates_needed = True
            else:
                # No repair needed or source also empty
                pass
                
            repaired_issues.append({'issue_id': tid, 'data': tdata})
            
        if updates_needed:
            print(f"  >> Saving Repaired Snapshot for {name}...")
            db.save_case_issues(pid, repaired_issues, stage='DRC-01A')
            fixed_count += 1
            print("  >> SUCCESS.")
        else:
            print("  >> No repairs needed.")
            
    print(f"\n--- REPAIR COMPLETE. Fixed {fixed_count} cases. ---")

if __name__ == "__main__":
    repair_snapshots()
