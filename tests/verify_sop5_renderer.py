import sys
import os

# Adjust path to import source modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.asmt10_generator import ASMT10Generator

def test_renderer():
    print("Testing SOP-5 Renderer...")
    
    # Mock Issue: Status PASS, Tables Present, Status Msg Present
    issue = {
        "issue_id": "TDS_TCS_MISMATCH",
        "status": "pass",
        "status_msg": "TDS: Matched | TCS: Matched",
        "tables": [
            {
                "title": "TDS Mismatch",
                "columns": [{"id": "c1", "label": "Desc"}, {"id": "c2", "label": "Amt"}],
                "rows": [{"c1": {"value": "Row1"}, "c2": {"value": 100}}]
            },
               {
                "title": "TCS Mismatch",
                "columns": [{"id": "c1", "label": "Desc"}, {"id": "c2", "label": "Amt"}],
                "rows": [{"c1": {"value": "Row1"}, "c2": {"value": 100}}]
            }
        ],
        "grid_data": [] # Assumed empty after fix
    }
    
    html = ASMT10Generator.generate_issue_table_html(issue)
    
    print("\n--- Generated HTML ---")
    print(html)
    
    if "TDS Mismatch" in html and "TCS Mismatch" in html:
        print("\nPASS: Tables are rendered.")
    else:
        print("\nFAIL: Tables are NOT rendered.")
        
    if "TDS: Matched" in html:
         print("WARNING: Status Message found in HTML (Unexpected if supposed to be tables only).")

if __name__ == "__main__":
    test_renderer()
