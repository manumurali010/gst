import sys
import os
import json
from PyQt6.QtWidgets import QApplication

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.ui.issue_card import IssueCard
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    app = QApplication(sys.argv)
    
    # Load Imported JSON
    try:
        with open('data/issues_from_excel.json', 'r') as f:
            data = json.load(f)
            issues = data['issues']
    except Exception as e:
        print(f"Failed to load JSON: {e}")
        sys.exit(1)
        
    if not issues:
        print("No issues found in JSON")
        sys.exit(1)
        
    # Pick the first issue (GSTR_3B_VS_GSTR_1)
    template = issues[0]
    print(f"Testing Issue: {template['issue_name']}")
    
    card = IssueCard(template)
    
    # Verify Table Creation
    if not hasattr(card, 'table'):
        print("Error: Table not created")
        sys.exit(1)
        
    rows = card.table.rowCount()
    print(f"Table Rows: {rows}")
    
    # Find Input Cells (Type 'input')
    # In the JSON, we saw inputs at:
    # Row 14 (Index 0 in grid): A14 (13), B14 (null), C14 (CGST)...
    # Wait, the JSON grid_data starts at row 14.
    # Let's find a cell that is an input.
    # In inspection: Row 14 has headers. Row 15 has data.
    # JSON grid_data[0] is Row 14.
    # JSON grid_data[1] is Row 15.
    # JSON grid_data[1][0] is A15 (14).
    # JSON grid_data[1][1] is B15 (Text).
    # JSON grid_data[1][2] is C15 (Empty/Input?).
    # Let's check JSON for C15:
    # "ref": "C15", "type": "empty" -> In my importer, empty cells are inputs?
    # Yes: `if val is None: cell_info["type"] = "empty"`
    # And in `IssueCard`, `ctype == 'input'` sets white background. 'empty' is default.
    # Wait, `IssueCard` code:
    # `ctype = cell_info.get('type', 'empty')`
    # `if ctype == 'input': ...`
    # My importer sets "empty" for None.
    # Does "empty" behave like input?
    # In `IssueCard`:
    # `item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)` is ONLY for static/formula.
    # So "empty" IS editable. Good.
    
    # Let's set inputs for C15 and C16 to test C17 (Difference)
    # C15 is grid_data[1][2] -> (1, 2) in table
    # C16 is grid_data[2][2] -> (2, 2) in table
    # C17 is grid_data[3][2] -> (3, 2) in table. Formula: =C15-C16
    
    print("Setting C15 = 1000")
    card.table.item(1, 2).setText("1000")
    
    print("Setting C16 = 400")
    card.table.item(2, 2).setText("400")
    
    # Check C17
    c17_item = card.table.item(3, 2)
    print(f"C17 Value: {c17_item.text()}")
    
    if c17_item.text() == "600.0" or c17_item.text() == "600":
        print("SUCCESS: Formula Calculated Correctly (1000 - 400 = 600)")
    else:
        print(f"FAILURE: Expected 600, got {c17_item.text()}")
        sys.exit(1)
        
    # Check Totals Signal
    # We need to see if `valuesChanged` was emitted.
    # Since we can't easily check signal history in this script without a slot,
    # we'll check the internal variables or labels.
    
    # Check Tax Label
    # Tax Mapping in JSON was null for this issue.
    # So Tax Label should be 0.
    print(f"Tax Label: {card.lbl_tax.text()}")
    
    # If we want to test mapping, we'd need to manually patch the template in this script
    # or rely on the fact that the calculation engine works.
    
    print("Verification Passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
