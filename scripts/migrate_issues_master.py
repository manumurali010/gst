
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "adjudication.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns = [
        ("table_definition", "TEXT"),
        ("analysis_type", "TEXT"),
        ("sop_version", "TEXT"),
        ("applicable_from_fy", "TEXT")
    ]

    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE issues_master ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column already exists: {col_name}")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    console_path = os.path.abspath(DB_PATH)
    print(f"Migrating DB at: {console_path}")
    migrate()
