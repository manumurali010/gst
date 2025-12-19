import pandas as pd
import os
import json
import openpyxl
import warnings

# Suppress OpenPyXL DrawingML warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

class ScrutinyParser:
    """
    Parses 'Tax Liability and ITC Comparison' Excel sheets to identify discrepancies
    for ASMT-10 generation.
    Returns consolidated issues (one per category) with detailed monthly breakdowns.
    """
    
    def __init__(self):
        pass

    def validate_metadata(self, file_path, expected_gstin, expected_fy):
        """
        Validate that the uploaded file matches the expected GSTIN and FY.
        Target Sheet: 'Tax liability summary'
        Target Cells: A4 (GSTIN), D5 (Financial Year)
        """
        try:
            with pd.ExcelFile(file_path) as xl:
                # Find the summary sheet (case-insensitive match)
                summary_sheet = next((s for s in xl.sheet_names if "tax liability" in s.lower() and "summary" in s.lower()), None)
            
            if not summary_sheet:
                return False, "Sheet 'Tax liability summary' not found."
            
            # Load specific cells using openpyxl for precision
            wb = openpyxl.load_workbook(file_path, data_only=True)
            try:
                ws = wb[summary_sheet]
                
                # Cell A4: GSTIN : <Value>
                cell_a4 = str(ws['A4'].value).strip() if ws['A4'].value else ""
                extracted_gstin = ""
                if "GSTIN" in cell_a4:
                    parts = cell_a4.split(":")
                    if len(parts) > 1:
                        extracted_gstin = parts[1].strip().split()[0] # Take first word
                
                # Cell D5: Financial Year : <Value>
                cell_d5 = str(ws['D5'].value).strip() if ws['D5'].value else ""
                extracted_fy = ""
                if "Financial Year" in cell_d5:
                    parts = cell_d5.split(":")
                    if len(parts) > 1:
                        extracted_fy = parts[1].strip()
            finally:
                wb.close()

            # Validation
            errors = []
            if expected_gstin and extracted_gstin and expected_gstin.upper() != extracted_gstin.upper():
                errors.append(f"GSTIN Mismatch: File has {extracted_gstin}, Case is {expected_gstin}")
            
            if expected_fy and extracted_fy and expected_fy != extracted_fy:
                errors.append(f"FY Mismatch: File has {extracted_fy}, Case is {expected_fy}")
                
            if errors:
                return False, "\n".join(errors)
                
            return True, "Validation Successful"

        except Exception as e:
            return False, f"Validation Error: {str(e)}"

    def _extract_metadata(self, file_path):
        """Extract GSTIN, Financial Year, Legal Name from summary sheet"""
        try:
            df = pd.read_excel(file_path, sheet_name=0, header=None, nrows=10)
            metadata = {
                "gstin": "Unknown",
                "legal_name": "Unknown",
                "financial_year": "Unknown",
                "trade_name": "Unknown"
            }
            for r in range(len(df)):
                row_str = " ".join([str(x) for x in df.iloc[r].values if pd.notna(x)])
                if "GSTIN:" in row_str:
                    parts = row_str.split("GSTIN:")
                    if len(parts) > 1: metadata["gstin"] = parts[1].split()[0].strip()
                if "Legal name:" in row_str:
                    parts = row_str.split("Legal name:")
                    if len(parts) > 1: metadata["legal_name"] = parts[1].strip()
                if "Financial Year:" in row_str:
                    parts = row_str.split("Financial Year:")
                    if len(parts) > 1: metadata["financial_year"] = parts[1].split()[0].strip()
            return metadata
        except Exception as e:
            print(f"Metadata extraction error: {e}")
            return {}

    def _extract_issue_name(self, file_path, target_sheet):
        """Extract Issue Name from Row 4 (Index 3)"""
        try:
            df = pd.read_excel(file_path, sheet_name=target_sheet, header=None, nrows=5)
            # Row 4 is index 3
            val = str(df.iloc[3, 0]).strip()
            # Remove numbering if present (e.g. "2. Tax liability...")
            if ". " in val:
                return val.split(". ", 1)[1]
            return val
        except:
            return "Scrutiny Issue"

    def _parse_group_a_liability(self, file_path, sheet_keyword, default_category, template_type, target_cols_indices):
        """
        Group A Analysis: Month-wise Liability Logic.
        Target Indices: J,K,L (9,10,11) or F,G (5,6)
        Logic: Return Rows where Shortfall (-ve) < -1.0. 
        Now extracting 3B and Reference values by analyzing headers.
        """
        try:
            xl = pd.ExcelFile(file_path)
            target_sheet = next((s for s in xl.sheet_names if sheet_keyword.lower() in s.lower() and "summary" not in s.lower()), None)
            if not target_sheet: return None
            
            # 1. Read Data
            # Header is Row 4, 5 (Index 4, 5). Data starts Row 7 (Index 6)
            df = pd.read_excel(file_path, sheet_name=target_sheet, header=[4, 5])
            issue_name = self._extract_issue_name(file_path, target_sheet)
            
            # 2. Identify Column Mapping
            # We need to map (SourceType, TaxHead) -> Column Index
            col_map = {} # (source, head) -> index
            labels = {
                "3b": "Liability Declared in GSTR-3B",
                "ref": "Liability as per GSTR-1/RCM",
                "diff": "Short Payment (Difference)"
            }
            
            for i, col in enumerate(df.columns):
                # col is (Level0, Level1)
                l0 = str(col[0])
                full = str(col).upper()
                
                # Determine Tax Head
                head = "unknown"
                if "IGST" in full: head = "igst"
                elif "CGST" in full: head = "cgst"
                elif "SGST" in full or "UTGST" in full: head = "sgst"
                elif "CESS" in full: head = "cess"
                
                if head == "unknown": continue
                
                # Determine Source
                source = "unknown"
                # Difference: Must have SHORT/DIFFERENCE but NOT CUMULATIVE or % or PERFORMANCE (some sheets have it)
                if ("DIFFERENCE" in full or "SHORT" in full) and "CUMULATIVE" not in full and "%" not in full:
                    source = "diff"
                elif "3B" in full or "DECLARED" in full:
                    source = "3b"
                elif "REFERENCE" in full or "GSTR-1" in full or "RCM" in full or "EXPORT" in full or "SEZ" in full or "2B" in full:
                    source = "ref"
                
                if source != "unknown":
                    # Preference: Only map if not already mapped, or if more specific
                    # For Group A, usually the first match is the monthly one
                    if (source, head) not in col_map:
                        col_map[(source, head)] = i
                        # Update labels if l0 is meaningful
                        if l0 and "Unnamed" not in l0:
                            labels[source] = l0

            consolidated_rows = []
            total_shortfall = 0.0
            
            # 3. Iterate Rows
            for idx, row in df.iterrows():
                period_val = row.iloc[0]
                period = str(period_val).strip()
                if pd.isna(period_val) or "TOTAL" in period.upper() or period == "nan" or "TAX PERIOD" in period.upper():
                    continue
                
                # Extract values and check for issues
                vals_3b = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                vals_ref = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                vals_diff = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                
                row_liability = 0.0
                has_issue = False
                
                # Helper to get rounded float
                def get_val(src, head):
                    idx_val = col_map.get((src, head))
                    if idx_val is not None and idx_val < len(row):
                        v = row.iloc[idx_val]
                        try:
                            return round(float(v)) if pd.notna(v) else 0
                        except:
                            return 0
                    return 0

                for head in ["igst", "cgst", "sgst", "cess"]:
                    diff_val = get_val("diff", head)
                    # Logic: Difference is usually negative (-ve) in these sheets for shortfall
                    # User expects absolute liability if shortfall exists
                    if diff_val < -1:
                        has_issue = True
                        liability = abs(diff_val)
                        vals_diff[head] = liability
                        row_liability += liability
                        
                        # Also get context values
                        vals_3b[head] = get_val("3b", head)
                        vals_ref[head] = get_val("ref", head)
                    else:
                        # Even if no shortfall for this head, show 0 or actual if needed?
                        # User wants the table filled. Let's fill all context for this row if has_issue
                        pass

                if has_issue:
                    # Re-fill all context for the row to show a complete table
                    for head in ["igst", "cgst", "sgst", "cess"]:
                        vals_3b[head] = get_val("3b", head)
                        vals_ref[head] = get_val("ref", head)
                        # Ensure diff is consistent (Ref - 3B or similar? Actually trust the sheet's diff)
                        # but we show absolute shortfall as "demand".
                        diff_val = get_val("diff", head)
                        vals_diff[head] = abs(diff_val) if diff_val < -1 else 0

                    consolidated_rows.append({
                        "period": period,
                        "3b": vals_3b,
                        "ref": vals_ref,
                        "diff": vals_diff
                    })
                    total_shortfall += row_liability
            
            if consolidated_rows:
                return {
                    "category": default_category,
                    "description": issue_name,
                    "total_shortfall": round(total_shortfall),
                    "rows": consolidated_rows,
                    "template_type": template_type,
                    "labels": labels
                }
            return None
            
        except Exception as e:
            print(f"Group A Parse Error ({sheet_keyword}): {e}")
            return None

    def _parse_group_b_itc_summary(self, file_path, sheet_keyword, default_category, 
                                   auto_indices, claimed_indices, diff_indices, header_row_idx=5):
        """
        Group B Analysis: Yearly Summary ITC Logic.
        Logic: Extract totals for Auto-drafted, Claimed, and Difference from the 'Total' row.
        Descriptions: Extracted from header_row_idx (1-based, default 5=Row 5).
        """
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            target_sheet = next((s for s in wb.sheetnames if sheet_keyword.lower() in s.lower()), None)
            if not target_sheet: return None
            
            ws = wb[target_sheet]
            issue_name = self._extract_issue_name(file_path, target_sheet)
            
            def get_desc(col_idx):
                # col_idx is 0-indexed, openpyxl is 1-indexed
                val = ws.cell(row=header_row_idx, column=col_idx + 1).value
                if val is None: return "Unknown"
                # Text Replacement: during the month -> for the Financial year
                return str(val).strip().replace("during the month", "for the Financial year")

            row_labels = [
                get_desc(auto_indices[0]),
                get_desc(claimed_indices[0]),
                get_desc(diff_indices[0])
            ]
            
            # Read Headers for tax heads - Rows 4, 5, 6 (Indices 4, 5, 6)
            df = pd.read_excel(file_path, sheet_name=target_sheet, header=[4, 5, 6])
            
            # Find TOTAL Row
            total_row = None
            for idx, row in df.iterrows():
                val = str(row.iloc[0]).lower().strip()
                if val == "total":
                    total_row = row
                    break
            
            wb.close()
            
            if total_row is None: 
                return None
            
            # Helper to map column index to Tax Head
            def identify_head(col_tuple):
                full = str(col_tuple).upper()
                if "IGST" in full: return "igst"
                if "CGST" in full: return "cgst"
                if "SGST" in full or "UTGST" in full: return "sgst"
                if "CESS" in full: return "cess"
                return "unknown"

            # Helper to extract values for a set of indices
            def get_vals(row_data, indices):
                res = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                for idx in indices:
                    if idx >= len(row_data): continue
                    val = row_data.iloc[idx]
                    try: 
                        f_val = float(val) if pd.notna(val) else 0.0
                    except: 
                        f_val = 0.0
                    
                    head = identify_head(df.columns[idx])
                    if head != "unknown":
                        res[head] = f_val
                return res

            vals_auto = get_vals(total_row, auto_indices)
            vals_claimed = get_vals(total_row, claimed_indices)
            vals_diff = get_vals(total_row, diff_indices)
            
            # Apply rounding to all values
            for v_dict in [vals_auto, vals_claimed, vals_diff]:
                for k in v_dict:
                    v_dict[k] = round(v_dict[k])
            
            # Use total shortfall from difference columns
            total_shortfall = sum(max(0, v) for v in vals_diff.values())
            
            # Logic: If any difference is > 1.0, it's an issue
            if any(v > 1.0 for v in vals_diff.values()):
                rows_for_table = [
                    {"description": row_labels[0], "vals": vals_auto},
                    {"description": row_labels[1], "vals": vals_claimed},
                    {"description": row_labels[2], "vals": vals_diff, "highlight": True}
                ]
                
                return {
                    "category": default_category,
                    "description": issue_name,
                    "total_shortfall": total_shortfall,
                    "rows": rows_for_table,
                    "template_type": "itc_yearly_summary"
                }

            return None
            
        except Exception as e:
            print(f"Group B Parse Error ({sheet_keyword}): {e}")
            return None

    def parse_file(self, file_path):
        """
        Parses the Excel file and checks for all 6 discrepancies.
        """
        if not os.path.exists(file_path):
            return {"error": "File not found"}

        issues = []
        
        # --- Group A: Output Liability (Month-wise) ---
        # 1. Tax Liability (Other than Export/RCM)
        # J,K,L = 9, 10, 11
        res = self._parse_group_a_liability(file_path, "Tax Liability", "Short Declaration of Tax Liability", "liability_monthwise", [9, 10, 11])
        if res: issues.append(res)
        
        # 2. Reverse Charge
        # J,K,L = 9, 10, 11
        res = self._parse_group_a_liability(file_path, "Reverse Charge", "Short Payment of RCM Liability", "liability_monthwise", [9, 10, 11])
        if res: issues.append(res)
        
        # 3. Export & SEZ (Cols F,G = 5,6)
        res = self._parse_group_a_liability(file_path, "Export", "Short Payment on Export/SEZ Supplies", "liability_monthwise", [5, 6])
        if res: issues.append(res)
        
        # --- Group B: ITC (Yearly Summary) ---
        
        # 4. ITC Other (Indices: Auto=5-8, Claimed=1-4, Diff=9-12)
        res = self._parse_group_b_itc_summary(
            file_path, "ITC (Other", "Excess ITC Claimed (Other)", 
            [5, 6, 7, 8], [1, 2, 3, 4], [9, 10, 11, 12]
        )
        if res: issues.append(res)
        
        # 5. ITC IMPG (Indices: Auto=3-4, Claimed=1-2, Diff=5-6)
        res = self._parse_group_b_itc_summary(
            file_path, "ITC (IMPG", "Excess ITC Claimed (Import)", 
            [3, 4], [1, 2], [5, 6]
        )
        if res: issues.append(res)
        
        # 6. RCM ITC (Indices: Liability=5-8, Claimed=1-4, Diff=9-12)
        res = self._parse_group_b_itc_summary(
            file_path, "RCM_Liability_ITC", "Excess ITC Claimed (RCM)", 
            [5, 6, 7, 8], [1, 2, 3, 4], [9, 10, 11, 12]
        )
        if res: issues.append(res)

        summary = {
            "total_issues": len(issues),
            "total_tax_shortfall": sum([i["total_shortfall"] for i in issues])
        }
        
        return {
            "metadata": self._extract_metadata(file_path),
            "issues": issues,
            "summary": summary
        }
