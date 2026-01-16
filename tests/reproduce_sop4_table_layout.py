import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Add project root (gst folder) to path (1 level up from tests/)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP4Layout(unittest.TestCase):

    def test_sop4_table_structure(self):
        """Test that SOP-4 generates a 4-row table with specific labels."""
        
        parser = ScrutinyParser()
        
        # Mocking the Excel reading process by patching pd.read_excel
        # We need to mock _identify_tax_head as well since it's used in the method
        
        with patch('pandas.read_excel') as mock_read_excel:
            # Setup mock DF
            # Structure: Period, ITC Available (Ref), ITC Claimed (3B), Difference
            data = {
                'Tax Period': ['April', 'May'],
                'ITC Available (IGST)': [100, 100],
                'ITC Available (CGST)': [100, 100],
                'ITC Available (SGST)': [100, 100], 
                'ITC Available (Cess)': [0, 0],
                'ITC Claimed (IGST)': [120, 80],
                'ITC Claimed (CGST)': [120, 80],
                'ITC Claimed (SGST)': [120, 80],
                'ITC Claimed (Cess)': [0, 0],
                'Difference (IGST)': [-20, 20], # -20 means 3B > 2B? Wait.
                # In real sheets: Difference = ITC Claimed (3B) - ITC Available (2B) usually? 
                # Or Available (2B) - Claimed (3B)?
                # The code says:
                # if diff_val > 1: has_issue = True; liability = diff_val
                # So positive difference = Liability = Excess Claim.
                # If 3B (120) > 2B (100) -> Diff should be 20 (Liability).
                # If 3B (80) < 2B (100) -> Diff should be -20 (No Liability).
                # Let's adjust mock data to match "Difference" column logic usually found in files.
                'Difference (IGST)': [20, -20],
                'Difference (CGST)': [20, -20],
                'Difference (SGST)': [20, -20],
                'Difference (Cess)': [0, 0]
            }
            # We need multi-index headers to simulate the real file structure or the code's expectation
            # The code tries header=[4,5,6] then [4,5].
            # Let's mock the dataframe returned by read_excel to simply have flat columns that match the logic's "full name" check
            
            # Actually, standardizing the mock is tricky because the parser operates on raw excel logic heavily.
            # But the parser has a logic: 
            # col_map[(source, head)] = i
            # It iterates columns.
            
            # Let's construct a DF that mimics the read result
            df = pd.DataFrame(data)
            # Rename columns to trigger logic
            # Source detection: '2B' -> ref, '3B' -> 3b, 'DIFFERENCE' -> diff
            df.columns = [
                'Tax Period', 
                'GSTR-2B IGST', 'GSTR-2B CGST', 'GSTR-2B SGST', 'GSTR-2B Cess',
                'GSTR-3B IGST', 'GSTR-3B CGST', 'GSTR-3B SGST', 'GSTR-3B Cess',
                'Difference IGST', 'Difference CGST', 'Difference SGST', 'Difference Cess'
            ]
            
            mock_read_excel.return_value = df
            
            # Mock openpyxl to return valid sheet names and cell values
            with patch('openpyxl.load_workbook') as mock_load_workbook:
                # Create a mock Workbook object
                mock_wb_obj = MagicMock()
                mock_wb_obj.sheetnames = ['ITC Data']
                
                # Create a mock Worksheet object
                mock_ws = MagicMock()
                mock_wb_obj.__getitem__.return_value = mock_ws
                
                # Configure load_workbook to return our mock Workbook
                mock_load_workbook.return_value = mock_wb_obj
                
                # Mock cell values for labels
                def get_cell(idx):
                    if idx == 'B5': return MagicMock(value='ITC Available')
                    if idx == 'F5': return MagicMock(value='ITC Claimed')
                    if idx == 'J5': return MagicMock(value='Difference')
                    return MagicMock(value='')
                mock_ws.__getitem__.side_effect = get_cell

                # Run Parser
                result = parser._parse_group_b_itc_summary(
                    file_path='dummy.xlsx',
                    sheet_keyword='ITC',
                    default_category='Category',
                    template_type='summary_3x4',
                    auto_indices=None,
                    claimed_indices=None,
                    diff_indices=None,
                    issue_id='ITC_3B_2B_OTHER'
                )
                
                if 'summary_table' not in result:
                    print("Parser returned Error Result:", result)
                    
                print("\nGenerated Table Rows:")
                for r in result['summary_table']['rows']:
                    print(r)
                
                rows = result['summary_table']['rows']
                
                # Assertions for New Layout
                # Expecting 4 rows for SOP-4
                if len(rows) != 4:
                    print(f"FAILURE: Expected 4 rows, got {len(rows)}")
                
                self.assertEqual(len(rows), 4, f"Expected 4 rows, got {len(rows)}")
                
                self.assertEqual(rows[0]['col0'], 'ITC Available')
                self.assertEqual(rows[1]['col0'], 'ITC Claimed')
                self.assertEqual(rows[2]['col0'], 'Difference (GSTR 3B-2B)')
                self.assertEqual(rows[3]['col0'], 'Liability')
                
                # Check Data
                # Row 2 (Difference): Should include negative values (arithmetic sum)
                # Diff IGST: April (20) + May (-20) = 0? 
                # Wait, the code sums them up.
                # Logic: 
                # totals[src][head] += val
                # totals['diff']['igst'] = 20 + (-20) = 0
                
                # Row 3 (Liability): Should ONLY be positive sum (accumulated in separate loop in original code, but we need to verify implementation)
                # Original Liability Logic:
                # if diff_val > 1: liability = diff_val; row_shortfall += liability
                # else: 0
                # So for April: 20. For May: 0. Total: 20.
                
                # So we expect:
                # Difference Row: 0
                # Liability Row: 20
                
                self.assertEqual(rows[2]['col1'], 0) # Diff IGST
                self.assertEqual(rows[3]['col1'], 20) # Liability IGST

if __name__ == '__main__':
    unittest.main()
