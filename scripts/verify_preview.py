from src.ui.developer.issue_manager import IssueManager
from PyQt6.QtWidgets import QApplication
import sys

def verify_preview():
    app = QApplication(sys.argv)
    
    manager = IssueManager()
    manager.create_new_issue()
    
    # Set some dummy data
    manager.issue_name_input.setText("Preview Test")
    manager.brief_facts_editor.setHtml("Facts")
    
    # Trigger Preview
    manager.refresh_preview()
    
    # Check if widget added
    if manager.preview_layout.count() > 0:
        widget = manager.preview_layout.itemAt(0).widget()
        if widget and widget.__class__.__name__ == "IssueCard":
            print("PASS: IssueCard created in preview")
        else:
            print(f"FAIL: Unexpected widget in preview: {widget}")
    else:
        print("FAIL: No widget in preview")

if __name__ == "__main__":
    verify_preview()
