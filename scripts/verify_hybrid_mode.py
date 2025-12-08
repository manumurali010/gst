from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication, QLineEdit
import sys

def verify_hybrid_mode():
    app = QApplication(sys.argv)
    
    # Template with BOTH Table and Placeholders
    template = {
        "issue_id": "test",
        "issue_name": "Hybrid Issue",
        "tables": {
            "rows": 2,
            "cols": 2,
            "cells": [["H1", "H2"], ["10", "20"]]
        },
        "placeholders": [
            {"name": "extra_field", "type": "string", "required": True}
        ],
        "templates": {
            "brief_facts": "Table says {{B2}}, Extra says {{extra_field}}."
        }
    }
    
    card = IssueCard(template)
    
    # 1. Check if Table exists
    if hasattr(card, 'table') and card.table.rowCount() == 2:
        print("PASS: Table created")
    else:
        print("FAIL: Table not created")
        
    # 2. Check if Placeholder Input exists
    if 'extra_field' in card.input_widgets:
        print("PASS: Placeholder input created")
        # Simulate input
        card.input_widgets['extra_field'].setText("ExtraValue")
        
        # Check variables
        if card.variables.get('extra_field') == "ExtraValue":
            print("PASS: Placeholder variable updated")
        else:
            print(f"FAIL: Placeholder variable mismatch: {card.variables.get('extra_field')}")
    else:
        print("FAIL: Placeholder input NOT created")

if __name__ == "__main__":
    verify_hybrid_mode()
