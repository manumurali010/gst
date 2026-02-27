import os
import sqlite3
from src.database.db_manager import DatabaseManager

def test():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'adjudication.db')
    print(f"Testing migration against: {db_path}")
    
    # Instantiate to trigger init_sqlite()
    db = DatabaseManager(db_path=db_path)
    print("DatabaseManager initialized successfully.")
    
    # Verify tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n--- SCHEMA_META ---")
    cursor.execute("SELECT * FROM schema_meta")
    print(cursor.fetchall())
    
    print("\n--- OFFICERS TABLE INFO ---")
    cursor.execute("PRAGMA table_info(officers)")
    for info in cursor.fetchall():
        print(info)
        
    print("\n--- PROCEEDINGS TABLE INFO (Last 5 cols) ---")
    cursor.execute("PRAGMA table_info(proceedings)")
    cols = cursor.fetchall()[-5:]
    for info in cols:
        print(info)
        
    conn.close()

if __name__ == "__main__":
    test()
