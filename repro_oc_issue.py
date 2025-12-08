
import sys
import os
import json
import sqlite3

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

def test_backend_persistence():
    print("Initializing DB Manager...")
    db = DatabaseManager()
    db.init_sqlite()
    
    # 1. Create a Dummy Proceeding
    print("\n1. Creating Dummy Proceeding...")
    proceeding_data = {
        'gstin': '99TESTTEST001',
        'legal_name': 'Test Company',
        'financial_year': '2023-24',
        'initiating_section': '73',
        'status': 'Draft'
    }
    pid = db.create_proceeding(proceeding_data)
    print(f"   Created Proceeding ID: {pid}")
    
    # 2. Simulate Save DRC-01A Metadata (logic from proceedings_workspace.py)
    print("\n2. Saving Metadata (OC Number)...")
    
    # Fetch current state first (like the app does)
    current_proc = db.get_proceeding(pid)
    
    metadata = {
        "oc_number": "OC-12345-TEST",
        "oc_date": "2024-01-01"
    }
    
    # The logic in proceedings_workspace.py:
    current_details = current_proc.get('additional_details', {})
    # It might be a string if DB returned it that way (before my fix)
    # But now db.get_proceeding should return a dict. Use verify.
    if isinstance(current_details, str):
        print("   WARNING: additional_details is a STRING in get_proceeding result!")
        current_details = json.loads(current_details)
    else:
        print("   additional_details is correct type (dict/list)")
        
    current_details.update(metadata)
    
    # Call update_proceeding
    # Note: proceedings_workspace.py does json.dumps() inside the update call dict?
    # No, let's check the code in proceedings_workspace.py again.
    # It calls: self.db.update_proceeding(pid, { ..., "additional_details": json.dumps(current_details) })
    
    update_data = {
        "additional_details": current_details # DatabaseManager.update_proceeding handles json.dumps?
    }
    
    # Let's check DatabaseManager.update_proceeding implementations
    # In step 110:
    # def update_proceeding(self, pid, data):
    #    ...
    #    for k, v in data.items():
    #        if k in ['demand_details', 'selected_issues']:
    #            v = json.dumps(v)
    #        fields.append(f"{k} = ?")
    
    # WAIT! 'additional_details' is NOT in that list in `update_proceeding`! 
    # So if we pass a dict, it might crash or convert to string representation?? 
    # Or if proceedings_workspace passes a JSON string, it gets saved as string.
    
    # Let's emulate exactly what proceedings_workspace does:
    # self.db.update_proceeding(self.proceeding_id, {
    #     ...,
    #     "additional_details": json.dumps(current_details)
    # })
    
    success = db.update_proceeding(pid, {
        "additional_details": json.dumps(current_details)
    })
    
    if success:
        print("   Save Successful.")
    else:
        print("   Save FAILED.")
        
    # 3. Reload Proceeding
    print("\n3. Reloading Proceeding...")
    reloaded_proc = db.get_proceeding(pid)
    
    print(f"   Reloaded Data: {reloaded_proc}")
    
    add_details = reloaded_proc.get('additional_details')
    print(f"   additional_details type: {type(add_details)}")
    print(f"   additional_details content: {add_details}")
    
    if isinstance(add_details, dict) and add_details.get('oc_number') == "OC-12345-TEST":
        print("\nSUCCESS: Backend is working correctly. OC Number preserved as Dict.")
        return True
    else:
        print("\nFAILURE: Data lost or incorrect type.")
        return False

if __name__ == "__main__":
    test_backend_persistence()
