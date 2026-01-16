import sys
import os
import sqlite3
import uuid

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

def restore_case():
    print("--- Restoring Adjudication Case for Kaitharan Agencies ---")
    db = DatabaseManager()
    conn = db._get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Hardcoded reconstruction based on registers
    target_pid = '4d8a6a4b-1d1a-44d5-be42-e431036a853a'
    
    print(f"[INFO] Attempting to reconstruct case {target_pid}...")
    
    cursor.execute("SELECT * FROM proceedings WHERE id = ?", (target_pid,))
    if cursor.fetchone():
        print("[INFO] Proceeding already exists (Update logic not implemented, assumed missing).")
    else:
        print("[WARN] Proceeding MISSING. Re-inserting shell from register data...")
        new_adj_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO proceedings (
                id, case_id, gstin, legal_name, financial_year, status, asmt10_status, adjudication_case_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            target_pid,
            'CASE-RESTORED-001', # Placeholder
            '32AAPFK0963M1ZZ',
            'M/S KAITHARAN AGENCIES',
            '2021-22',
            'ASMT-10 Issued',
            'finalised',
            new_adj_id
        ))
        
        cursor.execute("""
            INSERT INTO adjudication_cases (
                id, source_scrutiny_id, gstin, legal_name, financial_year, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            new_adj_id,
            target_pid,
            '32AAPFK0963M1ZZ',
            'M/S KAITHARAN AGENCIES',
            '2021-22',
            'Pending'
        ))
        
        conn.commit()
        print(f"[SUCCESS] Restored Scrutiny Case {target_pid} and created Adjudication Case {new_adj_id}")
            
    conn.close()

if __name__ == "__main__":
    restore_case()
