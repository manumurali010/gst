import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDate, Qt


# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.adjudication_wizard import AdjudicationWizard

def verify_drc01_redesign():
    app = QApplication(sys.argv)
    wizard = AdjudicationWizard(None)
    
    # Set Basic Info
    wizard.fy_combo.setCurrentIndex(1) # Select a year
    wizard.proceeding_combo.setCurrentText("Section 73 (Demand)")
    
    # Trigger form options update
    wizard.update_form_options()
    
    # Set form type and trigger section combo visibility
    form_index = wizard.form_combo.findText("DRC-01A", Qt.MatchFlag.MatchContains)
    if form_index >= 0:
        wizard.form_combo.setCurrentIndex(form_index)
    wizard.on_form_type_changed()  # Trigger visibility logic
    
    wizard.drc_section_combo.setCurrentText("Section 73(5)")

    
    # Set Period
    wizard.period_from_date.setDate(QDate(2023, 4, 1))
    wizard.period_to_date.setDate(QDate(2024, 3, 31))
    
    # Set Taxpayer Details
    wizard.gstin_input.setText("32AAACG1234A1Z1")
    wizard.legal_name_input.setText("Test Legal Name")
    wizard.trade_name_input.setText("Test Trade Name")
    wizard.address_input.setText("Test Address")
    
    # Set Issue
    wizard.issue_input.setText("Short payment of tax due to mismatch")
    
    # Set Amounts (Add a row)
    wizard.add_amount_row()
    wizard.amount_table.item(0, 3).setText("1000") # Tax
    wizard.amount_table.item(0, 4).setText("100")  # Interest
    wizard.amount_table.item(0, 5).setText("0")    # Penalty
    wizard.amount_table.item(0, 6).setText("1100") # Total
    
    # Generate HTML
    html = wizard.generate_drc01a_html()
    
    # Verify Placeholders
    errors = []
    
    if "01/04/2023" not in html:
        errors.append("Period From date not found or incorrect")
    if "31/03/2024" not in html:
        errors.append("Period To date not found or incorrect")
    if "Short payment of tax due to mismatch" not in html:
        errors.append("Issue Description not found")
    if "1,000" not in html: # Total Tax
        errors.append("Total Tax Amount not found")
    if "100" not in html: # Total Interest
        errors.append("Total Interest Amount not found")
    if "1,100" not in html: # Grand Total
        errors.append("Grand Total Amount not found")
        
    # Verify Conditional Text (Section 73)
    if "section 73(1)" not in html:
        errors.append("Section 73 conditional text incorrect")
        
    # Test Section 74
    wizard.drc_section_combo.setCurrentText("Section 74(5)")
    html_74 = wizard.generate_drc01a_html()
    if "section 74(1)" not in html_74:
        errors.append("Section 74 conditional text incorrect")

        
    if errors:
        print("Verification Failed:")
        for err in errors:
            print(f"- {err}")
    else:
        print("Verification Successful! All placeholders and logic verified.")

if __name__ == "__main__":
    verify_drc01_redesign()
