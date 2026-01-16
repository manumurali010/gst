import os
import re
import fitz  # PyMuPDF
import pandas as pd
import warnings
from datetime import datetime

# Suppress OpenPyXL warnings if any
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

class FileValidationService:
    """
    Reusable service for validating GSTIN and Financial Year in uploaded files.
    Enforces Class A (Strict) and Class B (Soft) validation rules.
    """

    @staticmethod
    def validate_file(file_path, file_key, expected_gstin, expected_fy, validation_mode='B'):
        """
        Validates the file against the expected case details using Strict Policy Matrix.
        """
        if not os.path.exists(file_path):
            return False, "CRITICAL", "File not found."

        # Map key to Matrix Type explicitly if typical keys are used
        key_lower = file_key.lower() if file_key else ""
        
        # Determine Matrix Category
        is_excel_strict = "gstr2" in key_lower # GSTR-2A / GSTR-2B
        is_excel_tax = "tax_liability" in key_lower # Tax Liability
        is_pdf_return = "gstr3b" in key_lower or "gstr1" in key_lower
        is_pdf_annual = "gstr9" in key_lower
        
        meta = {}
        ext = os.path.splitext(file_path)[1].lower()
        fatal_error = None
        
        try:
            if is_excel_strict:
                 # STRICT: Must check READ ME
                 meta = FileValidationService._scan_excel_readme(file_path, mandatory=True)
            elif is_excel_tax:
                 # SEMI-STRICT: Check READ ME if exists, else soft scan
                 meta = FileValidationService._scan_excel_readme(file_path, mandatory=False)
            elif ext == '.pdf':
                # PDF Best Effort
                file_type_pdf = "GSTR9" if is_pdf_annual else ("GSTR3B" if "gstr3b" in key_lower else "GSTR1")
                meta = FileValidationService._extract_pdf_metadata(file_path, file_type_pdf)
            else:
                 # Fallback
                 return True, "SUCCESS", "File category not strictly validated."
        except ValueError as ve:
             fatal_error = str(ve) # Capture specific error (e.g. Missing ReadMe)
        except Exception as e:
            if is_excel_strict: 
                 return False, "WARNING", [{"message": f"Could not read file structure (Corruption/Protect): {str(e)}", "warning_type": "READ_ERROR"}]
            return False, "CRITICAL", f"Error reading file validation metadata: {str(e)}"

        # Result Containers
        errors = []
        structured_warnings = []
        
        extracted_gstin = meta.get('gstin')
        extracted_fy = meta.get('fy')
        
        # 1. GSTIN Validation
        if not extracted_gstin:
             # Missing GSTIN
             if is_excel_strict:
                  msg = fatal_error if fatal_error else "Validation Failed: Could not extract GSTIN from 'READ ME' sheet."
                  return False, "CRITICAL", msg
             elif is_pdf_return or is_pdf_annual:
                  # Parsing Failure -> WARN
                  structured_warnings.append({
                      "file_key": file_key,
                      "warning_type": "GSTIN_NOT_VERIFIED",
                      "extracted_value": None,
                      "expected_value": expected_gstin,
                      "message": "Could not verify GSTIN (Extraction Failed). Please verify manually.",
                      "gstin_verification": "NOT_VERIFIED"
                  })
             elif is_excel_tax:
                  return False, "CRITICAL", "Validation Failed: Could not extract GSTIN from Tax Liability file."
             
        elif expected_gstin and extracted_gstin.upper() != expected_gstin.upper():
             # Mismatch -> ALWAYS BLOCK
             return False, "CRITICAL", f"GSTIN Mismatch: File belongs to {extracted_gstin}, but Case is {expected_gstin}."

        # 2. Tax Period / FY Validation
        if not extracted_fy:
             if is_excel_strict:
                 return False, "CRITICAL", "Validation Failed: Could not extract Financial Year from 'READ ME' sheet."
             elif is_pdf_annual:
                  structured_warnings.append({
                      "file_key": file_key,
                      "warning_type": "FY_MISSING",
                      "extracted_value": None,
                      "expected_value": expected_fy,
                      "message": "Could not verify Financial Year (Extraction Failed)."
                  })
             else: # GSTR-1/3B/Tax
                  structured_warnings.append({
                      "file_key": file_key,
                      "warning_type": "FY_MISSING",
                      "extracted_value": None,
                      "expected_value": expected_fy,
                      "message": "Could not verify Tax Period/FY."
                  })
                  
        elif expected_fy:
             match = FileValidationService._compare_fy(extracted_fy, expected_fy)
             if not match:
                  msg = f"Financial Year Mismatch: File appears to depend on {extracted_fy}, but Case is {expected_fy}."
                  if is_excel_strict or is_excel_tax or is_pdf_annual:
                       return False, "CRITICAL", msg
                  else:
                       structured_warnings.append({
                          "file_key": file_key,
                          "warning_type": "FY_MISMATCH",
                          "extracted_value": extracted_fy,
                          "expected_value": expected_fy,
                          "message": msg
                       })

        if errors:
            return False, "CRITICAL", "\n".join(errors)
        
        if structured_warnings:
            return False, "WARNING", structured_warnings

        return True, "SUCCESS", "Validation Successful"

    @staticmethod
    def _scan_excel_readme(file_path, mandatory=True):
        """
        Scans Excel for 'READ ME' sheet and extracts metadata using Anchor-Based Logic.
        Constraint: Scan first 50 rows, look for Keywords, extract value from same/next cell.
        """
        meta = {}

        xl = pd.ExcelFile(file_path)
        sheet_map = {s.lower(): s for s in xl.sheet_names}
        
        target_sheet = None
        if "read me" in sheet_map:
            target_sheet = sheet_map["read me"]
        elif "readme" in sheet_map:
            target_sheet = sheet_map["readme"]
            
        if mandatory and not target_sheet:
            # Immediate Failure for Strict Excel
            raise ValueError("Validation Failed: Mandatory 'READ ME' sheet not found.")
        
        if not target_sheet:
            # If not mandatory (Tax Liability fallback), try first sheet
            target_sheet = xl.sheet_names[0]

        # Read first 50 rows, all columns
        df = pd.read_excel(file_path, sheet_name=target_sheet, header=None, nrows=50)
        
        # Helper to normalize cell value
        def clean_val(v):
            if pd.isna(v): return ""
            return str(v).strip()
            
        def normalize_text(text):
             # Remove spaces, hyphens, colons to matching cleaner
             return re.sub(r'[\s\-\:]', '', text).upper()
            
        gstin_candidates = set()
        fy_candidates = set()
        
        # Regex for Normalized GSTIN (Strict Standard Pattern)
        # 2 Digits + 5 Chars + 4 Digits + 1 Char + 1 Char + 'Z' + 1 Char
        gstin_pat_str = r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}"
        
        # Iterate cells to find Anchors
        scan_range = 5 # Look-ahead range
        
        for idx, row in df.iterrows():
            for col_idx, cell_val in enumerate(row):
                val_str = clean_val(cell_val).lower()
                
                # 1. GSTIN Anchor
                if "gstin" in val_str:
                    # Strategy: Scan next N cells in Row and Column
                    
                    # Scan ROW (Right)
                    for offset in range(1, scan_range + 1):
                        if col_idx + offset < len(row):
                            target_val = clean_val(row.iloc[col_idx+offset])
                            norm_target = normalize_text(target_val)
                            # Check strict regex
                            g_match = re.search(gstin_pat_str, norm_target)
                            if g_match: 
                                gstin_candidates.add(g_match.group(0))

                    # Scan COLUMN (Below)
                    for offset in range(1, scan_range + 1):
                        if idx + offset < len(df):
                            target_val = clean_val(df.iloc[idx+offset, col_idx])
                            norm_target = normalize_text(target_val)
                            g_match = re.search(gstin_pat_str, norm_target)
                            if g_match: 
                                gstin_candidates.add(g_match.group(0))
                        
                    # Check Self (normalized) for cases like "GSTIN: 29..."
                    norm_self = normalize_text(val_str)
                    g_match_self = re.search(gstin_pat_str, norm_self)
                    if g_match_self: gstin_candidates.add(g_match_self.group(0))

                # 2. FY Anchor
                if "financial year" in val_str or "f.y." in val_str or "fy" in val_str:
                     fy_pat = r"20\d{2}-20\d{2}|20\d{2}-\d{2}"
                     
                     # Scan ROW
                     for offset in range(1, scan_range + 1):
                        if col_idx + offset < len(row):
                            target_val = clean_val(row.iloc[col_idx+offset])
                            f_match = re.search(fy_pat, target_val) # No heavy normalization for FY usually
                            if f_match: fy_candidates.add(f_match.group(0))
                            
                     # Scan COL
                     for offset in range(1, scan_range + 1):
                         if idx + offset < len(df):
                            target_val = clean_val(df.iloc[idx+offset, col_idx])
                            f_match = re.search(fy_pat, target_val)
                            if f_match: fy_candidates.add(f_match.group(0))
                        
                     f_match_self = re.search(fy_pat, val_str)
                     if f_match_self: fy_candidates.add(f_match_self.group(0))

        # Resolution
        if len(gstin_candidates) == 1:
            meta['gstin'] = list(gstin_candidates)[0]
        elif len(gstin_candidates) > 1:
            pass 
            
        if len(fy_candidates) == 1:
            meta['fy'] = list(fy_candidates)[0]
        elif len(fy_candidates) > 1:
            pass 
             
        return meta

    @staticmethod
    def _extract_pdf_metadata(file_path, file_type="GSTR3B"):
        """Extracts metadata from PDF headers using Regex (Robust)."""
        meta = {}
        try:
            doc = fitz.open(file_path)
            # Scan first 3 pages
            text = ""
            for i in range(min(3, len(doc))):
                text += doc[i].get_text() + "\n"
            doc.close()
            
            # RegEx Patterns
            gstin_pat = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"
            
            # 1. GSTIN (Anchor agnostic scan first, then filter)
            matches = re.findall(gstin_pat, text, re.IGNORECASE)
            unique = list(set([m.upper() for m in matches]))
            if len(unique) == 1:
                meta['gstin'] = unique[0]
            elif len(unique) > 1:
                # If multiple, look for "GSTIN:" anchor to disambiguate
                anchor_match = re.search(r"(?:GSTIN|GSTIN of the supplier|GSTIN of the Taxpayer)\s*[:\.]?\s*([0-9A-Z]{15})", text, re.IGNORECASE)
                if anchor_match:
                    meta['gstin'] = anchor_match.group(1).upper()
            
            # 2. FY / Tax Period
            
            # Helper to derive FY from Month/Year or Period Strings
            def derive_fy_val(m_str, y_str):
                try:
                     # Parse Month
                    if m_str.isdigit():
                         m = int(m_str)
                    else:
                         # Full or Abbr Month
                         try:
                             m = datetime.strptime(m_str[:3], "%b").month
                         except: return None
                    
                    y = int(y_str)
                    
                    # India FY: April (4) to March (3)
                    # If Month >= 4 (Apr-Dec): FY is Year-(Year+1) e.g. Apr 2018 -> 2018-19
                    if m >= 4:
                        start_y = y
                        end_y = y + 1
                    else:
                        start_y = y - 1
                        end_y = y
                    
                    short_end = str(end_y)[-2:]
                    return f"{start_y}-{short_end}"
                except: return None

            if file_type == "GSTR9":
                # Strict FY Search for Annual Return
                fy_match = re.search(r"(?:Financial Year|Year)\s*[:\.]?\s*(20\d{2}-[0-9]{2,4})", text, re.IGNORECASE)
                if fy_match:
                    meta['fy'] = fy_match.group(1)
            else:
                # Monthly Return (GSTR-1, GSTR-3B)
                
                # A. Check explicit FY string first (Strongest Signal)
                fy_match_explicit = re.search(r"(?:Financial Year|Year)\s*[:\.]?\s*(20\d{2}-[0-9]{2,4})", text, re.IGNORECASE)
                
                # B. Check "Month Year" (e.g. "April 2018")
                date_match = re.search(r"(April|May|June|July|August|September|October|November|December|January|February|March)\s*[\s\S]{0,5}\s*(20\d{2})", text, re.IGNORECASE)
                
                # C. Check "Period: MM/YYYY" (e.g. "04-2018")
                # Looks for MM followed by 20XX
                period_match = re.search(r"(?:Period|Month)\s*[:\-\.]?\s*(\d{2})[/\-](\d{4})", text, re.IGNORECASE)

                if fy_match_explicit:
                    meta['fy'] = fy_match_explicit.group(1)
                elif date_match:
                    # Derive from Month Name match
                    derived = derive_fy_val(date_match.group(1), date_match.group(2))
                    if derived: meta['fy'] = derived
                elif period_match:
                    # Derive from Numeric Period match
                    derived = derive_fy_val(period_match.group(1), period_match.group(2))
                    if derived: meta['fy'] = derived

        except Exception:
            pass
        return meta

    @staticmethod
    def _compare_fy(fy1, fy2):
        """Compare two FY strings robustly."""
        def normalize(f):
            if not f: return ""
            f = f.upper().replace("F.Y.","").replace("FY","").strip()
            # Expect YYYY-YY or YYYY-YYYY
            parts = f.split('-')
            if len(parts) == 2:
                start = parts[0].strip()
                end = parts[1].strip()
                if len(end) == 2:
                    end = start[:2] + end # 18 -> 2018
                return f"{start}-{end}"
            return f
            
        return normalize(fy1) == normalize(fy2)
