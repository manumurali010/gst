
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Mocking modules that might depend on UI resources not available in headless
from src.ui.issue_card import IssueCard

class TestIssueCardLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # QApplication is needed for QWidgets
        cls.app = QApplication([])

    def test_scn_mode_persistence(self):
        """Test that SCN mode preserves DRC-01A content and vice versa"""
        
        # 1. Simulate existing data from DB (saved DRC-01A)
        initial_data = {
            'issue_id': 'TEST_01',
            'variables': {'var1': '100'},
            'content': '<p>DRC-01A Content</p>',
            'tax_breakdown': {}
        }
        
        template = {
            'issue_id': 'TEST_01',
            'issue_name': 'Test Issue',
            'variables': {'var1': '0'}
        }
        
        print("Initializing IssueCard in SCN mode...")
        # 2. Load into Card in SCN Mode
        card_scn = IssueCard(template, mode="SCN", content_key="scn_content")
        card_scn.load_data(initial_data)
        
        # Verify content detected (should be empty initially for SCN if not in data)
        # Verify content detected (should be default text initially for SCN if not in data)
        self.assertIn("No SCN specific template defined", card_scn.editor.toPlainText(), "SCN content should show default if not in data")
        
        # 3. User Edits SCN Content
        print("Editing SCN content...")
        new_scn_content = "<p>My SCN Draft</p>"
        card_scn.editor.setHtml(new_scn_content)
        
        # 4. Save Data
        saved_data = card_scn.get_data()
        print(f"Saved Data: {saved_data}")
        
        # 5. Verify Persistence
        self.assertEqual(saved_data['content'], '<p>DRC-01A Content</p>', "DRC-01A content should be preserved")
        self.assertIn(new_scn_content, saved_data['scn_content'], "SCN content should be saved")
        self.assertEqual(saved_data['variables'], {'var1': '100'}, "Variables should be preserved/loaded")

    def test_drc01a_mode_persistence(self):
        """Test that DRC-01A mode preserves SCN content"""
        
        # 1. Simulate existing data (Mixed)
        initial_data = {
            'issue_id': 'TEST_01',
            'variables': {'var1': '100'},
            'content': '<p>Old DRC Content</p>',
            'scn_content': '<p>Important SCN Draft</p>',
            'tax_breakdown': {}
        }
        
        template = {'issue_id': 'TEST_01'}
        
        print("Initializing IssueCard in DRC-01A mode...")
        # 2. Load into Card in default Mode
        card = IssueCard(template) # Default mode="DRC-01A", content_key="content"
        card.load_data(initial_data)
        
        # Verify Editor loaded DRC content
        # Verify Editor loaded DRC content
        # setHtml wraps content, so we check if our content is present
        self.assertIn('Old DRC Content', card.editor.toHtml())
        
        # 3. Edit DRC Content
        new_drc = "<p>New DRC Content</p>"
        card.editor.setHtml(new_drc)
        
        # 4. Save
        saved_data = card.get_data()
        
        # 5. Verify
        self.assertIn(new_drc, saved_data['content'], "DRC content updated")
        self.assertEqual(saved_data['scn_content'], '<p>Important SCN Draft</p>', "SCN content preserved")

if __name__ == '__main__':
    unittest.main()
