import zipfile
import xml.etree.ElementTree as ET
import re
import os

file_path = r"c:\Users\manum\.gemini\antigravity\gst\032023_32AAMFM4610Q1Z0_GSTR2BQ_05012026.xlsx"

def parse_shared_strings(z):
    strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        print("Parsing sharedStrings.xml...")
        with z.open('xl/sharedStrings.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            # Namespace for matches finding
            ns = {'mq': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in root.findall('mq:si', ns):
                t = si.find('mq:t', ns)
                if t is not None:
                    strings.append(t.text)
                else:
                    strings.append("")
    return strings

def parse_sheet(z, sheet_path, shared_strings):
    print(f"Parsing {sheet_path}...")
    with z.open(sheet_path) as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'mq': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        sheet_data = root.find('mq:sheetData', ns)
        rows_data = []
        
        for row in sheet_data.findall('mq:row', ns):
            row_idx = row.get('r')
            cell_values = []
            for c in row.findall('mq:c', ns):
                t = c.get('t') # Type: s=sharedString, inlineStr, etc.
                v = c.find('mq:v', ns)
                
                val = ""
                if v is not None:
                    if t == 's':
                        idx = int(v.text)
                        if idx < len(shared_strings):
                            val = shared_strings[idx]
                    else:
                        val = v.text
                cell_values.append(val)
            
            # Reconstruct row text for analysis
            row_text_parts = [str(x).lower().strip() for x in cell_values if x]
            row_text = " ".join(row_text_parts)
            rows_data.append((row_idx, row_text, cell_values))
            
            # Limit to first 100 rows for debug
            if len(rows_data) > 100: break
            
    return rows_data

try:
    if os.name == 'nt':
        import sys
        sys.stdout.reconfigure(encoding='utf-8')

    with zipfile.ZipFile(file_path, 'r') as z:
        shared_strings = parse_shared_strings(z)
        print(f"Loaded {len(shared_strings)} shared strings.")
        
        # We assume 'ITC Available' is sheet2 based on previous run (rId2)
        # Note: rId2 usually maps to worksheets/sheet2.xml
        
        rows = parse_sheet(z, 'xl/worksheets/sheet2.xml', shared_strings)
        
        print("\n--- RECONSTRUCTED ROWS (Rows 7-20) ---")
        for r_idx, r_text, r_vals in rows[6:20]:
            print(f"Row {r_idx}: {r_text}")
            
            if "inward supplies" in r_text and "reverse charge" in r_text:
                print(f"  [MATCH CANDIDATE] -> {r_vals}")

except Exception as e:
    print(f"Error: {e}")
