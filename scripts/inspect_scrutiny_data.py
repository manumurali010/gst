import sqlite3
import pandas as pd

DB_PATH = 'data/adjudication.db'

def inspect_scrutiny_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open('scrutiny_inspection_log.txt', 'w', encoding='utf-8') as f:
        f.write("--- Issues Master (Current) ---\n")
        cursor.execute("SELECT issue_id, issue_name FROM issues_master")
        masters = cursor.fetchall()
        master_ids = {m[0] for m in masters}
        for m in masters:
            f.write(f"{m[0]}: {m[1]}\n")

        f.write("\n--- Scrutiny Results (Inspection) ---\n")
        try:
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scrutiny_results'")
            if not cursor.fetchone():
                f.write("Table 'scrutiny_results' does not exist.\n")
                # Check proceedings table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proceedings'")
                if cursor.fetchone():
                    f.write("Table 'proceedings' exists. Checking data structure...\n")
                    cursor.execute("SELECT * FROM proceedings LIMIT 5")
                    rows = cursor.fetchall()
                    cols = [description[0] for description in cursor.description]
                    f.write(f"Columns: {cols}\n")
                    
                    for row in rows:
                        row_dict = dict(zip(cols, row))
                        f.write(f"Row ID: {row_dict.get('id')}\n")
                        # Check additional_details or other JSON fields
                        if 'additional_details' in row_dict:
                            f.write(f"  additional_details: {str(row_dict['additional_details'])[:500]}...\n")
                        if 'findings' in row_dict:
                             f.write(f"  findings: {str(row_dict['findings'])[:500]}...\n")

            else:
                cursor.execute("SELECT * FROM scrutiny_results")
                rows = cursor.fetchall()
                
                # Get column names
                cols = [description[0] for description in cursor.description]
                f.write(f"Columns: {cols}\n")
                
                orphaned_count = 0
                for row in rows:
                    row_dict = dict(zip(cols, row))
                    issue_id = row_dict.get('issue_id')
                    case_id = row_dict.get('case_id')
                    
                    status = "VALID" if issue_id in master_ids else "ORPHANED"
                    if status == "ORPHANED":
                        orphaned_count += 1
                        f.write(f"[{status}] Case: {case_id} | Issue: {issue_id}\n")
                
                f.write(f"\nTotal Orphaned Records: {orphaned_count}\n")
        
        except Exception as e:
            f.write(f"Error: {e}\n")
    
    conn.close()

if __name__ == "__main__":
    inspect_scrutiny_data()
