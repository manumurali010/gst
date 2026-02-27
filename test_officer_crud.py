import os
import sqlite3
from src.database.db_manager import DatabaseManager
from src.utils.constants import WorkflowStage

def run_tests():
    print("--- Testing Officer Registry CRUD Operations ---\n")
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'adjudication.db')
    db = DatabaseManager(db_path=db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Add Officer
    print("1. Testing add_officer()...")
    officer_id = db.add_officer("Agent Test", "Inspector", "Division Z", "Z HQ")
    if officer_id:
        print(f"✅ Success: Officer created with ID {officer_id}")
    else:
        print("❌ Failed to create officer.")
        return
        
    # 2. Update Officer
    print("\n2. Testing update_officer()...")
    success = db.update_officer(officer_id, "Agent Test Updated", "Superintendent", "Division Y", "Y HQ")
    if success:
        # Verify update
        off = db.get_officer_by_id(officer_id)
        if off and off['name'] == "Agent Test Updated":
            print("✅ Success: Officer updated and verified.")
        else:
            print("❌ Failed: Officer data mismatch after update.")
    else:
        print("❌ Failed to run update operator.")
        
    # 3. Toggle Status
    print("\n3. Testing toggle_officer_status()...")
    before = db.get_officer_by_id(officer_id)['is_active']
    db.toggle_officer_status(officer_id, 0)
    after = db.get_officer_by_id(officer_id)['is_active']
    
    if before == 1 and after == 0:
        print("✅ Success: Officer toggled to inactive (0).")
    else:
        print(f"❌ Failed: Expected 1 -> 0, got {before} -> {after}")
        
    # Re-enable for further testing
    db.toggle_officer_status(officer_id, 1)
    
    # 4. Delete Officer (Happy Path)
    print("\n4. Testing delete_officer() (Happy Path)...")
    # Clean up the test officer created above
    success, msg = db.delete_officer(officer_id)
    if success:
        print(f"✅ Success: {msg}")
    else:
        print(f"❌ Failed: {msg}")
        
    # 5. Delete Officer (Blocked Path)
    print("\n5. Testing delete_officer() (Blocked Path)...")
    
    # Create an officer specifically to link
    linked_officer_id = db.add_officer("Agent Blocked", "Comm", "Div", "HQ")
    print(f"-> Created officer ID {linked_officer_id} for blocking test.")
    
    # Link to a fake proceeding
    cursor.execute('''
        INSERT INTO proceedings (gstin, legal_name, issuing_officer_id) 
        VALUES ('TEST9999', 'Block Test Corp', ?)
    ''', (linked_officer_id,))
    conn.commit()
    pid = cursor.lastrowid
    print(f"-> Linked officer to proceeding ID {pid}.")
    
    # Attempt deletion
    success, msg = db.delete_officer(linked_officer_id)
    if not success and "Cannot delete officer. They are currently acting as the Issuing Authority" in msg:
        print(f"✅ Success: Deletion correctly blocked. Message: {msg}")
    else:
        print(f"❌ Failed: Expected block message. Got: Success={success}, Msg={msg}")
        
    # Cleanup block testing
    cursor.execute('DELETE FROM proceedings WHERE id = ?', (pid,))
    cursor.execute('DELETE FROM officers WHERE id = ?', (linked_officer_id,))
    conn.commit()
    conn.close()
    
    print("\n--- All CRUD Tests Completed ---")

if __name__ == "__main__":
    run_tests()
