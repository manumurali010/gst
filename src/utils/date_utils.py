import re
from datetime import datetime

def normalize_financial_year(fy_str):
    """
    Safely normalizes financial year strings to YYYY-YY format.
    Handles: '2022-23', '2022-2023', '22-23', '2022- 23', etc.
    
    Returns:
        str: Normalized FY (e.g., '2022-23') or None if invalid.
    """
    if not fy_str:
        return None
        
    # Clean string: remove spaces and tabs
    clean_fy = re.sub(r'\s+', '', str(fy_str))
    
    # Pattern 1: Digit(2 or 4) - Digit(2 or 4)
    hyphen_match = re.match(r'^(\d{2,4})-(\d{2,4})$', clean_fy)
    if hyphen_match:
        p1, p2 = hyphen_match.groups()
        
        # Normalize P1 (Start Year)
        if len(p1) == 4:
            start_year = int(p1)
        elif len(p1) == 2:
            start_year = int("20" + p1)
        else:
            return None
            
        # Normalize P2 (End Year)
        if len(p2) == 4:
            end_year = int(p2)
        elif len(p2) == 2:
            end_year = int("20" + p2)
        else:
            return None
            
        # Sanity Check: End year must be start year + 1
        if end_year != start_year + 1:
            return None
            
        return f"{start_year}-{str(end_year)[-2:]}"

    # Pattern 2: Single 4-digit year (e.g. 2022)
    single_year_match = re.match(r'^(\d{4})$', clean_fy)
    if single_year_match:
        start_year = int(single_year_match.group(1))
        if 2017 <= start_year <= 2100:
            end_year = start_year + 1
            return f"{start_year}-{str(end_year)[-2:]}"

    return None

def get_fy_end_year(fy_str):
    """
    Extracts the 4-digit end year from an FY string.
    Example: '2022-23' -> 2023
    """
    norm = normalize_financial_year(fy_str)
    if not norm:
        return None
    
    p1, p2 = norm.split('-')
    start_year = int(p1)
    return start_year + 1

def validate_gstin_format(gstin):
    """
    Strict regex validation for Indian 15-digit GSTIN.
    Format: State(2) + PAN(10) + EntityType(1) + Checksum(2)
    Note: The 14th character (index 13) is strictly 'Z'.
    """
    if not gstin:
        return False
    # index: 01 23456 7890 1 2 3 4
    # chars: SS PPPPP NNNN E Z C
    pattern = r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$'
    return bool(re.match(pattern, str(gstin).upper()))

def validate_fy_sanity(fy_str):
    """
    True if the FY is within the valid GST operating range (2017+).
    """
    norm = normalize_financial_year(fy_str)
    if not norm:
        return False
    start_year = int(norm.split('-')[0])
    return 2017 <= start_year <= datetime.now().year + 1
