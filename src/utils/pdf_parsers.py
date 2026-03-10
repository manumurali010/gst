import fitz  # PyMuPDF
import re
import os
import logging
from src.utils.date_utils import normalize_financial_year
from src.utils.number_utils import safe_int

# Set up logger for PDF Parsers
logger = logging.getLogger("pdf_parsers")
if not logger.handlers:
    handler = logging.FileHandler("audit_log.txt")
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def _clean_amount(val_str):
    """
    Safely cleans monetary strings (commas, currency symbols) and returns float.
    """
    if val_str is None: return 0.0
    if isinstance(val_str, (int, float)): return float(val_str)
    
    # Extract numeric part only (handle trailing decimals or negative signs)
    # This is a bit safer than just replace()
    clean = str(val_str).replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
    try:
        if not clean: return 0.0
        return float(clean)
    except (ValueError, TypeError):
        return 0.0

def _validate_token_sanity(tokens, min_expected=3):
    """Universal sanity check for numeric token extraction."""
    return len(tokens) >= min_expected

def _detect_token_anomalies(tokens, context_line=""):
    """Logs warnings for suspicious numeric token patterns."""
    for t in tokens:
        # Fragmented Indian grouping check (e.g. "1, 23, 456.78" split into parts)
        if "," in t:
            parts = t.split(",")
            # If intermediate parts are only 1 digit, it's highly suspicious for Indian/Intl formats
            if any(len(p) == 1 for p in parts[1:-1]):
                logger.warning(f"SUSPICIOUS TOKEN GROUPING: '{t}' in line '{context_line.strip()}'")
        
        # Tiny tokens (e.g. ".00" or single digits) isolated from labels
        if len(t.replace(".", "")) <= 2:
            logger.debug(f"TINY TOKEN DETECTED: '{t}' in line '{context_line.strip()}'")

def _extract_numbers_from_text(text):
    if not text: return []
    # Normalize spaces around commas and dots to prevent number fragmentation
    # Example: "1, 01, 90, 410. 82" -> "1,01,90,410.82"
    clean_text = re.sub(r"\s*,\s*", ",", text)
    clean_text = re.sub(r"\s*\.\s*", ".", clean_text)
    
    p = r"\d[\d,]*\.?\d*"
    tokens = re.findall(p, clean_text)
    if tokens:
        _detect_token_anomalies(tokens, clean_text)
    return tokens

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

# Global cache for GSTR-3B PDF text to avoid redundant parsing
_GSTR3B_TEXT_CACHE = {}

def find_anchor_window(lines, anchor_terms, window_size=5):
    """
    Scans lines for proximity-based anchor detection.
    Returns the line index where the FIRST term was found if all terms are 
    present within 'window_size' lines from that point.
    """
    for i in range(len(lines)):
        # Check if the primary (first) term exists in current line
        if anchor_terms[0].lower() in lines[i].lower():
            # Check window for all other terms
            found_all = True
            for term in anchor_terms[1:]:
                term_found_in_window = False
                for j in range(i, min(len(lines), i + window_size)):
                    if term.lower() in lines[j].lower():
                        term_found_in_window = True
                        break
                if not term_found_in_window:
                    found_all = False
                    break
            
            if found_all:
                return i
    return -1

def parse_full_gstr3b(file_path):
    """Parses full text of GSTR-3B and caches it."""
    if file_path in _GSTR3B_TEXT_CACHE:
        return _GSTR3B_TEXT_CACHE[file_path]
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        _GSTR3B_TEXT_CACHE[file_path] = full_text
        return full_text
    except Exception as e:
        print(f"Error reading GSTR-3B {file_path}: {e}")
        return ""

def parse_gstr3b_pdf_table_3_1_a(file_path):
    """
    Extracts Table 3.1(a) Outward taxable supplies.
    Uses line-bounded scanning for robustness.
    Returns: {"parsed": bool, "data": dict}
    """
    full_text = parse_full_gstr3b(file_path)
    if not full_text: return {"parsed": False, "data": None}

    # 1. Row Detection - Use _parse_3_1_row with relaxed anchor
    anchor_regex = r"\(a\)\s*Outward\s*taxable\s*supplies"
    return _parse_3_1_row(full_text, anchor_regex)

