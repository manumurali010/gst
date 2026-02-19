
import sys
import os
import unittest

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.scn_generator import generate_intro_narrative
from src.ui.components.grounds_forms import ScrutinyGroundsForm
from PyQt6.QtWidgets import QApplication

# Create a global app instance for testing UI components
app = QApplication.instance() or QApplication(sys.argv)

class TestSCNGroundsGenerator(unittest.TestCase):
    
    def test_basic_generation(self):
        data = {
            "version": 1,
            "type": "scrutiny",
            "manual_override": False,
            "data": {
                "financial_year": "2023-24",
                "docs_verified": ["GSTR-1", "GSTR-3B"],
                "asmt10_ref": {
                    "oc_no": "OC/123",
                    "date": "2024-01-01",
                    "officer_designation": "Superintendent",
                    "office_address": "Kochi"
                },
                "reply_ref": {
                    "received": False
                }
            }
        }
        
        narrative = generate_intro_narrative(data)
        self.assertIn("2023-24", narrative)
        self.assertIn("GSTR-1, GSTR-3B", narrative)
        self.assertIn("OC/123", narrative)
        self.assertIn("Superintendent", narrative)
        self.assertIn("no reply has been received", narrative)

    def test_reply_received(self):
        data = {
            "manual_override": False,
            "data": {
                "financial_year": "2023-24",
                "reply_ref": {
                    "received": True,
                    "date": "2024-02-01"
                }
            }
        }
        narrative = generate_intro_narrative(data)
        # Expecting dd-MM-yyyy
        self.assertIn("reply dated <b>01-02-2024</b> have been received", narrative)

    def test_missing_data_omission(self):
        data = {
            "manual_override": False,
            "data": {}
        }
        narrative = generate_intro_narrative(data)
        # Omission test: Should not find brackets
        self.assertNotIn("[FINANCIAL YEAR]", narrative)
        self.assertNotIn("[ASMT-10 OC NO]", narrative)
        # Proper tags
        self.assertTrue(narrative.startswith("<p>"))
        self.assertTrue(narrative.endswith("</p>"))

    def test_manual_override(self):
        data = {
            "manual_override": True,
            "manual_text": "Custom narrative text here."
        }
        narrative = generate_intro_narrative(data)
        self.assertEqual(narrative, "Custom narrative text here.")

class TestSCNUXLogic(unittest.TestCase):
    def setUp(self):
        self.form = ScrutinyGroundsForm()

    def test_initial_state(self):
        self.assertFalse(self.form.is_intro_modified_by_user)
        self.assertIn("System-generated", self.form.lbl_status.text())

    def test_auto_regeneration_on_field_change(self):
        # 1. Set initial data
        self.form.input_asmt_oc.setText("OC/INITIAL")
        self.form.auto_regenerate()
        initial_text = self.form.manual_editor.toPlainText()
        self.assertIn("OC/INITIAL", initial_text)
        
        # 2. Change field -> Should trigger auto_regenerate (via signal)
        self.form.input_asmt_oc.setText("OC/CHANGED")
        # In a real event loop, this happens via signal. For unit test, we call it.
        self.form.auto_regenerate() 
        new_text = self.form.manual_editor.toPlainText()
        self.assertIn("OC/CHANGED", new_text)
        self.assertFalse(self.form.is_intro_modified_by_user)

    def test_manual_edit_stops_auto_regeneration(self):
        # 1. Set initial 
        self.form.input_asmt_oc.setText("OC/1")
        self.form.auto_regenerate()
        
        # 2. Manually edit
        self.form.manual_editor.setPlainText("USER CUSTOM TEXT")
        # Ensure flag flipped (textChanged signal)
        self.assertTrue(self.form.is_intro_modified_by_user)
        self.assertIn("Modified manually", self.form.lbl_status.text())
        
        # 3. Change field -> Should NOT regenerate
        self.form.input_asmt_oc.setText("OC/2")
        self.form.auto_regenerate()
        text_after_change = self.form.manual_editor.toPlainText()
        self.assertEqual(text_after_change, "USER CUSTOM TEXT")
        self.assertTrue(self.form.is_intro_modified_by_user)

    def test_regenerate_button_resets_state(self):
        # 1. Manually edit
        self.form.manual_editor.setHtml("<p>USER CUSTOM TEXT</p>")
        # Set some data that would be in the OC
        self.form.input_asmt_oc.setText("OC/TARGET")
        
        # 2. Click Regenerate (triggers _on_regenerate_clicked)
        self.form._on_regenerate_clicked()
        
        # 3. Verify
        current_text = self.form.manual_editor.toHtml()
        self.assertIn("OC/TARGET", current_text)
        self.assertNotIn("USER CUSTOM TEXT", current_text)
        self.assertFalse(self.form.is_intro_modified_by_user)

    def test_persistence_logic_html(self):
        # 1. Create a "Modified" state with HTML
        data = {
            "version": 1,
            "is_intro_modified_by_user": True,
            "manual_text": "<p>PERSISTED <b>BOLD</b> TEXT</p>",
            "data": { "financial_year": "2025-26" }
        }
        
        # 2. Load it
        self.form.set_data(data)
        self.assertTrue(self.form.is_intro_modified_by_user)
        self.assertIn("BOLD", self.form.manual_editor.toPlainText())
        
        # 3. Extract it (Sanitized)
        extracted = self.form.get_data()
        self.assertTrue(extracted["is_intro_modified_by_user"])
        # Should contain BOLD content. Qt might use span or b.
        # Just check for text and lack of style block.
        self.assertIn("BOLD", extracted["manual_text"])
        self.assertNotIn("<style", extracted["manual_text"])

    def test_legacy_plain_text_wrap(self):
        data = {
            "is_intro_modified_by_user": True,
            "manual_text": "PLAIN TEXT WITHOUT TAGS"
        }
        self.form.set_data(data)
        # Should contain the text and some p tag (Qt adds style attributes)
        self.assertIn("PLAIN TEXT WITHOUT TAGS", self.form.manual_editor.toHtml())
        self.assertIn("<p", self.form.manual_editor.toHtml().lower())

    def test_safe_body_extraction_case_insensitive(self):
        # Force a weird case-sensitive HTML internally
        raw = "<html><HEAD></HEAD><BODY>CASE TEST</BODY></html>"
        self.form.manual_editor.setHtml(raw)
        extracted = self.form._extract_clean_html()
        # Verify CASE TEST is present
        self.assertIn("CASE TEST", extracted)
        # Verify header junk is gone
        self.assertNotIn("<html>", extracted.lower())
        self.assertNotIn("<head>", extracted.lower())
        self.assertNotIn("<style", extracted.lower())
        # Verify it's within a p tag (Qt's representation)
        self.assertIn("<p", extracted.lower())

    def test_ghost_paragraph_prevention(self):
        self.form.manual_editor.setHtml("<p><br></p>")
        extracted = self.form._extract_clean_html()
        self.assertEqual(extracted, "")

if __name__ == '__main__':
    unittest.main()
