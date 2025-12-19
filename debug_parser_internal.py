import pandas as pd

file_path = "c:\\Users\\manum\\.gemini\\antigravity\\scratch\\GST_Adjudication_System\\2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"

try:
    print("--- Testing Header Extraction for Group B ---")
    xl = pd.ExcelFile(file_path)
    
    # Check 'ITC (Other than IMPG)'
    sheet_name = next((s for s in xl.sheet_names if "ITC (Other" in s), None)
    
    if sheet_name:
        # Read Headers (Rows 3,4,5,6)
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=[3, 4], nrows=0)
        
        print(f"\nSheet: {sheet_name}")
        cols = df.columns.values
        
        # We look for the "3B" and "2B" headers to extract the table name
        # Typcally: "ITC claimed in GSTR-3B [Table 4A(4)...]"
        
        for c in cols:
             # c is tuple
             col_str = " | ".join([str(p) for p in c if "nan" not in str(p)]).replace('\n', ' ')
             if "GSTR-3B" in col_str or "GSTR-2B" in col_str:
                 print(f"Header: {col_str}")

except Exception as e:
    print(f"Error: {e}")
