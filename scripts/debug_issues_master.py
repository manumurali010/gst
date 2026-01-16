import sqlite3
import json

db_path = "data/adjudication.db"

def inspect_master():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check Point 1 (Liability)
        cursor.execute("SELECT issue_id, grid_data, templates FROM issues_master WHERE issue_id = 'LIABILITY_3B_R1'")
        row = cursor.fetchone()
        
        if row:
            print(f"=== Issue: {row[0]} ===")
            try:
                grid = json.loads(row[1])
                print(f"Grid Data: {json.dumps(grid, indent=2)}")
            except:
                print(f"Grid Data (Raw): {row[1]}")
            
            try:
                tmpl = json.loads(row[2])
                print(f"Templates: {json.dumps(tmpl, indent=2)}")
            except:
                print(f"Templates (Raw): {row[2]}")
        else:
            print("Issue LIABILITY_3B_R1 not found.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_master()
