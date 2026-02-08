
import sys
import os
import json
import sqlite3

# Ad-hoc setup to import DatabaseManager
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager

def migrate_issue_master_grids():
    print("--- [MIGRATION] Issue Master Grid Schema Fix ---")
    
    db = DatabaseManager()
    conn = db._get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Fetch all issues from issues_master
        cursor.execute("SELECT issue_id, issue_name, grid_data FROM issues_master")
        rows = cursor.fetchall()
        
        updated_count = 0
        
        for row in rows:
            issue_id = row['issue_id']
            issue_name = row['issue_name']
            raw_grid = row['grid_data']
            
            grid_data = {}
            if raw_grid:
                try:
                    grid_data = json.loads(raw_grid)
                except:
                    print(f"Skipping {issue_id}: Invalid JSON in grid_data")
                    continue
            
            # Check for Legacy List Format
            if isinstance(grid_data, list):
                print(f"Migrating {issue_id} ({issue_name})...")
                print(f"  Legacy Type: LIST (Length {len(grid_data)})")
                
                # Conversion Logic
                new_schema = {'columns': [], 'rows': []}
                
                # Heuristic: If list contains dicts, try to extract headers from Row 0
                if len(grid_data) > 0:
                     first_row = grid_data[0]
                     cols = []
                     
                     # Case A: List of Dicts (Standard Legacy)
                     if isinstance(first_row, dict):
                          # Strategy: Inspect first item structure more deeply
                          print(f"  Sample Row 0: {repr(first_row)[:100]}...")
                          
                          # If Row 0 looks like headers ({'value': 'HeaderName', ...})
                          # Or simply use keys?
                          # Let's assume the structure seen in logs: 
                          # [{'value': 'Description'}, {'value': 'CGST'}] -> List (Row) of Dicts (Cells)
                          # NO, "List of Dicts" usually means [ {'colA': 'val'}, {'colA': 'val'} ] (Records)
                          # BUT legacy grid_data was often [[{'value': '..'}, ...]] (List of Lists of Dicts)
                          
                          # Let's check if it is List-of-Records (unlikely for grid_data, likely for 'tables')
                          # or just a single Dict (invalid for list check)?
                          
                          # If first_row IS a dict, maybe the whole grid is [Row1_Dict, Row2_Dict]?
                          # That would be List-of-Records.
                          keys = first_row.keys()
                          # Sort keys to be deterministic
                          sorted_keys = sorted(list(keys))
                          
                          for k in sorted_keys:
                               val = first_row[k]
                               label = val
                               if isinstance(val, dict):
                                    label = val.get('value', k)
                               
                               cols.append({'id': k, 'label': str(label), 'type': 'input'})
                          
                     # Case B: List of Lists (Table Data - Most Common Legacy)
                     elif isinstance(first_row, list):
                          print(f"  Detected List-of-Lists structure (Rows: {len(grid_data)}).")
                          # Assume Row 0 defines columns
                          for idx, cell in enumerate(first_row):
                               label = "Column"
                               if isinstance(cell, dict):
                                   label = cell.get('value', f"Col {idx+1}")
                               elif isinstance(cell, str):
                                   label = cell
                               
                               # Clean label
                               label = str(label).strip()
                               if not label: label = f"Col {idx+1}"
                               
                               cols.append({
                                   'id': f"col{idx}",
                                   'label': label,
                                   'type': 'input' # Default to input
                               })
                          
                          print(f"  Extracted {len(cols)} columns: {[c['label'] for c in cols]}")
                     
                     new_schema['columns'] = cols

                     # Generate Default Rows (Preserve row count/structure as placeholders)
                     # We do NOT migrate values here (Issue Master values are defaults/examples usually)
                     # But we must create row objects so the grid isn't 0-height
                     for r_idx, row_data in enumerate(grid_data):
                          # Skip header row if we used it
                          if r_idx == 0: continue 
                          
                          row_obj = {'id': f"r{r_idx}"}
                          # We can carry over some default values if they exist in master
                          new_schema['rows'].append(row_obj)
                
                # Final Check: Did we get columns?
                if not new_schema['columns']:
                     print(f"  WARNING: Could not infer columns for {issue_id}. Creating generic schema.")
                     new_schema['columns'] = [
                         {'id': 'col0', 'label': 'Description', 'type': 'text'},
                         {'id': 'col1', 'label': 'Amount', 'type': 'currency'}
                     ]
                     # Add dummy row
                     new_schema['rows'] = [{'id': 'r1'}]
                
                # Update DB
                new_json = json.dumps(new_schema)
                cursor.execute("UPDATE issues_master SET grid_data = ?, updated_at = CURRENT_TIMESTAMP WHERE issue_id = ?", (new_json, issue_id))
                updated_count += 1
                print("  -> FIXED.")

        conn.commit()
        print(f"\n--- Migration Complete. Updated {updated_count} issues. ---")
        
    except Exception as e:
        print(f"Migration Failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_issue_master_grids()
