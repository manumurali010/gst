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
        Also extracts a 4x4 Summary Table (Description, CGST, SGST, IGST).
        Row Headers from B5, F5, J5.
        """
        try:
            # 1. Extract Headers using OpenPyXL (Precise cell reading)
            wb = openpyxl.load_workbook(file_path, data_only=True)
            target_sheet_name = next((s for s in wb.sheetnames if sheet_keyword.lower() in s.lower() and "summary" not in s.lower()), None)
            
            if not target_sheet_name: 
                wb.close()
                return None
            
            ws = wb[target_sheet_name]
            desc_3b = str(ws['B5'].value).strip() if ws['B5'].value else "Liability as per GSTR-3B"
            desc_ref = str(ws['F5'].value).strip() if ws['F5'].value else "Liability as per GSTR-1"
            desc_diff = str(ws['J5'].value).strip() if ws['J5'].value else "Difference"
            wb.close() # Close quickly to free resource for pandas

            # 2. Read Data with Pandas
            # Header is Row 4, 5 (Index 4, 5). Data starts Row 7 (Index 6)
            df = pd.read_excel(file_path, sheet_name=target_sheet_name, header=[4, 5])
            issue_name = self._extract_issue_name(file_path, target_sheet_name)
            
            # 3. Identify Column Mapping
            # We need to map (SourceType, TaxHead) -> Column Index
            col_map = {} # (source, head) -> index
            labels = {
                "3b": desc_3b,
                "ref": desc_ref,
                "diff": desc_diff
            }
            
            last_valid_l0 = ""
            
            for i, col in enumerate(df.columns):
                # col is (Level0, Level1)
                l0 = str(col[0]).strip()
                if "Unnamed" in l0 or l0 == "nan":
                    l0 = last_valid_l0
                else:
                    last_valid_l0 = l0
                    
                full = f"{l0} {col[1]}".upper()
                
                # Determine Tax Head
                head = "unknown"
                if "IGST" in full: head = "igst"
                elif "CGST" in full: head = "cgst"
                elif "SGST" in full or "UTGST" in full: head = "sgst"
                elif "CESS" in full: head = "cess"
                
                if head == "unknown": continue
                
                # Determine Source
                source = "unknown"
                # Difference: Must have SHORT/DIFFERENCE but NOT CUMULATIVE
                # Difference: Must have SHORT/DIFFERENCE but NOT CUMULATIVE
                if ("DIFFERENCE" in full or "SHORT" in full) and "CUMULATIVE" not in full:
                    source = "diff"
                elif "REFERENCE" in full or "GSTR-1" in full or "RCM" in full or "EXPORT" in full or "SEZ" in full or "2B" in full:
                    source = "ref"
                elif "3B" in full:
                    source = "3b"
                
                if source != "unknown":
                    # Preference: Only map if not already mapped, or if more specific
                    if (source, head) not in col_map:
                        col_map[(source, head)] = i
            
            consolidated_rows = []
            total_shortfall = 0.0
            
            # Totals Accumulators
            totals = {
                "3b": {"igst": 0.0, "cgst": 0.0, "sgst": 0.0},
                "ref": {"igst": 0.0, "cgst": 0.0, "sgst": 0.0},
                "diff": {"igst": 0.0, "cgst": 0.0, "sgst": 0.0}
            }
            
            # 4. Iterate Rows
            for idx, row in df.iterrows():
                period_val = row.iloc[0]
                period = str(period_val).strip()
                if pd.isna(period_val) or "TOTAL" in period.upper() or period == "nan" or "TAX PERIOD" in period.upper():
                    continue
                
                # Helper to get rounded float
                def get_val(src, head):
                    idx_val = col_map.get((src, head))
                    if idx_val is not None and idx_val < len(row):
                        v = row.iloc[idx_val]
                        try:
                            val = float(v) if pd.notna(v) else 0.0
                            return val
                        except:
                            return 0.0
                    return 0.0

                # Accumulate Totals
                for src in ["3b", "ref", "diff"]:
                    for head in ["igst", "cgst", "sgst"]:
                        val = get_val(src, head)
                        totals[src][head] += val

                # Check for Issues (Shortfall)
                vals_3b = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                vals_ref = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                vals_diff = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
                
                row_liability = 0.0
                has_issue = False

                for head in ["igst", "cgst", "sgst", "cess"]:
                    diff_val = get_val("diff", head)
                    if diff_val < -1: # Tolerance of 1
                        has_issue = True
                        liability = abs(diff_val)
                        vals_diff[head] = round(liability)
                        row_liability += liability
                        
                        vals_3b[head] = round(get_val("3b", head))
                        vals_ref[head] = round(get_val("ref", head))
                    else:
                         vals_diff[head] = 0

                if has_issue:
                    consolidated_rows.append({
                        "period": period,
                        "3b": vals_3b,
                        "ref": vals_ref,
                        "diff": vals_diff
                    })
                    total_shortfall += row_liability
            
            # Construct Summary Table Data
            # Format: [Desc, CGST, SGST, IGST]
            summary_rows = [
                {
                    "col0": desc_3b, 
                    "col1": round(totals["3b"]["cgst"]), 
                    "col2": round(totals["3b"]["sgst"]), 
                    "col3": round(totals["3b"]["igst"])
                },
                {
                    "col0": desc_ref, 
                    "col1": round(totals["ref"]["cgst"]), 
                    "col2": round(totals["ref"]["sgst"]), 
                    "col3": round(totals["ref"]["igst"])
                },
                {
                    "col0": desc_diff, 
                    "col1": round(totals["diff"]["cgst"]), 
                    "col2": round(totals["diff"]["sgst"]), 
                    "col3": round(totals["diff"]["igst"])
                }
            ]
            
            # Make sure we return something if found, even if no shortfall issues
            if consolidated_rows or total_shortfall >= 0:
                return {
                    "category": default_category,
                    "description": default_category, # Use canonical name for mapping
                    "original_header": issue_name, # Keep original just in case
                    "total_shortfall": round(total_shortfall),
                    "rows": consolidated_rows,
                    "template_type": template_type,
                    "labels": labels,
                    "summary_table": {
                        "headers": ["Description", "CGST", "SGST", "IGST"],
                        "rows": summary_rows
                    }
                }
            return None
            
        except Exception as e:
            print(f"Group A Parse Error ({sheet_keyword}): {e}")
            return None

    def _parse_rcm_liability(self, file_path):
        """
        SOP Point 2: RCM Liability (3B) vs ITC Claimed (3B).
        Target Sheet: 'RCM_LIABILITY_ITC'
        Cols B-E: ITC Claimed (IGST, CGST, SGST, CESS)
        Cols F-I: Liability Declared (IGST, CGST, SGST, CESS)
        Cols J-M: Difference (ITC - Liability)
        """
        try:
            # 1. Identify Sheet
            wb = openpyxl.load_workbook(file_path, data_only=True)
            target_sheet_name = next((s for s in wb.sheetnames if "RCM" in s.upper() and "ITC" in s.upper()), None)
            
            if not target_sheet_name:
                wb.close()
                return None
            
            # Read Headers for Description (Row 5/6 in Excel -> Index 4/5)
            ws = wb[target_sheet_name]
            # B5: ITC Claimed Description
            desc_itc = str(ws['B5'].value).strip() if ws['B5'].value else "ITC Claimed (4A2 + 4A3)"
            # F5: Liability Description
            desc_liab = str(ws['F5'].value).strip() if ws['F5'].value else "RCM Liability (3.1 d)"
            # J5: Diff Description
            desc_diff = str(ws['J5'].value).strip() if ws['J5'].value else "Difference"
            wb.close()
            
            # 2. Read Data
            df = pd.read_excel(file_path, sheet_name=target_sheet_name, header=[4, 5])
            
            # 3. Map Columns
            # We want to identify the broad groups (ITC, Liab, Diff) and then specific tax heads.
            # Strategy: Search for keywords in Level 0 header.
            col_map = {} # (group, head) -> index
            
            # Heuristic for Tax Head
            def get_head(col_name):
                cn = str(col_name).upper()
                if "IGST" in cn: return "igst"
                if "CGST" in cn: return "cgst"
                if "SGST" in cn: return "sgst"
                if "CESS" in cn: return "cess"
                return None
                
            last_l0 = ""
            for i, col in enumerate(df.columns):
                l0 = str(col[0]).strip()
                if "Unnamed" in l0 or l0 == "nan":
                    l0 = last_l0
                else:
                    last_l0 = l0
                
                full_l0 = l0.upper()
                head = get_head(col[1])
                if not head: continue
                
                group = None
                if "ITC CLAIMED" in full_l0:
                    group = "itc"
                elif "REVERSE CHARGE" in full_l0 and "LIABILITY" in full_l0:
                    group = "liab"
                elif "SHORTFALL" in full_l0 or "EXCESS" in full_l0:
                    if "CUMULATIVE" not in full_l0:
                        group = "diff"
                
                if group:
                     col_map[(group, head)] = i

            # 4. Process Rows
            consolidated_rows = []
            total_shortfall = 0.0
            
            # Accumulators for Summary
            totals = {
                "itc": {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
                "liab": {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
                "diff": {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
            }
            
            for idx, row in df.iterrows():
                period_val = row.iloc[0]
                period = str(period_val).strip()
                if pd.isna(period_val) or "TOTAL" in period.upper() or period == "nan" or "TAX PERIOD" in period.upper():
                    continue

                def get_val(grp, hd):
                    idx_c = col_map.get((grp, hd))
                    if idx_c is not None and idx_c < len(row):
                        v = row.iloc[idx_c]
                        try: return float(v) if pd.notna(v) else 0.0
                        except: return 0.0
                    return 0.0
                
                # Accumulate Totals
                for grp in ["itc", "liab", "diff"]:
                    for hd in ["igst", "cgst", "sgst", "cess"]:
                        val = get_val(grp, hd)
                        totals[grp][hd] += val
                
                # Check for Issues
                # Issue if Difference (ITC - Liability) > 0 (Excess Claim)
                # Or Difference != 0 depending on strictness.
                # Sheet says: Shortfall (-)/ Excess (+)
                # We care about Excess (+) -> Revenue Loss
                # But user wants to see table regardless.
                
                row_vals_itc = {h: round(get_val("itc", h)) for h in ["igst", "cgst", "sgst", "cess"]}
                row_vals_liab = {h: round(get_val("liab", h)) for h in ["igst", "cgst", "sgst", "cess"]}
                row_vals_diff = {h: round(get_val("diff", h)) for h in ["igst", "cgst", "sgst", "cess"]}
                
                # Identify if this row has an issue to flag in detailed breakdown
                # Flag if significant Excess (+)
                row_issue_amt = sum(max(0, v) for v in row_vals_diff.values()) # Only count Excess
                
                if row_issue_amt > 1.0: # Tolerance
                     consolidated_rows.append({
                        "period": period,
                        "3b": row_vals_liab, # Mapping '3b' to Liability for generic template compatibility?
                                             # Wait, generic template expects "3b", "ref", "diff".
                                             # Here "3b" is Liability, "ref" is ITC?
                                             # SOP 2: "Liability (3B) vs ITC (3B)".
                                             # Let's map "3b" -> Liability, "ref" -> ITC.
                        "ref": row_vals_itc,
                        "diff": row_vals_diff
                     })
                     total_shortfall += row_issue_amt

            # 5. Construct Summary Table
            # Rows: Liability, ITC, Difference
            summary_rows = [
                {
                    "col0": desc_liab,
                    "col1": round(totals["liab"]["cgst"]),
                    "col2": round(totals["liab"]["sgst"]),
                    "col3": round(totals["liab"]["igst"])
                },
                {
                    "col0": desc_itc,
                    "col1": round(totals["itc"]["cgst"]),
                    "col2": round(totals["itc"]["sgst"]),
                    "col3": round(totals["itc"]["igst"])
                },
                {
                    "col0": desc_diff, # "Shortfall/Excess"
                    "col1": round(totals["diff"]["cgst"]),
                    "col2": round(totals["diff"]["sgst"]),
                    "col3": round(totals["diff"]["igst"])
                }
            ]
            
            return {
                "category": "RCM Liability Mismatch",
                "description": "RCM Liability Mismatch",
                "original_header": "RCM Liability Analysis",
                "total_shortfall": round(total_shortfall),
                "rows": consolidated_rows,
                "template_type": "liability_monthwise", # Reusing Point 1 template
                "labels": {"3b": desc_liab, "ref": desc_itc, "diff": desc_diff},
                "summary_table": {
                    "headers": ["Description", "CGST", "SGST", "IGST"],
                    "rows": summary_rows
                }
            }

        except Exception as e:
            print(f"RCM Parse Error: {e}")
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

    def parse_2a_invoices(self, file_path):
        """
        Param 7 & 8: Parse GSTR-2A Invoice Level Excel.
        Looks for 'Supplier Registration Status' (Cancelled) and 'GSTR-3B Filing Status' (No).
        """
        try:
            df = pd.read_excel(file_path)
            # Normalize headers
            df.columns = [str(c).strip() for c in df.columns]
            
            # Find relevant column names (flexible matching)
            cancel_col = next((c for c in df.columns if "registration" in c.lower() and "status" in c.lower()), None)
            filing_col = next((c for c in df.columns if "3b" in c.lower() and "filing" in c.lower() and "status" in c.lower()), None)
            gstin_col = next((c for c in df.columns if "gstin" in c.lower() and "supplier" in c.lower()), "GSTIN of supplier")
            name_col = next((c for c in df.columns if "legal" in c.lower() and "name" in c.lower()), "Legal name of supplier")
            itc_col = next((c for c in df.columns if "itc" in c.lower() or "igst" in c.lower()), None) # Approximation

            cancelled_issues = []
            non_filer_issues = []
            
            for _, row in df.iterrows():
                # Approximation of ITC value for the row
                row_itc = float(row.get(itc_col, 0)) if itc_col else 0.0
                
                # Check for Cancelled Suppliers
                if cancel_col and "cancel" in str(row[cancel_col]).lower():
                    cancelled_issues.append({
                        "gstin": row.get(gstin_col, "Unknown"),
                        "name": row.get(name_col, "Unknown"),
                        "itc_availed": row_itc
                    })
                
                # Check for Non-Filers
                if filing_col and ("no" == str(row[filing_col]).lower().strip() or "not filed" in str(row[filing_col]).lower()):
                    non_filer_issues.append({
                        "gstin": row.get(gstin_col, "Unknown"),
                        "name": row.get(name_col, "Unknown"),
                        "itc_availed": row_itc
                    })
            
            # TODO: Aggregate by GSTIN and include in return
            return {
                "cancelled": cancelled_issues,
                "non_filers": non_filer_issues
            }
        except Exception as e:
            print(f"Error parsing 2A invoices: {e}")
            return {"error": str(e)}

    def parse_eway_bills(self, file_path):
        """Param 6: Compare E-Way Bill taxable value against reported."""
        try:
            df = pd.read_excel(file_path)
            # Find Net Taxable Value
            taxable_col = next((c for c in df.columns if "taxable" in str(c).lower() and "value" in str(c).lower()), None)
            tax_col = next((c for c in df.columns if "total" in str(c).lower() and "tax" in str(c).lower()), None)
            
            total_taxable = df[taxable_col].sum() if taxable_col else 0.0
            total_tax = df[tax_col].sum() if tax_col else 0.0
            
            return {
                "total_taxable": total_taxable,
                "total_tax": total_tax
            }
        except Exception as e:
            print(f"Error parsing E-Way Bills: {e}")
            return {"total_taxable": 0.0, "total_tax": 0.0}

    def parse_tcs_tds(self, file_path):
        """Param 5: Parse TDS/TCS credits from GSTR-2A Table 9."""
        try:
            df = pd.read_excel(file_path)
            # Find Gross Value/Taxable Value
            val_col = next((c for c in df.columns if "taxable" in str(c).lower() and "value" in str(c).lower()), None)
            total_val = df[val_col].sum() if val_col else 0.0
            
            return {"total_taxable_value": total_val}
        except Exception as e:
            print(f"Error parsing TDS/TCS: {e}")
            return {"total_taxable_value": 0.0}

    def calculate_interest_late_fees(self, main_file_path):
        """Param 12 & 13: Interest and Late Fees from Summary Comparison."""
        # This data is often in the 'Comparison Summary' sheet or specifically in 3B table 5.1
        # For now, return placeholders
        return {"interest_due": 0.0, "late_fee_due": 0.0}

    def parse_file(self, file_path, extra_files=None):
        """
        Parses the Excel file and checks for all 13 SOP discrepancies.
        extra_files: dict containing paths for 'gstr_2b', 'eway_bill', etc.
        """
        if not os.path.exists(file_path):
            return {"error": "File not found"}

        issues = []
        extra_files = extra_files or {}
        
        # --- Output Liability (Params 1, 2, 6) ---
        
        # 1. Outward Liability (3B vs 1)
        # 1. Outward Liability (3B vs 1)
        res = self._parse_group_a_liability(file_path, "Tax Liability", "Outward Liability Mismatch (GSTR-1 vs 3B)", "liability_monthwise", [9, 10, 11])
        if res: 
            # Always add Point 1 result so the table shows up, even if 0 shortfall
            issues.append(res)
        
        # 2. Reverse Charge (Param 2)
        # 2. Reverse Charge (Param 2)
        res = self._parse_rcm_liability(file_path)
        if res: issues.append(res)
        
        # 3. Export & SEZ
        res = self._parse_group_a_liability(file_path, "Export", "Short Payment on Export/SEZ Supplies", "liability_monthwise", [5, 6])
        if res: issues.append(res)
        
        # --- ITC (Params 4, 10, 3) ---
        
        # 4. All Other ITC (Param 4)
        res = self._parse_group_b_itc_summary(
            file_path, "ITC (Other", "Excess ITC Claimed (3B vs 2B)", 
            [5, 6, 7, 8], [1, 2, 3, 4], [9, 10, 11, 12]
        )
        if res: issues.append(res)
        
        # 5. Import ITC (Param 10)
        res = self._parse_group_b_itc_summary(
            file_path, "ITC (IMPG", "Import ITC Mismatch (3B vs ICEGATE)", 
            [3, 4], [1, 2], [5, 6]
        )
        if res: issues.append(res)
        
        # 6. RCM ITC
        res = self._parse_group_b_itc_summary(
            file_path, "RCM_Liability_ITC", "Excess ITC Claimed (RCM)", 
            [5, 6, 7, 8], [1, 2, 3, 4], [9, 10, 11, 12]
        )
        if res: issues.append(res)

        # 7. ISD Credit (Param 3)
        # Attempt to isolate ISD if possible, otherwise placeholder or part of 'Other'
        # Logic: Looking for ISD specific columns in 'ITC (Other than IMPG)'
        
        # --- Advanced Checks (Params 5-9, 11-13) ---

        # 8 & 9. Cancelled & Non-Filers (Params 7, 8)
        if 'gstr_2a_invoices' in extra_files:
            res_2a = self.parse_2a_invoices(extra_files['gstr_2a_invoices'])
            if res_2a.get("cancelled"):
                issues.append({
                    "category": "Ineligible ITC",
                    "description": "ITC from Cancelled Suppliers",
                    "total_shortfall": sum(x.get("itc_availed", 0) for x in res_2a["cancelled"]),
                    "rows": res_2a["cancelled"],
                    "template_type": "ineligible_itc"
                })
            if res_2a.get("non_filers"):
                issues.append({
                    "category": "Ineligible ITC",
                    "description": "ITC from Non-Filing Suppliers",
                    "total_shortfall": sum(x.get("itc_availed", 0) for x in res_2a["non_filers"]),
                    "rows": res_2a["non_filers"],
                    "template_type": "ineligible_itc"
                })

        # 10. E-Way Bill (Param 6)
        if 'eway_bill_summary' in extra_files:
            res_ewb = self.parse_eway_bills(extra_files['eway_bill_summary'])
            if res_ewb["total_tax"] > 0:
                 issues.append({
                    "category": "E-Way Bill Mismatch",
                    "description": "E-Way Bill vs GSTR-1 Mismatch",
                    "total_shortfall": 0.0,
                    "template_type": "eway_bill"
                })

        # 11. TDS/TCS (Param 5)
        if 'tds_tcs_credit' in extra_files:
            res_tcs = self.parse_tcs_tds(extra_files['tds_tcs_credit'])
            if res_tcs["total_taxable_value"] > 0:
                issues.append({
                    "category": "TDS/TCS Mismatch",
                    "description": "TDS/TCS Credit Mismatch",
                    "total_shortfall": 0.0,
                    "template_type": "tds_tcs"
                })

        # 12 & 13. Interest & Late Fees (Params 12, 13)
        # Check if interest/late fee is needed based on previous analysis
        interest_res = self.calculate_interest_late_fees(file_path)
        if interest_res["interest_due"] > 0:
            issues.append({
                "category": "Interest",
                "description": "Interest on Delayed Filing",
                "total_shortfall": interest_res["interest_due"],
                "template_type": "interest"
            })

        summary = {
            "total_issues": len(issues),
            "total_tax_shortfall": sum([i.get("total_shortfall", 0) for i in issues])
        }
        
        return {
            "metadata": self._extract_metadata(file_path),
            "issues": issues,
            "summary": summary
        }
