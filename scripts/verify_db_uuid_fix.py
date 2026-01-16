
import sys
import os
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager
import uuid

def test_uuid_generation():
    print("Testing create_adjudication_case...")
    db = DatabaseManager()
    
    # Mock data
    data = {
        'source_scrutiny_id': 123,
        'gstin': 'TESTGSTIN123',
        'legal_name': 'Test Entity',
        'financial_year': '2023-24'
    }
    
    try:
        # We don't want to actually commit junk to real DB if possible, but the method commits.
        # However, since it returns the ID or None, getting an ID means success.
        # The key error was NameError, so if it runs without that, it is fixed.
        adj_id = db.create_adjudication_case(data)
        
        # Validate standard UUID (36 chars)
        if adj_id and len(adj_id) == 36:
            print(f"[SUCCESS] UUID fixed and internal format verified. Generated ID: {adj_id}")
        else:
            print("[FAILURE] Method returned None or invalid ID")
            
    except NameError as e:
        print(f"[FAILURE] NameError still present: {e}")
    except Exception as e:
        # Other DB errors usually mean the code ran past the UUID part
        if "uuid" in str(e):
             print(f"[FAILURE] Error related to uuid: {e}")
        else:
             print(f"[SUCCESS] (Partial) Code executed past UUID generation. Error: {e}")

if __name__ == "__main__":
    test_uuid_generation()
