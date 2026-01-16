import sqlite3
import os

db_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\data\adjudication.db"

def analyze():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Get Schema
    print("--- TABLE SCHEMAS ---")
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    for name, sql in cursor.fetchall():
        print(f"Table: {name}\n{sql}\n")

    # 2. Check for foreign keys or references to issues_master
    print("--- REFERENCES TO issues_master ---")
    # Some tables might have issue_id column but not formal FK
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [c[1] for c in cursor.fetchall()]
        if 'issue_id' in columns:
            print(f"Table '{table}' has column 'issue_id'")
            
            # Check for non-SOP usage
            query = f"""
                SELECT issue_id, COUNT(*) 
                FROM {table} 
                WHERE issue_id NOT LIKE 'SOP-%'
                GROUP BY issue_id
            """
            cursor.execute(query)
            usage = cursor.fetchall()
            if usage:
                print(f"  Found non-SOP usage in '{table}':")
                for u in usage:
                    print(f"    {u[0]}: {u[1]} rows")
            else:
                print(f"  No non-SOP usage in '{table}'.")

    conn.close()

if __name__ == "__main__":
    analyze()
