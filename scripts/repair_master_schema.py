import sqlite3
import os

DB_PATH = 'data/adjudication.db'

def repair():
    print("--- Repairing issues_master Schema ---")
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(issues_master)")
        existing_cols = [r[1] for r in cursor.fetchall()]
        print(f"Existing columns: {existing_cols}")
        
        # Add templates if missing
        if 'templates' not in existing_cols:
            print("Adding 'templates' column...")
            cursor.execute("ALTER TABLE issues_master ADD COLUMN templates TEXT")
        else:
            print("'templates' column already exists.")
            
        # Add grid_data if missing
        if 'grid_data' not in existing_cols:
            print("Adding 'grid_data' column...")
            cursor.execute("ALTER TABLE issues_master ADD COLUMN grid_data TEXT")
        else:
            print("'grid_data' column already exists.")

        conn.commit()
        print("Schema Repair Complete.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    repair()
