
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock PyQt6
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()
sys.modules['src.ui.components.finalization_panel'] = MagicMock()

# Mock Dependencies
sys.modules['src.database.db_manager'] = MagicMock()
sys.modules['src.services.asmt10_generator'] = MagicMock()
sys.modules['src.utils.preview_generator'] = MagicMock()
sys.modules['jinja2'] = MagicMock()
sys.modules['src.ui.rich_text_editor'] = MagicMock()
sys.modules['src.ui.adjudication_setup_dialog'] = MagicMock()

# Defines for mock base classes
class MockWidget:
    def __init__(self, parent=None): pass
    def setObjectName(self, name): pass
    def setStyleSheet(self, style): pass
    def setFixedSize(self, w, h): pass
    def setAlignment(self, align): pass
    def setLayout(self, layout): pass
    def layout(self): return MagicMock()
    def show(self): pass
    def hide(self): pass
    def deleteLater(self): pass
    def setWidget(self, w): pass
    def setWidgetResizable(self, b): pass
    def setSpacing(self, s): pass
    def setContentsMargins(self, a, b, c, d): pass
    def addWidget(self, w): pass
    def addLayout(self, l): pass
    def addStretch(self, s=0): pass
    def setFrameShape(self, s): pass
    def count(self): return 0
    def takeAt(self, i): return MagicMock()
    class Shape:
        NoFrame = 0
    def __getattr__(self, name): return MagicMock()

sys.modules['PyQt6.QtWidgets'].QWidget = MockWidget
sys.modules['PyQt6.QtWidgets'].QFrame = MockWidget
sys.modules['PyQt6.QtWidgets'].QScrollArea = MockWidget
sys.modules['PyQt6.QtWidgets'].QVBoxLayout = MockWidget
sys.modules['PyQt6.QtWidgets'].QLabel = MockWidget

import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.proceedings_workspace import ProceedingsWorkspace

class TestASMT10Preview(unittest.TestCase):
    def setUp(self):
        # Instantiate
        self.mock_callback = MagicMock()
        self.workspace = ProceedingsWorkspace(self.mock_callback)
        
        # Inject DB (Replace the real one created in init)
        self.workspace.db = MagicMock()
        
        # Setup UI references manually since we mocked init logic and it might have skipped create_asmt10_tab in partial mocks
        # But wait, specific method calls in init might have run if we didn't mock ProceedingsWorkspace entirely.
        # We imported the REAL class.
        pass

    @patch('src.ui.proceedings_workspace.ASMT10Generator')
    @patch('src.ui.proceedings_workspace.PreviewGenerator')
    def test_render_preview(self, MockPreviewGen, MockASMT10Gen):
        # Setup Data
        source_id = "test_scrutiny_id"
        mock_data = {
            'case_id': 'CASE/001',
            'financial_year': '2024-25',
            'taxpayer_details': {'name': 'Test TP'},
            'selected_issues': [{'id': 'issue1'}]
        }
        self.workspace.db.get_scrutiny_case_data.return_value = mock_data
        
        # Mock Generator
        mock_gen_instance = MockASMT10Gen.return_value
        mock_gen_instance.generate_html.return_value = "<html>Test</html>"
        
        # Mock Preview
        MockPreviewGen.generate_preview_image.return_value = [b'fake_image_bytes']
        MockPreviewGen.get_qpixmap_from_bytes.return_value = MagicMock() # QPixmap
        
        # Setup Layout Mock
        mock_layout = MagicMock()
        self.workspace.asmt10_page_layout = mock_layout
        mock_layout.count.return_value = 0 # Empty initially
        
        # Act
        print(f"Calling render_asmt10_preview with {source_id}")
        self.workspace.render_asmt10_preview(source_id)
        
        # Assertions
        print("Checking DB calls...")
        print(self.workspace.db.mock_calls)
        
        # 1. DB Fetch
        self.workspace.db.get_scrutiny_case_data.assert_called_with(source_id)
        
        # 2. Generator Call
        # Check if generate_html was called
        self.assertTrue(mock_gen_instance.generate_html.called)
        
        # 3. Preview Gen Call
        MockPreviewGen.generate_preview_image.assert_called_with("<html>Test</html>", all_pages=True)
        
        # 4. Layout Update
        # Should add widget (QLabel)
        self.assertTrue(mock_layout.addWidget.called)
        print("Verification Passed: render_asmt10_preview logic is correct.")

if __name__ == '__main__':
    unittest.main()
