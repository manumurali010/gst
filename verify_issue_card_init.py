
import sys
import os
from PyQt6.QtWidgets import QApplication

# Mock environment
sys.path.append(os.getcwd())

from src.ui.issue_card import IssueCard

def test_init():
    app = QApplication(sys.argv)
    
    print("--- Test 1: Replay Mode ---")
    mock_template = {
        'issue_id': 'TEST', 
        'issue_name': 'Test Issue', 
        'grid_data': {
            'columns': [{'id': 'c0', 'label': 'Col 0'}],
            'rows': [{'c0': {'value': 'val'}}]
        }
    }
    try:
        # Note: In real app restore_snapshot calls __init__
        card = IssueCard(IssueCard._FACTORY_TOKEN, template=mock_template, is_replay=True)
        print("SUCCESS: Replay Init")
    except Exception as e:
        print(f"FAIL: Replay Init - {e}")
        import traceback
        traceback.print_exc()

    print("\n--- Test 2: Construction Mode ---")
    try:
        card2 = IssueCard(IssueCard._FACTORY_TOKEN, template=mock_template, is_replay=False)
        print("SUCCESS: Construction Init")
    except Exception as e:
        print(f"FAIL: Construction Init - {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_init()
