
import sys
import os
import json

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db_manager import DatabaseManager

def audit_scn_issues():
    db = DatabaseManager()
    
    # 1. Get all proceedings
    proceedings = db.get_all_proceedings()
    print(f"--- SCN ISSUE AUDIT REPORT ---")
    print(f"Found {len(proceedings)} total proceedings.")
    
    issues_found = 0
    issues_broken = 0
    issues_narrative_candidates = 0
    
    for proc in proceedings:
        pid = proc['id']
        p_title = f"{proc.get('taxpayer', {}).get('legal_name', 'Unknown')} ({pid})"
        
        # 2. Get SCN issues
        issues = db.get_case_issues(pid, stage='SCN')
        if not issues:
            continue
            
        print(f"\nProceeding: {p_title}")
        
        for issue_record in issues:
            issues_found += 1
            data = issue_record.get('data', {})
            issue_id = issue_record.get('issue_id')
            origin = data.get('origin', 'UNKNOWN')
            
            # Check Grid Presence
            has_baseline = bool(data.get('baseline_grid_data'))
            # Check for modern grid OR legacy list (which boundary would catch)
            grid_val = data.get('grid_data')
            has_grid = bool(grid_val) and isinstance(grid_val, dict) and 'rows' in grid_val
            has_legacy = isinstance(data.get('table_data'), list)
            
            status = "OK"
            if has_baseline and has_grid:
                status = "WARN [Mixed]"
            elif not has_baseline and not has_grid:
                status = "BROKEN [No Table]"
                issues_broken += 1
                if origin != 'ASMT10':
                     issues_narrative_candidates += 1
            
            print(f"  [{status}] ID: {issue_id:<15} Origin: {origin:<10} "
                  f"Baseline: {'YES' if has_baseline else 'NO ':<3} "
                  f"Grid: {'YES' if has_grid else 'NO ':<3} "
                  f"Legacy: {'YES' if has_legacy else 'NO '}")
                  
    print(f"\n--- SUMMARY ---")
    print(f"Total SCN Issues: {issues_found}")
    print(f"Broken (No Table): {issues_broken}")
    print(f"  - Candidates for Repair (ASMT10 Origin): {issues_broken - issues_narrative_candidates}")
    print(f"  - Candidates for Narrative Mode: {issues_narrative_candidates}")

if __name__ == "__main__":
    audit_scn_issues()
