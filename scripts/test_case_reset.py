
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock PyQt6 modules BEFORE importing ui
# Define a simple base class for QWidget to preserve method definitions in subclasses
class MockBase:
    def __init__(self, *args, **kwargs): pass
    def setVisible(self, v): pass
    def setEnabled(self, v): pass
    def setText(self, t): pass
    def setCurrentIndex(self, i): pass
    # Handle all other QWidget method calls gracefully
    def __getattr__(self, name):
        return MagicMock()


pyqt6 = MagicMock()
sys.modules["PyQt6"] = pyqt6
sys.modules["PyQt6.QtWidgets"] = MagicMock()
# IMPORTANT: Replace QWidget with a real class so ScrutinyTab attributes aren't masked by MagicMock
sys.modules["PyQt6.QtWidgets"].QWidget = MockBase
sys.modules["PyQt6.QtCore"] = MagicMock()
sys.modules["PyQt6.QtGui"] = MagicMock()
sys.modules["PyQt6.QtWebEngineWidgets"] = MagicMock()
sys.modules["PyQt6.QtPrintSupport"] = MagicMock()

# Inject into PyQt6 mock so 'from PyQt6.QtPrintSupport import ...' works?
# No, sys.modules is enough for 'import ...'. 
# But 'from PyQt6.QtCore import QDate' requires QDate to be on the module mock.
sys.modules["PyQt6.QtCore"].QDate.currentDate.return_value.addDays.return_value = "MockDate+30"

# Add gst (project root) to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.ui.scrutiny_tab import ScrutinyTab

class TestCaseReset(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        
        # Patch __init__ to skip UI setup
        with patch.object(ScrutinyTab, '__init__', return_value=None):
            self.tab = ScrutinyTab()
            self.tab.db = self.mock_db
        
        # Inject Mock Widgets referenced in reset_ui_state
        self.tab.scrutiny_results = ["OLD DATA"]
        self.tab.current_case_id = "OLD_CASE_ID"
        self.tab.case_state = "ANALYZED" # OLD STATE
        self.tab.file_paths = {"old": "path"}
        self.tab.current_case_data = {"some": "data"} # Ensure this is cleared
        self.tab.current_adj_id = "ADJ_ID"
        
        self.tab.compliance_dashboard = MagicMock()
        self.tab.case_info_lbl = MagicMock()
        self.tab.gstin_combo = MagicMock()
        self.tab.details_frame = MagicMock()
        self.tab.recent_container = MagicMock()
        self.tab.analyze_btn = MagicMock()
        self.tab.asmt_preview = MagicMock()
        self.tab.header_lbl = MagicMock() 
        self.tab.results_filter = MagicMock() 
        
        # Inputs
        self.tab.oc_num_input = MagicMock()
        self.tab.notice_date_edit = MagicMock()
        self.tab.reply_date_edit = MagicMock()
        self.tab.finalize_btn = MagicMock()
        self.tab.summary_strip = MagicMock()
        self.tab.results_area = MagicMock()
        # Mock layout for results_area
        self.tab.results_area.layout.return_value = MagicMock()

    def test_reset_ui_state_full(self):
        print("Testing Full UI Reset...")
        
        # Act
        self.tab.reset_ui_state(full=True)
        
        # Assert Data & Lifecycle Cleared
        self.assertEqual(self.tab.scrutiny_results, [], "scrutiny_results should be empty")
        self.assertIsNone(self.tab.current_case_id, "current_case_id should be None")
        self.assertEqual(len(self.tab.file_paths), 0, "file_paths should be empty")
        self.assertEqual(self.tab.case_state, "INIT", "case_state should be reset to INIT")
        
        # Assert Signal Disconnect (check if disconnect was called)
        self.tab.asmt_preview.loadFinished.disconnect.assert_called()
        self.tab.results_area.issueSelected.disconnect.assert_called()
        
        # Assert UI Resets
        self.tab.compliance_dashboard.reset_all.assert_called_once()
        self.tab.case_info_lbl.setText.assert_called_with("No Case Selected")
        # clear_results might be called multiple times (via clear_results_view and explicit reset), which is fine
        self.tab.results_area.clear_results.assert_called()
        self.tab.results_area.layout().update.assert_called()
        
        # Assert WebEngine Reset
        # Checking if setUrl was called with a QUrl
        # Since we mocked PyQt6.QtCore, QUrl is a mock. We can just check setUrl call count.
        self.tab.asmt_preview.setUrl.assert_called()
        self.tab.asmt_preview.history().clear.assert_called()
        
        # Assert Unlocks
        self.tab.oc_num_input.setEnabled.assert_called_with(True)
        self.tab.oc_num_input.clear.assert_called_once()
        self.tab.finalize_btn.setEnabled.assert_called_with(False) # Should be FALSE now per updated logic
        
        # Verify deeper reset of dashboard cards
        # Since we mocked compliance_dashboard in setUp, we can't easily check internal card calls 
        # unless we unmock it or check if reset_all was called (which we did).
        # We assume the unit test logic for reset_all -> card.reset() holds if the code is correct.
        
        print("Reset Logic Verified Successfully.")

if __name__ == '__main__':
    unittest.main()
