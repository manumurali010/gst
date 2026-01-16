import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.ui.scrutiny_tab import ScrutinyTab
    print("SUCCESS: ScrutinyTab imported without syntax errors.")
except ImportError as e:
    print(f"FAIL: ImportError - {e}")
except SyntaxError as e:
    print(f"FAIL: SyntaxError - {e}")
except IndentationError as e:
    print(f"FAIL: IndentationError - {e}")
except Exception as e:
    print(f"FAIL: Other Error - {e}")
