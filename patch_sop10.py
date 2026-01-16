
import os

TARGET_FILE = r"C:\Users\manum\.gemini\antigravity\scratch\gst\src\services\scrutiny_parser.py"

NEW_IMPL = r'''    def _parse_import_itc_phase2(self, file_path, gstr2a_analyzer, gstr3b_pdf_paths=None):
        """
        SOP 10 Isolated Logic: 3B vs 2A (IMPG).
        Now supports GSTR-3B PDF (Table 4(A)(1)) aggregation.
        """
        try:
             # 1. Get 2A/2B Data
             print(f"DEBUG: Invoking analyze_sop(10)...")
             print("DISPATCH_MARKER: Calling analyzer for SOP-10")
             res_2a = gstr2a_analyzer.analyze_sop(10)
             if not res_2a or res_2a.get('error'):
                 err = res_2a.get('error') if res_2a else 'Unknown'
                 status, msg = self._map_analyzer_error(err)
                 
                 return {
                    "issue_id": "IMPORT_ITC_MISMATCH",
                    "category": "Import of Goods (3B vs ICEGATE)",
                    "description": "Import of Goods (3B vs ICEGATE)",
                    "status_msg": msg,
                    "status": status,
                    "error_details": err,
                    "total_shortfall": 0
                }

             val_2a = res_2a.get('igst', 0)

             # 2. Get 3B Data
             # Priority 1: GSTR-3B PDF (Table 4(A)(1))
             val_3b = 0.0
             found_3b_source = False
             
             if gstr3b_pdf_paths:
                 for path in gstr3b_pdf_paths:
                     try:
                         # Table 4(A)(1) - Import of Goods
                         res_3b_pdf = parse_gstr3b_pdf_table_4_a_1(path)
                         if res_3b_pdf:
                             val_3b += float(res_3b_pdf.get('igst', 0.0))
                             found_3b_source = True
                     except Exception as e:
                         print(f"SOP-10: Error parsing PDF {path}: {e}")
            
             # Priority 2: Excel Fallback (if no PDF data found)
             df = None
             if not found_3b_source:
                 # Match SOP-10 Sheet Name Logic with Analyzer
                 sop10_candidates = ["ITC (IMPG", "Input Tax Credit (Imports)", "Input Tax Credit (IMPG)"]
                 for cand in sop10_candidates: # Try robust list
                     try:
                         wb_tmp = openpyxl.load_workbook(file_path, read_only=True)
                         target_sheet = next((s for s in wb_tmp.sheetnames if any(k in s for k in ["ITC (IMPG", "Input Tax Credit (Imports)", "Input Tax Credit (IMPG)"])), None)
                         wb_tmp.close()
                         
                         if target_sheet:
                             df = pd.read_excel(file_path, sheet_name=target_sheet, header=None)
                             found_3b_source = True # Treat Excel as found source even if empty
                             break
                     except: pass
                 
             if not found_3b_source:
                  # No source available (No PDF, No Excel Sheet)
                  # If we have 2A data but no 3B, we can't do comparison.
                  # INFO state.
                  return {
                    "issue_id": "IMPORT_ITC_MISMATCH",
                    "category": "Import of Goods (3B vs ICEGATE)",
                    "description": "Import of Goods (3B vs ICEGATE)",
                    "status_msg": "GSTR-3B Data Not Available (Missing PDF or Excel Sheet)",
                    "status": "info",
                    "total_shortfall": 0
                }
             
             # If using Excel (df is not None), parse it
             if df is not None:
                 # --- EXCEL LOGIC BLOCK ---
                 val_3b = 0.0 # Reset to parse from Excel
                 
                 # Locate row via Header Search (Deterministic)
                 
                 # Headers to look for: 'Description', 'Integrated Tax' (or IGST), 'Central', 'State', 'Cess'
                 header_row_ids = []
                 
                 for i, row in df.iterrows():
                     row_vals = [str(x).lower() for x in row.values]
                     if any("description" in x for x in row_vals) and any("integrated" in x or "igst" in x for x in row_vals):
                         header_row_ids.append(i)
                 
                 # Ambiguity Check (Symmetry)
                 if len(header_row_ids) > 1:
                     return {
                        "issue_id": "IMPORT_ITC_MISMATCH",
                        "category": "Import of Goods (3B vs ICEGATE)",
                        "description": "Import of Goods (3B vs ICEGATE)",
                        "status_msg": "Ambiguity Detected in 3B File (Multiple ITC Header Rows)",
                        "status": "info",
                        "total_shortfall": 0
                     }
                     
                 if not header_row_ids:
                     # Header not found -> Template Mismatch -> Status INFO
                     return {
                        "issue_id": "IMPORT_ITC_MISMATCH",
                        "category": "Import of Goods (3B vs ICEGATE)",
                        "description": "Import of Goods (3B vs ICEGATE)",
                        "status_msg": "Standard headers (Description, Integrated Tax) not found in ITC sheet.",
                        "status": "info",
                        "total_shortfall": 0
                    }
    
                 header_row_idx = header_row_ids[0]
                 
                 # Identify columns from the unique header row
                 row_vals = [str(x).lower() for x in df.iloc[header_row_idx].values]
                 igst_col_idx = None
                 desc_col_idx = None
                 for c_idx, val in enumerate(row_vals):
                     if "description" in val: desc_col_idx = c_idx
                     if "integrated" in val or "igst" in val: igst_col_idx = c_idx
                 
                 # If Header found, find 'Import of goods' row below it
                 if igst_col_idx is not None:
                     for i in range(header_row_idx + 1, len(df)):
                         row = df.iloc[i]
                         desc_val = str(row[desc_col_idx]).lower() if desc_col_idx is not None else ""
                         if "import of goods" in desc_val:
                             # Found it.
                             try:
                                 val = float(df.iloc[i, igst_col_idx])
                                 if pd.isna(val): val = 0.0
                                 val_3b += val
                             except:
                                 pass
                             break
                 else:
                     # Should be caught by header_row_ids check above but safe guard
                     return {
                        "issue_id": "IMPORT_ITC_MISMATCH",
                        "category": "Import of Goods (3B vs ICEGATE)",
                        "description": "Import of Goods (3B vs ICEGATE)",
                        "status_msg": "Standard headers (Description, Integrated Tax) not found in ITC sheet.",
                        "status": "info",
                        "total_shortfall": 0
                    }
 
             # 3. Compare
             diff = val_3b - val_2a
             shortfall = diff if diff > 0 else 0
             
             return {
                "issue_id": "IMPORT_ITC_MISMATCH",
                "category": "Import of Goods (3B vs ICEGATE)",
                "description": "Import of Goods (3B vs ICEGATE)",
                "total_shortfall": round(shortfall),
                "rows": [
                    {"col0": "ITC Claimed in 3B", "igst": val_3b},
                    {"col0": "ITC Available in 2A", "igst": val_2a}
                ],
                "summary_table": {
                    "headers": ["Description", "IGST"],
                    "rows": [
                        {"col0": "ITC Claimed in 3B", "col1": val_3b},
                        {"col0": "ITC Available in 2A", "col1": val_2a},
                        {"col0": "Excess Claimed", "col1": shortfall}
                    ]
                },
                "status": "fail" if shortfall > 0 else "pass"
            }
             
        except Exception as e:
             # Catch-all for any pandas/analyzer crashes
             # Enforce single exit path: INFO
             status = "info" 
             msg = "Import (IMPG) data not available"
             
             # Log the raw error for debugging if needed, but UI sees CLEAN message.
             print(f"DEBUG: SOP-10 Exception caught: {str(e)}")
             
             return {
                "issue_id": "IMPORT_ITC_MISMATCH",
                "category": "Import of Goods (3B vs ICEGATE)",
                "description": "Import of Goods (3B vs ICEGATE)",
                "status_msg": msg, 
                "status": status,
                "total_shortfall": 0
            }
'''

def patch_file():
    try:
        # Read content
        with open(TARGET_FILE, 'rb') as f:
            content = f.read().decode('utf-8')
        
        # Locate Start
        start_marker = "def _parse_import_itc_phase2(self, file_path, gstr2a_analyzer"
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print("ERROR: Start marker not found!")
            return

        # Locate End (Start of next function)
        end_marker = "def _check_sop_guard(self, sop_id, has_3b, has_2a):"
        end_idx = content.find(end_marker)
        if end_idx == -1:
            print("ERROR: End marker not found!")
            return
            
        # Reconstruct
        # Ensure we keep the blank line before next function
        new_content = content[:start_idx] + NEW_IMPL + "\n\n    " + content[end_idx:]
        
        # Write back
        with open(TARGET_FILE, 'wb') as f:
            f.write(new_content.encode('utf-8'))
            
        print("SUCCESS: File patched.")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    patch_file()
