import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

def cleanup_oc():
    print("--- Cleaning up ASMT-10 OC Numbers ---")
    db = DatabaseManager()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    # 1. Remove Specific OC
    print("Deleting OC/2025/001...")
    cursor.execute("DELETE FROM asmt10_register WHERE oc_number = 'OC/2025/001'")
    print(f"Deleted {cursor.rowcount} specific rows.")
    
    # 2. Deduplicate Keep Latest
    print("Deduplicating OC Numbers (Keeping Latest)...")
    
    delete_query = """
    DELETE FROM asmt10_register 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM asmt10_register 
        GROUP BY oc_number
    )
    """
    cursor.execute(delete_query)
    print(f"Deleted {cursor.rowcount} duplicate OC rows.")
    
    conn.commit()
    
    # 3. Verify
    cursor.execute("SELECT * FROM asmt10_register")
    rows = cursor.fetchall()
    print("\nFinal State:")
    for row in rows:
        print(dict(row))
        
    conn.close()

if __name__ == "__main__":
    cleanup_oc()
