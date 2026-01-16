import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock PyQt6 modules BEFORE importing project code
# Define a dummy base class for QWidget so inheritance works properly
class MockWidget:
    class Shape:
        NoFrame = 0
        
    def __init__(self, parent=None):
        pass
    def setObjectName(self, name): pass
    def setStyleSheet(self, style): pass
    def setFixedSize(self, w, h): pass
    def setAlignment(self, align): pass
    def hide(self): pass
    def show(self): pass
    def setCursor(self, cursor): pass
    def setFixedHeight(self, h): pass
    def layout(self): return None
    def mousePressEvent(self, event): pass
    
    # Swallow all other calls like a Mock
    def __getattr__(self, name):
        return MagicMock()

# Patch module imports
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtWidgets'].QWidget = MockWidget # Inherit from this!
sys.modules['PyQt6.QtWidgets'].QFrame = MockWidget
sys.modules['PyQt6.QtWidgets'].QStackedWidget = MockWidget
sys.modules['PyQt6.QtWidgets'].QScrollArea = MockWidget

sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()
sys.modules['PyQt6.QtPrintSupport'] = MagicMock() # Added this

# Mock other context
sys.modules['PyQt6.QtWebEngineWidgets'] = MagicMock()


# Mock other external dependencies
sys.modules['fitz'] = MagicMock()
sys.modules['docx'] = MagicMock()
sys.modules['win32com'] = MagicMock()
sys.modules['win32com.client'] = MagicMock()
sys.modules['weasyprint'] = MagicMock()
sys.modules['xhtml2pdf'] = MagicMock()
sys.modules['jinja2'] = MagicMock() # Re-added
sys.modules['openpyxl'] = MagicMock()

from src.ui.proceedings_workspace import ProceedingsWorkspace
# Sidebar might need its base classes mocked too if it inherits
# Sidebar might need its base classes mocked too if it inherits
pass


class TestAdjudicationUI(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = MagicMock()
        # Mock minimal proceeding data
        self.mock_scrutiny_origin = {
            'id': 'ADJ-1',
            'is_adjudication': True,
            'source_scrutiny_id': 'SCR-1',
            'adjudication_section': '74',
            'status': 'ASMT-10 Finalised',
            'gstin': 'G1',
            'legal_name': 'L1',
            'financial_year': '2024-25',
            'selected_issues': [],
            'additional_details': {}
        }
        self.mock_direct_origin = {
            'id': 'ADJ-2',
            'is_adjudication': True,
            'source_scrutiny_id': None,
            'adjudication_section': '73',
            'status': 'Draft',
            'gstin': 'G2',
            'legal_name': 'L2',
            'financial_year': '2023-24',
            'additional_details': {}
        }
        
    @patch('src.ui.proceedings_workspace.DatabaseManager')
    def test_scrutiny_origin_accordion(self, MockDB):
        # Setup
        # ProceedingsWorkspace(navigate_callback, sidebar, proceeding_id)
        mock_callback = MagicMock()
        mock_sidebar = MagicMock()
        workspace = ProceedingsWorkspace(mock_callback, sidebar=mock_sidebar)
        
        # Inject DB return (The workspace.db attribute is the instance returned by MockDB())
        workspace.db = MockDB.return_value 
        workspace.db.get_proceeding.return_value = self.mock_scrutiny_origin
        workspace.db.get_documents.return_value = []
        workspace.db.get_active_issues.return_value = []
        
        # Mock internal components that might be created
        workspace.asmt10_panel = MagicMock()
        # Mock sidebar manually since it's injected
        workspace.sidebar = MagicMock()
        
        # Execute Load
        workspace.load_proceeding('ADJ-1')
        
        # Assertions
        workspace.sidebar.set_button_visible.assert_any_call('asmt10', True)
        workspace.sidebar.set_button_visible.assert_any_call('drc01a', False)
        print("PASS: Scrutiny Origin -> ASMT-10 Shown, DRC-01A Hidden")
        
    @patch('src.ui.proceedings_workspace.DatabaseManager')
    def test_direct_origin_accordion(self, MockDB):
        # Setup
        mock_callback = MagicMock()
        mock_sidebar = MagicMock()
        workspace = ProceedingsWorkspace(mock_callback, sidebar=mock_sidebar)
        
        workspace.db = MockDB.return_value
        workspace.db.get_proceeding.return_value = self.mock_direct_origin
        workspace.db.get_documents.return_value = []
        workspace.db.get_active_issues.return_value = []
        
        workspace.asmt10_panel = MagicMock()
        workspace.sidebar = MagicMock()
        
        # Execute Load
        workspace.load_proceeding('ADJ-2')
        
        # Assertions
        workspace.sidebar.set_button_visible.assert_any_call('asmt10', False)
        workspace.sidebar.set_button_visible.assert_any_call('drc01a', True)
        print("PASS: Direct Origin -> DRC-01A Shown, ASMT-10 Hidden")

if __name__ == '__main__':
    unittest.main()
