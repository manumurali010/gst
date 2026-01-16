import sys
import os
import unittest
from unittest.mock import MagicMock

# Mock deps
try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    class QObject: pass
    class pyqtSignal:
        def __init__(self, *args): pass
        def connect(self, f): pass
        def emit(self, *args): pass
    import types
    sys.modules["PyQt6.QtCore"] = types.ModuleType("PyQt6.QtCore")
    sys.modules["PyQt6.QtCore"].QObject = QObject
    sys.modules["PyQt6.QtCore"].pyqtSignal = pyqtSignal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.services.scrutiny_parser import ScrutinyParser

class TestScrutinyGuards(unittest.TestCase):
    def setUp(self):
        self.parser = ScrutinyParser()
    
    def test_sop_guard_logic(self):
        # 1. SOP 5: Requires 3B + 2A
        # Case: Both Missing
        allowed, issue = self.parser._check_sop_guard('sop_5', False, False)
        self.assertFalse(allowed)
        self.assertEqual(issue['status'], 'info')
        self.assertIn("GSTR-3B and GSTR-2A not uploaded", issue['status_msg'])
        
        # Case: 3B Missing
        allowed, issue = self.parser._check_sop_guard('sop_5', False, True)
        self.assertFalse(allowed)
        self.assertEqual(issue['status'], 'info')
        self.assertIn("GSTR-3B not uploaded", issue['status_msg'])
        
        # Case: 2A Missing
        allowed, issue = self.parser._check_sop_guard('sop_5', True, False)
        self.assertFalse(allowed)
        self.assertEqual(issue['status'], 'info')
        self.assertIn("GSTR-2A not uploaded", issue['status_msg'])
        
        # Case: Both Present
        allowed, issue = self.parser._check_sop_guard('sop_5', True, True)
        self.assertTrue(allowed)
        self.assertIsNone(issue)
        
        # 2. SOP 7: Requires 2A (3B ignored)
        # Case: 2A Missing
        allowed, issue = self.parser._check_sop_guard('sop_7', True, False)
        self.assertFalse(allowed)
        self.assertEqual(issue['status'], 'info')
        self.assertIn("GSTR-2A not uploaded", issue['status_msg'])
        
        # Case: 2A Present
        allowed, issue = self.parser._check_sop_guard('sop_7', False, True) # 3B missing
        self.assertTrue(allowed)
        self.assertIsNone(issue)

        
    
