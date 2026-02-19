import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import sqlite3

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Better Mocking for PyQt6
class MockPackage(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__path__ = []

mock_pyqt6 = MockPackage()
sys.modules['PyQt6'] = mock_pyqt6
sys.modules['PyQt6.QtWidgets'] = MockPackage()
sys.modules['PyQt6.QtCore'] = MockPackage()
sys.modules['PyQt6.QtGui'] = MockPackage()
sys.modules['PyQt6.QtWebEngineWidgets'] = MockPackage()
sys.modules['PyQt6.QtWebEngineCore'] = MockPackage()
sys.modules['PyQt6.QtPrintSupport'] = MockPackage()

# Mock the base class QWidget
class MockQWidget:
    def __init__(self, *args, **kwargs): pass
    def setStyleSheet(self, *args): pass
    def setObjectName(self, *args): pass
    def setLayout(self, *args): pass
    def setContentsMargins(self, *args): pass
    def setVisible(self, *args): pass
    def show(self): pass
    def hide(self): pass
    def setEnabled(self, *args): pass
    def setToolTip(self, *args): pass
    def objectName(self): return "MockWorkspace"

with patch('PyQt6.QtWidgets.QWidget', MockQWidget):
    from src.database.db_manager import DatabaseManager
    from src.utils.constants import WorkflowStage
    from src.ui.proceedings_workspace import ProceedingsWorkspace

class VerifyPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a temporary database for testing
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.db = DatabaseManager(db_path=cls.db_path)
        cls.db.init_sqlite()
        
        # Create a fresh test proceeding using the correct API
        cls.pid = cls.db.create_proceeding({
            "gstin": "TEST33333333333",
            "legal_name": "Test Phase 3 Corp",
            "financial_year": "2023-24",
            "form_type": "ASMT-10",
            "status": "Scrutiny Active",
            "additional_details": {"drc01a_skipped": False}
        }, source_type='SCRUTINY')
        
        print(f"DEBUG: Created Test Proceeding PID: {cls.pid}")

    @classmethod
    def tearDownClass(cls):
        # We don't have a direct close() for DatabaseManager, but let's try to ensure no connections remain
        cls.db = None
        os.close(cls.db_fd)
        try:
            if os.path.exists(cls.db_path):
                os.remove(cls.db_path)
        except Exception as e:
            print(f"Cleanup Warning: {e}")

    def setUp(self):
        # Instantiate workspace
        with patch.object(ProceedingsWorkspace, 'init_ui'):
            self.workspace = ProceedingsWorkspace(navigate_callback=lambda x: None, proceeding_id=self.pid)
            self.workspace.db = self.db
            
            # Mock UI updates to silence errors
            self.workspace.update_summary_tab = MagicMock()
            self.workspace.check_existing_documents = MagicMock()
            self.workspace.evaluate_scn_workflow_phase = MagicMock()
            self.workspace.restore_draft_state = MagicMock()
            self.workspace.context_title_lbl = MagicMock()
            # Mock UI elements that might be accessed
            self.workspace.scn_no_input = MagicMock()
            self.workspace.issue_cards = []
        
        # Reset state to ASMT10_DRAFT for standard path
        self.db.update_proceeding(self.pid, {
            "workflow_stage": int(WorkflowStage.ASMT10_DRAFT), 
            "drc01a_skipped": 0
        })
        self.workspace.load_proceeding(self.pid)

    def test_illegal_backward_transition(self):
        """Verify that moving backward raises ValueError"""
        # Move forward LEGALLY: DRAFT -> ISSUED -> SCN_DRAFT -> SCN_ISSUED
        self.workspace.transition_to(WorkflowStage.ASMT10_ISSUED)
        self.workspace.transition_to(WorkflowStage.SCN_DRAFT)
        self.workspace.transition_to(WorkflowStage.SCN_ISSUED)
        
        # Try to move backward to SCN_DRAFT (Forbidden)
        with self.assertRaises(ValueError) as cm:
            self.workspace.transition_to(WorkflowStage.SCN_DRAFT)
        self.assertIn("Illegal Backward Transition", str(cm.exception))

    def test_invalid_matrix_transition(self):
        """Verify that jump-over transitions are blocked"""
        with self.assertRaises(ValueError) as cm:
            self.workspace.transition_to(WorkflowStage.ORDER_ISSUED)
        self.assertIn("Invalid Transition", str(cm.exception))

    def test_skip_logic_enforcement(self):
        """Verify that DRC01A_DRAFT -> SCN_DRAFT requires drc01a_skipped=True"""
        # Set to DRC01A_DRAFT
        self.db.update_proceeding(self.pid, {
            "workflow_stage": int(WorkflowStage.DRC01A_DRAFT), 
            "drc01a_skipped": 0
        })
        self.workspace.load_proceeding(self.pid)
        
        with self.assertRaises(ValueError) as cm:
            self.workspace.transition_to(WorkflowStage.SCN_DRAFT)
        self.assertIn("Illegal Skip", str(cm.exception))
        
        # Now set skip and try again
        self.db.update_proceeding(self.pid, {"drc01a_skipped": 1})
        self.workspace.load_proceeding(self.pid)
        self.workspace.transition_to(WorkflowStage.SCN_DRAFT)
        self.assertEqual(self.workspace.get_current_stage(), WorkflowStage.SCN_DRAFT)

    def test_ph_lifecycle_sequence(self):
        """Verify mandatory PH_COMPLETED before ORDER_ISSUED"""
        # Start at SCN_ISSUED (Legal Path)
        self.db.update_proceeding(self.pid, {"workflow_stage": int(WorkflowStage.ASMT10_ISSUED)})
        self.workspace.load_proceeding(self.pid)
        self.workspace.transition_to(WorkflowStage.SCN_DRAFT)
        self.workspace.transition_to(WorkflowStage.SCN_ISSUED)
        
        # Try to jump to Order (Should fail)
        with self.assertRaises(ValueError):
            self.workspace.transition_to(WorkflowStage.ORDER_ISSUED)
            
        # Move to PH_SCHEDULED
        self.workspace.transition_to(WorkflowStage.PH_SCHEDULED)
        
        # Conclude PH (to PH_COMPLETED)
        self.workspace.transition_to(WorkflowStage.PH_COMPLETED)
        
        # Now Order should be allowed
        self.workspace.transition_to(WorkflowStage.ORDER_ISSUED)
        self.assertEqual(self.workspace.get_current_stage(), WorkflowStage.ORDER_ISSUED)

    def test_dual_update(self):
        """Verify status string is also updated"""
        # Setup valid state for SCN_ISSUED jump
        self.db.update_proceeding(self.pid, {"workflow_stage": int(WorkflowStage.SCN_DRAFT)})
        self.workspace.load_proceeding(self.pid)
        
        self.workspace.transition_to(WorkflowStage.SCN_ISSUED)
        
        # Check DB
        data = self.db.get_proceeding(self.pid)
        self.assertEqual(data['status'], "SCN Issued")

if __name__ == "__main__":
    unittest.main()
