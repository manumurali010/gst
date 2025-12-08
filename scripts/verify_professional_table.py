from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication
import sys

def verify_professional_table():
    app = QApplication(sys.argv)
    
    # Create issue card with sample data matching user's screenshot
    template = {
        "issue_id": "test",
        "issue_name": "GSTR Mismatch",
        "tables": {
            "rows": 4,
            "cols": 4,
            "cells": [
                ["", "CGST", "SGST", "IGST"],
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
    
    print("=== TABLE HTML FORMATTING VERIFICATION ===\n")
    
    # Check for professional formatting features
    checks = [
        ("border: 2px solid #000" in html, "Outer border (2px)"),
        ("border: 1px solid #000" in html, "Cell borders (1px)"),
        ("padding: 10px" in html, "Cell padding (10px)"),
        ("background-color: #e8e8e8" in html, "Header background color"),
        ("font-weight: bold" in html, "Bold headers"),
        ("text-align: center" in html, "Centered column headers"),
        ("text-align: right" in html, "Right-aligned numbers"),
        ("text-align: left" in html, "Left-aligned text"),
        ("border-collapse: collapse" in html, "Collapsed borders"),
        ("Bookman Old Style" in html, "Professional font"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {desc}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("SUCCESS: All formatting checks passed!")
        print("\nThe table will now have:")
        print("  - Professional borders on every cell")
        print("  - Centered, bold headers with gray background")
        print("  - Right-aligned numbers, left-aligned text")
        print("  - Proper spacing and padding")
        print("  - Bookman Old Style font matching DRC-01A")
    else:
        print("FAILED: Some checks did not pass")
    
    # Save sample HTML for inspection
    with open("sample_table.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Sample Table</title>
        </head>
        <body style="font-family: 'Bookman Old Style', serif; padding: 20px;">
            {html}
        </body>
        </html>
        """)
    print("\nSample HTML saved to: sample_table.html")
    print("Open this file in a browser to preview the table formatting.")

if __name__ == "__main__":
    verify_professional_table()
