import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

def cleanup_oc_register():
    print("--- Cleaning up OC Register ---")
    db = DatabaseManager()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    # 1. Remove Specific OC
    print("Deleting OC/2025/001...")
    cursor.execute("DELETE FROM oc_register WHERE oc_number = 'OC/2025/001'")
    print(f"Deleted {cursor.rowcount} specific rows.")
    
    # 2. Deduplicate Keep Latest
    print("Deduplicating OC Numbers (Keeping Latest)...")
    
    delete_query = """
    DELETE FROM oc_register 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM oc_register 
        GROUP BY oc_number
    )
    """
    cursor.execute(delete_query)
    print(f"Deleted {cursor.rowcount} duplicate OC rows.")
    
    conn.commit()
    
    # 3. Verify
    cursor.execute("SELECT * FROM oc_register")
    rows = cursor.fetchall()
    print("\nFinal State:")
    for row in rows:
        print(dict(zip([c[0] for c in cursor.description], row)))
        
    conn.close()

if __name__ == "__main__":
    cleanup_oc_register()
