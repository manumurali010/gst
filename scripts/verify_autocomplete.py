import sys
import os
from PyQt6.QtWidgets import QApplication
from src.ui.case_initiation_wizard import CaseInitiationWizard
from src.database.db_manager import DatabaseManager

# Add src to path
sys.path.append(os.getcwd())

def test_autocomplete():
    app = QApplication(sys.argv)
    
    # 1. Test Database Method
    db = DatabaseManager()
    gstins = db.get_all_gstins()
    print(f"Fetched {len(gstins)} GSTINs from DB.")
    if len(gstins) > 0:
        print(f"Sample GSTIN: {gstins[0]}")
    else:
        print("Error: No GSTINs fetched.")
        return

    # 2. Test UI Integration
    def mock_navigate(page, pid):
        pass

    wizard = CaseInitiationWizard(mock_navigate)
    completer = wizard.gstin_input.completer()
    
    if completer:
        print("Success! QCompleter is attached to GSTIN input.")
        model = completer.model()
        if model.rowCount() == len(gstins):
            print(f"Success! Completer model has {model.rowCount()} items, matching DB.")
        else:
            print(f"Warning: Completer model has {model.rowCount()} items, expected {len(gstins)}.")
    else:
        print("Failed! QCompleter is NOT attached.")

if __name__ == "__main__":
    test_autocomplete()