def parse_gstr1_pdf_total_liability(file_path):
    """
    Extracts "Total Liability (Outward supplies other than Reverse charge)" from GSTR-1 PDF.
    Returns: {"parsed": bool, "data": dict}
    """
    results = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
    
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}
        
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        
        anchor_terms = ["Total Liability", "Outward supplies", "Reverse charge"]
        anchor_idx = find_anchor_window(lines, anchor_terms, window_size=6)
        
        if anchor_idx != -1:
            logger.debug(f"[GSTR1 DEBUG] Anchor index detected: {anchor_idx}")
            logger.debug(f"[GSTR1 DEBUG] Anchor line: '{lines[anchor_idx]}'")
            
            collected_tokens = []
            # Scan more lines (up to 12) because GSTR-1 rows are often multi-line
            for j in range(anchor_idx, min(len(lines), anchor_idx + 12)):
                tokens = _extract_numbers_from_text(lines[j])
                if tokens:
                    collected_tokens.extend(tokens)
                    # Break only after collecting at least 5 tokens to avoid TV-only capture
                    if len(collected_tokens) >= 5:
                        break
            
            logger.debug(f"[GSTR1 DEBUG] Raw numeric tokens extracted: {collected_tokens}")

            # Token Sanity: Expected min 3 (IGST, CGST, SGST) - User requirement: loosen validation
            if not _validate_token_sanity(collected_tokens, 3):
                logger.warning(f"GSTR-1 Liability Parse Failed: Insufficient tokens ({len(collected_tokens)})")
                return {"parsed": False, "data": None}

            # Mapping Logic (User Approved):
            # 5+ Tokens: [Taxable Value, IGST, CGST, SGST, Cess] -> Map idx 1-4
            if len(collected_tokens) >= 5:
                results["igst"] = _clean_amount(collected_tokens[1])
                results["cgst"] = _clean_amount(collected_tokens[2])
                results["sgst"] = _clean_amount(collected_tokens[3])
                results["cess"] = _clean_amount(collected_tokens[4]) if len(collected_tokens) > 4 else 0.0
            # 4 Tokens: [IGST, CGST, SGST, Cess] OR [Taxable, IGST, CGST, SGST]
            # Mapping idx 0-3 as tax heads for now, as per user's "assumption" concern.
            else:
                results["igst"] = _clean_amount(collected_tokens[0])
                results["cgst"] = _clean_amount(collected_tokens[1])
                results["sgst"] = _clean_amount(collected_tokens[2])
                results["cess"] = _clean_amount(collected_tokens[3]) if len(collected_tokens) > 3 else 0.0
            
            logger.debug(f"[GSTR1 DEBUG] Final mapped IGST/CGST/SGST/CESS values: {results}")
            return {"parsed": True, "data": results}
                
    except Exception as e:
        logger.error(f"Error parsing GSTR-1 PDF: {e}")
        
    return {"parsed": False, "data": None}

def parse_gstr3b_pdf_table_3_1_d(file_path):
    """
    Extracts Table 3.1(d) Inward supplies Liable to Reverse Charge.
    Returns: {"parsed": bool, "data": dict}
    """
    full_text = parse_full_gstr3b(file_path)
    if not full_text: return {"parsed": False, "data": None}
    return _parse_3_1_row(full_text, r"\(d\)\s*Inward\s*Supplies\s*\(liable\s*to\s*reverse\s*charge\)")

def parse_gstr3b_pdf_table_4_a_2_3(file_path):
    """
    Extracts ITC Availed from Table 4(A)(2) and (3) of GSTR-3B PDF.
    Returns: {"parsed": bool, "data": dict}
    """
    results = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
    if not file_path: return {"parsed": False, "data": None}
    
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}
        
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        
        any_success = False
        
        # We need to collect BOTH (2) and (3)
        anchors = [
            ("(2)", ["Import of services"]),
            ("(3)", ["Inward supplies", "reverse charge", "other than 1 & 2"])
        ]
        
        for label, terms in anchors:
            found_for_anchor = False
            # Find anchor line
            for i, line in enumerate(lines):
                if label in line and all(t.lower() in line.lower() for t in terms):
                    logger.debug(f"[RCM DEBUG] Found anchor {label} at line {i}: '{line}'")
                    # Scan next lines for tokens
                    collected_tokens = []
                    for j in range(i + 1, min(len(lines), i + 10)):
                        # If we hit another label, stop
                        if re.search(r"^\(\d+\)", lines[j]):
                             break
                        
                        tokens = _extract_numbers_from_text(lines[j])
                        if tokens:
                            collected_tokens.extend(tokens)
                            if len(collected_tokens) >= 4:
                                break
                    
                    if _validate_token_sanity(collected_tokens, 3):
                        logger.debug(f"[RCM DEBUG] Matched {label} | Collected Tokens: {collected_tokens}")
                        results["igst"] += _clean_amount(collected_tokens[0])
                        results["cgst"] += _clean_amount(collected_tokens[1])
                        results["sgst"] += _clean_amount(collected_tokens[2])
                        if len(collected_tokens) > 3:
                            results["cess"] += _clean_amount(collected_tokens[3])
                        
                        any_success = True
                        found_for_anchor = True
                        break # Move to next anchor
            
            if not found_for_anchor:
                logger.debug(f"[RCM DEBUG] Anchor {label} not found in this PDF.")

        if any_success:
            logger.debug(f"[RCM DEBUG] Final Mapped RCM: {results}")
            return {"parsed": True, "data": results}
            
    except Exception as e:
         logger.error(f"Error parsing GSTR-3B PDF Table 4(A)(2)/(3): {e}")
         
    return {"parsed": False, "data": None}

