
import sys
print("DEBUG: Script Starting...")
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget
from PyQt6.QtCore import Qt

# Adjust path to import src
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MOCK WIDGETS ---
class MockWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.reset_all = MagicMock()
        self.clear_results = MagicMock()
        self.set_state = MagicMock()
        self.update_summary = MagicMock()
        self.set_active = MagicMock()
        # Signals
        self.clicked = MagicMock()
        self.clicked.connect = MagicMock()

# Inject MockWidgets into sys.modules
sys.modules['src.ui.components.side_nav_card'] = MagicMock()
sys.modules['src.ui.components.side_nav_card'].SideNavCard = MockWidget

sys.modules['src.ui.components.compliance_dashboard'] = MagicMock()
sys.modules['src.ui.components.compliance_dashboard'].ComplianceDashboard = MockWidget

sys.modules['src.ui.components.results_container'] = MagicMock()
sys.modules['src.ui.components.results_container'].ResultsContainer = MockWidget

sys.modules['src.ui.components.analysis_summary_strip'] = MagicMock()
sys.modules['src.ui.components.analysis_summary_strip'].AnalysisSummaryStrip = MockWidget

sys.modules['src.ui.components.dynamic_upload_group'] = MagicMock()
sys.modules['src.ui.components.dynamic_upload_group'].DynamicUploadGroup = MockWidget

sys.modules['src.ui.rich_text_editor'] = MagicMock()
sys.modules['src.ui.rich_text_editor'].RichTextEditor = MockWidget


from src.ui.issue_card import IssueCard
from src.ui.scrutiny_tab import ScrutinyTab

class TestSOP5Fixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create App instance
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()


    def test_issue_card_rendering_sop5(self):
        """Verify IssueCard renders multiple tables from list (Logic Check)"""
        print("\n[TEST] Testing IssueCard SOP-5 List Support (Logic)...")
        try:
            # SOP-5 Payload
            tables_payload = [
                {"title": "Table 1", "rows": [], "columns": []},
                {"title": "Table 2", "rows": [], "columns": []}
            ]
            
            template = {
                "issue_id": "SOP-5",
                "tables": tables_payload,
                "variables": {}
            }
            
            # Mock init_grid_ui to avoid actual rendering crash
            with patch.object(IssueCard, 'init_grid_ui') as mock_init_grid:
                with patch.object(IssueCard, 'init_excel_table_ui'): # Ensure not called
                    card = IssueCard(template)
                
                print(f"DEBUG: init_grid_ui called {mock_init_grid.call_count} times")
                self.assertEqual(mock_init_grid.call_count, 2, "init_grid_ui should be called twice")
                
                # Verify args
                # call_args_list items are (args, kwargs)
                # We expect data=tables_payload[0] and [1]
                calls = mock_init_grid.call_args_list
                
                # Check call 1
                args1, kwargs1 = calls[0]
                # init_grid_ui(layout, data=...)
                self.assertEqual(kwargs1.get('data'), tables_payload[0], "First call should pass Table 1")
                
                # Check call 2
                args2, kwargs2 = calls[1]
                self.assertEqual(kwargs2.get('data'), tables_payload[1], "Second call should pass Table 2")

            print("[SUCCESS] IssueCard logic handles list-based tables.")
        except Exception as e:
            print(f"[FAIL] IssueCard Test Failed: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def test_persistence_fix(self):
        """Verify finalize_asmt_notice persists 'tables' key"""
        print("\n[TEST] Testing Persistence of 'tables' key...")
        try:
            # Setup Mock DB
            mock_db = MagicMock()
            mock_db.get_proceeding.return_value = {
                "legal_name": "Test Co", 
                "gstin": "ABC", 
                "financial_year": "2023-24",
                "additional_details": "{}",
                "taxpayer_details": {}
            }
            mock_db.finalize_proceeding_transaction.return_value = (True, "ADJ-123")
            mock_db.get_next_oc_number.return_value = "1/2024"
            
            tab = ScrutinyTab(mock_db)
            
            tab.current_case_id = "CASE-123"
            tab.current_case_data = {"gstin": "ABC", "financial_year": "2023-24", "legal_name": "Test Co"}
            tab.case_state = "ANALYZED"
            
            tab.oc_num_input = MagicMock()
            tab.oc_num_input.text.return_value = "OC/123"
            tab.notice_date_edit = MagicMock()
            tab.notice_date_edit.date().toString.return_value = "2024-01-01"
            tab.reply_date_edit = MagicMock()
            tab.reply_date_edit.date().toString.return_value = "2024-02-01"
            
            with patch('src.ui.scrutiny_tab.FinalizationConfirmationDialog') as MockDlg:
                instance = MockDlg.return_value
                instance.exec.return_value = 1 
                
                sop5_issue = {
                    "issue_id": "SOP-5",
                    "total_shortfall": 500,
                    "tables": [{"dummy": "data"}],
                    "grid_data": None
                }
                tab.scrutiny_results = [sop5_issue]
                
                tab.finalize_asmt_notice()
                
                call_args = mock_db.save_case_issues.call_args
                if not call_args:
                    self.fail("save_case_issues not called")
                
                issues_list = call_args[0][1]
                saved_item = issues_list[0] # {"issue_id":..., "data": {...}}
                
                # Check 'data' dict inside the saved item structure
                # The structure passed to save_case_issues is [{"issue_id":..., "data": {...}}]
                # My fix added 'tables' to that "data" dict.
                
                snapshot = saved_item['data']
                print(f"Saved Snapshot Keys: {snapshot.keys()}")
                
                self.assertIn('tables', snapshot, "'tables' key must be persisted")
                self.assertEqual(snapshot['tables'], [{"dummy": "data"}])
                
                print("[SUCCESS] 'tables' key persisted.")
                
        except Exception as e:
            print(f"[FAIL] Persistence Test Failed: {e}")
            import traceback
            traceback.print_exc()
            raise e

if __name__ == '__main__':
    unittest.main()
