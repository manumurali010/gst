
import sys
import os
import pandas as pd
import unittest
from unittest.mock import MagicMock

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Mock PyQt6 before importing src
try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    from unittest.mock import MagicMock
    class MockQObject:
        def __init__(self, *args, **kwargs): pass
    
    import sys
    sys.modules["PyQt6"] = MagicMock()
    sys.modules["PyQt6.QtCore"] = MagicMock()
    sys.modules["PyQt6.QtCore"].QObject = MockQObject
    sys.modules["PyQt6.QtCore"].pyqtSignal = lambda *args: MagicMock()
    sys.modules["PyQt6.QtWidgets"] = MagicMock()

from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

class TestHeaderScan(unittest.TestCase):
    def setUp(self):
        self.analyzer = GSTR2AAnalyzer("dummy.xlsx")
        # Mock xl_file
        self.analyzer.xl_file = MagicMock()
        
    def test_descriptive_header_override(self):
        # Scenario: 
        # Row 0: Irrelevant
        # Row 1: Irrelevant
        # ...
        # Row 4: "Details of taxable inward supplies received from registered persons" (Descriptive)
        # Row 5: "GSTIN", "Taxable Value", "Integrated Tax", "Central Tax", "State Tax" (Tax Tokens)
        
        # Create a Mock DataFrame simulating the read of first 10 rows
        data = [
            ["Row 0", "", "", "", "", ""],
            ["Row 1", "", "", "", "", ""],
            ["Row 2", "", "", "", "", ""],
            ["Row 3", "", "", "", "", ""],
            ["Details of taxable inward supplies received from registered persons", "", "", "Details of... cont", "", ""], # Row 4 (Parent)
            ["GSTIN of Supplier", "Invoice Number", "Taxable Value", "Integrated Tax", "Central Tax", "State Tax"]  # Row 5 (Child)
        ]
        
        # We need 10 rows for safety as per code
        while len(data) < 10:
            data.append(["", "", "", "", "", ""])
            
        df_scan = pd.DataFrame(data)
        
        # Mock parse to return this df
        self.analyzer.xl_file.parse.return_value = df_scan
        self.analyzer.xl_file.sheet_names = ["B2B"]
        
        print("\n--- Testing B2B Descriptive Header Override ---")
        mapping, start_row = self.analyzer._scan_headers("B2B")
        
        print(f"Mapping Keys: {list(mapping.keys())}")
        
        # Assertions
        # 1. "integratedtax" should be a key (due to overridden merge), NOT "details...integratedtax"
        self.assertIn("integratedtax", mapping, "IGST column not found with simple key")
        self.assertIn("centraltax", mapping)
        self.assertIn("statetax", mapping)
        
        # 2. Check indices
        # "Integrated Tax" is at index 3
        igst_indices = [item['idx'] for item in mapping['integratedtax']]
        self.assertIn(3, igst_indices, "IGST index incorrect")
        
        print("[SUCCESS] Descriptive Header Override Verification Passed")

    def test_normal_concatenation_preserved(self):
        # Scenario: Normal case without descriptive text trigger
        # Row 4: "Invoice"
        # Row 5: "Number"
        # Result: "Invoice Number"
        
        data = [
            ["Row 0", "", ""],
            ["Row 1", "", ""],
            ["Row 2", "", ""],
            ["Row 3", "", ""],
            ["Invoice", "Taxable", "Integrated"], # Row 4
            ["Number",  "Value",   "Tax"]        # Row 5
        ]
        while len(data) < 10: data.append(["", "", ""])
        
        df_scan = pd.DataFrame(data)
        self.analyzer.xl_file.parse.return_value = df_scan
        self.analyzer.xl_file.sheet_names = ["B2B"]
        
        print("\n--- Testing Normal Concatenation Preservation ---")
        mapping, start_row = self.analyzer._scan_headers("B2B")
        
        print(f"Mapping Keys: {list(mapping.keys())}")
        
        # "invoicenumber" should exist
        self.assertIn("invoicenumber", mapping)
        
        # "integratedtax" should exist (merged)
        self.assertIn("integratedtax", mapping)
        
        print("[SUCCESS] Normal Concatenation Verification Passed")

if __name__ == '__main__':
    unittest.main()