def parse_gstr3b_pdf_table_4_a_4(file_path):
    """
    Extracts ITC Availed from Table 4(A)(4) of GSTR-3B PDF.
    Returns: {"parsed": bool, "data": dict}
    """
    results = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
    if not file_path: return {"parsed": False, "data": None}
    
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}
        
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        
        # Proximity-based detection for Table 4(A)(4) ISD
        anchor_terms = ["(4)", "Inward supplies", "ISD"]
        anchor_idx = find_anchor_window(lines, anchor_terms, window_size=6)
        
        if anchor_idx != -1:
            # Scan the next 6 lines for numeric tokens
            collected_tokens = []
            for j in range(anchor_idx, min(len(lines), anchor_idx + 8)):
                tokens = _extract_numbers_from_text(lines[j])
                if tokens:
                    collected_tokens.extend(tokens)
                    if len(collected_tokens) >= 4:
                        break
            
            if _validate_token_sanity(collected_tokens, 3):
                # CLEAN LABEL INTERFERENCE: Remove (4), Table, 4A, etc. to prevent capturing label index as value
                # This is safe because _extract_numbers_from_text handles the main numeric extraction.
                # However, since we collect tokens LINE BY LINE, we must clean the line BEFORE extraction.
                
                # RE-SCAN with cleaning
                collected_tokens = []
                for j in range(anchor_idx, min(len(lines), anchor_idx + 8)):
                    clean_line = lines[j].replace("(4)", "").replace("4(A)(4)", "").replace("4(a)(4)", "").strip()
                    tokens = _extract_numbers_from_text(clean_line)
                    if tokens:
                        collected_tokens.extend(tokens)
                        if len(collected_tokens) >= 4:
                            break
                
                logger.debug(f"[4A4 DEBUG] Anchor Line: {lines[anchor_idx]} | Cleaned Tokens: {collected_tokens}")
                results["igst"] = _clean_amount(collected_tokens[0])
                results["cgst"] = _clean_amount(collected_tokens[1])
                results["sgst"] = _clean_amount(collected_tokens[2])
                if len(collected_tokens) > 3: results["cess"] = _clean_amount(collected_tokens[3])
                logger.debug(f"[4A4 DEBUG] Mapped: {results}")
                return {"parsed": True, "data": results}
            else:
                logger.debug(f"Table 4(A)(4) Parse Warning: Insufficient tokens ({len(collected_tokens)}) in block near line {anchor_idx}")
    
    except Exception as e:
        logger.error(f"Error parsing GSTR-3B PDF Table 4(A)(4): {e}")
    return {"parsed": False, "data": None}

