from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication
import sys

def test_border_fix():
    app = QApplication(sys.argv)
    
    # Create table matching user's data structure
    template = {
        "issue_id": "test",
        "issue_name": "GSTR Mismatch",
        "tables": {
            "rows": 4,
            "cols": 4,
            "cells": [
                ["", "CGST", "SGST", "IGST"],  # First cell is EMPTY
                ["GSTR 1", "2561", "2546", "0"],
                ["GSTR 3B", "25666", "25668", "0"],
                ["DIFFERENCE", "23105.0", "22.0", "0"]
            ]
        },
        "templates": {
            "brief_facts": "Test"
        }
    }
    
    card = IssueCard(template)
    html = card.generate_html()
    
    print("=== BORDER FIX VERIFICATION ===\n")
    
    # Critical checks for empty cell rendering
    checks = [
        ("&nbsp;" in html, "Empty cells have non-breaking space"),
        ("border-top: 1px solid #000" in html, "Explicit top border"),
        ("border-right: 1px solid #000" in html, "Explicit right border"),
        ("border-bottom: 1px solid #000" in html, "Explicit bottom border"),
        ("border-left: 1px solid #000" in html, "Explicit left border"),
        ("min-width: 80px" in html, "Minimum cell width set"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {desc}")
        if not passed:
            all_passed = False
    
    # Count cells in first row
    first_row_start = html.find("<tr>")
    first_row_end = html.find("</tr>", first_row_start)
    first_row_html = html[first_row_start:first_row_end]
    cell_count = first_row_html.count("<td")
    
    print(f"\nFirst row has {cell_count} cells (should be 4)")
    
    # Check if first cell has content
    if "&nbsp;" in first_row_html:
        print("PASS: First cell (empty) has &nbsp; placeholder")
    else:
        print("FAIL: First cell might not render properly")
    
    print("\n" + "="*50)
    if all_passed:
        print("SUCCESS: All border fixes applied!")
        print("\nThe table should now:")
        print("  - Show borders on ALL cells including empty ones")
        print("  - Display the first column properly")
        print("  - Have consistent cell widths")
    else:
        print("FAILED: Some fixes missing")
    
    # Save for inspection
    with open("fixed_table.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Fixed Table</title>
        </head>
        <body style="font-family: 'Bookman Old Style', serif; padding: 20px;">
            <h2>Table with Border Fix</h2>
            {html}
        </body>
        </html>
        """)
    print("\nFixed HTML saved to: fixed_table.html")

if __name__ == "__main__":
    test_border_fix()
