
import sys
import unittest
from unittest.mock import MagicMock

# Mock PyQt6
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

# Defines for mock base classes
class MockWidget:
    def __init__(self, parent=None): pass
    def setObjectName(self, name): pass
    def setStyleSheet(self, style): pass
    def setFixedSize(self, w, h): pass
    def setAlignment(self, align): pass
    def hide(self): pass
    def show(self): pass
    def setCursor(self, cursor): pass
    def setFixedHeight(self, h): pass
    def layout(self): return MagicMock()
    def mousePressEvent(self, event): pass
    def __getattr__(self, name): return MagicMock()

sys.modules['PyQt6.QtWidgets'].QWidget = MockWidget
sys.modules['PyQt6.QtWidgets'].QFrame = MockWidget
sys.modules['PyQt6.QtWidgets'].QTableWidget = MockWidget
sys.modules['PyQt6.QtWidgets'].QLabel = MockWidget
sys.modules['PyQt6.QtWidgets'].QPushButton = MockWidget
sys.modules['PyQt6.QtWidgets'].QCheckBox = MockWidget

# Adjust path
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.components.finalization_panel import FinalizationPanel

class TestFinalizationPanel(unittest.TestCase):
    # No need for QApp in mock environment
    
    def test_clear_data(self):
        panel = FinalizationPanel()
        
        # Override members with standard MagicMocks for tracking
        panel.tp_name_lbl = MagicMock()
        panel.tp_gstin_lbl = MagicMock()
        panel.tp_trade_lbl = MagicMock()
        panel.case_id_lbl = MagicMock()
        panel.fy_lbl = MagicMock()
        panel.section_lbl = MagicMock()
        panel.doc_no_lbl = MagicMock()
        panel.doc_date_lbl = MagicMock()
        panel.doc_ref_lbl = MagicMock()
        panel.issue_list_widget = MagicMock()
        panel.amounts_table = MagicMock()
        panel.grand_total_lbl = MagicMock()
        panel.finalize_btn = MagicMock()
        panel.confirm_chk = MagicMock()
        
        # 2. Call clear_data
        try:
            panel.clear_data()
            print("clear_data called successfully")
        except AttributeError as e:
            self.fail(f"clear_data raised AttributeError: {e}")
            
        # 3. Verify reset state (Mock methods called)
        panel.tp_name_lbl.setText.assert_called_with("Taxpayer Name")
        panel.amounts_table.setRowCount.assert_called_with(0)
        panel.finalize_btn.setEnabled.assert_called_with(False)
        panel.doc_no_lbl.setText.assert_called_with("No: -")
        
if __name__ == '__main__':
    unittest.main()
