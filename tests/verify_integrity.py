import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import sqlite3

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock PyQt6
class MockPackage(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__path__ = []

sys.modules['PyQt6'] = MockPackage()
sys.modules['PyQt6.QtWidgets'] = MockPackage()
sys.modules['PyQt6.QtCore'] = MockPackage()
sys.modules['PyQt6.QtGui'] = MockPackage()

from src.database.db_manager import DatabaseManager, ConcurrencyError
from src.utils.constants import WorkflowStage
from src.database.schema import init_db

class VerifyIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        init_db(cls.db_path)
        cls.db = DatabaseManager(db_path=cls.db_path)
        
        # Create a test proceeding
        cls.pid = cls.db.create_proceeding({
            "gstin": "TEST44444444444",
            "legal_name": "Integrity Test Corp",
            "financial_year": "2023-24",
            "form_type": "ASMT-10"
        }, source_type='SCRUTINY')

    @classmethod
    def tearDownClass(cls):
        cls.db = None
        os.close(cls.db_fd)
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def test_workflow_stage_check_constraint(self):
        """Verify that illegal workflow_stage values are blocked by CHECK constraint"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 999 is not in (10, 20, 30, 40, 50, 60, 70, 75, 80)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "CHECK constraint failed"):
            cursor.execute("UPDATE proceedings SET workflow_stage = 999 WHERE id = ?", (self.pid,))
        
        conn.close()

    def test_forward_only_trigger(self):
        """Verify that backward workflow_stage updates are blocked by TRIGGER"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Set to SCN_ISSUED (60)
        cursor.execute("UPDATE proceedings SET workflow_stage = 60 WHERE id = ?", (self.pid,))
        conn.commit()
        
        # Try to move back to SCN_DRAFT (50)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "Illegal Backward Transition"):
            cursor.execute("UPDATE proceedings SET workflow_stage = 50 WHERE id = ?", (self.pid,))
            
        conn.close()

    def test_optimistic_locking_concurrency(self):
        """Verify that version_no mismatch raises ConcurrencyError"""
        # Get current version (should be 1 or higher)
        p_data = self.db.get_proceeding(self.pid)
        current_version = p_data['version_no']
        
        # Success Update (Correct Version)
        self.db.update_proceeding(self.pid, {"status": "Updated Once"}, version_no=current_version)
        
        # Check version incremented to current_version + 1
        new_data = self.db.get_proceeding(self.pid)
        self.assertEqual(new_data['version_no'], current_version + 1)
        
        # Collision: Try updating with same OLD version (Stale)
        with self.assertRaises(ConcurrencyError):
            self.db.update_proceeding(self.pid, {"status": "Collision Update"}, version_no=current_version)

    def test_atomic_increment(self):
        """Verify that version_no increments atomically on every update"""
        p_data = self.db.get_proceeding(self.pid)
        v1 = p_data['version_no']
        
        self.db.update_proceeding(self.pid, {"legal_name": "Incr Test"})
        v2 = self.db.get_proceeding(self.pid)['version_no']
        self.assertEqual(v2, v1 + 1)
        
        self.db.update_proceeding(self.pid, {"trade_name": "Incr Test 2"})
        v3 = self.db.get_proceeding(self.pid)['version_no']
        self.assertEqual(v3, v2 + 1)

if __name__ == "__main__":
    unittest.main()
