
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock PyQt6
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtCore import Qt

# Mock ALL other dependencies to prevent side effects
mock_deps = [
    'src.database.db_manager',
    'src.utils.preview_generator',
    'src.ui.collapsible_box',
    'src.ui.rich_text_editor',
    'src.ui.components.modern_card',
    'src.ui.issue_card',
    'src.ui.components.finalization_panel',
    'src.ui.adjudication_setup_dialog',
    'src.services.asmt10_generator',
    'jinja2'
]
for dep in mock_deps:
    sys.modules[dep] = MagicMock()

# Define a real-enough MockWidget for inheritance
class MockWidget:
    def __init__(self, *args, **kwargs):
        self._visible = True
        self._current_index = 0
    def setVisible(self, v): self._visible = v
    def isVisible(self): return self._visible
    def setCurrentIndex(self, i): self._current_index = i
    def currentIndex(self): return self._current_index
    def addWidget(self, *args): pass
    def show(self): self._visible = True
    def hide(self): self._visible = False
    def setSizes(self, s): pass
    def setContentsMargins(self, *args): pass
    def addLayout(self, *args): pass
    def addStretch(self, *args): pass
    def setObjectName(self, *args): pass
    def setStyleSheet(self, *args): pass
    def setHandleWidth(self, *args): pass

QtWidgets.QWidget = MockWidget
QtWidgets.QStackedWidget = MockWidget
QtWidgets.QSplitter = MockWidget
QtWidgets.QFrame = MockWidget
QtWidgets.QVBoxLayout = MagicMock
QtWidgets.QHBoxLayout = MagicMock
QtWidgets.QLabel = MagicMock
QtWidgets.QPushButton = MagicMock
QtWidgets.QScrollArea = MockWidget

from src.ui.proceedings_workspace import ProceedingsWorkspace

class TestUIRedesign(unittest.TestCase):
    def setUp(self):
        self.navigate_callback = MagicMock()
        self.sidebar = MagicMock()
        
        with patch('src.database.db_manager.DatabaseManager') as mock_db:
            # Prevent __init__ from doing too much
            with patch.object(ProceedingsWorkspace, 'init_ui'):
                self.workspace = ProceedingsWorkspace(self.navigate_callback, self.sidebar)
                # Manually setup what init_ui would do for testing logic
                self.workspace.content_stack = MockWidget()
                self.workspace.preview_container = MockWidget()
                self.workspace.workspace_splitter = MagicMock() # Use MagicMock for splitter to track setSizes
                self.workspace.is_hydrated = True
                self.workspace.proceeding_data = {'source_scrutiny_id': 'SCR-123'}

    def test_apply_context_layout_asmt10(self):
        self.workspace.apply_context_layout("asmt10")
        self.assertFalse(self.workspace.content_stack.isVisible())
        self.assertTrue(self.workspace.preview_container.isVisible())
        self.workspace.workspace_splitter.setSizes.assert_called_with([0, 1000])

    def test_apply_context_layout_scn(self):
        self.workspace.apply_context_layout("scn")
        self.assertTrue(self.workspace.content_stack.isVisible())
        self.assertTrue(self.workspace.preview_container.isVisible())
        self.workspace.workspace_splitter.setSizes.assert_called_with([700, 300])

    def test_handle_sidebar_action_routing(self):
        with patch.object(self.workspace, 'update_preview') as mock_update:
            with patch.object(self.workspace, 'apply_context_layout') as mock_apply:
                # Mock the action map inside handle_sidebar_action by effect
                self.workspace.handle_sidebar_action("asmt10")
                self.assertEqual(self.workspace.content_stack.currentIndex(), 2)
                mock_apply.assert_called_with("asmt10")
                mock_update.assert_called_with("asmt10")

    def test_update_preview_routing(self):
        self.workspace.preview_label_widget = MagicMock()
        self.workspace.preview_container_layout = MagicMock()
        self.workspace.preview_scroll = MagicMock()
        self.workspace.preview_scroll.width.return_value = 800
        
        with patch('src.services.asmt10_generator.ASMT10Generator') as mock_gen_class:
            mock_gen = mock_gen_class.return_value
            mock_gen.generate_html.return_value = "<html></html>"
            
            with patch('src.utils.preview_generator.PreviewGenerator.generate_preview_image') as mock_prev:
                mock_prev.return_value = [b'fakeimg']
                self.workspace.update_preview("asmt10")
                self.workspace.preview_label_widget.setText.assert_called_with("🔒 Finalised ASMT-10 (Read-Only)")

if __name__ == '__main__':
    unittest.main()
