import sqlite3
import os

DB_PATH = "data/adjudication.db"

def migrate():
    print("--- Migrating Schema: Adding adjudication_section ---")
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(adjudication_cases)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'adjudication_section' not in columns:
            print("Adding 'adjudication_section' column...")
            cursor.execute("ALTER TABLE adjudication_cases ADD COLUMN adjudication_section TEXT")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'adjudication_section' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
