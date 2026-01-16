
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# Add gst (project root) to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.services.scrutiny_parser import ScrutinyParser

class TestParser(unittest.TestCase):
    def test_liability_parsing(self):
        parser = ScrutinyParser()
        
        # Mocking pandas read_excel to avoid needing a real file
        # We need to mock os.path.exists and openpyxl as well since the parser checks them
        
        with patch('os.path.exists') as mock_exists, \
             patch('openpyxl.load_workbook') as mock_wb, \
             patch('pandas.read_excel') as mock_df:
            
            mock_exists.return_value = True
            
            # Setup Workbook Mock
            wb_instance = MagicMock()
            wb_instance.sheetnames = ["Summary of Liability"]
            mock_wb.return_value = wb_instance
            
            # Setup DataFrame Mock
            # Columns: Period, 3B IGST, 3B CGST, 3B SGST, 3B Cess, Ref IGST, Ref CGST, Ref SGST, Ref Cess
            # Row 1 (Headers): Level 0 | Level 1
            # We simulate the MultiIndex logic or just flattened logic depending on how parser reads.
            # The parser reads header=[4, 5].
            
            # Simplified: The parser logic for column mapping is robust.
            # Let's mock the df.columns and iterrows behavior.
            
            # Create a sample DF
            cols = [
                ("Period", "nan"),
                ("3B", "IGST"), ("3B", "CGST"), ("3B", "SGST"), ("3B", "Cess"),
                ("GSTR-1", "IGST"), ("GSTR-1", "CGST"), ("GSTR-1", "SGST"), ("GSTR-1", "Cess")
            ]
            
            data = [
                ["Apr", 100, 100, 100, 0, 120, 120, 120, 0], # Shortfall 20
                ["May", 200, 200, 200, 0, 150, 150, 150, 0]  # Excess 50 (Shortfall 0)
            ]
            
            df = pd.DataFrame(data, columns=pd.MultiIndex.from_tuples(cols))
            mock_df.return_value = df
            
            result = parser._parse_group_a_liability("dummy.xlsx", "Liability", "Cat", "Type", [])
            
            self.assertIsNotNone(result)
            self.assertIn("facts", result)
            self.assertIn("analysis_meta", result)
            self.assertNotIn("snapshot", result) # STRICT CHECK
            
            self.assertEqual(result['analysis_meta']['sop_version'], "CBIC_SCRUTINY_SOP_2024.1")
            self.assertEqual(result['analysis_meta']['confidence'], "HIGH")
            
            # Check Shortfall Calculation
            # Apr: 120 - 100 = 20 shortfall * 3 (IGST, CGST, SGST) = 60
            # May: 150 - 200 = -50 (No shortfall)
            # Total = 60
            self.assertEqual(result['total_shortfall'], 60)
            
            print("Facts structure verified successfully!")
            print(result['facts'])

if __name__ == '__main__':
    unittest.main()