def parse_gstr3b_pdf_table_4_a_5(file_path):
    """
    Extracts ITC Availed from Table 4(A)(5) of GSTR-3B PDF.
    Returns: {"parsed": bool, "data": dict}
    """
    results = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
    if not file_path: return {"parsed": False, "data": None}
    
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}
        
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        
        # Proximity-based detection for Table 4(A)(5) All other ITC
        anchor_terms = ["(5)", "All other ITC"]
        anchor_idx = find_anchor_window(lines, anchor_terms, window_size=5)
        
        if anchor_idx != -1:
            # Scan the next 6 lines for numeric tokens
            collected_tokens = []
            for j in range(anchor_idx, min(len(lines), anchor_idx + 8)):
                # Clean the line of labels to prevent interference
                clean_line = lines[j].replace("(5)", "").replace("All other ITC", "").strip()
                tokens = _extract_numbers_from_text(clean_line)
                if tokens:
                    collected_tokens.extend(tokens)
                    if len(collected_tokens) >= 4:
                        break
            
            if _validate_token_sanity(collected_tokens, 3):
                logger.debug(f"[4A5 DEBUG] Anchor Line: {lines[anchor_idx]} | Tokens: {collected_tokens}")
                results["igst"] = _clean_amount(collected_tokens[0])
                results["cgst"] = _clean_amount(collected_tokens[1])
                results["sgst"] = _clean_amount(collected_tokens[2])
                if len(collected_tokens) > 3: results["cess"] = _clean_amount(collected_tokens[3])
                logger.debug(f"[4A5 DEBUG] Mapped: {results}")
                return {"parsed": True, "data": results}
            else:
                logger.debug(f"Table 4(A)(5) Parse Warning: Insufficient tokens ({len(collected_tokens)}) in block near line {anchor_idx}")
                
    except Exception as e:
        logger.error(f"Error parsing GSTR-3B PDF Table 4(A)(5): {e}")
    return {"parsed": False, "data": None}

def parse_gstr3b_pdf_table_4_a_1(file_path):
    """
    Extracts ITC from Table 4(A)(1) - Import of Goods.
    Returns: {"parsed": bool, "data": dict}
    """
    results = { "igst": 0, "cgst": 0, "sgst": 0, "cess": 0 }
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}

        pattern = r"\(1\)\s*Import\s*of\s*goods.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            nums = _extract_numbers_from_text(match.group(1))
            if _validate_token_sanity(nums, 4):
                results["igst"] = _clean_amount(nums[0])
                results["cgst"] = _clean_amount(nums[1])
                results["sgst"] = _clean_amount(nums[2])
                results["cess"] = _clean_amount(nums[3])
                return {"parsed": True, "data": results}
            else:
                logger.debug(f"Table 4(A)(1) Parse Warning: Insufficient tokens ({len(nums)})")
    except Exception as e: 
        logger.error(f"Error parsing 4A1: {e}")
    return {"parsed": False, "data": None}

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
        def _get_vals(res):
            if isinstance(res, dict) and res.get("parsed") and res.get("data"):
                return res.get("data")
            return {"igst": 0, "cgst": 0, "sgst": 0, "cess": 0}

        res1 = parse_gstr3b_pdf_table_4_a_1(file_path)
        res23 = parse_gstr3b_pdf_table_4_a_2_3(file_path)
        res4 = parse_gstr3b_pdf_table_4_a_4(file_path)
        res5 = parse_gstr3b_pdf_table_4_a_5(file_path)
        
        r1 = _get_vals(res1)
        r23 = _get_vals(res23)
        r4 = _get_vals(res4)
        r5 = _get_vals(res5)
        
        for k in meta["itc"]:
            val = r1.get(k, 0) + r23.get(k, 0) + r4.get(k, 0) + r5.get(k, 0)
            meta["itc"][k] = float(val)

    except Exception as e:
        print(f"Error extracting GSTR-3B metadata from {file_path}: {e}")

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
        m_match = re.search(r"Month\s*[:\-\s]*([A-Za-z]+)", text, re.IGNORECASE)
        if m_match and meta["fy"]:
             meta["return_period"] = f"{m_match.group(1)} {meta['fy']}"
        else:
             rp_match = re.search(r"Return\s*Period\s*[:\-\s]*([A-Za-z]+\s*[\-]?\s*\d{4})", text, re.IGNORECASE)
             if rp_match: meta["return_period"] = rp_match.group(1).replace('\n', ' ').strip()
                
    except Exception as e:
        print(f"Error extracting GSTR-1 metadata from {file_path}: {e}")
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

