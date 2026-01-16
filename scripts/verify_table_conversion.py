
import sys
import os
import json

# Mock self for testing methods
class MockWorkspace:
    def __init__(self):
        self.proceeding_id = "TEST_PROC_ID"
        self.proceeding_data = {"source_scrutiny_id": "TEST_SCRUTINY_ID"}

    def _normalize_summary_table(self, summary_table: dict) -> dict:
        headers = summary_table.get('headers', [])
        rows_data = summary_table.get('rows', [])
        columns = []
        for i, h in enumerate(headers):
            h_upper = str(h).upper()
            col = {"id": f"col_{i}", "label": str(h)}
            if i == 0:
                col["id"] = "label"
                col["static"] = True
            elif "IGST" in h_upper: col["tax_head"] = "IGST"; col["id"] = "igst"
            elif "CGST" in h_upper: col["tax_head"] = "CGST"; col["id"] = "cgst"
            elif "SGST" in h_upper: col["tax_head"] = "SGST"; col["id"] = "sgst"
            elif "CESS" in h_upper: col["tax_head"] = "CESS"; col["id"] = "cess"
            columns.append(col)
        normalized_rows = []
        num_rows = len(rows_data)
        for i, row in enumerate(rows_data):
            label = str(row[0]) if isinstance(row, list) and len(row) > 0 else ""
            values = row[1:] if isinstance(row, list) else []
            role = "BASE"
            if num_rows >= 3:
                if i == num_rows - 1:
                    label_upper = label.upper()
                    if "TOTAL" in label_upper: role = "TOTAL"
                    else: role = "DIFFERENCE"
            normalized_rows.append({"role": role, "label": label, "values": values})
        return {"columns": columns, "rows": normalized_rows}

    def _convert_normalized_to_grid(self, normalized_table: dict) -> list:
        columns = normalized_table["columns"]
        rows = normalized_table["rows"]
        grid_data = []
        header_row = []
        for col in columns:
            header_row.append({"value": col["label"], "type": "static", "style": "header"})
        grid_data.append(header_row)
        for norm_row in rows:
            grid_row = []
            role = norm_row["role"]
            label = norm_row["label"]
            values = norm_row["values"]
            grid_row.append({"value": label, "type": "static"})
            for i, val in enumerate(values):
                col_idx = i + 1
                if col_idx >= len(columns): break
                col_meta = columns[col_idx]
                tax_head = col_meta.get("tax_head")
                cell = {"value": val}
                if role == "DIFFERENCE" and tax_head:
                    cell["type"] = "input"
                    cell["var"] = f"tax_{tax_head.lower()}"
                else:
                    cell["type"] = "static"
                grid_row.append(cell)
            grid_data.append(grid_row)
        return grid_data

# Test Data
summary_table = {
  "headers": ["Description", "IGST", "CGST", "SGST", "CESS"],
  "rows": [
    ["As per GSTR-1", 1000, 500, 500, 0],
    ["As per GSTR-3B", 800, 400, 400, 0],
    ["Difference", 200, 100, 100, 0]
  ]
}

ws = MockWorkspace()
normalized = ws._normalize_summary_table(summary_table)
print("Normalized Table:")
print(json.dumps(normalized, indent=2))

grid = ws._convert_normalized_to_grid(normalized)
print("\nGrid Data:")
for r in grid:
    print(r)

# Check bindings
diff_row = grid[3]
print("\nDifference Row Bindings:")
for cell in diff_row:
    if "var" in cell:
        print(f"Cell value {cell['value']} bound to {cell['var']}")
