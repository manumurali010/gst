import fitz  # PyMuPDF
import re
import os
import logging
from src.utils.date_utils import normalize_financial_year

# Set up logger for PDF Parsers
logger = logging.getLogger("pdf_parsers")
if not logger.handlers:
    handler = logging.FileHandler("audit_log.txt")
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def _clean_amount(amt_str):
    if not amt_str: return 0.0
    # Handle spacing in standard Indian format that might occur (e.g. "1, 12, 123.00")
    # Our regex captures it, but we need to remove space before float conversion
    amt_str = amt_str.replace(' ', '').replace(',', '')
    try:
        return float(amt_str)
    except:
        return 0.0

def _extract_fy_from_text(text):
    """
    Robustly extract Financial Year string from arbitrary text.
    Handles: "Year 2022-23", "Financial Year: 2022-23", "Return Period March-2023", etc.
    """
    if not text: return None
    
    # 1. Look for explicit FY/Year pattern
    # Pattern: Year followed by YYYY-YY or YYYY-YYYY or YYYY
    pattern_fy = re.search(r"(?:Financial\s+)?Year\s*[:\-\s]*([\d\-]{4,9})", text, re.IGNORECASE)
    if pattern_fy:
        return pattern_fy.group(1).strip()
    
    # 2. Look for Return Period pattern (e.g. March-2023)
    pattern_rp = re.search(r"Return\s*Period\s*[:\-\s]*([A-Za-z]+\s*[\-]?\s*\d{4})", text, re.IGNORECASE)
    if pattern_rp:
        y_match = re.search(r"(\d{4})", pattern_rp.group(1))
        if y_match: return y_match.group(1)
        
    # 3. Aggressive numeric fallback in first 1000 chars
    pattern_agg = re.search(r"\b(20\d{2}-\d{2,4})\b", text[:1000])
    if pattern_agg: return pattern_agg.group(1)
    
    pattern_y = re.search(r"\b(20\d{2})\b", text[:1000])
    if pattern_y: return pattern_y.group(1)
    
    return None

def _extract_numbers_from_text(text):
    r"""
    Unified/Deterministic numeric extraction for SOP 11.
    Strictly enforces Indian Numbering System OR Integers.
    Regex: ((?:\d{1,3}(?:,\s*\d{2})*,\s*\d{3}|\d+)\.\d{2})
    Selection: Longest match wins.
    """
    # Strict Indian Regex mandated by user
    pattern = r"((?:\d{1,3}(?:,\s*\d{2})*,\s*\d{3}|\d+)\.\d{2})"
    
    # We find all matches in the text chunk
    matches = re.findall(pattern, text)
    
    if not matches:
        return []
        
    # [DETERMINISTIC SELECTION]
    # If the text chunk contains multiple numbers (e.g. a row with Taxable, IGST, etc),
    # re.findall returns them in order.
    # However, if we are parsing a *single* value context or need to be robust against partials:
    # Use re.finditer to get positions if needed, OR trust that findall returns non-overlapping matches from left to right.
    # For table parsers that expect a list of columns (Taxable, IGST, CGST...), we typically match numeric tokens.
    # The requirement "Always select the longest numeric token" applies when we are extracting a *single* entity or disambiguating.
    # But tables have multiple columns.
    # WAIT: The prompt said "If re.findall() is used... You MUST confirm... Selection must be: the longest match".
    # This implies we are extracting ONE value or tokenizing.
    # For table rows, we expect MULTIPLE values (Cols 1..5).
    # So we return ALL valid tokens found, but ensure each token captured is the "longest" version of itself (which regex greedy quantifiers handle).
    # IF the intent is to avoid splitting "1,12" and "77,521", the Regex structure `(?:\d{1,3}...` handles that validation.
    # The `max(matches, key=len)` rule seems specific to "Selection" of a single value?
    # Actually, let's look at `_parse_3_1_row`. It gets `post_text` (all columns).
    # It expects `nums` list.
    # So we return the list of matches. The Regex itself guarantees we don't pick "77,521" if "1,12,77,521" is present because `findall` consumes the full string if it matches the complex pattern.
    
    return matches

