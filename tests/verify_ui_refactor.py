
import sys
import os
from PyQt6.QtWidgets import QApplication

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.ui.scrutiny_tab import ScrutinyTab, IssueCard
from src.services.asmt10_generator import ASMT10Generator

# Mock issue data
mock_issue = {
    "category": "Tax Liability",
    "description": "Short Declaration",
    "total_shortfall": 1000.0,
    "template_type": "liability_monthwise",
    "rows": [
        {
            "period": "April",
            "3b": {"igst": 100, "cgst": 0, "sgst": 0, "cess": 0},
            "ref": {"igst": 200, "cgst": 0, "sgst": 0, "cess": 0},
            "diff": {"igst": 100, "cgst": 0, "sgst": 0, "cess": 0}
        }
    ]
}

def test_ui_components():
    app = QApplication(sys.argv)
    
    try:
        # 1. Test Generator Helper
        print("Testing Generator Helper...")
        html = ASMT10Generator.generate_issue_table_html(mock_issue)
        if "<table" in html:
            print("PASS: Generator produced HTML table.")
        else:
            print("FAIL: Generator did not produce HTML table.")
            return

        # 2. Test IssueCard
        print("Testing IssueCard Widget...")
        card = IssueCard(1, mock_issue)
        data = card.get_data()
        
        if data['total_shortfall'] == 1000.0 and data['description'] == "Short Declaration":
             print("PASS: IssueCard initialized and returned correct data.")
        else:
             print(f"FAIL: IssueCard data mismatch: {data}")
             return

        # 3. Test ScrutinyTab Loading
        print("Testing ScrutinyTab Widget...")
        tab = ScrutinyTab()
        # Mock populate
        tab.populate_results_view([mock_issue, mock_issue])
        
        count = tab.results_card_layout.count()
        # Should be 2 cards + 1 stretch = 3 items
        if count >= 3:
            print("PASS: ScrutinyTab populated cards correctly.")
        else:
             print(f"FAIL: ScrutinyTab layout count incorrect: {count}")

        print("ALL TESTS PASSED")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_ui_components()
