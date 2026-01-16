
import sys
import os
import pandas as pd

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Mock PyQt6
from unittest.mock import MagicMock
class MockQObject:
    def __init__(self, *args, **kwargs): pass

sys.modules["PyQt6"] = MagicMock()
sys.modules["PyQt6.QtCore"] = MagicMock()
sys.modules["PyQt6.QtCore"].QObject = MockQObject
sys.modules["PyQt6.QtCore"].pyqtSignal = lambda *args: MagicMock()
sys.modules["PyQt6.QtWidgets"] = MagicMock()

from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

FILE_PATH = "GSTR2A_32AAMFM4610Q1_2022-23_Apr-Mar.xlsx"

def run_debug():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    print(f"--- STARTING RCA ON {FILE_PATH} ---")
    analyzer = GSTR2AAnalyzer(FILE_PATH)
    
    sops = [3, 5, 7, 8, 10]
    
    for sop in sops:
        print(f"\n>>> ANALYZING SOP-{sop} <<<")
        try:
            res = analyzer.analyze_sop(sop)
            print(f"Result: {res}")
        except Exception as e:
            print(f"CRITICAL EXCEPTION in SOP-{sop}: {e}")

if __name__ == "__main__":
    run_debug()
