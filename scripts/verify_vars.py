import sys
import os
import json
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager

db = DatabaseManager()
master = db.get_issue("LIABILITY_3B_R1")
print("Grid Vars:")
if master:
    grid = master.get('grid_data')
    if isinstance(grid, list):
         for r in grid:
             for c in r:
                 if 'var' in c:
                     print(f"  {c['var']}")
    elif isinstance(grid, str):
        print("  Grid is string: " + grid)
    else:
        print("  Grid is: " + str(grid))
else:
    print("  Master not found")
