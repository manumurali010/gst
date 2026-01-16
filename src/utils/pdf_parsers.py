import fitz  # PyMuPDF
import re

def _clean_amount(text):
    """
    Cleans a numeric string (removes commas) and converts to float.
    Returns 0.0 if conversion fails.
    """
    if not text:
        return 0.0
    try:
        # Remove commas and spaces
        cleaned = text.replace(',', '').strip()
        return float(cleaned)
    except ValueError:
        return 0.0

def parse_gstr3b_pdf_table_3_1_a(file_path):
    """
    Extracts Tax Liability from Table 3.1(a) of GSTR-3B PDF.
    Target Row: "(a) Outward taxable supplies (other than zero rated, nil rated and exempted)"
    Returns: { "igst": float, "cgst": float, "sgst": float, "cess": float }
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    print(f"DEBUG: Parsing GSTR-3B 3.1(a) from {file_path}")
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
        
        # 1. Dynamic Header Mapping (Robuistness against reordered columns)
        def find_header(pattern, text):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.start() if m else 999999

        # Identify positions of tax headers
        headers = [
            ("igst", find_header(r"integrated\s*tax", full_text)),
            ("cgst", find_header(r"central\s*tax", full_text)),
            ("sgst", find_header(r"state(/ut)?\s*tax", full_text)),
            ("cess", find_header(r"cess", full_text))
        ]
        
        # Sort headers by position implies column order
        # Filter out not found (999999) - though standard 3B has them all.
        headers.sort(key=lambda x: x[1])
        
        # Verify valid headers found
        detected_order = [h[0] for h in headers if h[1] < 999999]
        print(f"DEBUG: Detected Column Order (Taxes): {detected_order}")
        
        if len(detected_order) < 4:
            print("WARNING: Could not find all tax headers. Assuming Standard Order [IGST, CGST, SGST, Cess].")
            detected_order = ["igst", "cgst", "sgst", "cess"]

        # 2. Extract Data Row
        pattern = r"\(a\)\s*Outward\s*taxable\s*supplies.*?((?:[\d,]+\.?\d*\s+){4}[\d,]+\.?\d*)"
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            numbers_str = match.group(1)
            nums = numbers_str.split()
            print(f"DEBUG: 3.1(a) Regex matched. Tokens found: {len(nums)} -> {nums}")
            
            if len(nums) >= 5:
                # Index 0 is always Taxable Value in Table 3.1 structure
                results["taxable_value"] = _clean_amount(nums[0])
                
                # Indexes 1..4 map to the detected tax headers
                for i, tax_type in enumerate(detected_order):
                    if i+1 < len(nums):
                        results[tax_type] = _clean_amount(nums[i+1])
                
                print(f"DEBUG: 3.1(a) Extracted Values -> {results}")
                # Legacy block removed.
                
    except Exception as e:
        print(f"Error parsing GSTR-3B PDF: {e}")
        return None
        
    # Check if we actually found 3.1(a) data. 
    # If "taxable_value" is NOT in results, it means regex failed.
    if "taxable_value" not in results:
        print("DEBUG: 3.1(a) Row not found in PDF.")
        return None
        
    return results

def parse_gstr1_pdf_total_liability(file_path):
    """
    Extracts "Total Liability (Outward supplies other than Reverse charge)" from GSTR-1 PDF.
    Returns: { "igst": float, "cgst": float, "sgst": float, "cess": float }
    """
    results = { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    
    try:
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
            nums = numbers_str.split()
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
        if match:
            numbers_str = match.group(1)
            nums = numbers_str.split()
            
            if len(nums) >= 5:
                # Indices: 0=Taxable, 1=IGST, 2=CGST, 3=SGST, 4=Cess
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
            nums = match2.group(1).split()
            # Expect 4 numbers: IGST, CGST, SGST, Cess
            if len(nums) >= 4:
                results["igst"] += _clean_amount(nums[0])
                results["cgst"] += _clean_amount(nums[1])
                results["sgst"] += _clean_amount(nums[2])
                results["cess"] += _clean_amount(nums[3])
                
        # Extract (3)
        match3 = re.search(p3, full_text, re.IGNORECASE | re.DOTALL)
        if match3:
             nums = match3.group(1).split()
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
            nums = match.group(1).split()
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
                curr_line_clean = raw_line.replace("All other ITC", "").replace("(5)", "").strip()
                
                tokens = curr_line_clean.split()
                
                print(f"DEBUG:   Line {j} tokens: {tokens}")
                
                for token in tokens:
                    # Strict validation: Number-like
                    if re.match(r'^[\d,]+\.?\d*$', token) and re.search(r'\d', token):
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
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc: full_text += page.get_text() + "\n"
        doc.close()

        # Pattern: (1) Import of Goods
        pattern = r"\(1\)\s*Import\s*of\s*goods.*?((?:[\d,]+\.?\d*\s+){3}[\d,]+\.?\d*)"
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            nums = match.group(1).split()
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
        "return_period": None,
        "filing_date": None,
        "itc": { "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0 }
    }
    
    if not file_path: return meta

    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc: full_text += page.get_text() + "\n"
        doc.close()
        
        # 1. Filing Date
        # Regex: Date of Filing followed by DD/MM/YYYY
        date_match = re.search(r"Date\s*of\s*Filing.*?(\d{2}[/\-]\d{2}[/\-]\d{4})", full_text, re.IGNORECASE)
        if date_match:
            meta["filing_date"] = date_match.group(1).replace('-', '/')
            
        # 2. Return Period
        # Primary: Year ... Month ...
        # Standard GSTR-3B: "Year		2022		Month		April"
        ym_match = re.search(r"Year\s+(\d{4}).*?Month\s+([A-Za-z]+)", full_text, re.IGNORECASE | re.DOTALL)
        if ym_match:
            meta["return_period"] = f"{ym_match.group(2)} {ym_match.group(1)}" # April 2022
        else:
            # Fallback: "Return Period: April 2022"
            rp_match = re.search(r"Return\s*Period\s*[:\-\s]*([A-Za-z]+\s*[\-]?\s*\d{4})", full_text, re.IGNORECASE)
            if rp_match:
                # Basic cleanup
                clean_rp = rp_match.group(1).replace('\n', ' ').strip()
                meta["return_period"] = clean_rp

        # 3. Total ITC (Aggregation)
        # 4A1
        r1 = parse_gstr3b_pdf_table_4_a_1(file_path)
        # 4A2 + 4A3
        r23 = parse_gstr3b_pdf_table_4_a_2_3(file_path)
        # 4A4
        r4 = parse_gstr3b_pdf_table_4_a_4(file_path)
        # 4A5
        r5 = parse_gstr3b_pdf_table_4_a_5(file_path)
        
        # Summation
        for k in meta["itc"]:
            val = r1.get(k, 0) + r23.get(k, 0) + (r4.get(k, 0) if r4 else 0) + (r5.get(k, 0) if r5 else 0)
            meta["itc"][k] = float(f"{val:.2f}")

    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")

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
                # Look for amounts formatted like 0.00 or 1,234.56 within reasonable distance
                nums = re.findall(r"((?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})", post_text[:250])
                
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
        doc = fitz.open(file_path)
        for page in doc:
            text = page.get_text()
            # Matches "(1) As per rules 42 & 43 of CGST Rules" or "& 43"
            match = re.search(r"\(1\)\s*As\s*per\s*rules\s*42\s*(&|and)\s*43", text, re.IGNORECASE)
            if match:
                post_text = text[match.end():]
                nums = re.findall(r"((?:\d{1,3}(?:,\d{3})*|\d+)\.\d{2})", post_text[:250])
                
                if len(nums) >= 1: vals['igst'] = _clean_amount(nums[0])
                if len(nums) >= 2: vals['cgst'] = _clean_amount(nums[1])
                if len(nums) >= 3: vals['sgst'] = _clean_amount(nums[2])
                if len(nums) >= 4: vals['cess'] = _clean_amount(nums[3])
                
                break
        doc.close()
    except Exception as e:
        print(f"Error parsing 4B1: {e}")
    return vals
