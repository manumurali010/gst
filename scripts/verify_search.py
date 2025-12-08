import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from PyQt6.QtWidgets import QApplication
from src.ui.adjudication_wizard import AdjudicationWizard

# Create app
app = QApplication(sys.argv)

# Create wizard
try:
    wizard = AdjudicationWizard(lambda: None)
    
    # Test 1: Simulate Completer Activation
    print("Testing Completer Activation...")
    # Use a known GSTIN from previous check
    test_gstin = "32AAAAC2146E1ZI" 
    wizard.search_gstin(test_gstin)
    
    legal_name = wizard.legal_name_input.text()
    print(f"Legal Name: {legal_name}")
    
    if legal_name:
        print("SUCCESS: Completer populated details.")
    else:
        print("FAILURE: Completer did not populate details.")

    # Test 2: Simulate Button Click
    print("\nTesting Button Click...")
    wizard.gstin_input.setText(test_gstin)
    wizard.legal_name_input.clear()
    wizard.search_gstin(False) # Simulate clicked(False)
    
    legal_name = wizard.legal_name_input.text()
    print(f"Legal Name: {legal_name}")
    
    if legal_name:
        print("SUCCESS: Button populated details.")
    else:
        print("FAILURE: Button did not populate details.")
        
except Exception as e:
    print(f"An error occurred: {e}")
