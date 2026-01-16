import sys
import os
sys.path.append(os.getcwd())
import sqlite3
import json
from src.utils.initialize_scrutiny_master import issues
from datetime import datetime

DB_PATH = 'data/adjudication.db'

def update_master():
    print(f"Updating issues_master in {DB_PATH} using definitions from initialize_scrutiny_master.py...")
    if not os.path.exists(DB_PATH):
        print("DB not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for issue in issues:
        issue_id = issue['issue_id']
        grid_data = json.dumps(issue.get('grid_data', []))
        templates = json.dumps(issue.get('templates', {}))
        sop_point = issue.get('sop_point')
        
        # Verify grid data has content
        if not issue.get('grid_data'):
            print(f"Warning: {issue_id} has empty grid_data")
        else:
            # Check a sample var
            try:
                sample_var = issue['grid_data'][1][1]['var'] # checking row 1 col 1 input
                # print(f"  {issue_id} Grid Valid. Var: {sample_var}")
            except:
                pass

        try:
            cursor.execute("""
                UPDATE issues_master 
                SET grid_data = ?, templates = ?, sop_point = ?, updated_at = ?
                WHERE issue_id = ?
            """, (grid_data, templates, sop_point, datetime.now(), issue_id))
            
            if cursor.rowcount == 0:
                print(f"Issue {issue_id} not found in DB - Inserting...")
                cursor.execute("""
                    INSERT INTO issues_master (issue_id, issue_name, category, sop_point, grid_data, templates, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (issue_id, issue['issue_name'], issue.get('issue_name'), sop_point, grid_data, templates, datetime.now()))
            
            count += 1
        except Exception as e:
            print(f"Error updating {issue_id}: {e}")

    conn.commit()
    conn.close()
    print(f"Updated {count} issues.")

if __name__ == "__main__":
    update_master()