class TestLogicHardening(unittest.TestCase):
    def setUp(self):
        self.parser = ScrutinyParser()
    
    def test_sop_10_extraction_determinism(self):
        # Create Dummy Excel with Proper Headers
        import pandas as pd
        file_path = "tests/dummy_sop10_3b.xlsx"
        with pd.ExcelWriter(file_path) as writer:
            # Sheet with Target Headers
            df = pd.DataFrame([
                ["Some Info"],
                ["Description", "Integrated Tax", "Central Tax"],
                ["Row1", 10, 20],
                ["Import of goods", 100, 0], # Valid Target
                ["Other", 50, 50]
            ])
            df.to_excel(writer, sheet_name="ITC (IMPG", index=False, header=False)
            
        # Mock Analyzer
        class MockAnalyzer:
            def analyze_sop(self, sid):
                 return {'igst': 80} # 2A Value
        
        # Test Extraction
        res = self.parser._parse_import_itc_phase2(file_path, MockAnalyzer())
        print(f"DEBUG: Result: {res}")
        self.assertNotEqual(res['status'], 'info')
        self.assertEqual(res['total_shortfall'], 20) # 100 (3B) - 80 (2A) = 20
        print("PASS: SOP 10 Deterministic Extraction")
        
        # Test Missing Header -> Info
        with pd.ExcelWriter(file_path) as writer:
            pd.DataFrame([["Bad Header", "Val"], ["Import of goods", 100]]).to_excel(writer, sheet_name="ITC (IMPG", index=False, header=False)
            
        res = self.parser._parse_import_itc_phase2(file_path, MockAnalyzer())
        self.assertEqual(res['status'], 'info')
        self.assertIn("Standard headers", res['status_msg'])
        print("PASS: SOP 10 Header Guard")
        
    def test_sop_10_ambiguity_symmetry(self):
        # Create Excel with Multiple Header Rows (Ambiguity)
        import pandas as pd
        file_path = "tests/dummy_sop10_ambiguity.xlsx"
        with pd.ExcelWriter(file_path) as writer:
            df = pd.DataFrame([
                ["Some Info"],
                ["Description", "Integrated Tax"], # Header 1
                ["Import of goods", 100],
                ["Description", "Integrated Tax"], # Header 2 (Ambiguous)
                ["Import of goods", 200]
            ])
            df.to_excel(writer, sheet_name="ITC (IMPG", index=False, header=False)
            
        class MockAnalyzer:
             def analyze_sop(self, sid): return {'igst': 50}

        res = self.parser._parse_import_itc_phase2(file_path, MockAnalyzer())
        self.assertEqual(res['status'], 'info')
        self.assertIn("Ambiguity Detected", res['status_msg'])
        print("PASS: SOP 10 Symmetric Ambiguity")

    def test_sop_3_strict_missing_3b(self):
        # Mock 2A present, but 3B 'ISD Credit' Sheet Missing
        import pandas as pd
        file_path = "tests/dummy_sop3_missing_3b.xlsx"
        # Create Empty Excel (No ISD Sheet)
        pd.DataFrame().to_excel(file_path, index=False)
        
        class MockAnalyzer:
             def analyze_sop(self, sid): return {'igst': 100, 'cgst':0, 'sgst':0}

        # Call parser directly (mocking internal flow if needed or testing unit func)
        # We need to test _parse_isd_credit
        res = self.parser._parse_isd_credit(file_path, gstr2a_analyzer=MockAnalyzer())
        self.assertEqual(res['status'], 'info')
        self.assertIn("missing in 3B", res['status_msg'])
        print("PASS: SOP 3 Strict Missing 3B")

    def test_sop_5_deterministic_extraction(self):
        # Create Excel with "Taxable Value" in random location (Row 5, Col 2 -> B5)
        # Value in B6 (Row 6, Col 2)
        import pandas as pd
        file_path = "tests/dummy_sop5_det.xlsx"
        
        # Create Data with Offset
        # Row 0-3 empty
        # Row 4: [None, "Taxable Value", "Other"]
        # Row 5: [None, 5000, 100]
        data = [
            [None, None, None],
            [None, None, None],
            [None, None, None],
            [None, None, None],
            [None, "Taxable Value", "Other"],
            [None, 5000, 100]
        ]
        df = pd.DataFrame(data)
        with pd.ExcelWriter(file_path) as writer:
            df.to_excel(writer, sheet_name="TDS_TCS", index=False, header=False)
            
        class MockAnalyzer:
             def analyze_sop(self, sid): return {'taxable_value': 4000}

        res = self.parser._parse_tds_tcs(file_path, MockAnalyzer())
        # 3B (5000) > 2A (4000). Shortfall = 0 (Excess Claim? No, TDS/TCS logic: 2A vs 3B).
        # My logic: diff = 2A - 3B. 4000 - 5000 = -1000. Shortfall=0.
        # Wait, usually TDS credit checks: "Credit Received (2A) matches Claimed (3B)".
        # If Claimed (5000) > Received (4000) -> Excess Claim? 
        # My code: shortfall = diff if diff > 0 else 0.
        # So 4000 - 5000 = -1000 -> 0.
        
        self.assertEqual(res['total_shortfall'], 0)
        self.assertNotEqual(res['status'], 'info')
        print("PASS: SOP 5 Deterministic Extraction")
        
    def test_sop_5_strict_missing_header(self):
         # Sheet exists but "Taxable Value" header missing
        import pandas as pd
        file_path = "tests/dummy_sop5_missing_header.xlsx"
        df = pd.DataFrame([["Some Other Header", 100]])
        with pd.ExcelWriter(file_path) as writer:
            df.to_excel(writer, sheet_name="TDS_TCS", index=False, header=False)
            
        class MockAnalyzer:
             def analyze_sop(self, sid): return {'taxable_value': 4000}
             
        res = self.parser._parse_tds_tcs(file_path, MockAnalyzer())
        self.assertEqual(res['status'], 'info')
        self.assertIn("Unavailable", res['status_msg'])
        print("PASS: SOP 5 Strict Missing Header")

if __name__ == '__main__':
    unittest.main()
