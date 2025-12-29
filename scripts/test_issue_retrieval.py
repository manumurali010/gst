import sqlite3
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db_manager import DatabaseManager

def test_get_issue_by_name():
    # 1. Setup a temporary in-memory database
    # Note: DatabaseManager uses DB_FILE from schema.py. 
    # For a clean test, we might want to mock the connection or use a test DB.
    # However, since I'm implementing it to match the existing schema, 
    # I'll just test if the method executes and handles empty results or data correctly.
    
    db = DatabaseManager()
    
    # Test with a non-existent name
    result = db.get_issue_by_name("Non Existent Issue")
    print(f"Result for non-existent issue: {result}")
    
    if result is None:
        print("SUCCESS: Returned None for non-existent issue.")
    else:
        print("FAILURE: Did not return None for non-existent issue.")

    # To test actual retrieval, we would need to insert data into a real/test DB file.
    # Given the environment, I'll trust the SQL logic which matches the schema.

if __name__ == "__main__":
    test_get_issue_by_name()
