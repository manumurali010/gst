
import sys
import os
import unittest
import pandas as pd
from unittest.mock import MagicMock

# Mock PyQt6
class MockQObject:
    def __init__(self, *args, **kwargs): pass
sys.modules["PyQt6"] = MagicMock()
sys.modules["PyQt6.QtCore"] = MagicMock()
sys.modules["PyQt6.QtCore"].QObject = MockQObject
sys.modules["PyQt6.QtCore"].pyqtSignal = lambda *args: MagicMock()
sys.modules["PyQt6.QtWidgets"] = MagicMock()

# Mock OpenPyXL
class MockWorkbook:
    def __init__(self, *args, **kwargs):
        self.sheetnames = ['ISD', 'TDS', 'TCS', 'IMPG']
    def close(self): pass
    def __getitem__(self, key): return MagicMock()

mock_openpyxl = MagicMock()
sys.modules["openpyxl"] = mock_openpyxl
sys.modules["openpyxl"].load_workbook = MagicMock(return_value=MockWorkbook())

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.services.scrutiny_parser import ScrutinyParser
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

class TestExecutionPaths(unittest.TestCase):
    def test_markers(self):
        print("\n--- BEGIN EXECUTION TRACE ---")
        parser = ScrutinyParser()
        
        # We must instantiate Analyzer to trigger Phase-2
        analyzer = GSTR2AAnalyzer("dummy.xlsx")
        
        try:
            # Pass correct args
            issues = parser.parse_file("dummy.xlsx", gstr2a_analyzer=analyzer)
            print("Parser Result Issues:", issues)
        except RuntimeError as e:
            print(f"CRITICAL EXCEPTION CAUGHT: {e}")
        except Exception as e:
            print(f"Exception Caught: {e}")
            
if __name__ == '__main__':
    unittest.main()