def _parse_3_1_row(full_text, row_regex):
    """
    Helper to parse a row from Table 3.1 using line-bounded scanning.
    Expects 5 columns: Taxable, IGST, CGST, SGST, Cess.
    """
    vals = {'taxable_value': 0, 'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0}
    try:
        # Robust Anchor Detection: Find character index in full text first
        match = re.search(row_regex, full_text, re.IGNORECASE | re.DOTALL)
        if not match:
            return {"parsed": False, "data": None}
            
        # Determine line index of the match
        lines = full_text.split('\n')
        
        # Adjust start_idx if the anchor itself spans multiple lines (we want to scan AFTER the anchor)
        # But for GST PDFs, anchors are usually short. 
        # We start scanning from the line where the anchor ENDS.
        line_where_anchor_ends = full_text.count('\n', 0, match.end())
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[3.1 PARSE] Anchor found at line {line_where_anchor_ends}")

        collected_nums = []
        # Generalized Token Scanning (up to 15 lines)
        for j in range(line_where_anchor_ends, min(len(lines), line_where_anchor_ends + 15)):
            line = lines[j].strip()
            if not line: continue
            
            # Boundary Detection: Stop if another 3.1 row label is detected
            # Pattern: 3.1 ( or 3.1( or individual row markers (b), (c), (d), (e)
            # Safeguard: Skip boundary check for the anchor line itself (j == line_where_anchor_ends)
            if j > line_where_anchor_ends:
                if re.search(r"3\.1\s*\(", line, re.IGNORECASE) or re.search(r"^\s*\([a-e]\)\s*", line, re.IGNORECASE):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"[3.1 PARSE] Row Boundary detected at line {j}: '{line}'")
                    break
            
            tokens = _extract_numbers_from_text(line)
            if tokens:
                # Header/Numbering Filter: Ignore single-digit integers at the start of line
                filtered_tokens = []
                for idx, t in enumerate(tokens):
                    if idx == 0 and len(t) == 1 and t.isdigit():
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"[3.1 PARSE] Filtering row numbering token: '{t}'")
                        continue
                    filtered_tokens.append(t)
                
                for t in filtered_tokens:
                    val = _clean_amount(t)
                    collected_nums.append(val)
                
                # Stop if we have at least 5 tokens
                if len(collected_nums) >= 5:
                    break
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[3.1 PARSE] Tokens collected: {collected_nums}")

        # Dynamic Column Mapping
        num_count = len(collected_nums)
        results_found = False
        if num_count >= 5:
            vals['taxable_value'] = collected_nums[0]
            vals['igst'] = collected_nums[1]
            vals['cgst'] = collected_nums[2]
            vals['sgst'] = collected_nums[3]
            vals['cess'] = collected_nums[4]
            results_found = True
        elif num_count == 4:
            vals['igst'] = collected_nums[0]
            vals['cgst'] = collected_nums[1]
            vals['sgst'] = collected_nums[2]
            vals['cess'] = collected_nums[3]
            results_found = True
        elif num_count == 3:
            vals['igst'] = collected_nums[0]
            vals['cgst'] = collected_nums[1]
            vals['sgst'] = collected_nums[2]
            results_found = True

        if results_found and any(v > 0 for v in vals.values()):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[3.1 PARSE] Final mapped values: {vals}")
            return {"parsed": True, "data": vals}
            
        return {"parsed": False, "data": None}

    except Exception as e:
        logger.error(f"Error parsing 3.1 row: {e}")
        return {"parsed": False, "data": None}

def parse_gstr3b_pdf_table_3_1_b(file_path):
    """
    Extracts 3.1(b) Outward taxable supplies (zero rated).
    """
    full_text = parse_full_gstr3b(file_path)
    if not full_text: return {"parsed": False, "data": None}
    return _parse_3_1_row(full_text, r"\(b\)\s*Outward\s*taxable\s*supplies\s*\(zero\s*rated\)")

def parse_gstr3b_pdf_table_3_1_c(file_path):
    """
    Extracts 3.1(c) Other outward supplies (Nil rated, exempted).
    Regex: Allow whitespace inside (c ).
    """
    full_text = parse_full_gstr3b(file_path)
    if not full_text: return {"parsed": False, "data": None}
    return _parse_3_1_row(full_text, r"\(c\s*\)\s*Other\s*outward\s*supplies\s*\(Nil\s*rated,\s*exempted\)")

def parse_gstr3b_pdf_table_3_1_e(file_path):
    """
    Extracts 3.1(e) Non-GST outward supplies.
    Regex: Allow whitespace inside (e ).
    """
    full_text = parse_full_gstr3b(file_path)
    if not full_text: return {"parsed": False, "data": None}
    return _parse_3_1_row(full_text, r"\(e\s*\)\s*Non-GST\s*outward\s*supplies")

def parse_gstr3b_pdf_table_4_b_1(file_path):
    """
    Extracts Table 4(B)(1) ITC Reversed (Rule 42 & 43).
    Columns: I, C, S, Cess. (Taxable Value not applicable).
    Returns: {"parsed": bool, "data": dict}
    """
    vals = {'igst': 0, 'cgst': 0, 'sgst': 0, 'cess': 0}
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}

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
            nums = _extract_numbers_from_text(post_text[:250])
            
            if _validate_token_sanity(nums, 4):
                vals['igst'] = _clean_amount(nums[0])
                vals['cgst'] = _clean_amount(nums[1])
                vals['sgst'] = _clean_amount(nums[2])
                vals['cess'] = _clean_amount(nums[3])
                return {"parsed": True, "data": vals}
            else:
                logger.debug(f"Table 4(B)(1) Parse Warning: Insufficient tokens ({len(nums)})")
            
    except Exception as e:
        logger.error(f"Error parsing 4B1: {e}")
    return {"parsed": False, "data": None}

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
        logger.error(f"SOP-9 Metadata Parse Error: {e}")

    return meta

