from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
import sys

def verify_tax_aggregation():
    app = QApplication(sys.argv)
    
    # Create issue card with sample data
    # Table structure:
    # Row 0: Headers [Description, CGST, SGST, IGST]
    # Row 1: Data [GSTR 1, 100, 100, 0]
    # Row 2: Data [GSTR 3B, 80, 80, 0]
    # Row 3: Total [Difference, 20, 20, 0]
    
    template = {
        "issue_id": "test",
        "issue_name": "Tax Mismatch",
        "tables": {
            "rows": 4,
            "cols": 4,
            "cells": [
                ["Description", "CGST", "SGST", "IGST"],
                ["GSTR 1", "100", "100", "0"],
                ["GSTR 3B", "80", "80", "0"],
                ["Difference", "20", "20", "0"]
            ]
        }
    }
    
    card = IssueCard(template)
    
    print("=== TAX AGGREGATION VERIFICATION ===\n")
    
    # Test get_tax_breakdown
    breakdown = card.get_tax_breakdown()
    print("Breakdown extracted from Issue Card:")
    print(breakdown)
    
    # Expected values from last row (Difference)
    expected_cgst = 20.0
    expected_sgst = 20.0
    expected_igst = 0.0
    
    checks = [
        (breakdown['CGST']['tax'] == expected_cgst, f"CGST Tax should be {expected_cgst}"),
        (breakdown['SGST']['tax'] == expected_sgst, f"SGST Tax should be {expected_sgst}"),
        (breakdown['IGST']['tax'] == expected_igst, f"IGST Tax should be {expected_igst}"),
    ]
    
    all_passed = True
    for passed, desc in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {desc}")
        if not passed:
            all_passed = False
            
    print("\n" + "="*50)
    if all_passed:
        print("SUCCESS: Tax breakdown extraction works correctly!")
        print("The system will now automatically populate the Tax Demand table")
        print("using these values when this issue is added.")
    else:
        print("FAILED: Tax extraction incorrect")

if __name__ == "__main__":
    verify_tax_aggregation()
