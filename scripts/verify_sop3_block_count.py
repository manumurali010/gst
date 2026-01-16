import unittest
from unittest.mock import MagicMock
import pandas as pd
import sys
import os
import openpyxl

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.gstr_2b_analyzer import GSTR2BAnalyzer

class TestSOP3BlockCount(unittest.TestCase):
    
    def setUp(self):
        # Create a dummy Excel file
        self.test_file = "test_sop3_yearly.xlsx"
        wb = openpyxl.Workbook()
        
        # 1. Read me (Required for validation)
        ws_readme = wb.active
        ws_readme.title = "Read me"
        ws_readme['A1'] = "GSTIN: 29ABCDE1234F1Z5"
        ws_readme['A2'] = "Financial Year: 2023-24"
        
        # 2. ITC Available (The target sheet)
        # Structure: Description, [13 blocks of 4 columns] = 52 Tax Columns
        # Row 1: Headers (mock)
        # Row 2: "Inward Supplies from ISD" + 52 values
        
        ws_itc = wb.create_sheet("ITC Available")
        
        # Header Row
        headers = ["Details", "Desc", "Other"] + ["Tax"] * 52
        ws_itc.append(headers)
        
        # Inward Row (Values: 10.0 * col_index)
        # We want the LAST block (Total) to be distinct.
        # Let's say last block is [1000, 500, 500, 100]
        row_vals = ["", "Inward Supplies from ISD", ""] 
        # Add 12 blocks of junk (but numeric)
        for i in range(12):
            row_vals.extend([10, 10, 10, 10])
        # Add 13th block (Total)
        row_vals.extend([1000, 500, 500, 100])
        
        ws_itc.append(row_vals)
        
        # Credit Note Row
        # Last block: [100, 50, 50, 10]
        row_vals_cn = ["", "ISD - Credit Notes", ""]
        for i in range(12):
            row_vals_cn.extend([1, 1, 1, 1])
        row_vals_cn.extend([100, 50, 50, 10])
        ws_itc.append(row_vals_cn)

        wb.save(self.test_file)
        
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_yearly_block_count(self):
        """Test parsing of 13-block (Yearly) GSTR-2B file"""
        print("\nTesting Yearly GSTR-2B (13 Blocks)...")
        analyzer = GSTR2BAnalyzer(self.test_file)
        
        # This calls analyze_sop_3 which currently uses strict block count check (1 or 4)
        # We expect this to fail currently with "Unsupported block count 13"
        try:
             res = analyzer.analyze_sop_3()
             print(f"Result: {res}")
             
             # Assertions (Netting: 1000-100=900, 500-50=450...)
             self.assertEqual(res['igst'], 900.0)
             self.assertEqual(res['cgst'], 450.0)
             self.assertEqual(res['sgst'], 450.0)
             self.assertEqual(res['cess'], 90.0)
             self.assertEqual(res['status'], 'pass')
             
        except ValueError as e:
             print(f"Caught expected error (pre-fix): {e}")
             if "Unsupported block count" in str(e):
                  self.fail(f"Validation Error: {e}")
             else:
                  raise e

if __name__ == '__main__':
    unittest.main()
