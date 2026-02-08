import sys
import os
sys.path.append(os.getcwd())
from src.database.db_manager import DatabaseManager
from src.services.asmt10_generator import ASMT10Generator
from src.utils.preview_generator import PreviewGenerator
import json

def debug_render():
    db = DatabaseManager()
    db.init_sqlite()
    
    # Get the case with the most issues to be safe/likely what the user sees
    cursor = db._get_conn().cursor()
    cursor.execute("SELECT id, asmt10_snapshot, selected_issues, additional_details, created_at FROM proceedings WHERE oc_number = ?", ('2/2026',))
    rows = cursor.fetchall()
    
    target_case = None
    max_issues = -1
    
    for row in rows:
        pid, snapshot_json, _, _, created = row
        if snapshot_json:
            snap = json.loads(snapshot_json)
            issues = snap.get('issues', [])
            cnt = len([i for i in issues if i.get('is_included') and (float(i.get('total_shortfall', 0)) > 0)])
            print(f"Case {pid} ({created}): {cnt} active issues")
            if cnt > max_issues:
                max_issues = cnt
                target_case = row

    if not target_case:
        print("No suitable case found.")
        return

    pid, snapshot_json, _, _, _ = target_case
    snapshot = json.loads(snapshot_json)
    case_data = snapshot.get('case_data', {})
    issues = snapshot.get('issues', [])
    taxpayer = snapshot.get('taxpayer_details', {})
    
    print(f"Rendering Case {pid} with {max_issues} active issues.")
    
    # Generate HTML
    html = ASMT10Generator.generate_html(case_data, issues, for_preview=True)
    
    # Save HTML
    with open("debug_output.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved debug_output.html")
    
    # Check for Issue titles in HTML
    if "Issue 1" in html: print("Found Issue 1")
    if "Issue 2" in html: print("Found Issue 2")
    if "Issue 3" in html: print("Found Issue 3")
    
    # Generate PDF (simulate Preview)
    try:
        pdfs = PreviewGenerator.generate_preview_image(html, all_pages=True)
        if pdfs:
            with open("debug_output.pdf", "wb") as f:
                f.write(pdfs[0])
            print("Saved debug_output.pdf")
        else:
            print("PDF Generation returned no data.")
    except Exception as e:
        print(f"PDF Gen failed: {e}")

if __name__ == "__main__":
    debug_render()
