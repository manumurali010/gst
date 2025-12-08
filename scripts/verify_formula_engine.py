import sys
import os
import re

# Mocking QTableWidget item for testing logic without full GUI
class MockItem:
    def __init__(self, text):
        self._text = text
    def text(self):
        return self._text
    def setText(self, t):
        self._text = str(t)

class MockTable:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.items = {} # (r,c) -> MockItem
    
    def rowCount(self): return self.rows
    def columnCount(self): return self.cols
    
    def setItem(self, r, c, item):
        self.items[(r,c)] = item
        
    def item(self, r, c):
        return self.items.get((r,c))

def test_formula_engine():
    print("Testing Formula Engine...")
    
    # Setup Table 3x3
    # A1: 10, B1: 20, C1: =A1+B1
    # A2: 5,  B2: 5,  C2: =A2*B2
    
    table = MockTable(3, 3)
    table.setItem(0, 0, MockItem("10")) # A1
    table.setItem(0, 1, MockItem("20")) # B1
    table.setItem(0, 2, MockItem("0"))  # C1 (Formula target)
    
    table.setItem(1, 0, MockItem("5"))  # A2
    table.setItem(1, 1, MockItem("5"))  # B2
    table.setItem(1, 2, MockItem("0"))  # C2
    
    formulas = {
        (0, 2): "A1+B1",
        (1, 2): "A2*B2"
    }
    
    def get_cell_val(ref):
        match = re.match(r"([A-Z]+)([0-9]+)", ref.upper())
        if not match: return 0
        col_str, row_str = match.groups()
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord('A') + 1)
        col -= 1
        row = int(row_str) - 1
        item = table.item(row, col)
        if not item: return 0
        try: return float(item.text())
        except: return 0

    for (r, c), formula in formulas.items():
        def replace_ref(match):
            return str(get_cell_val(match.group(0)))
        
        eval_expr = re.sub(r"[A-Z]+[0-9]+", replace_ref, formula.upper())
        res = eval(eval_expr)
        table.item(r, c).setText(res)
        
    # Verify
    c1 = float(table.item(0, 2).text())
    c2 = float(table.item(1, 2).text())
    
    if c1 == 30.0:
        print("[PASS] Addition (A1+B1): 30.0")
    else:
        print(f"[FAIL] Addition: Expected 30.0, Got {c1}")
        
    if c2 == 25.0:
        print("[PASS] Multiplication (A2*B2): 25.0")
    else:
        print(f"[FAIL] Multiplication: Expected 25.0, Got {c2}")

if __name__ == "__main__":
    test_formula_engine()
