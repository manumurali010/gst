import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'data', 'adjudication.db')

def backup_table():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues_data'")
        if not cursor.fetchone():
            print("Table 'issues_data' not found. Skipping backup.")
            return

        # Create backup table
        print("Backing up 'issues_data' to 'issues_data_backup_refactor'...")
        cursor.execute("DROP TABLE IF EXISTS issues_data_backup_refactor")
        cursor.execute("CREATE TABLE issues_data_backup_refactor AS SELECT * FROM issues_data")
        
        conn.commit()
        print("Backup complete.")
        
        # Verify count
        cursor.execute("SELECT COUNT(*) FROM issues_data")
        orig_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM issues_data_backup_refactor")
        bkp_count = cursor.fetchone()[0]
        print(f"Original: {orig_count} rows | Backup: {bkp_count} rows")
        
        conn.close()
    except Exception as e:
        print(f"Backup failed: {e}")

if __name__ == "__main__":
    backup_table()
