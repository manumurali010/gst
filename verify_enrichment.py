from src.database.db_manager import DatabaseManager
import json
import copy

def verify_legacy_conversion(issue_id):
    db = DatabaseManager()
    master = db.get_issue(issue_id)
    if not master:
        print(f"Issue {issue_id} not found.")
        return

    master_grid = master.get('grid_data')
    if not master_grid or not isinstance(master_grid, list):
        print(f"Master grid is invalid: {type(master_grid)}")
        return

    print(f"Original Master Grid Rows: {len(master_grid)}")
    
    rehydrated_grid = copy.deepcopy(master_grid)
    
    # Assume Logic
    if len(rehydrated_grid) > 0:
         header_row = rehydrated_grid[0]
         data_rows = rehydrated_grid[1:]
         
         col_keys = []
         print("\n--- Header Analysis ---")
         for i, h_cell in enumerate(header_row):
              if isinstance(h_cell, dict):
                  cid = h_cell.get("id") or f"col{i}"
                  print(f"Col {i}: ID='{cid}' (from {h_cell.get('id')})")
                  col_keys.append(cid)
              else:
                  print(f"Col {i}: ID='col{i}' (Non-dict)")
                  col_keys.append(f"col{i}")
                  
         # Transform Data Rows
         dict_rows = []
         print("\n--- Row Analysis ---")
         for r_idx, row in enumerate(data_rows):
              row_dict = {}
              debug_keys = []
              for i, cell in enumerate(row):
                  if i < len(col_keys):
                       key = col_keys[i]
                       row_dict[key] = cell
                       debug_keys.append(key)
              dict_rows.append(row_dict)
              if r_idx == 0:
                  print(f"Row 0 Keys Generated: {debug_keys}")

         grid_data = {
             "columns": header_row,
             "rows": dict_rows
         }
         
         print(f"\nFinal Grid Rows: {len(grid_data['rows'])}")
         return grid_data
    else:
         print("Grid empty")

# Find ID
db = DatabaseManager()
issues = db.get_all_issues_metadata()
target_id = None
for i in issues:
    if "3B" in i['issue_name'] and "2B" in i['issue_name']:
         target_id = i['issue_id']
         break

if target_id:
    print(f"Verifying {target_id}...")
    verify_legacy_conversion(target_id)
else:
    print("Issue not found")
