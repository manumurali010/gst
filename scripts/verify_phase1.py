import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock PyQt6 before imports
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

# Import the class to test
# We need to bypass actual imports of UI components that might fail in headless
with patch('src.ui.proceedings_workspace.RichTextEditor', MagicMock()), \
     patch('src.ui.proceedings_workspace.FinalizationPanel', MagicMock()), \
     patch('src.ui.proceedings_workspace.IssueCard', MagicMock()) as MockIssueCard:
     
    from src.ui.proceedings_workspace import ProceedingsWorkspace

    class TestPhase1(unittest.TestCase):
        def setUp(self):
            self.workspace = ProceedingsWorkspace(navigate_callback=MagicMock())
            self.workspace.issue_combo = MagicMock()
            self.workspace.issue_templates = {
                "test_issue": {"issue_id": "test_issue", "issue_name": "Test Issue"}
            }
            self.workspace.issues_layout = MagicMock()
            self.workspace.issue_cards = []
            self.workspace.calculate_grand_totals = MagicMock()

        def test_insert_selected_issue_instantiation(self):
            # 1. Setup
            self.workspace.issue_combo.currentData.return_value = "test_issue"
            
            # 2. Execute
            self.workspace.insert_selected_issue()
            
            # 3. Verify
            MockIssueCard.assert_called_with(
                {"issue_id": "test_issue", "issue_name": "Test Issue"}, 
                mode="DRC-01A"
            )
            self.assertEqual(len(self.workspace.issue_cards), 1)
            
            # Verify Signal Connections
            card = self.workspace.issue_cards[0]
            card.removeClicked.connect.assert_called_with(self.workspace.remove_issue_card)
            card.valuesChanged.connect.assert_called_with(self.workspace.calculate_grand_totals)
            
            # Verify Calculation trigger
            card.calculate_values.assert_called_once()
            self.workspace.calculate_grand_totals.assert_called()

        def test_signal_safety_in_restore(self):
            # Verify that restore_draft_state clears existing cards
            self.workspace.db = MagicMock()
            self.workspace.db.get_case_issues.return_value = []
            
            initial_card = MagicMock()
            self.workspace.issue_cards = [initial_card]
            
            self.workspace.restore_draft_state()
            
            initial_card.deleteLater.assert_called_once()
            self.assertEqual(len(self.workspace.issue_cards), 0)

    if __name__ == "__main__":
        unittest.main()
