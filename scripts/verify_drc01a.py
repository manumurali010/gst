import sys
import os
from PyQt6.QtWidgets import QApplication
from src.ui.adjudication_wizard import AdjudicationWizard

# Add src to path
sys.path.append(os.getcwd())

def test_drc01a_generation():
    app = QApplication(sys.argv)
    
    def mock_navigate(page, pid=None):
        pass
        
    wizard = AdjudicationWizard(mock_navigate)
    
    # Mock data
    wizard.gstin_input.setText("32AAAAC2146E1ZI")
    wizard.legal_name_input.setText("Test Taxpayer")
    wizard.form_combo.setCurrentText("DRC-01A")
    wizard.letterhead_html = "<div id='mock-letterhead'><h1>LETTERHEAD</h1></div>"
    
    # Test 1: Section 73
    print("\n--- Test 1: Section 73 ---")
    wizard.proceeding_combo.setCurrentText("Section 73 (Determination of tax not paid - non-fraud)")
    html_73 = wizard.generate_drc01a_html()
    
    expected_73 = "failing which Show Cause Notice will be issued under section 73(1)"
    if expected_73 in html_73:
        print("Success! Section 73 advice text found.")
    else:
        print("Failed! Section 73 advice text NOT found.")
        print(f"Snippet: {html_73[-1000:]}")

    # Test 2: Section 74
    print("\n--- Test 2: Section 74 ---")
    wizard.proceeding_combo.setCurrentText("Section 74 (Determination of tax not paid - fraud)")
    html_74 = wizard.generate_drc01a_html()
    
    expected_74 = "failing which Show Cause Notice will be issued under section 74(1)"
    if expected_74 in html_74:
        print("Success! Section 74 advice text found.")
    else:
        print("Failed! Section 74 advice text NOT found.")
        print(f"Snippet: {html_74[-1000:]}")
        
    # Test 3: Letterhead Toggle
    print("\n--- Test 3: Letterhead Toggle ---")
    
    # Checked
    wizard.show_letterhead_cb.setChecked(True)
    html_checked = wizard.generate_drc01a_html()
    if "<div id='mock-letterhead'>" in html_checked:
        print("Success! Letterhead present when checked.")
    else:
        print("Failed! Letterhead missing when checked.")
        
    # Unchecked
    wizard.show_letterhead_cb.setChecked(False)
    html_unchecked = wizard.generate_drc01a_html()
    if "<div id='mock-letterhead'>" not in html_unchecked:
        print("Success! Letterhead absent when unchecked.")
    else:
        print("Failed! Letterhead present when unchecked.")
        
    # Check Visibility
    print("\n--- Test 4: Checkbox Visibility ---")
    if wizard.show_letterhead_cb.isVisible():
        print("Success! Checkbox is visible.")
    else:
        print("Failed! Checkbox is NOT visible.")
        
    print(f"Checkbox Parent: {wizard.show_letterhead_cb.parent()}")
    print(f"Checkbox Geometry: {wizard.show_letterhead_cb.geometry()}")
    
    # Check if parent is Step 1-4 Combined (where we added it)
    if wizard.show_letterhead_cb.parent() == wizard.step1_4_combined:
        print("Success! Checkbox is in Step 1-4 Combined.")
    else:
        print(f"Checkbox is in: {wizard.show_letterhead_cb.parent()}")

if __name__ == "__main__":
    test_drc01a_generation()
