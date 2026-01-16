
import sys
import os
sys.path.append(os.getcwd()) # Ensure root is in path
import unittest
from PyQt6.QtWidgets import QApplication, QDialog, QAbstractItemView
from src.ui.scrutiny_tab import FinalizationConfirmationDialog

app = QApplication(sys.argv)

class TestFinalizationDialog(unittest.TestCase):
    def test_dialog_logic(self):
        # Mock Data
        data = {
            'oc_num': '12/2025',
            'issue_date': '2025-01-01',
            'gstin': 'TestGSTIN',
            'legal_name': 'Test Trader',
            'fy': '2023-24'
        }
        
        # Mixed issues: one with shortfall, one zero
        issues = [
            {'category': 'Issue 1', 'total_shortfall': 1000},
            {'category': 'Issue 2', 'total_shortfall': 0} # Should be filtered out by logic BEFORE dialog, but dialog itself just displays what it gets.
        ]
        
        # Test 1: Dialog Read-Only Property
        # We pass "issues" as is, assuming the caller has done the filtering. 
        # But here we just test the UI properties.
        dlg = FinalizationConfirmationDialog(data, issues)
        
        # Access the table (it's the 2nd widget in c_layout, index 1 is label, index 2 is table... actually hard to get by index rely on findChildren)
        # c_layout adds: grid, label, table, warn_frame.
        
        from PyQt6.QtWidgets import QTableWidget
        table = dlg.findChild(QTableWidget)
        
        self.assertIsNotNone(table, "Table widget not found in dialog")
        
        # Check properties
        triggers = table.editTriggers()
        self.assertEqual(triggers, QAbstractItemView.EditTrigger.NoEditTriggers, "Table should be read-only")
        
        mode = table.selectionMode()
        self.assertEqual(mode, QAbstractItemView.SelectionMode.NoSelection, "Table selection should be disabled")
        
        print("[SUCCESS] Dialog Read-Only Verification Passed")
        dlg.close()

if __name__ == '__main__':
    unittest.main()
