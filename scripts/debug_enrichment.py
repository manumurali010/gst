import sys
import os
import json
import sqlite3

sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager

DB_PATH = 'data/adjudication.db'

def enrich_issues_with_templates(db, issues):
    """(Copied from ScrutinyTab logic)"""
    enriched = []
    print(f"Enriching {len(issues)} issues...")
    
    for i, issue in enumerate(issues):
        desc = issue.get("description") or issue.get("category")
        issue_id = issue.get('issue_id') 
        
        print(f"[{i}] Processing {issue_id}...")

        if not issue_id:
             error_msg = f"INTEGRITY ERROR: Scrutiny Issue '{desc}' has no 'issue_id'."
             raise RuntimeError(error_msg)

        # Step 2: Fetch Master Record
        master = db.get_issue(issue_id)
        
        if master:
            master_json = master 
            print(f"    Found Master: {master_json.get('issue_name')}, SOP: {master_json.get('sop_point')}")
            
            issue['issue_master_id'] = master_json.get('issue_id')
            issue['issue_name'] = master_json.get('issue_name')
            issue['sop_point'] = master_json.get('sop_point')
            
            master_grid = master_json.get('grid_data')
            if master_grid:
                print("    Enriching Grid Data...")
            
        else:
             error_msg = f"CRITICAL: Issue ID '{issue_id}' not found in 'issues_master'."
             raise RuntimeError(error_msg)
        
        enriched.append(issue)
    return enriched

def debug_flow():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT selected_issues FROM proceedings WHERE legal_name LIKE '%Kaitharan%'")
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        print("No data found for Kaitharan")
        return

    try:
        data = json.loads(row[0])
        issues = data.get('issues', [])
    except:
        issues = []
        
    db = DatabaseManager()
    
    try:
        enriched = enrich_issues_with_templates(db, issues)
        print("Enrichment Successful!")
        print(f"Result count: {len(enriched)}")
    except Exception as e:
        print(f"ENRICHMENT FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_flow()
