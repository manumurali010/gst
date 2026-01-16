import sqlite3
import json
import os
import sys
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager

def inspect():
    db = DatabaseManager()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    pid = '4d8a6a4b-1d1a-44d5-be42-e431036a853a'
    print(f"Checking Proceeding ID: {pid}")
    
    cursor.execute("SELECT * FROM proceedings WHERE id = ?", (pid,))
    row = cursor.fetchone()
    
    if row:
        cols = [c[0] for c in cursor.description]
        d = dict(zip(cols, row))
        print("\n--- Proceeding Record ---")
        for k, v in d.items():
            print(f"{k}: {v}")
            
        # Check additional_details for OC Number
        if d.get('additional_details'):
            try:
                ad = json.loads(d['additional_details'])
                print(f"\nAdditional Details OC: {ad.get('oc_number')}")
            except:
                print("\nAdditional Details: Raw string (failed parse)")
    else:
        print("\nProceeding NOT FOUND in DB.")
        
    print("\n--- OC Register Check (Searching for 1/2026) ---")
    cursor.execute("SELECT * FROM oc_register WHERE oc_number = '1/2026'")
    oc_rows = cursor.fetchall()
    for r in oc_rows:
        print(r)
        
    conn.close()

if __name__ == "__main__":
    inspect()
