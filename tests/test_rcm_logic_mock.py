
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.append(os.getcwd())
from src.services.gstr_2b_analyzer import GSTR2BAnalyzer

class TestRCMLogic(unittest.TestCase):
    
    @patch('src.utils.xlsx_light.XLSXLight')
    def test_rcm_summation(self, mock_xlsx):
        # Setup Mock Data matching what XLSXLight.read_sheet returns (list of lists)
        # Row format: [GSTIN, ..., Taxable, IGST, CGST, SGST, Cess]
        # We need to ensure the row TEXT matches the filter logic in get_rcm_inward_supplies
        # "reverse" AND "inward"
        
        # Row 1: "Inward Supplies ... Reverse Charge" - 100 IGST
        row1 = ["Inward Supplies liable for Reverse Charge", None, 1000, 100, 0, 0, 0]
        # Row 2: "Inward Supplies ... Reverse Charge" - 50 IGST
        row2 = ["Inward Supplies liable for Reverse Charge", None, 500, 50, 0, 0, 0]
        # Row 3: Irrelevant row
        row3 = ["Other Data", None, 100, 10, 0, 0, 0]
        
        mock_xlsx.read_sheet.return_value = [row1, row2, row3]
        
        analyzer = GSTR2BAnalyzer("dummy.xlsx")
        # Force use_light_parser = True to use our mock
        analyzer.use_light_parser = True
        
        # Override _extract_tax_block_strict to return the values from our mock rows
        # The real method parses text/indices. Let's mock it to make test redundant? 
        # No, better to patch the analyzer's _extract_tax_block_strict
        
        def side_effect(row):
            # Simple extractor for our mock rows (Indices: 3=IGST, 4=CGST, 5=SGST, 6=Cess)
            if "Reverse Charge" in str(row[0]):
                return {'igst': row[3], 'cgst': row[4], 'sgst': row[5], 'cess': row[6]}
            return None
            
        analyzer._extract_tax_block_strict = MagicMock(side_effect=side_effect)
        
        # Run
        result = analyzer.get_rcm_inward_supplies()
        
        print(f"Mock Result: {result}")
        
        # Assert Summation: 100 + 50 = 150
        self.assertEqual(result['igst'], 150)
        self.assertEqual(result['cgst'], 0)

if __name__ == '__main__':
    unittest.main()
