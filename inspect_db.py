import sqlite3
import os

def check_sop_points():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'adjudication.db')
    print(f"Connecting to {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        issues = ('LIABILITY_3B_R1', 'RCM_3B_VS_CASH', 'RCM_ITC_VS_CASH', 'RCM_ITC_VS_2B', 'RCM_CASH_VS_2B')
        placeholders = ','.join('?' for _ in issues)
        query = f"SELECT issue_id, category, description, sop_point FROM issues_master WHERE issue_id IN ({placeholders})"
        
        c.execute(query, issues)
        rows = c.fetchall()
        
        print("\n--- DB RESULTS ---")
        if not rows:
            print("No matching rows found. Are these issue_ids in this database?")
            
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Category: {row[1]}")
            print(f"SOP Point: {repr(row[3])} (Type: {type(row[3])})")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_sop_points()