def parse_gstr3b_pdf_table_3_1_a(file_path):
    """
    Extracts Table 3.1(a) Outward taxable supplies.
    Uses robust dynamic column mapping to handle variations in tax head order.
    Returns: {taxable_value, igst, cgst, sgst, cess}
    """
    results = {"taxable_value": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
    if not file_path: return results

    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        # 1. Dynamic Header Mapping
        def find_header(pattern, text):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.start() if m else 999999

        headers = [
            ("igst", find_header(r"integrated\s*tax", full_text)),
            ("cgst", find_header(r"central\s*tax", full_text)),
            ("sgst", find_header(r"state(/ut)?\s*tax", full_text)),
            ("cess", find_header(r"cess", full_text))
        ]
        
        headers.sort(key=lambda x: x[1])
        detected_order = [h[0] for h in headers if h[1] < 999999]
        
        if len(detected_order) < 4:
            detected_order = ["igst", "cgst", "sgst", "cess"]

        # 2. Extract Data Row - Strict anchoring to "(a) Outward taxable supplies"
        pattern = r"\(a\)\s*Outward\s*taxable\s*supplies.*?((?:[\d,]+\.?\d*\s+){4}[\d,]+\.?\d*)"
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            nums = _extract_numbers_from_text(match.group(1))
            if len(nums) >= 5:
                # Column 0: Taxable Value
                results["taxable_value"] = _clean_amount(nums[0])
                # Columns 1..4: Taxes in detected order
                for i, tax_type in enumerate(detected_order):
                    if i+1 < len(nums):
                        results[tax_type] = _clean_amount(nums[i+1])
                return results

    except Exception as e:
        print(f"Error parsing GSTR-3B PDF Table 3.1(a): {e}")

    # Fallback/Not Found
    return None

def parse_gstr1_pdf_total_liability(file_path):
    """
    Extracts "Total Liability (Outward supplies other than Reverse charge)" from GSTR-1 PDF.
    Returns: { "igst": float, "cgst": float, "sgst": float, "cess": float }
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        target_label = r"Total\s*Liability\s*\(Outward\s*supplies\s*other\s*than\s*Reverse\s*charge\)"
        pattern = target_label + r".*?((?:[\d,]+\.?\d*\s+){1,10})"
        
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            # Observability: Log Matched Header
            print(f"DEBUG: [GSTR-1 Parser] Header Found: '{match.group(0)[:50]}...'")
            
            numbers_str = match.group(1)
            # [Audit Fix] Use unified extractor for safety
            nums = _extract_numbers_from_text(numbers_str)
            print(f"DEBUG: [GSTR-1 Parser] Raw Tokens Found ({len(nums)}): {nums}")
            
            if len(nums) == 4:
                # Exact match for IGST, CGST, SGST, Cess
                results["igst"] = _clean_amount(nums[0])
                results["cgst"] = _clean_amount(nums[1])
                results["sgst"] = _clean_amount(nums[2])
                results["cess"] = _clean_amount(nums[3])
                print(f"DEBUG: [GSTR-1 Parser] Extracted (4-token mode): {results}")
            elif len(nums) >= 5:
                # 5+ tokens: Assume first is Taxable Value
                # Map indices 1-4 to Taxes
                results["igst"] = _clean_amount(nums[1])
                results["cgst"] = _clean_amount(nums[2])
                results["sgst"] = _clean_amount(nums[3])
                results["cess"] = _clean_amount(nums[4])
                print(f"DEBUG: [GSTR-1 Parser] Extracted (5-token mode): {results}")
            else:
                print(f"DEBUG: [GSTR-1 Parser] Parsing Rejected. Insufficient tokens: Found {len(nums)}, Expected >=4.")
        else:
            print("DEBUG: [GSTR-1 Parser] Header Pattern NOT found in PDF text.")
            
    except Exception as e:
        print(f"Error parsing GSTR-1 PDF: {e}")
        
    return results

def parse_gstr3b_pdf_table_3_1_d(file_path):
    """
    Extracts RCM Liability from Table 3.1(d) of GSTR-3B PDF.
    Target Row: "(d) Inward supplies liable to reverse charge"
    Returns: { "igst": float, "cgst": float, "sgst": float, "cess": float }
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        # Pattern: "(d) Inward supplies (liable to reverse charge)" or similar variance
        # Followed by 5 numbers (Taxable, IGST, CGST, SGST, Cess)
        # Regex needs to be robust to whitespace and potential line breaks.
        # "Inward supplies \r\n (liable to reverse charge)"
        
        pattern = r"\(d\)\s*Inward\s*supplies.*?((?:[\d,]+\.?\d*\s+){4}[\d,]+\.?\d*)"
        
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match: # Added this if block to fix indentation
            # [SOP-11 FIX] Use unified extraction
            nums = _extract_numbers_from_text(match.group(1))
            
            if len(nums) >= 5:
                # Indices: 0=Taxable, 1=IGST, 2=CGST, 3=SGST, 4=Cess
                results["taxable_value"] = _clean_amount(nums[0])
                results["igst"] = _clean_amount(nums[1])
                results["cgst"] = _clean_amount(nums[2])
                results["sgst"] = _clean_amount(nums[3])
                results["cess"] = _clean_amount(nums[4])
                
    except Exception as e:
        print(f"Error parsing GSTR-3B PDF Table 3.1(d): {e}")
        
    return results

def parse_gstr3b_pdf_table_4_a_2_3(file_path):
    """
    Extracts and Sums ITC Availed from Table 4(A)(2) and 4(A)(3).
    4(A)(2): Import of services
    4(A)(3): Inward supplies liable to reverse charge (other than 1 & 2 above)
    Returns: { "igst": float, "cgst": float, "sgst": float, "cess": float }
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        # We need to find both rows and sum them.
        
        # 4(A)(2) "Import of services"
        # Usually 4 columns: IGST, CGST, SGST, Cess
        # Sometimes 5 if Taxable value? 
        # Requirement says: Extract values per tax head. 
        # Table 4(A) columns are usually: IGST, CGST, SGST, Cess. (No Taxable Value usually shown in Table 4 summary?)
        # Let's check standard GSTR-3B PDF format. 
        # Table 4 ITC Available: (1) Import of Goods, (2) Import of Services, (3) Inward supplies liable to reverse charge...
        # Columns: Integrated Tax, Central Tax, State/UT Tax, Cess
        # So 4 numbers expected.
        
        # Pattern for 4(A)(2) "Import of services"
        p2 = r"\(2\)\s*Import\s*of\s*services.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
        
        # Pattern for 4(A)(3) "Inward supplies liable to reverse charge"
        # Note: distinct from 3.1(d) because this is under Table 4 (ITC) section.
        # But regex search on full text might collide with 3.1(d) if text is similar?
        # 3.1(d) usually has "(d)" prefix.
        # 4(A)(3) usually has "(3)" prefix inside Table 4 block.
        # However, regex global might find either.
        # Safety: Look for "(3)" followed by "Inward supplies liable to reverse charge"
        
        p3 = r"\(3\)\s*Inward\s*supplies\s*liable\s*to\s*reverse\s*charge\s*\(other.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
        
        # Extract (2)
        match2 = re.search(p2, full_text, re.IGNORECASE | re.DOTALL)
        if match2:
            # [Audit Fix] Unified extractor
            nums = _extract_numbers_from_text(match2.group(1))
            # Expect 4 numbers: IGST, CGST, SGST, Cess
            if len(nums) >= 4:
                results["igst"] += _clean_amount(nums[0])
                results["cgst"] += _clean_amount(nums[1])
                results["sgst"] += _clean_amount(nums[2])
                results["cess"] += _clean_amount(nums[3])
                
        # Extract (3)
        match3 = re.search(p3, full_text, re.IGNORECASE | re.DOTALL)
        if match3:
             # [Audit Fix] Unified extractor
             nums = _extract_numbers_from_text(match3.group(1))
             if len(nums) >= 4:
                results["igst"] += _clean_amount(nums[0])
                results["cgst"] += _clean_amount(nums[1])
                results["sgst"] += _clean_amount(nums[2])
                results["cess"] += _clean_amount(nums[3])
                
    except Exception as e:
         print(f"Error parsing GSTR-3B PDF Table 4(A)(2)/(3): {e}")
         
    return results

def parse_gstr3b_pdf_table_4_a_4(file_path):
    """
    Extracts ITC Availed from Table 4(A)(4) of GSTR-3B PDF.
    4(A)(4): Inward supplies from ISD
    
    STRICT IMPLEMENTATION:
    1. Locates Table 4 Boundary (Start: "Table 4", End: "Table 5" or "Ineligible")
    2. Searches strictly within this block.
    3. Returns None if table/row not found or ambiguous.
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        # 1. Boundary Detection
        # Standard 3B Headers
        start_marker = re.search(r"4\.\s*Eligible\s*ITC", full_text, re.IGNORECASE)
        if not start_marker:
            print("DEBUG: [3B-Parser] Table 4 Start Marker not found.")
            return None
            
        # End marker could be "5. Exempt" or "Ineligible ITC" (Section D of Table 4) or "5. Values"
        # Using "5." as primary delimiter for next table
        end_marker = re.search(r"5\.\s*Values\s*of\s*exempt", full_text, re.IGNORECASE)
        
        start_idx = start_marker.start()
        end_idx = end_marker.start() if end_marker else len(full_text)
        
        table_4_text = full_text[start_idx:end_idx]
        
        # 2. Row Detection within Table 4
        # Pattern: "(4)" followed by "Inward supplies from ISD"
        # Flexible for newlines: "(4)\nInward..."
        row_pattern = r"\(4\)\s*Inward\s*supplies\s*from\s*ISD.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
        
        match = re.search(row_pattern, table_4_text, re.IGNORECASE | re.DOTALL)
        if match:
            # [Audit Fix] Unified extractor
            nums = _extract_numbers_from_text(match.group(1))
            # Expect 4 columns: I, C, S, Cess
            if len(nums) >= 4:
                results["igst"] = _clean_amount(nums[0])
                results["cgst"] = _clean_amount(nums[1])
                results["sgst"] = _clean_amount(nums[2])
                results["cess"] = _clean_amount(nums[3])
                return results
            else:
                 print(f"DEBUG: [3B-Parser] Table 4(A)(4) found but insufficient columns: {nums}")
                 return None # Silent zero forbidden

        # Fallback: Check if row title exists but regex didn't catch numbers (Parse Failure)
        if "Inward supplies from ISD" in table_4_text:
             print("DEBUG: [3B-Parser] 'Inward supplies from ISD' text found but values unparseable.")
             return None # Unsafe to return 0.0

        print("DEBUG: [3B-Parser] Table 4(A)(4) Row not identified in Table 4 block.")
        return None # Not found
    
    except Exception as e:
        print(f"Error parsing GSTR-3B PDF Table 4(A)(4): {e}")
        return None

def parse_gstr3b_pdf_table_4_a_5(file_path):
    """
    Extracts ITC Availed from Table 4(A)(5) of GSTR-3B PDF.
    4(A)(5): All other ITC
    
    STRICT IMPLEMENTATION:
    1. Validates presence of Table 4 headers (Integrated, Central, State, Cess) in correct relative order.
    2. Uses strict anchoring for row (5) "All other ITC".
    3. Fails if headers or data are ambiguous (No guessing).
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    try:
        print(f"DEBUG: Starting strict parse of GSTR-3B PDF: {file_path}")
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        # 1. Header Validation (Safety Guard)
        # We need to ensure the columns are in the expected order: IGST, CGST, SGST, Cess
        # We look for the headers in the text.
        # Note: PDF text extraction might interleave things, but generally headers appear in block.
        # Regex to find them appearing in sequence (allowing for some chars in between but not too many)
        
        # 1. Header Validation (Safety Guard)
        # Regex-based search to handle "Integrated\nTax" or extra spaces
        
        # Helper: Find first match index
        def find_header(pattern, text):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.start() if m else -1
            
        # Patterns with flexible whitespace
        idx_igst = find_header(r"integrated\s*tax", full_text)
        idx_cgst = find_header(r"central\s*tax", full_text)
        idx_sgst = find_header(r"state/ut\s*tax", full_text)
        if idx_sgst == -1: idx_sgst = find_header(r"state\s*tax", full_text)
        idx_cess = find_header(r"cess", full_text)
        
        # Debug: Print first 500 chars to see layout if failed
        if idx_igst == -1 or idx_cgst == -1:
             print("DEBUG: [3B-Parser] Text Dump (Head):")
             print(full_text[:500].replace('\n', '\\n'))
        
        header_valid = (
            idx_igst != -1 and 
            idx_cgst != -1 and 
            idx_sgst != -1 and 
            idx_cess != -1 and
            idx_igst < idx_cgst < idx_sgst < idx_cess
        )
        
        if not header_valid:
            print("WARNING: [3B-Parser] Table 4 headers not found in standard order (Integrated...Central...State...Cess).")
            print(f"DEBUG Headers Found at: IGST={idx_igst}, CGST={idx_cgst}, SGST={idx_sgst}, Cess={idx_cess}")
            print("DEBUG: Failing parse to prevent mis-mapping.")
            return None # Strict Fallback
            
        print("DEBUG: [3B-Parser] Header validation successful (Standard Order Verified).")

        # 2. Anchor Detection & Data Extraction
        lines = full_text.split('\n')
        start_idx = -1
        
        for i, line in enumerate(lines):
            # Strict Anchor: Must contain "(5)" AND "All other ITC" (case insensitive)
            # This avoids matching random "5" or "All" texts.
            l_clean = line.lower().replace(" ", "")
            if "(5)" in l_clean and "allotheritc" in l_clean:
                start_idx = i
                print(f"DEBUG: [3B-Parser] Anchor Found at line {i}: '{line.strip()}'")
                break
        
        if start_idx != -1:
            collected_nums = []
            
            # Scan matches and subsequent lines (limit 10 lines)
            print("DEBUG: [3B-Parser] Scanning for tokens...")
            for j in range(start_idx, min(len(lines), start_idx + 10)):
                raw_line = lines[j]
                # Remove anchor text to avoid parsing '5' from '(5)' as a value if it wasn't separated well
                # But be careful not to remove data.
                # Simplest: Replace known non-digit patterns.
                
                # We care about number tokens.
                # Clean specific anchor strings if present in THIS line
                # Clean specific anchor strings if present in THIS line
                curr_line_clean = raw_line.replace("All other ITC", "").replace("(5)", "").strip()
                
                # [Audit Fix] Use unified extractor instead of split()
                # matches will be list of strings "1,234.00", "0.00" etc
                tokens = _extract_numbers_from_text(curr_line_clean)
                
                print(f"DEBUG:   Line {j} tokens: {tokens}")
                
                for token in tokens:
                    # Tokens are already validated by regex in helper
                    collected_nums.append(token)
                        
            print(f"DEBUG: [3B-Parser] Total Tokens Collected: {collected_nums}")
            
            if len(collected_nums) >= 4:
                # We take the first 4 numbers found after the anchor.
                # Based on header validation, we map them to I-C-S-Ces
                results["igst"] = _clean_amount(collected_nums[0])
                results["cgst"] = _clean_amount(collected_nums[1])
                results["sgst"] = _clean_amount(collected_nums[2])
                results["cess"] = _clean_amount(collected_nums[3])
                
                print(f"DEBUG: [3B-Parser] Final Mapping: {results}")
                return results
            else:
                 print(f"DEBUG: [3B-Parser] Insufficient data tokens found (Expected 4, Got {len(collected_nums)}).")
                 return None

        print(f"DEBUG: [3B-Parser] Anchor '(5) All other ITC' NOT found.")
        return None

    except Exception as e:
        print(f"Error parsing GSTR-3B PDF Table 4(A)(5): {e}")
        import traceback; traceback.print_exc()
        return None

def parse_gstr3b_pdf_table_4_a_1(file_path):
    """
    Extracts ITC from Table 4(A)(1) - Import of Goods.
    Returns: {igst, cgst, sgst, cess}
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    if not file_path: return results

    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc: full_text += page.get_text() + "\n"
        doc.close()

        # Pattern: (1) Import of Goods
        pattern = r"\(1\)\s*Import\s*of\s*goods.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            # [Audit Fix] Unified extractor
            nums = _extract_numbers_from_text(match.group(1))
            if len(nums) >= 4:
                results["igst"] = _clean_amount(nums[0])
                results["cgst"] = _clean_amount(nums[1])
                results["sgst"] = _clean_amount(nums[2])
                results["cess"] = _clean_amount(nums[3])
    except Exception as e: 
        print(f"Error parsing 4A1: {e}")
        pass
    return results

def parse_gstr3b_metadata(file_path):
    """
    Extracts Metadata + Total ITC (4A) for SOP-9.
    1. Return Period (Strict Anchor: 'Year...Month' or 'Return Period')
    2. Date of Filing (Anchor: 'Date of Filing')
    3. Total ITC (Sum of 4A1-4A5)
    """
    meta = {
        "gstin": None,
        "fy": None,
        "return_period": None,
        "filing_date": None,
        "itc": { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    }
    
    if not file_path: return meta

    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        # Scan first 2 pages for metadata (Robuistness)
        for i in range(min(2, len(doc))):
            full_text += doc[i].get_text() + "\n"
        doc.close()
        
        # 0. GSTIN
        gstin_match = re.search(r"GSTIN\s+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])", full_text, re.IGNORECASE)
        if gstin_match:
            meta["gstin"] = gstin_match.group(1).upper()

        # 1. Filing Date
        date_match = re.search(r"Date\s*of\s*Filing.*?(\d{2}[/\-]\d{2}[/\-]\d{4})", full_text, re.IGNORECASE)
        if date_match:
            meta["filing_date"] = date_match.group(1).replace('-', '/')
            
        # 2. Return Period / FY
        meta["fy"] = _extract_fy_from_text(full_text)
        
        # Best effort for return_period display
        ym_match = re.search(r"Month\s+([A-Za-z]+)", full_text, re.IGNORECASE)
        if ym_match and meta["fy"]:
             meta["return_period"] = f"{ym_match.group(1)} {meta['fy']}"
        elif not meta["return_period"]:
             rp_match = re.search(r"Return\s*Period\s*[:\-\s]*([A-Za-z]+\s*[\-]?\s*\d{4})", full_text, re.IGNORECASE)
             if rp_match: meta["return_period"] = rp_match.group(1).replace('\n', ' ').strip()

        # 3. Total ITC (Aggregation)
        r1 = parse_gstr3b_pdf_table_4_a_1(file_path)
        r23 = parse_gstr3b_pdf_table_4_a_2_3(file_path)
        r4 = parse_gstr3b_pdf_table_4_a_4(file_path)
        r5 = parse_gstr3b_pdf_table_4_a_5(file_path)
        
        for k in meta["itc"]:
            val = (r1.get(k, 0) if r1 else 0) + (r23.get(k, 0) if r23 else 0) + (r4.get(k, 0) if r4 else 0) + (r5.get(k, 0) if r5 else 0)
            meta["itc"][k] = float(f"{val:.2f}")

    except Exception as e:
        logger.error(f"Error extracting GSTR-3B metadata from {file_path}: {e}")

    return meta

def parse_gstr1_pdf_metadata(file_path):
    """
    Extracts Metadata from GSTR-1 PDF.
    """
    meta = {"gstin": None, "fy": None, "return_period": None}
    if not file_path: return meta
    try:
        import fitz
        doc = fitz.open(file_path)
        text = ""
        for i in range(min(2, len(doc))):
            text += doc[i].get_text() + "\n"
        doc.close()
        
        gstin_match = re.search(r"GSTIN\s+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])", text, re.IGNORECASE)
        if gstin_match: meta["gstin"] = gstin_match.group(1).upper()
        
        meta["fy"] = _extract_fy_from_text(text)
        
        # Best effort for return_period
        m_match = re.search(r"Month\s*[:\-\s]*([A-Za-z]+)", text, re_IGNORECASE)
        if m_match and meta["fy"]:
             meta["return_period"] = f"{m_match.group(1)} {meta['fy']}"
        else:
             rp_match = re.search(r"Return\s*Period\s*[:\-\s]*([A-Za-z]+\s*[\-]?\s*\d{4})", text, re_IGNORECASE)
             if rp_match: meta["return_period"] = rp_match.group(1).replace('\n', ' ').strip()
                
    except Exception as e:
        logger.error(f"Error extracting GSTR-1 metadata from {file_path}: {e}")
    return meta

def parse_gstr9_pdf_metadata(file_path):
    """
    Extracts Metadata from GSTR-9 PDF.
    """
    meta = {"gstin": None, "fy": None}
    if not file_path: return meta
    try:
        import fitz
        doc = fitz.open(file_path)
        text = ""
        for i in range(min(2, len(doc))):
            text += doc[i].get_text() + "\n"
        doc.close()
        
        gstin_match = re.search(r"GSTIN\s+([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])", text, re.IGNORECASE)
        if gstin_match: meta["gstin"] = gstin_match.group(1).upper()
        
        meta["fy"] = _extract_fy_from_text(text)
                
    except Exception as e:
        logger.error(f"Error extracting GSTR-9 metadata from {file_path}: {e}")
    return meta

def _parse_3_1_row(file_path, row_regex):
    """
    Helper to parse a row from Table 3.1.
    Expects 5 columns: Taxable, IGST, CGST, SGST, Cess.
    
    STRICT NULL HANDLING CONTRACT:
    1. Returns 'None' if Row Label is NOT found.
    2. Returns 'None' if Row Label IS found but NO numeric values are extracted.
    3. Returns dict only if valid data is extracted.
    """
    vals = {'taxable_value': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
    try:
        import fitz
        doc = fitz.open(file_path)
        
        row_found = False
        data_found = False
        
        for page in doc:
            text = page.get_text()
            
            # [SOP-11 REGEX] Evidence
            # print(f"\n[SOP-11 REGEX] File: {file_path}")
            # print(f"[SOP-11 REGEX] ROW Regex: {row_regex}")
            
            match = re.search(row_regex, text, re.IGNORECASE)
            if match:
                row_found = True
                # print(f"[SOP-11 REGEX] MATCH_FOUND=True")
                post_text = text[match.end():]
                # [SOP-11 UNIFIED FIX] Use shared helper with strict Indian Regex
                nums = _extract_numbers_from_text(post_text[:250])
                
                # [SOP-11 REGEX] Detailed Payload
                # print(f"[SOP-11 REGEX] EXTRACTED_TEXT_SNIPPET={post_text[:100]!r}")
                # print(f"[SOP-11 REGEX] Tokens Found: {nums}")
                
                if nums:
                    data_found = True
                    if len(nums) >= 1: vals['taxable_value'] = _clean_amount(nums[0])
                    if len(nums) >= 2: vals['igst'] = _clean_amount(nums[1])
                    if len(nums) >= 3: vals['cgst'] = _clean_amount(nums[2])
                    if len(nums) >= 4: vals['sgst'] = _clean_amount(nums[3])
                    if len(nums) >= 5: vals['cess'] = _clean_amount(nums[4])
                    
                    # [SOP-11 REGEX] Raw Value Evidence
                    # print(f"[SOP-11 REGEX] FINAL_VALUE={vals}")
                    break # Found and extracted
                else:
                     # Row found but no numbers? Logic says return None.
                     pass 
            else:
                # print(f"[SOP-11 REGEX] MATCH_FOUND=False")
                pass

        doc.close()
        
        if not row_found:
             return None # Case 1: Label Missing
             
        if row_found and not data_found:
             return None # Case 2: Label Found, Data Missing (Scan failed)
             
        return vals # Case 3: Success

    except Exception as e:
        print(f"Error parsing 3.1 row: {e}")
        return None # Safety fallback

def parse_gstr3b_pdf_table_3_1_b(file_path):
    """
    Extracts 3.1(b) Outward taxable supplies (zero rated).
    """
    return _parse_3_1_row(file_path, r"\(b\)\s*Outward\s*taxable\s*supplies\s*\(zero\s*rated\)")

def parse_gstr3b_pdf_table_3_1_c(file_path):
    """
    Extracts 3.1(c) Other outward supplies (Nil rated, exempted).
    Regex: Allow whitespace inside (c ).
    """
    return _parse_3_1_row(file_path, r"\(c\s*\)\s*Other\s*outward\s*supplies\s*\(Nil\s*rated,\s*exempted\)")

def parse_gstr3b_pdf_table_3_1_e(file_path):
    """
    Extracts 3.1(e) Non-GST outward supplies.
    Regex: Allow whitespace inside (e ).
    """
    return _parse_3_1_row(file_path, r"\(e\s*\)\s*Non-GST\s*outward\s*supplies")

def parse_gstr3b_pdf_table_4_b_1(file_path):
    """
    Extracts Table 4(B)(1) ITC Reversed (Rule 42 & 43).
    Columns: I, C, S, Cess. (Taxable Value not applicable).
    """
    vals = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # Anchored Regex for Table 4(B)(1)
        # 1. Anchors to "Table 4" (approximate area) if possible, but definitely anchors to (B) and (1) rules
        # Pattern: (B) -> (1) -> rules -> 42/43
        # We search with DOTALL to cross lines
        
        # Regex explanation:
        # \(1\)         : Match "(1)"
        # \s*As\s*per   : Match "As per"
        # \s*rules      : Match "rules"
        # .*?           : Non-greedy match for any filler (like "38,")
        # (?:42|43)     : Match either "42" or "43"
        # .*?           : Filler until numbers
        # ((?:...))     : Capture the numbers block
        
        # We explicitly look for this pattern which might appear after "Table 4" or "ITC Reversed"
        # Safety: We just use the specific row text variation which is quite unique.
        
        pattern = r"\(1\)\s*As\s*per\s*rules.*?(?:42|43).*?((?:(?:\d{1,3}(?:,\s*\d{3})*|\d+)\.\d{2}\s*)+)"
        
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            post_text = match.group(1)
            # [SOP-11 UNIFIED FIX] Use shared helper
            nums = _extract_numbers_from_text(post_text[:250])
            
            if len(nums) >= 1: vals['igst'] = _clean_amount(nums[0])
            if len(nums) >= 2: vals['cgst'] = _clean_amount(nums[1])
            if len(nums) >= 3: vals['sgst'] = _clean_amount(nums[2])
            if len(nums) >= 4: vals['cess'] = _clean_amount(nums[3])
            
    except Exception as e:
        print(f"Error parsing 4B1: {e}")
    return vals

def parse_gstr3b_sop9_identifiers(file_path):
    """
    SOP-9 Specialized Metadata Extraction.
    
    Target Data (Page 1 ONLY):
    1. Financial Year (from 'Year ... Period ...' block).
    2. Tax Period Month.
    3. Date of ARN (or Date of Filing).
    
    Safety:
    - Scopes strict regex searches to Page 1 only.
    - Uses Semantic Anchors ("Date of ARN", "Year...Period").
    - Does NOT rely on "2(d)" numbering.
    """
    meta = {
        "fy": None,
        "month": None,
        "filing_date": None,
        "frequency": "Unknown", # Monthly, Quarterly, Yearly, Unknown
        "error": None
    }
    
    if not file_path: 
        meta["error"] = "File path missing"
        return meta

    try:
        import fitz
        doc = fitz.open(file_path)
        # SCOPE: 2 PAGES
        p_text = ""
        for i in range(min(2, len(doc))):
             p_text += doc[i].get_text() + "\n"
        doc.close()
        
        # 0. Frequency Detection (Applicability Check)
        lower_text = p_text.lower()
        
        # Default to Unknown. Logic will upgrade if patterns found.
        # Check for Period/Month presence first as it's the strongest signal for Monthly/Quarterly.
        
        period_pattern = r"(?:Tax\s+)?Period\s*[:\-\s]*([A-Za-z]+)"
        period_match = re.search(period_pattern, p_text, re.IGNORECASE)
        
        raw_period = None
        if period_match:
            raw_period = period_match.group(1).strip()
            meta["month"] = raw_period # Valid candidate
            
            # Check for Quarterly markers in strict context
            if "quarter" in raw_period.lower() or "jan" in raw_period.lower() and "mar" in raw_period.lower() or "apr" in raw_period.lower() and "jun" in raw_period.lower():
                 meta["frequency"] = "Quarterly"
            else:
                 # It looked like a month (e.g. "February")
                 meta["frequency"] = "Monthly"

        # Global overrides (Safety)
        if "quarterly" in lower_text[:1000] and meta["frequency"] != "Quarterly":
             meta["frequency"] = "Quarterly"
             
        if meta["frequency"] == "Unknown":
            if "annual" in lower_text or "yearly" in lower_text:
                meta["frequency"] = "Yearly"

        # 1. Financial Year Extraction
        meta["fy"] = _extract_fy_from_text(p_text)
            
        # 2. Date of ARN Extraction
        date_pattern = r"(?:(?:Date\s*of\s*ARN)|(?:Date\s*of\s*Filing))\s*[:\-\s]*(\d{2}[/\-]\d{2}[/\-]\d{4})"
        
        arn_match = re.search(date_pattern, p_text, re.IGNORECASE)
        if arn_match:
            d_str = arn_match.group(1).replace('-', '/')
            meta["filing_date"] = d_str
            
    except Exception as e:
        meta["error"] = str(e)
        print(f"SOP-9 Metadata Parse Error: {e}")

    return meta
