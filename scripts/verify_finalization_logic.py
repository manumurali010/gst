
import sqlite3
import os
import json

def verify():
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "adjudication.db")
    print(f"Checking DB at: {db_path}")
    
    if not os.path.exists(db_path):
        print("FAIL: DB file not found")
        return False
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Check Schema
    print("Checking Schema...")
    cursor.execute("PRAGMA table_info(case_issues)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"case_issues Columns: {columns}")
    
    if 'category' not in columns or 'amount' not in columns:
        print("FAIL: case_issues missing columns")
        conn.close()
        return False
        
    cursor.execute("PRAGMA table_info(asmt10_register)")
    asmt_cols = [row[1] for row in cursor.fetchall()]
    print(f"asmt10_register Columns: {asmt_cols}")
    if not asmt_cols:
         print("FAIL: asmt10_register table missing")
         conn.close()
         return False

    print("\nALL VERIFICATIONS PASSED")
    conn.close()
    return True

if __name__ == "__main__":
    verify()
