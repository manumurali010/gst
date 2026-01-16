import sqlite3
import json
import os
import sys

sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager

def fix():
    print("--- Fixing Missing OC Number for Case 4d8a6a4b... ---")
    db = DatabaseManager()
    
    pid = '4d8a6a4b-1d1a-44d5-be42-e431036a853a'
    
    # 1. Fetch current details to be safe
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proceedings WHERE id = ?", (pid,))
    row = cursor.fetchone()
    
    if not row:
        print("Error: Proceeding not found!")
        return

    # 2. Prepare Update Data
    # The OC register says: '1/2026', '2026-01-01'
    
    new_details = {
        'oc_number': '1/2026',
        'oc_date': '2026-01-01'
    }
    
    # Update via DB Manager to handle JSON serialization
    success = db.update_proceeding(pid, {'additional_details': new_details})
    
    if success:
        print("SUCCESS: Updated proceeding with OC Number 1/2026.")
    else:
        print("FAILED to update proceeding.")

if __name__ == "__main__":
    fix()
