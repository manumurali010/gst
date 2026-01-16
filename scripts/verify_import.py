import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.ui.proceedings_workspace import ProceedingsWorkspace
    print("SUCCESS: ProceedingsWorkspace imported successfully.")
except ImportError as e:
    print(f"FAILURE: {e}")
except Exception as e:
    print(f"FAILURE: {e}")
