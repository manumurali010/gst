
import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database.db_manager import DatabaseManager

def dump_data():
    db = DatabaseManager()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    print("--- OC REGISTER ---")
    cursor.execute("SELECT id, case_id, oc_number, oc_content FROM oc_register")
    rows = cursor.fetchall()
    for r in rows:
        print(r)
        
    print("\n--- ASMT-10 REGISTER ---")
    cursor.execute("SELECT id, case_id, oc_number FROM asmt10_register")
    rows = cursor.fetchall()
    for r in rows:
        print(r)
        
    print("\n--- PROCEEDINGS ---")
    cursor.execute("SELECT id, case_id, status, asmt10_status, asmt10_finalised_on FROM proceedings")
    rows = cursor.fetchall()
    for r in rows:
        print(r)

    conn.close()

if __name__ == "__main__":
    dump_data()