# ==========================================
# New Parsers for SOP 13-16 (RCM/Cash/Interest)
# ==========================================

def _extract_period_strict(text):
    """
    Safeguard: Strict extraction of Financial Period from file content.
    Returns: "YYYY-YY" string.
    Raises: ValueError if indeterminate.
    """
    # 1. Look for definitive "Year: 2022-23" or "2022-23" ID pattern
    match = re.search(r"(?:Year|Period)\s*[:\-\s]*(\d{4}-\d{2})", text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # 2. Fallback: Search for any YYYY-YY pattern in header area (first 1000 chars)
    header = text[:1000]
    match = re.search(r"\b(20\d{2}-\d{2})\b", header)
    if match:
        return match.group(1)
        
    raise ValueError("Could not strictly determine Financial Year from file content.")

def parse_gstr3b_pdf_table_6_1_cash(file_path):
    """
    Extracts 'Paid in Cash' columns from Table 6.1 of GSTR-3B.
    Returns: {"parsed": bool, "data": dict}
    """
    results = {
        "igst": 0, "cgst": 0, "sgst": 0, "cess": 0
    }
    
    try:
        full_text = parse_full_gstr3b(file_path)
        if not full_text: return {"parsed": False, "data": None}
        
        # 1. Period Safeguard
        try:
            full_text_meta = full_text[:2000] 
            results["period"] = _extract_period_strict(full_text_meta)
        except ValueError:
            return {"parsed": False, "data": None}

        # 2. Anchor to Table 6.1
        start_marker = re.search(r"6\.1\s*Payment\s*of\s*tax", full_text, re.IGNORECASE)
        if not start_marker:
            return {"parsed": False, "data": None}
            
        table_text = full_text[start_marker.start():]
        
        # 3. Find Row (B) Section
        row_regex = r"\(B\)\s*Reverse\s*charge.*"
        
        match = re.search(row_regex, table_text, re.IGNORECASE)
        if match:
            # Limit scope to max 2000 chars to cover all tax heads
            section_b_text = table_text[match.end():match.end()+2000]
            
            # Helper to extract Cash from a Tax Head Row
            # Strategy: Find row label, get numbers. Cash is usually Col 7 (idx 6) or near end.
            # RCM rows often have 8 numbers: Pay, ITC(4 empty?), Cash, Int, Fee.
            # If 8 numbers: Cash is at index 5 (0-1-2-3-4-5-6-7)? 
            # 19840 (0), 0(1), 0(2), 0(3), 0(4), 19840(5), 0(6), 0(7).
            # Yes, Index 5 (6th number) seems to be Cash.
            # Alternatively: Index -3.
            
            def extract_cash_from_row(label_pattern, text_block):
                m = re.search(label_pattern, text_block, re.IGNORECASE)
                if m:
                    # Get text until next newline or reasonable length needed for numbers
                    # Numbers might be on next line or same line.
                    # We grab a chunk after the label.
                    post_label = text_block[m.end():m.end()+300]
                    nums = _extract_numbers_from_text(post_label)
                    
                    # RCM Rows have 8 numbers: Pay, ITC(4), Cash, Int, Fee.
                    # Cash is the 6th number (Index 5).
                    if _validate_token_sanity(nums, 6): 
                        val_str = nums[5]
                        return int(round(_clean_amount(val_str)))
                return 0

            results["igst"] = extract_cash_from_row(r"Integrated\s*Tax", section_b_text)
            results["cgst"] = extract_cash_from_row(r"Central\s*Tax", section_b_text)
            results["sgst"] = extract_cash_from_row(r"State(?:/UT)?\s*Tax", section_b_text)
            results["cess"] = extract_cash_from_row(r"Cess", section_b_text)
            
            return {"parsed": True, "data": results}
                
        return {"parsed": False, "data": None}
        
    except Exception as e:
        logger.error(f"Error parsing Table 6.1 (Cash Paid): {e}")
        return {"parsed": False, "data": None}
