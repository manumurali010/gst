
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

try:
    from src.database.db_manager import DatabaseManager
    
    print("Initializing DatabaseManager...")
    db = DatabaseManager()
    
    print("Fetching Issue: CANCELLED_SUPPLIERS")
    issue = db.get_issue("CANCELLED_SUPPLIERS")
    
    if issue:
        print("--- Issue Found ---")
        grid = issue.get('grid_data')
        print(f"Grid Data Type: {type(grid)}")
        if isinstance(grid, dict):
            print(f"Grid Keys: {grid.keys()}")
            print("SUCCESS: Grid data is a dictionary.")
        else:
            print(f"FAILURE: Grid data is {grid} (Expected dict)")
            
        templates = issue.get('templates')
        print(f"Templates Type: {type(templates)}")
    else:
        print("FAILURE: Issue not found in DB via DatabaseManager")
        
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
