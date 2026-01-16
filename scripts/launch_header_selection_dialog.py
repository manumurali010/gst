
import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from PyQt6.QtWidgets import QApplication, QMessageBox
try:
    from src.ui.components.header_selection_dialog import HeaderSelectionDialog
except ImportError:
    print("Could not import HeaderSelectionDialog. Run from project root or ensure src is reachable.")
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    # Mock data for SOP-8
    sop_id = 8
    # Canonical Key is usually what we looked for, e.g., 'tax_amount'
    canonical_key = "tax_amount" 
    
    # Scenario 1: Mixed options (Recommended + Others)
    print("\n--- Launching Dialog (Scenario 1: Recommended + Others) ---")
    options_mixed = [
        {'label': 'IGST Amount (Recommended)', 'value': 'igst', 'category': 'recommended'},
        {'label': 'Some Random Column', 'value': 'col_a'},
        {'label': 'Long Column Name That Should Wrap Properly In The UI Layout Without Being Cut Off Or Truncated', 'value': 'col_long'}
    ]
    
    dlg = HeaderSelectionDialog(sop_id, canonical_key, options_mixed)
    result = dlg.exec()
    print(f"Result: {result} (1=Accepted, 0=Rejected)")
    if result == 1:
        print(f"Selected: {dlg.selected_header}")
    
    # Scenario 2: No Recommended (Heuristic Warning)
    print("\n--- Launching Dialog (Scenario 2: No Recommended) ---")
    options_none = [
        {'label': 'Just A Column', 'value': 'col_1'},
        {'label': 'Another Column', 'value': 'col_2'}
    ]
    dlg2 = HeaderSelectionDialog(sop_id, canonical_key, options_none)
    result2 = dlg2.exec()
    print(f"Result: {result2}")
    if result2 == 1:
        print(f"Selected: {dlg2.selected_header}")

    # Scenario 3: Verify Confirm Button Logic (Manual Check)
    # User should visually verify that Confirm is disabled initially.
    print("\n--- Launching Dialog (Scenario 3: Empty Recommended / Logic Check) ---")
    print("INSTRUCTIONS: Check that 'Confirm Selection' is DISABLED initially. Select an option to ENABLE it.")
    dlg3 = HeaderSelectionDialog(sop_id, canonical_key, options_none)
    dlg3.exec()

if __name__ == "__main__":
    main()
