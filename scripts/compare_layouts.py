
import sys
import os
import json
sys.path.append(os.getcwd())
try:
    from src.utils.initialize_scrutiny_master import issues
except ImportError:
    # Handle running from scripts dir
    sys.path.append(os.path.dirname(os.getcwd()))
    from src.utils.initialize_scrutiny_master import issues

def compare_layouts():
    print("# Layout Discrepancy Report\n")
    print("| Issue ID | Row ID | Developer Console (grid_data) | Issue Card (table_definition) | Status |")
    print("|---|---|---|---|---|")
    
    for issue in issues:
        issue_id = issue['issue_id']
        grid_data = issue.get('grid_data', {})
        table_def = issue.get('table_definition', {})
        
        # Normalize grid_rows
        grid_rows = []
        if isinstance(grid_data, dict):
            grid_rows = grid_data.get('rows', [])
        elif isinstance(grid_data, list):
            # Old format: List of Lists
            # Skip header if it exists (usually first row)
            grid_rows = grid_data 

        def_rows = []
        if isinstance(table_def, dict):
             def_rows = table_def.get('rows', [])

        
        # Compare first few rows (assuming they map 1:1)
        max_len = max(len(grid_rows), len(def_rows))
        
        for i in range(max_len):
            g_row = grid_rows[i] if i < len(grid_rows) else None
            d_row = def_rows[i] if i < len(def_rows) else None
            
            # Extract Label/Description from Grid
            g_desc = "N/A"
            if g_row:
                if isinstance(g_row, dict):
                    # Standard Dict Row
                    if isinstance(g_row.get('description'), dict):
                        g_desc = g_row['description'].get('value', 'N/A')
                    else:
                        g_desc = g_row.get('description', 'N/A')
                elif isinstance(g_row, list):
                    # Legacy List Row: [{"value": "Desc"}, ...]
                    # Assuming first col is description
                    if len(g_row) > 0 and isinstance(g_row[0], dict):
                         g_desc = g_row[0].get('value', 'N/A')
                    
            d_desc = "N/A"
            if d_row:
                # table_definition uses 'label' key
                d_desc = d_row.get('label', 'N/A')
            
            # Compare
            status = "MATCH"
            if g_desc != d_desc:
                status = "**MISMATCH**"
                print(f"| {issue_id} | Row {i+1} | {g_desc} | {d_desc} | {status} |")
            
if __name__ == "__main__":
    compare_layouts()
