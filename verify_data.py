import sqlite3
import json

def verify_data():
    conn = sqlite3.connect('data/adjudication.db')
    cursor = conn.cursor()
    
    print("--- Sample issues_master data ---")
    cursor.execute("SELECT issue_id, liability_config FROM issues_master WHERE issue_id = 'ITC_3B_2B_9X4'")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row[0]}")
        print(f"Liability Config: {row[1]}")
    else:
        print("Issue not found")
        
    conn.close()

if __name__ == "__main__":
    verify_data()
