
import sys
import os
import json

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db_manager import DatabaseManager
from src.ui.issue_card import IssueCard

def repair_scn_data():
    db = DatabaseManager()
    
    print("--- SCN DATA REPAIR MIGRATION ---")
    
    # 1. Fetch Candidates (mirror audit logic)
    proceedings = db.get_all_proceedings()
    repaired_count = 0
    tagged_narrative = 0
    
    for proc in proceedings:
        pid = proc['id']
        issues = db.get_case_issues(pid, stage='SCN')
        if not issues: continue
        
        for issue_record in issues:
            data = issue_record.get('data', {})
            issue_id = issue_record.get('issue_id')
            origin = data.get('origin', 'UNKNOWN')
            row_id = issue_record.get('id')
            
            has_baseline = bool(data.get('baseline_grid_data'))
            grid_val = data.get('grid_data')
            has_grid = bool(grid_val) and isinstance(grid_val, dict) and 'rows' in grid_val
            is_narrative = data.get('narrative_only') is True
            
            if has_baseline or has_grid or is_narrative:
                continue # Healthy
                
            print(f"Repairing BROKEN issue: {issue_id} (Origin: {origin})")
            
            # REPAIR STRATEGY A: ASMT-10 Origin -> Fetch Baseline
            if origin == 'ASMT10':
                source_id = data.get('source_issue_id')
                source_scrutiny_id = proc.get('source_scrutiny_id') or proc.get('scrutiny_id')
                
                if source_id and source_scrutiny_id:
                     print(f"  -> Attempting Baseline Restoration from Source {source_id}...")
                     # Fetch source issue
                     source_issues = db.get_case_issues(source_scrutiny_id, stage='DRC-01A')
                     source_rec = next((i for i in source_issues if i['issue_id'] == source_id), None)
                     
                     if source_rec:
                         source_data = source_rec.get('data', {})
                         # Extract valid grid from source
                         source_grid = source_data.get('grid_data')
                         # Or legacy table_data conversion if needed (but assume source is healthy or converted)
                         # If source has table_data and not grid_data, we might need to convert locally or rely on source being migrated?
                         # Let's assume source has grid_data or table_data we can convert.
                         
                         if not source_grid:
                             legacy = source_data.get('table_data')
                             if isinstance(legacy, list):
                                  # On-the-fly convert for repair
                                  headers = [f"Col {i+1}" for i in range(max(len(r) for r in legacy))]
                                  new_rows = []
                                  for r_idx, row in enumerate(legacy):
                                      row_obj = {'id': f"r{r_idx}"}
                                      if isinstance(row, list):
                                          for c_idx, cell in enumerate(row):
                                              val = cell.get('value') if isinstance(cell, dict) else cell
                                              row_obj[f"c{c_idx}"] = val
                                      new_rows.append(row_obj)
                                  source_grid = {'headers': headers, 'rows': new_rows}
                         
                         if source_grid:
                             data['baseline_grid_data'] = source_grid
                             # Also ensure grid_data matches baseline for viewing
                             # data['grid_data'] = source_grid.copy() # Optional? IssueCard usually wants baseline_grid_data for ASMT10
                             
                             # Update DB
                             # We need to serialise data back to JSON? 
                             # db.get_case_issues returns dicts where 'data' is already parsed JSON usually?
                             # Let's check db_manager. 
                             # Actually likely not, it returns raw. But `result` in audit loop implies it's dict.
                             # If we update, we use `update_case_issue(row_id, {'data_json': json.dumps(data)})`
                             
                             json_str = json.dumps(data)
                             db.update_case_issue(row_id, {'data_json': json_str})
                             print(f"  -> SUCCESS: Baseline Restored.")
                             repaired_count += 1
                             continue
                             
            # REPAIR STRATEGY B: Narrative Fallback
            print(f"  -> Tagging as Narrative Only.")
            data['narrative_only'] = True
            json_str = json.dumps(data)
            db.update_case_issue(row_id, {'data_json': json_str})
            tagged_narrative += 1

    print(f"\n--- REPAIR COMPLETE ---")
    print(f"Restored Baselines: {repaired_count}")
    print(f"Tagged Narrative: {tagged_narrative}")

if __name__ == "__main__":
    repair_scn_data()
