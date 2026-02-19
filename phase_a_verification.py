import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDate
from src.ui.rich_text_editor import SCNTextEdit
from src.ui.components.grounds_forms import ScrutinyGroundsForm
from src.ui.issue_card import IssueCard

# We need a dummy application for PyQt widgets
app = QApplication(sys.argv)

class PhaseAStressTest(unittest.TestCase):
    def test_html_sanitizer(self):
        """Test 3: Rich Text Sanitizer Stress"""
        editor = SCNTextEdit()
        mso_html = """
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word">
        <head><style> p.MsoNormal { color: red; font-family: "Times New Roman"; } </style></head>
        <body>
            <p class="MsoNormal" style="margin-top:0in;margin-right:0in;margin-bottom:10.0pt;margin-left:0in;line-height:115%;">
                <b style="mso-bidi-font-weight:normal"><span style="font-size:12.0pt;line-weight:115%;font-family:Arial">
                    This is a bold Word paragraph.
                </span></b>
            </p>
            <table border="1"><tr><td>Word Table (Should be stripped)</td></tr></table>
            <script>alert('malicious')</script>
            <p><i>Italic text</i> and <u>Underline</u></p>
        </body>
        </html>
        """
        sanitized = editor.sanitize_html(mso_html)
        print("\n--- SANITIZER OUTPUT ---")
        print(sanitized)
        print("------------------------")
        
        # Check for core tags and content (allowing for whitespace/structural variants)
        self.assertIn("<b>", sanitized)
        self.assertIn("This is a bold Word paragraph", sanitized)
        self.assertIn("<i>Italic text</i>", sanitized)
        self.assertIn("<u>Underline</u>", sanitized)
        
        # Verify strict stripping
        self.assertNotIn("<table", sanitized)
        self.assertNotIn("<script", sanitized)
        self.assertNotIn("MsoNormal", sanitized)
        self.assertNotIn("style=", sanitized)
        self.assertNotIn("xmlns=", sanitized)

    def test_date_validation(self):
        """Test 4: Date Mutation Tests"""
        form = ScrutinyGroundsForm()
        
        # Scenario: Reply Received = True, but Date is earlier than ASMT-10
        form.check_reply_received.setChecked(True)
        form.input_asmt_date.setDate(QDate(2025, 1, 10))
        form.input_reply_date.setDate(QDate(2025, 1, 5)) # INVALID: Before ASMT
        
        errors = form.validate()
        print(f"\n--- DATE VALIDATION ERRORS (ASMT: 10th, Reply: 5th) ---")
        for e in errors: print(f"  [x] {e}")
        self.assertTrue(any("earlier than ASMT-10" in e for e in errors))

    def test_negative_demand_validation(self):
        """Test 5: Negative Demand Reload Test"""
        dummy_template = {
            "title": "Test Issue",
            "grid_data": {
                "columns": ["Particulars", "CGST", "SGST", "IGST"],
                "rows": [
                    {"Particulars": "Tax", "cgst": 0, "sgst": 0, "igst": 0}
                ]
            }
        }
        card = IssueCard(template=dummy_template)
        card.init_ui()
        
        # Simulate negative input in the table
        item = card.table.item(0, 3) 
        if not item:
            from PyQt6.QtWidgets import QTableWidgetItem
            item = QTableWidgetItem("-500.00")
            card.table.setItem(0, 3, item)
        else:
            item.setText("-500.00")
            
        is_valid = card.validate_tax_inputs(show_ui=False)
        print(f"\n--- NEGATIVE DEMAND VALIDATION (Value: -500) ---")
        print(f"  [x] Valid: {is_valid}")
        self.assertFalse(is_valid)

if __name__ == "__main__":
    unittest.main()
