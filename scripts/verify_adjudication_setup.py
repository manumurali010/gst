import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.getcwd())

from src.ui.proceedings_workspace import ProceedingsWorkspace

class TestAdjudicationSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)

    @patch('src.ui.proceedings_workspace.AdjudicationSetupDialog')
    def test_setup_dialog_launch(self, mock_dialog_cls):
        print("\nTesting Adjudication Setup Workflow...")
        
        # Mock Dialog Success
        mock_dlg_instance = mock_dialog_cls.return_value
        mock_dlg_instance.exec.return_value = True
        mock_dlg_instance.selected_section = "74"
        
        # Mock DB
        mock_db = MagicMock()
        # Initial state: Adjudication case but no section set
        initial_data = {
            'id': 'ADJ-101',
            'is_adjudication': True,
            'adjudication_section': None,
            'gstin': 'test_gstin',
            'legal_name': 'Test User'
        }
        mock_db.get_proceeding.return_value = initial_data
        mock_db.update_adjudication_case.return_value = True
        
        # Init Workspace
        workspace = ProceedingsWorkspace(proceeding_id="ADJ-101", navigate_callback=lambda x: None)
        workspace.db = mock_db
        
        # Call load_proceeding
        workspace.load_proceeding("ADJ-101")
        
        # 1. Verify Dialog Launched
        mock_dialog_cls.assert_called()
        print("SUCCESS: Setup Dialog launched.")
        
        # 2. Verify DB Update
        mock_db.update_adjudication_case.assert_called_with("ADJ-101", {'adjudication_section': '74'})
        print("SUCCESS: Section 74 saved to DB.")
        
        # 3. Verify Local Data Update
        self.assertEqual(workspace.proceeding_data['adjudication_section'], "74")
        print("SUCCESS: Local data updated.")
        
        # 4. Verify SCN Rendering uses section
        # Mock inputs
        workspace.scn_date_input = MagicMock()
        workspace.scn_date_input.date.return_value.toString.return_value = "01/01/2026"
        workspace.scn_oc_input = MagicMock()
        workspace.scn_oc_input.text.return_value = "SCN/001"
        workspace.scn_no_input = MagicMock()
        workspace.scn_no_input.text.return_value = "SCN/REF/001"
        
        html = workspace.render_scn()
        self.assertIn("74", html) # Should contain "74" from the logic
        print("SUCCESS: SCN rendered with Section 74 logic.")

if __name__ == "__main__":
    unittest.main()
