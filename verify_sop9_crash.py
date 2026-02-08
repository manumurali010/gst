
import sys
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.services.scrutiny_parser import ScrutinyParser

class TestSOP9CrashReproduction(unittest.TestCase):
    
    @patch('src.utils.pdf_parsers.parse_gstr3b_sop9_identifiers')
    @patch('src.utils.pdf_parsers.parse_gstr3b_pdf_table_4_a_1')
    @patch('src.utils.pdf_parsers.parse_gstr3b_pdf_table_4_a_2_3')
    @patch('src.utils.pdf_parsers.parse_gstr3b_pdf_table_4_a_4')
    @patch('src.utils.pdf_parsers.parse_gstr3b_pdf_table_4_a_5')
    def test_crash_scenario(self, mock_p5, mock_p4, mock_p23, mock_p1, mock_parser):
        print("\n--- Starting Crash Reproduction Test ---")
        
        # 1. Setup Mock PDF
        # ARN Date > Cut-off Date (Violation Scenario)
        # FY: 2022-23 (Standard)
        mock_parser.return_value = {
            "fy": "2022-23",
            "month": "April",
            "filing_date": "20/04/2023", # 20 April 2023
            "frequency": "Monthly",
            "error": None
        }
        
        # Mock ITC to trigger violation logic
        mock_p1.return_value = {"igst": 100}
        mock_p23.return_value = {}
        mock_p4.return_value = {}
        mock_p5.return_value = {}

        parser = ScrutinyParser()
        pdf_path = "dummy_crash.pdf"
        with open(pdf_path, 'w') as f: f.write("dummy")

        # 2. Setup User Configs (Cut-off Override)
        # User selects 30-03-2023 (Before ARN 20-04-2023)
        # This forces the violation path.
        user_cutoff = "30/03/2023"
        configs = {"sop9_cutoff_date": user_cutoff}
        
        try:
            print(f"Executing _parse_sop_9 with user_cutoff={user_cutoff}")
            # Call with BOTH argument binding and configs (as per UI logic)
            result = parser._parse_sop_9(
                [pdf_path], 
                user_cutoff_date=user_cutoff, 
                configs=configs
            )
            
            print("Execution Result Status:", result['status'])
            print("Execution Result Message:", result['status_msg'])
            
            # Check if violation was detected
            self.assertEqual(result['status'], 'fail')
            self.assertGreater(result['total_shortfall'], 0)
            
            # Check row details
            rows = result['summary_table']['rows']
            self.assertTrue(len(rows) > 0)
            print("Row 0:", rows[0])
            
            # Verify Cut-off column reflects USER date (Check Dict Structure)
            # col3 should be {"value": "30/03/2023"}
            self.assertEqual(rows[0]['col3']['value'], "30/03/2023")
            
            print(">>> SUCCESS: No Crash. Logic handled override correctly.")
            
        except Exception as e:
            print(f">>> CRITICAL FAILURE: Crashed with error: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"Crashed: {e}")
            
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

if __name__ == '__main__':
    unittest.main()
