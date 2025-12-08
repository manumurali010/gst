import sqlite3
import os

db_path = 'data/adjudication.db'
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    case_id = 'CASE/2025/ADJ/0001'
    print(f"Searching for Case ID: {case_id}")
    
    cursor.execute("SELECT id FROM proceedings WHERE case_id=?", (case_id,))
    pid = cursor.fetchone()
    
    if pid:
        print(f"Found Proceeding ID: {pid[0]}")
        cursor.execute("SELECT content_html FROM documents WHERE proceeding_id=? AND doc_type='DRC-01A' ORDER BY created_at DESC LIMIT 1", (pid[0],))
        row = cursor.fetchone()
        if row:
            content = row[0]
            print("--- Document Content Start ---")
            # print(content[:2000]) 
            print("--- Document Content End ---")
            
            if "Calculation Table" in content:
                 print("SUCCESS: 'Calculation Table' text found.")
                 # Extract table content to see if it's empty
                 start = content.find("Calculation Table")
                 end = content.find("</div>", start)
                 table_html = content[start:end]
                 print(f"Table HTML snippet: {table_html}")
            else:
                 print("FAILURE: 'Calculation Table' text NOT found.")

            if "Tax Demand Details" in content:
                print("SUCCESS: 'Tax Demand Details' found.")
            else:
                print("FAILURE: 'Tax Demand Details' NOT found.")
                 
        else:
            print("No DRC-01A document found for this case.")
    else:
        print("Case ID not found.")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if conn: conn.close()
