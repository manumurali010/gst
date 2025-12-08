import sqlite3
import os

DB_FILE = os.path.join(os.getcwd(), "data", "adjudication.db")

def check_schema():
    print(f"Checking schema for DB: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("\n--- Current Columns in 'proceedings' ---")
    cursor.execute("PRAGMA table_info(proceedings)")
    columns = [row[1] for row in cursor.fetchall()]
    print(columns)
    
    if "additional_details" not in columns:
        print("\n'additional_details' column is MISSING. Attempting to add it...")
        try:
            cursor.execute("ALTER TABLE proceedings ADD COLUMN additional_details TEXT")
            conn.commit()
            print("Successfully added 'additional_details' column.")
        except Exception as e:
            print(f"FAILED to add column: {e}")
    else:
        print("\n'additional_details' column already EXISTS.")

    conn.close()

if __name__ == "__main__":
    check_schema()
