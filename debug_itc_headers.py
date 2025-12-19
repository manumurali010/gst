import pandas as pd

file_path = "c:\\Users\\manum\\.gemini\\antigravity\\scratch\\GST_Adjudication_System\\2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"

try:
    xl = pd.ExcelFile(file_path)
    sheet_name = next((s for s in xl.sheet_names if "ITC (Other" in s), None)
    
    if sheet_name:
        print(f"--- Sheet: {sheet_name} ---")
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=[3, 4, 5, 6])
        
        print("\n--- All Column Headers (0-40) ---")
        for idx, col in enumerate(df.columns.values):
            if idx > 40: break
            clean_name = " | ".join([str(p).strip() for p in col if str(p).strip() not in ["nan", "Unnamed", ""]])
            print(f"Idx {idx}: {clean_name}")

        print("\n--- Total Row Values ---")
        for idx, row in df.iterrows():
            first_vals = [str(v).lower() for v in row.iloc[0:5].values]
            if any("total" in v for v in first_vals):
                print(f"Total Row Index: {idx}")
                for c_idx, val in enumerate(row):
                    if c_idx > 40: break
                    try:
                        v = float(val)
                        if abs(v) > 1:
                            print(f"  Col {c_idx}: {v}")
                    except: pass
                break
                
except Exception as e:
    print(e)
