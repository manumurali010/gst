
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP12UI(unittest.TestCase):
    
    def setUp(self):
        self.parser = ScrutinyParser()
        
    @patch('fitz.open')
    def test_sop12_ui_structure_fail(self, mock_fitz):
        """
        Verify SOP-12 output payload structure for a FAIL scenario.
        Mock PDF content with tables 8A, 8B, 8C such that 8D is Negative (Excess Claim).
        8A = 1000.
        8B = 400.
        8C = 100.
        8D = 1000 - (400+100) = 500 (Positive/Matched). Wait.
        Logic: 8A - (8B + 8C).
        If 8D is POSITIVE -> Matched/Lapse.
        If 8D is NEGATIVE -> Excess Claim.
        
        Let's mock FAIL:
        8A = 100.
        8B = 100.
        8C = 100.
        8D = 100 - (100+100) = -100.
        Excess = 100.
        """
        mock_doc = MagicMock()
        mock_page = MagicMock()
        # Create text resembling GSTR-9
        # Regex patterns:
        # 8A: ITC as per GSTR-2A \(Table 3 & 5 thereof\)\s+([0-9,.]+)...
        # 8B: ITC as per sum total of 6\(B\) and 6\(H\) above...
        # 8C: next financial year upto specified period...
        
        pdf_text = """
        FORM GSTR-9
        Title Table 8
        ITC as per GSTR-2A (Table 3 & 5 thereof)   100.00   100.00   100.00   100.00
        ITC as per sum total of 6(B) and 6(H) above   100.00   100.00   100.00   100.00
        For the previous financial year
        Plus ITC on inward supplies (other than imports and inward supplies liable to reverse charge) but to be availed in the next financial year upto specified period   100.00   100.00   100.00   100.00
        """
        mock_page.get_text.return_value = pdf_text
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz.return_value = mock_doc
        
        extra_files = {'gstr9_yearly': 'dummy_gstr9.pdf'}
        
        # Act
        # parse_file calls _parse_gstr9_pdf if gstr9_yearly exists
        result = self.parser.parse_file("dummy.xlsx", extra_files)
        
        # Extract SOP-12 Issue
        issue = next(i for i in result['issues'] if i['issue_id'] == 'ITC_3B_2B_9X4')
        
        print("\n=== SOP-12 Payload Dump ===")
        print(issue)
        
        # Verify Logic
        # Shortfall: 100 (IGST) + 100 (CGST) + 100 (SGST) + 100 (Cess) = 400.
        self.assertEqual(issue['total_shortfall'], 400.0)
        self.assertEqual(issue['status'], 'fail')
        
        # Verify UI Contract (Canonical)
        st = issue['summary_table']
        self.assertIn('columns', st)
        self.assertIn('rows', st)
        self.assertNotIn('template_type', issue) # Should be removed or ignored if not in payload
        # Code explicitly returns 'template_type'?
        # Wait, I removed it in my edit? 
        # Checking implementation Step 890:
        # "template_type": "summary_3x4" was REMOVED.
        # It's NOT in the return dict.
        
        # Columns
        expected_cols = ["Description", "CGST", "SGST", "IGST", "Cess"] # Labels
        labels = [c['label'] for c in st['columns']]
        self.assertEqual(labels, expected_cols)
        
        # Rows
        rows = st['rows']
        self.assertEqual(len(rows), 4)
        
        # Row 0: 8A
        self.assertEqual(rows[0]['col0']['value'], "ITC as per Table 8A of GSTR 9")
        self.assertEqual(rows[0]['col1']['value'], "100.00") # CGST
        
        # Row 3: Excess (8D)
        self.assertEqual(rows[3]['col0']['value'], "ITC availed in Excess (8D)")
        self.assertEqual(rows[3]['col1']['value'], "100.00") # Excess is Abs(-100) = 100

if __name__ == '__main__':
    unittest.main()
