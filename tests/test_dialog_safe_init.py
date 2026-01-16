
import sys
import unittest
import types

# ---------------- MOCK PYQT6 ----------------
module_name = "PyQt6"
if module_name not in sys.modules:
    # Create a dummy module
    dummy_qt = types.ModuleType(module_name)
    sys.modules[module_name] = dummy_qt
    
    # Mock QtWidgets
    dummy_widgets = types.ModuleType("PyQt6.QtWidgets")
    sys.modules["PyQt6.QtWidgets"] = dummy_widgets
    
    # Mock QtCore
    dummy_core = types.ModuleType("PyQt6.QtCore")
    sys.modules["PyQt6.QtCore"] = dummy_core
    
    # Define Dummy Classes
    class DummyQWidget:
        def __init__(self, *args, **kwargs): pass
        def setWindowTitle(self, *args): pass
        def setFixedWidth(self, *args): pass
        def setWindowFlags(self, *args): pass
        def windowFlags(self): return 0
        def setLayout(self, *args): pass
        def addWidget(self, *args): pass
        def setSpacing(self, *args): pass
        def setContentsMargins(self, *args): pass
        def setStyleSheet(self, *args): pass
        def setWordWrap(self, *args): pass
        def setToolTip(self, *args): pass
        def setEnabled(self, *args): pass
        def addStretch(self, *args): pass
        def addLayout(self, *args): pass
        def addButton(self, *args): pass
        def addSpacing(self, *args): pass
        
    class DummyQDialog(DummyQWidget):
        def reject(self): pass
        def accept(self): pass

    class DummySignal:
        def connect(self, func): pass

    class DummyButton(DummyQWidget):
        def __init__(self, *args, **kwargs): 
            self.clicked = DummySignal()
            super().__init__()
            
    class DummyButtonGroup(DummyQWidget):
        def __init__(self, *args, **kwargs): 
            self.buttonClicked = DummySignal()
            super().__init__()

    # Inject into QtWidgets
    dummy_widgets.QDialog = DummyQDialog
    dummy_widgets.QWidget = DummyQWidget
    dummy_widgets.QVBoxLayout = DummyQWidget
    dummy_widgets.QHBoxLayout = DummyQWidget
    dummy_widgets.QLabel = DummyQWidget
    dummy_widgets.QRadioButton = DummyButton
    dummy_widgets.QPushButton = DummyButton
    dummy_widgets.QButtonGroup = DummyButtonGroup
    dummy_widgets.QFrame = DummyQWidget
    dummy_widgets.QApplication = DummyQWidget
    dummy_widgets.QApplication.instance = lambda: True # Pretend app exists
    
    # Inject into QtCore
    dummy_core.Qt = types.SimpleNamespace()
    dummy_core.Qt.WindowType = types.SimpleNamespace()
    dummy_core.Qt.WindowType.WindowContextHelpButtonHint = 1

# ---------------- END MOCK ----------------

# Mocking the module path to import from src
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ui.components.header_selection_dialog import HeaderSelectionDialog

class TestDialogInit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass # App already mocked via instance lambda

    def test_init_integer(self):
        try:
            dlg = HeaderSelectionDialog(8, "gstin", ["col1", "col2"])
            print("Init with int: OK")
        except Exception as e:
            self.fail(f"Init with int failed: {e}")

    def test_init_string_simple(self):
        try:
            dlg = HeaderSelectionDialog("8", "gstin", ["col1", "col2"])
            print("Init with str number: OK")
        except Exception as e:
            self.fail(f"Init with str number failed: {e}")

    def test_init_string_prefix(self):
        try:
            dlg = HeaderSelectionDialog("sop_8", "gstin", ["col1", "col2"])
            print("Init with prefix: OK")
        except Exception as e:
            self.fail(f"Init with prefix failed: {e}")

    def test_init_invalid(self):
        try:
            dlg = HeaderSelectionDialog("sop_unknown", "gstin", ["col1", "col2"])
            print("Init with invalid: OK (Handled gracefully)")
        except Exception as e:
            self.fail(f"Init with invalid failed: {e}")

    def test_init_dict_options(self):
        try:
            options = [
                {'label': 'Column A (Original)', 'value': 'cola'},
                {'label': 'Column B (Original)', 'value': 'colb'}
            ]
            dlg = HeaderSelectionDialog(8, "gstin", options)
            print("Init with dict options: OK")
            
            # Verify options are stored
            self.assertEqual(len(dlg.options), 2)
            # Verify selection logic (can't easily click button in mock, but can verify no crash)
            
        except Exception as e:
            self.fail(f"Init with dict options failed: {e}")

    def test_init_categorized_ux(self):
        try:
            options = [
                {'label': 'Tax Amount', 'value': 'taxamt', 'category': 'recommended'},
                {'label': 'GSTIN', 'value': 'gstin', 'category': 'other'},
                {'label': 'Note', 'value': 'note', 'category': 'other'}
            ]
            dlg = HeaderSelectionDialog(10, "igst", options)
            print("Init with categorized options: OK")
            
            # Verify internal map maps buttons to original indices
            # Note: The dialog splits rec/other, so visual order != input order optionally
            self.assertTrue(hasattr(dlg, 'btn_map'))
            self.assertEqual(len(dlg.btn_map), 3)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.fail(f"Init with categorized options failed: {e}")

    def test_init_no_recommended(self):
        try:
            # All options are 'other'
            options = [
                {'label': 'GSTIN - ❌ Not a Tax Amount', 'value': 'gstin', 'category': 'other'},
                {'label': 'Date - ❌ Not a Tax Amount', 'value': 'date', 'category': 'other'}
            ]
            dlg = HeaderSelectionDialog(8, "tax", options)
            print("Init with no recommended: OK")
            
            # Verify internal map maps buttons to original indices
            self.assertEqual(len(dlg.btn_map), 2)
            
            # Since we can't easily check UI children text in this mock without more complex setup, 
            # we assume if it didn't crash, the logic path for "if recommended: ... else: ..." executed safely.
            
        except Exception as e:
            self.fail(f"Init with no recommended failed: {e}")


if __name__ == '__main__':
    unittest.main()
