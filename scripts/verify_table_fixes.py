from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication
import sys

def verify_table_updates():
    app = QApplication(sys.argv)
    
    # Create issue card with table
    template = {
        "issue_id": "test",
        "issue_name": "Test Issue",
        "tables": {
            "rows": 3,
            "cols": 3,
            "cells": [
                ["Item", "Qty", "Total"],
                ["Product A", "10", "=B2*100"],
                ["Product B", "20", "=B3*100"]
            ]
        },
        "templates": {
            "brief_facts": "Test facts"
        }
    }
    
    card = IssueCard(template)
    
    # Track signal emissions
    signal_count = [0]
    def on_values_changed(data):
        signal_count[0] += 1
        print(f"Signal emitted #{signal_count[0]}")
    
    card.valuesChanged.connect(on_values_changed)
    
    # Simulate changing a value
    print("Changing cell B2 from '10' to '15'...")
    item = card.table.item(1, 1)
    if item:
        item.setText("15")
    
    # Check if signal was emitted
    if signal_count[0] > 0:
        print(f"PASS: valuesChanged signal emitted {signal_count[0]} time(s)")
    else:
        print("FAIL: valuesChanged signal NOT emitted")
    
    # Check table HTML
    html = card.generate_html()
    
    # Check for improved styling
    checks = [
        ("font-size: 10pt" in html, "Font size specified"),
        ("Bookman Old Style" in html, "Bookman font specified"),
        ("cellpadding=\"8\"" in html, "Proper cell padding"),
        ("text-align: right" in html, "Number alignment"),
    ]
    
    print("\nTable HTML Formatting Checks:")
    for passed, desc in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {desc}")

if __name__ == "__main__":
    verify_table_updates()
