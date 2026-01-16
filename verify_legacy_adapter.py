
import sys
import copy

# Mock Logic mirroring CompliancePointCard.set_status logic
def test_adapter_logic(details):
    print("--- Testing Adapter Logic ---")
    print(f"Input: keys={list(details.keys())}")
    if "tables" in details:
        print(f"Input 'tables' count: {len(details['tables'])}")

    # [LEGACY ADAPTER] Auto-convert old 'tables' payload to 'summary_table' (Native Grid)
    if "tables" in details and details["tables"] and "summary_table" not in details:
         print(f"DEBUG: Adapting legacy 'tables' to 'summary_table'")
         try:
             legacy_tables = details["tables"]
             adapter_rows = []
             adapter_cols = []
             
             if legacy_tables and isinstance(legacy_tables, list) and len(legacy_tables) > 0:
                 # Use columns from first table as master schema
                 if "columns" in legacy_tables[0]:
                     adapter_cols = legacy_tables[0]["columns"]
                 
                 for tbl in legacy_tables:
                     # Add Title Row (Section Header)
                     if "title" in tbl and tbl["title"]:
                         # Bold section header in col0
                         header_row = {}
                         # Populate col0 with title
                         header_row["col0"] = {"value": f"*** {tbl['title']} ***", "style": "bold"}
                         # Populate other cols empty
                         for col in adapter_cols:
                             if col["id"] != "col0":
                                 header_row[col["id"]] = {"value": ""}
                         adapter_rows.append(header_row)
                     
                     # Add Data Rows
                     if "rows" in tbl:
                         adapter_rows.extend(tbl["rows"])
                         
                     # Spacer Row
                     spacer = {c["id"]: {"value": ""} for c in adapter_cols}
                     adapter_rows.append(spacer)
                     
                 details["summary_table"] = {
                     "columns": adapter_cols,
                     "rows": adapter_rows
                 }
                 # CRITICAL: Remove 'tables' key
                 del details["tables"]
                 print(f"DEBUG: Adapter Success. Converted to Native Grid.")
         except Exception as e:
             print(f"ERROR: Legacy adapter failed: {e}")

    # [GUARD]
    if "tables" in details and details["tables"]:
        print("[FAIL] FAIL: Guardrail tripped! 'tables' key still present.")
        raise RuntimeError("Guardrail Tripped")
    else:
        print("[PASS] PASS: Guardrail passed.")

    if "summary_table" in details:
        print(f"[PASS] PASS: 'summary_table' created. Rows: {len(details['summary_table']['rows'])}")
        # Print first few rows to verify structure
        for i, row in enumerate(details['summary_table']['rows'][:5]):
            print(f"Row {i}: {row}")
    else:
         print("[FAIL] FAIL: 'summary_table' MISSING.")

def run_tests():
    # Test Case 1: SOP-5 Legacy Format (Multiple Tables)
    legacy_sop5 = {
        "tables": [
            {
                "title": "TDS Mismatch",
                "columns": [{"id": "col0", "label": "Desc"}, {"id": "col1", "label": "Amt"}],
                "rows": [{"col0": {"value": "TDS Row 1"}, "col1": {"value": "100"}}]
            },
            {
                "title": "TCS Mismatch",
                "columns": [{"id": "col0", "label": "Desc"}, {"id": "col1", "label": "Amt"}],
                "rows": [{"col0": {"value": "TCS Row 1"}, "col1": {"value": "50"}}]
            }
        ]
    }
    
    print("\n[TEST 1] SOP-5 Legacy (Multiple Tables)")
    try:
        test_adapter_logic(copy.deepcopy(legacy_sop5))
    except RuntimeError:
        pass

    # Test Case 2: SOP-7 Legacy Format (Single Table)
    legacy_sop7 = {
        "tables": [
            {
                "title": "Cancelled Suppliers",
                "columns": [{"id": "col0"}, {"id": "col1"}, {"id": "col2"}],
                "rows": [{"col0": {"value": "GSTIN1"}, "col1": {"value": "INV1"}}]
            }
        ]
    }
    
    print("\n[TEST 2] SOP-7 Legacy (Single Table)")
    try:
        test_adapter_logic(copy.deepcopy(legacy_sop7))
    except RuntimeError:
        pass

if __name__ == "__main__":
    run_tests()
