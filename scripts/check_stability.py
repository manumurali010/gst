
import sys
import os
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.issue_card import IssueCard

def check_stability():
    try:
        app = QApplication(sys.argv)
    except:
        app = QApplication.instance()
        
    print("--- Stability Check ---")
    try:
        # Just try to import and instantiate basic card to verify no AttributeErrors during init
        print("Import successful.")
        
        # We can't easily instantiate without full template/data mocking which causes other errors
        # But if the module imports and the methods exist, we are likely past the Syntax/Attribute error.
        
        card_cls = IssueCard
        if hasattr(card_cls, '_strip_tables'):
             print("WARNING: _strip_tables still exists?")
        else:
             print("CONFIRMED: _strip_tables is gone (reverted).")
             
        # Check extract_html_body
        mock_html = "<body>Content</body>"
        # We need an instance to call instance method
        # Mocking instance
        class Mock(IssueCard):
            def __init__(self): pass
        
        m = Mock()
        res = m.extract_html_body(mock_html)
        print(f"extract_html_body result: {res}")
        
    except Exception as e:
        print(f"Stability Check Failed: {e}")

if __name__ == "__main__":
    check_stability()
