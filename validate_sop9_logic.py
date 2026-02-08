
import os
import sys
import re
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from src.utils.pdf_parsers import parse_gstr3b_metadata
except ImportError:
    # Fallback if running from root without src in path properly
    sys.path.append(os.getcwd())
    from src.utils.pdf_parsers import parse_gstr3b_metadata

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except:
        return None

def get_financial_year(month, year):
    # If month is Jan-Mar (1-3), FY is PreviousYear-CurrentYear
    # If month is Apr-Dec (4-12), FY is CurrentYear-NextYear
    m_idx = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }.get(month.lower())
    
    y = int(year)
    if m_idx <= 3:
        return f"{y-1}-{str(y)[2:]}"
    else:
        return f"{y}-{str(y+1)[2:]}"

def calculate_cutoff_date(fy_str):
    # FY "2022-23" -> Cut-off is 30th Nov 2023
    # Logic: End Year of FY (2023) -> 30th Nov
    end_year = int("20" + fy_str.split('-')[1]) # 23 -> 2023
    return datetime(end_year, 11, 30)

def validate_sop9(pdf_path):
    print(f"--- Validating SOP-9 Logic on: {os.path.basename(pdf_path)} ---")
    
    if not os.path.exists(pdf_path):
        print("Error: File not found.")
        return

    # 1. Extraction
    meta = parse_gstr3b_metadata(pdf_path)
    print(f"Extracted Metadata: {meta}")
    
    if not meta['return_period']:
        print("FAIL: Return Period not extracted.")
        return
    if not meta['filing_date']:
        print("FAIL: Filing Date (ARN Date) not extracted.")
        return

    # 2. Logic Validation
    # Parse Return Period "February 2023"
    rp_parts = meta['return_period'].split()
    if len(rp_parts) == 2:
        month, year = rp_parts
        fy = get_financial_year(month, year)
        print(f"Derived FY: {fy}")
        
        cut_off = calculate_cutoff_date(fy)
        print(f"Calculated Cut-off Date: {cut_off.strftime('%d-%m-%Y')}")
        
        arn_date = parse_date(meta['filing_date'])
        print(f"ARN Date: {arn_date.strftime('%d-%m-%Y')}")
        
        if arn_date > cut_off:
            print(">>> VIOLATION DETECTED: ARN Date > Cut-off Date")
            print(f"    Ineligible ITC: {meta['itc']}")
        else:
            print(">>> PASS: ARN Date <= Cut-off Date")
            
    else:
        print("FAIL: Return Period format unexpected.")

if __name__ == "__main__":
    sample_pdf = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_022023.pdf"
    validate_sop9(sample_pdf)
