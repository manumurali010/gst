import sys
import os
import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.getcwd())

from src.ui.proceedings_workspace import ProceedingsWorkspace

class TestHydrationFixed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create App instance
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_missing_case_handling(self):
        print("\nTesting Missing Case Hydration...")
        workspace = ProceedingsWorkspace(proceeding_id=None, navigate_callback=lambda x: None)
        
        # Mock DB
        mock_db = MagicMock()
        mock_db.get_proceeding.return_value = None # Simulate missing case
        workspace.db = mock_db
        
        # Test load_proceeding
        print("Calling load_proceeding('INVALID_ID')...")
        workspace.load_proceeding('INVALID_ID')
        
        # Assertions
        print(f"is_hydrated: {workspace.is_hydrated}")
        print(f"proceeding_data: {workspace.proceeding_data}")
        
        self.assertFalse(workspace.is_hydrated, "Should be unhydrated")
        self.assertEqual(workspace.proceeding_data, {}, "Should be empty dict, not None")
        
        # Test Preview Trigger (Should not crash)
        print("Calling update_preview()...")
        try:
            workspace.update_preview()
            print("update_preview() finished without error.")
        except Exception as e:
            self.fail(f"update_preview crashed: {e}")
            
        # Test Render method directly
        print("Calling generate_drc01a_html()...")
        html = workspace.generate_drc01a_html()
        print(f"Result: {html}")
        self.assertIn("No Case Data", html)

if __name__ == "__main__":
    unittest.main()
