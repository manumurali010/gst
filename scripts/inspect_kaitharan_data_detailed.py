import sqlite3
import json

DB_PATH = 'data/adjudication.db'

def inspect_issues_detailed():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("--- Detailed Issue Inspection (Kaitharan) ---")
    cursor.execute("SELECT id, selected_issues FROM proceedings WHERE legal_name LIKE '%KAITHARAN%'")
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"Proc ID: {row['id']}")
        val = row['selected_issues']
        
        if not val:
            print("  selected_issues is Empty/Null")
            continue
            
        try:
            # Handle potential double-encoding
            parsed = json.loads(val)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
                
            issues = []
            if isinstance(parsed, dict):
                print("  Root is Dict. Keys:", parsed.keys())
                issues = parsed.get('issues', [])
            elif isinstance(parsed, list):
                print("  Root is List.")
                issues = parsed
            
            print(f"  Total Issues found in JSON: {len(issues)}")
            
            for i, issue in enumerate(issues):
                cat = issue.get('category', 'N/A')
                desc = issue.get('issue_name') or issue.get('description', 'N/A')
                tmpl = issue.get('template_type', 'N/A')
                status = issue.get('status', 'N/A')
                print(f"    Issue {i}:")
                print(f"      Category: {cat}")
                print(f"      Template: {tmpl}")
                print(f"      Status:   {status}")
                print(f"      Keys:     {list(issue.keys())}")
                if tmpl == "summary_3x4" or "9" in cat:
                     print(f"      Table Data: {str(issue.get('summary_table', 'N/A'))[:100]}...")

        except Exception as e:
            print(f"  Parse Error: {e}")

    conn.close()

if __name__ == "__main__":
    inspect_issues_detailed()
