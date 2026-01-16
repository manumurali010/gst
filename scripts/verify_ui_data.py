import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
from services.scrutiny_parser import ScrutinyParser

def create_mock_excel_point4():
    """Create mock data for Point 4 with monthly breakdown and labels in B5, F5, J5."""
    path = "mock_point4.xlsx"
    # Row 0-3 (Excel Rows 1-4)
    data = [[""] * 13 for _ in range(4)]
    
    # Row 4 (Excel Row 5) - Headers for Pandas header=[4, 5] AND Labels for openpyxl
    # B5=Index(4,1), F5=Index(4,5), J5=Index(4,9)
    # We use these as Level 0 headers for pandas too
    h1 = [""] * 13
    h1[0] = "Tax Period"
    h1[1] = h1[2] = h1[3] = h1[4] = "ITC Auto-drafted in GSTR 2B"
    h1[5] = h1[6] = h1[7] = h1[8] = "ITC Claimed in GSTR-3B"
    h1[9] = h1[10] = h1[11] = h1[12] = "Shortfall (-) / Excess (+)"
    data.append(h1)
    
    # Row 5 (Excel Row 6) - Tax Heads for Level 1
    h2 = ["Desc", "IGST", "CGST", "SGST", "Cess", "IGST", "CGST", "SGST", "Cess", "IGST", "CGST", "SGST", "Cess"]
    data.append(h2)
    
    # Monthly Data (Standard SOP starts data at Row 7 = Index 6)
    # Simulate Excess: Claimed (120) > Available (100) -> Diff (-20)
    for i in range(12):
        month = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"][i]
        data.append([f"{month}-23", 100, 100, 100, 0, 120, 120, 120, 0, -20, -20, -20, 0])
        
    # Total Row (Excel Row 19 = Index 18)
    data.append(["Total", 1200, 1200, 1200, 0, 1440, 1440, 1440, 0, -240, -240, -240, 0])
    
    df = pd.DataFrame(data)
    # Use standard pandas write to save it
    # We need to ensure cells B5, F5, J5 have values for labels
    df.to_excel(path, sheet_name="ITC (Other than IMPG)", index=False, header=False)
    return path

def run_test():
    parser = ScrutinyParser()
    file_path = create_mock_excel_point4()
    
    print("--- Test Point 4 Table Structure ---")
    print("Starting parse_file...")
    results = parser.parse_file(file_path, extra_files={}, configs={'gstr3b_freq': 'Yearly'})
    issues = results.get('issues', [])
    print(f"Found {len(issues)} issues")
    
    p4 = next((i for i in issues if "Point 4" in i.get('category', '') or "Other ITC" in i.get('description', '')), None)
    
    if p4:
        print(f"Point 4 Issue Found: {p4.get('description')}")
        if "summary_table" in p4:
            st = p4["summary_table"]
            print(f"Headers: {st.get('headers')}")
            print("Summary Row Values:")
            for r in st.get('rows', []):
                print(f"  - {r.get('col0')}: CGST={r.get('col1')}, SGST={r.get('col2')}, IGST={r.get('col3')}")
            print(f"Monthly Rows Extracted: {len(p4.get('rows', []))}")
        else:
            print("ERROR: summary_table NOT FOUND in Point 4 issue")
    else:
        print("Point 4 Issue NOT FOUND")

    # Cleanup
    try:
        os.remove(file_path)
    except: pass

if __name__ == "__main__":
    run_test()
