import sqlite3
import os

DB_FILE = os.path.join("data", "adjudication.db")

def cleanup_issues():
    if not os.path.exists(DB_FILE):
        print(f"Database file not found at {DB_FILE}")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 1. Identify issues to delete
        cursor.execute("SELECT issue_id, issue_name FROM issues_master WHERE issue_id NOT LIKE 'SOP-%'")
        to_delete = cursor.fetchall()
        
        if not to_delete:
            print("No non-SOP issues found to delete.")
            conn.close()
            return

        print(f"Found {len(to_delete)} issues to delete:")
        for row in to_delete:
            print(f" - {row[0]}: {row[1]}")
        
        # 2. Delete from issues_master
        # Note: Foreign key constraints should cascade delete from issues_data if configured,
        # but we'll manually ensure if needed. Schema says ON DELETE CASCADE for issues_data.
        
        ids_to_delete = [row[0] for row in to_delete]
        
        # Use parameterized query for safety
        placeholders = ','.join('?' for _ in ids_to_delete)
        query = f"DELETE FROM issues_master WHERE issue_id IN ({placeholders})"
        
        cursor.execute(query, ids_to_delete)
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"\nSuccessfully deleted {deleted_count} issues.")

    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_issues()
