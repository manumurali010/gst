import sys
import os
from PyQt6.QtWidgets import QApplication
from src.database.db_manager import DatabaseManager

# Add src to path
sys.path.append(os.getcwd())

def verify_templates():
    print("Verifying Templates Module...")
    
    db = DatabaseManager()
    db.init_sqlite()
    
    # 1. Test Save
    data = {
        "name": "Test Template",
        "type": "Other",
        "content": "<h1>Test</h1>",
        "version": "1.0",
        "is_default": 0
    }
    tmpl_id = db.save_template(data)
    if tmpl_id:
        print(f"SUCCESS: Template saved with ID {tmpl_id}")
    else:
        print("FAILURE: Template save failed")
        return

    # 2. Test Get
    tmpl = db.get_template(tmpl_id)
    if tmpl and tmpl['name'] == "Test Template":
        print("SUCCESS: Template retrieved correctly")
    else:
        print("FAILURE: Template retrieval failed")

    # 3. Test Delete
    if db.delete_template(tmpl_id):
        print("SUCCESS: Template deleted")
    else:
        print("FAILURE: Template deletion failed")
        
    print("Templates Module Verification Complete.")

if __name__ == "__main__":
    verify_templates()
