from src.ui.issue_card import IssueCard
from PyQt6.QtWidgets import QApplication
import sys

def verify_placeholder_mapping():
    app = QApplication(sys.argv)
    
    # Template with Excel-like table and a placeholder in text
    template = {
        "issue_name": "Test Issue",
        "tables": {
            "rows": 2,
            "cols": 2,
            "cells": [
                ["Header", "Value"],
                ["Label", "100"]
            ]
        },
        "templates": {
            "brief_facts": "The value is {{B2}}."
        }
    }
    
    card = IssueCard(template)
    
    # Check if B2 is in variables
    print(f"Variables keys: {list(card.variables.keys())}")
    
    # Check editor content
    editor_text = card.editor.toPlainText()
    print(f"Editor Text: '{editor_text}'")
    
    if "100" in editor_text:
        print("PASS: Placeholder replaced correctly")
    else:
        print("FAIL: Placeholder NOT replaced")

if __name__ == "__main__":
    verify_placeholder_mapping()
