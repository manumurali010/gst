import sqlite3
import json

def check_schema():
    conn = sqlite3.connect('data/adjudication.db')
    cursor = conn.cursor()
    
    print("--- issues_master schema ---")
    cursor.execute("PRAGMA table_info(issues_master)")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- issues_data schema ---")
    cursor.execute("PRAGMA table_info(issues_data)")
    for row in cursor.fetchall():
        print(row)
    
    conn.close()

if __name__ == "__main__":
    check_schema()
