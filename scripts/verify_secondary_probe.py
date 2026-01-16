import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# Add src to path
sys.path.append(r"c:\Users\manum\.gemini\antigravity\scratch\gst")
sys.path.append(r"c:\Users\manum\.gemini\antigravity\scratch\gst\src")

from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

class TestSecondaryProbe(unittest.TestCase):
    def setUp(self):
        self.analyzer = GSTR2AAnalyzer("dummy.xlsx")
        self.analyzer.xl_file = MagicMock()
        self.analyzer.xl_file.sheet_names = ['Sheet1']
        
    def create_dummy_df(self, rows_count, has_headers=False, start_row=0):
        # Create a DF. If has_headers is True, put headers at start_row.
        data = [[''] * 5 for _ in range(rows_count)]
        if has_headers:
             # Make sure it matches enough to be detected (>=2 matches)
             # Let's say Row `start_row` has headers
             if start_row < rows_count:
                 # Parent row
                 data[start_row] = ['Taxable Value', 'Integrated Tax', 'Central Tax', 'State Tax', 'Cess']
                 # Child row (empty or simple)
                 if start_row + 1 < rows_count:
                     data[start_row+1] = ['(Rs)', '(Rs)', '(Rs)', '(Rs)', '(Rs)']
                 
                 # Data probe row
                 if start_row + 2 < rows_count:
                     data[start_row+2] = [100, 18, 9, 9, 0]
                     
        return pd.DataFrame(data)

    def test_sop3_no_secondary_probe(self):
        """SOP-3: Secondary Probe should NEVER trigger, even if Pass 1 fails."""
        # Setup: Pass 1 returns no headers
        df_fail = self.create_dummy_df(15, has_headers=False)
        
        # Mock parse to return df_fail
        self.analyzer.xl_file.parse.side_effect = [df_fail]
        
        with patch.object(self.analyzer, '_scan_headers_in_df', return_value=({}, -1)) as mock_scan:
            headers, row = self.analyzer._scan_headers('Sheet1', sop_id='sop_3')
            
            # Assertions
            self.assertEqual(row, -1)
            # parse called once (Pass 1)
            self.assertEqual(self.analyzer.xl_file.parse.call_count, 1)
            # Verify call args for parse: nrows=15
            args, kwargs = self.analyzer.xl_file.parse.call_args
            self.assertEqual(kwargs.get('nrows'), 15)

    def test_sop5_pass1_success(self):
        """SOP-5: If Pass 1 succeeds, Pass 2 should NOT run."""
        # Setup: Pass 1 returns headers
        df_success = self.create_dummy_df(15, has_headers=True, start_row=5)
        
        self.analyzer.xl_file.parse.side_effect = [df_success]
        
        # Mock scanner to return success
        with patch.object(self.analyzer, '_scan_headers_in_df', return_value=({'some_header': 1}, 7)):
            headers, row = self.analyzer._scan_headers('Sheet1', sop_id='sop_5')
            
            self.assertEqual(row, 7)
            # parse called once
            self.assertEqual(self.analyzer.xl_file.parse.call_count, 1)

    def test_sop5_pass1_fail_pass2_run(self):
        """SOP-5: If Pass 1 fails, Pass 2 MUST run."""
        # Setup: Pass 1 returns empty headers, Pass 2 returns headers
        df_pass1 = self.create_dummy_df(15, has_headers=False)
        df_pass2 = self.create_dummy_df(30, has_headers=True, start_row=20)
        
        self.analyzer.xl_file.parse.side_effect = [df_pass1, df_pass2]
        
        # We need _scan_headers_in_df to return fail first, then success
        with patch.object(self.analyzer, '_scan_headers_in_df', side_effect=[({}, -1), ({'some_header': 1}, 22)]):
            headers, row = self.analyzer._scan_headers('Sheet1', sop_id='sop_5')
            
            self.assertEqual(row, 22)
            # parse called TWICE
            self.assertEqual(self.analyzer.xl_file.parse.call_count, 2)
            
            # Verify Pass 2 call args: nrows=30
            args_list = self.analyzer.xl_file.parse.call_args_list
            self.assertEqual(args_list[0].kwargs.get('nrows'), 15)
            self.assertEqual(args_list[1].kwargs.get('nrows'), 30)

    def test_sop10_pass1_fail_pass2_run(self):
        """SOP-10: Same as SOP-5."""
        df_pass1 = self.create_dummy_df(15, has_headers=False)
        df_pass2 = self.create_dummy_df(30, has_headers=True, start_row=20)
        
        self.analyzer.xl_file.parse.side_effect = [df_pass1, df_pass2]
        
        with patch.object(self.analyzer, '_scan_headers_in_df', side_effect=[({}, -1), ({'some_header': 1}, 22)]):
            headers, row = self.analyzer._scan_headers('Sheet1', sop_id='sop_10')
            
            self.assertEqual(row, 22)
            self.assertEqual(self.analyzer.xl_file.parse.call_count, 2)

if __name__ == '__main__':
    unittest.main()
