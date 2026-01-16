import pandas as pd
import os

excel_path = "032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

def verify_netting():
    if not os.path.exists(excel_path):
        print("Excel not found.")
        return

    print(f"Analyzing {excel_path}...")
    
    try:
        # 1. READ SUMMARY ROW ("All other ITC")
        df_summary = pd.read_excel(excel_path, sheet_name="ITC Available")
        summary_row = None
        for i, row in df_summary.iterrows():
            row_str = " ".join([str(x) for x in row.values if pd.notna(x)])
            if "All other ITC" in row_str and "Supplies from registered persons" in row_str:
                summary_row = row
                break
        
        if summary_row is None:
            print("Summary Row 'All other ITC' not found!")
            return

        # Extract values (Monthly/Quarterly logic simplified: just grab the last valid floats)
        vals_summary = []
        for x in summary_row.values:
            if isinstance(x, (int, float)) and pd.notna(x):
                vals_summary.append(float(x))
        
        if len(vals_summary) < 4:
            print(f"Startlingly few numbers in summary row: {vals_summary}")
            return
            
        # Assuming last 4 are IGST, CGST, SGST, Cess for the Quarter (Total)
        # Note: In the previous debug run, we saw huge numbers, likely totals.
        summ_igst = vals_summary[-4]
        summ_cgst = vals_summary[-3]
        summ_sgst = vals_summary[-2]
        summ_cess = vals_summary[-1]
        
        print(f"\n[A] SUMMARY ROW ('All other ITC'):")
        print(f"IGST: {summ_igst}, CGST: {summ_cgst}, SGST: {summ_sgst}, Cess: {summ_cess}")


        # 2. READ DETAILS (B2B)
        # We need to find tax columns. Usually strict names.
        # B2B Sheet
        print(f"\n[B] CALCULATING FROM DETAILS...")
        
        def sum_sheet(sheet_name):
            if sheet_name not in pd.ExcelFile(excel_path).sheet_names:
                return 0,0,0,0
            
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            # Find columns: "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"
            # Normalize Headers
            # Often headers are on row 5 or 6?
            # Let's simple sum ALL numeric columns? No, dangerous.
            
            df = pd.read_excel(excel_path, sheet_name=sheet_name, header=5) 
            # Header is split, but let's assume Row 5 (0-indexed) contains the specific names like "Integrated Tax"
            # Actual data starts row 6?
            # From inspect output: Row 5 has 'Integrated Tax(₹)'...
            
            # Use indices 10,11,12,13 based on visual inspection
            if "Integrated Tax" not in str(df.columns[10]):
                # Fallback or check exact names
                 pass

            # Summing columns by index (safe for this specific file format)
            # 10=IGST, 11=CGST, 12=SGST, 13=Cess
            
            s_igst = df.iloc[:, 10].sum()
            s_cgst = df.iloc[:, 11].sum()
            s_sgst = df.iloc[:, 12].sum()
            s_cess = df.iloc[:, 13].sum()
            
            return s_igst, s_cgst, s_sgst, s_cess

        b2b_i, b2b_c, b2b_s, b2b_cs = sum_sheet("B2B")
        print(f"B2B Sum: I={b2b_i}, C={b2b_c}, S={b2b_s}, Cs={b2b_cs}")
        
        cdnr_i, cdnr_c, cdnr_s, cdnr_cs = sum_sheet("B2B-CDNR")
        print(f"CDNR Sum: I={cdnr_i}, C={cdnr_c}, S={cdnr_s}, Cs={cdnr_cs}")
        
        # 3. COMPARE
        # Is Summary == B2B - CDNR?
        calc_i = b2b_i - cdnr_i
        calc_c = b2b_c - cdnr_c
        calc_s = b2b_s - cdnr_s
        calc_cs = b2b_cs - cdnr_cs # Note: CDNR might be Credit Note (negative) or Debit Note (positive)?
        # Actually in CDNR sheet, Credit Notes are usually positive values but with "Note Type" = C?
        # Or are they signed?
        # Let's peek at CDNR first.
        
        df_cdnr = pd.read_excel(excel_path, sheet_name="B2B-CDNR") if "B2B-CDNR" in pd.ExcelFile(excel_path).sheet_names else pd.DataFrame()
        if not df_cdnr.empty:
            print("Peeking CDNR Note Types...")
            # Look for "Note Type" column
            display_cols = [c for c in df_cdnr.columns if "Note Type" in str(c)]
            if display_cols: 
                print(df_cdnr[display_cols[0]].unique())

        print(f"\n Calculated Net (B2B - CDNR_Sum?): I={calc_i:.2f}, C={calc_c:.2f}, S={calc_s:.2f}")

        # Check Match
        match_i = abs(summ_igst - calc_i) < 5.0
        match_c = abs(summ_cgst - calc_c) < 5.0
        
        if match_i and match_c:
             print("\nCONCLUSION: Summary Row IS NET of CDNR (B2B - CDNR matches Summary).")
        elif abs(summ_igst - b2b_i) < 5.0:
             print("\nCONCLUSION: Summary Row matches B2B GROSS (NOT NET of CDNR).")
        else:
             print("\nCONCLUSION: No obvious match. Detailed analysis required.")
             print(f"Diff Summary vs Calc Net: I={summ_igst - calc_i}, C={summ_cgst - calc_c}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_netting()
