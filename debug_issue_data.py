from src.database.db_manager import DatabaseManager
import json

db = DatabaseManager()

issues = db.get_all_issues_metadata()
target_id = None

for i in issues:
    # print(f"{i['issue_id']}: {i['issue_name']}")
    if "3B" in i['issue_name'] and "2B" in i['issue_name']:
         target_id = i['issue_id']
         print(f"FOUND TARGET ID: {target_id}")
         break

if target_id:
    data = db.get_issue(target_id)
    grid_data = data.get('grid_data')
    if grid_data and isinstance(grid_data, list):
        print("HEADER ROW:", json.dumps(grid_data[0], indent=2))
        print("ROW 1:", json.dumps(grid_data[1], indent=2))
    else:
        print("Grid Data is not a list or empty", type(grid_data))
else:
    print("Target Issue not found.")
