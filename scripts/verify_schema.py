import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.getcwd())

from src.database.schema import init_db, DB_FILE

def verify_migration():
    print(f"Checking database at {DB_FILE}")
    
    # Run initialization (should trigger migration if needed)
    init_db()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check columns in proceedings table
    cursor.execute("PRAGMA table_info(proceedings)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print(f"Columns in proceedings: {columns}")
    
    required_cols = ['address', 'case_id', 'form_type', 'created_by', 'taxpayer_details']
    all_present = True
    for col in required_cols:
        if col in columns:
            print(f"SUCCESS: '{col}' column found.")
        else:
            print(f"FAILURE: '{col}' column NOT found.")
            all_present = False
            
    if all_present:
        print("ALL SCHEMA CHECKS PASSED.")
        
    conn.close()

if __name__ == "__main__":
    verify_migration()
