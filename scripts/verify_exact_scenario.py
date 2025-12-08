from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication
import sys

def verify_exact_scenario():
    app = QApplication(sys.argv)
    
    # EXACT data from screenshot
    # Row 0: [Empty], "CGST", "SGST", "IGST"
    # Row 3: "DIFFERENCE", "23105.0", "22.0", "0"
    
    template = {
        "issue_id": "test",
        "issue_name": "GSTR Mismatch",
        "tables": {
            "rows": 4,
            "cols": 4,
            "cells": [
                ["", "CGST", "SGST", "IGST"],  # First cell EMPTY
                ["GSTR 1", "2561", "2546", "0"],
                ["GSTR 3B", "25666", "25668", "0"],
                ["DIFFERENCE", "23105.0", "22.0", "0"]
            ]
        }
    }
    
    card = IssueCard(template)
    
    print("=== EXACT SCENARIO VERIFICATION ===\n")
    
    breakdown = card.get_tax_breakdown()
    print("Breakdown extracted:")
    print(breakdown)
    
    # Check if it captured the values despite empty header
    cgst = breakdown['CGST']['tax']
    sgst = breakdown['SGST']['tax']
    
    print(f"\nCGST Tax: {cgst} (Expected: 23105.0)")
    print(f"SGST Tax: {sgst} (Expected: 22.0)")
    
    if cgst == 23105.0 and sgst == 22.0:
        print("\nSUCCESS: Extraction works even with empty first header.")
    else:
        print("\nFAILED: Extraction failed.")

if __name__ == "__main__":
    verify_exact_scenario()
