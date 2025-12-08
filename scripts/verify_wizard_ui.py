import sys
import os
from PyQt6.QtWidgets import QApplication
from src.ui.case_initiation_wizard import CaseInitiationWizard

# Add src to path
sys.path.append(os.getcwd())

def test_wizard_ui():
    app = QApplication(sys.argv)
    
    def mock_navigate(page, pid):
        print(f"Navigation requested to {page} with PID {pid}")
        app.quit()

    wizard = CaseInitiationWizard(mock_navigate)
    wizard.show()
    
    # Simulate user interaction
    print("Simulating GSTIN input...")
    wizard.gstin_input.setText("32AAAAC2146E1ZI") # Valid GSTIN from CSV
    
    # Check if details fetched
    # We can't easily check the label text immediately due to async nature if it was threaded, 
    # but here it's synchronous so we can try.
    print(f"Preview Label Text: {wizard.tp_details_lbl.text()[:50]}...")
    
    if "CHENDAMANGALAM" in wizard.tp_details_lbl.text():
        print("Success! Taxpayer details fetched and displayed.")
    else:
        print("Failed! Taxpayer details not displayed.")

    # Simulate Create
    wizard.fy_combo.setCurrentIndex(1) # Select first FY
    wizard.section_combo.setCurrentText("73")
    wizard.form_combo.setCurrentText("DRC-01A")
    
    print("Simulating Create Button Click...")
    # wizard.create_proceeding() # Call directly to test logic
    # We won't actually click because it might close the app before we see output if we used app.exec()
    # But since we are running a script, we can just call the method.
    
    wizard.create_proceeding()

if __name__ == "__main__":
    test_wizard_ui()
