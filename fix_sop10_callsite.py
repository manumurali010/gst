
import os

TARGET_FILE = r"C:\Users\manum\.gemini\antigravity\scratch\gst\src\services\scrutiny_parser.py"

NEW_BLOCK = r'''        # 10. Point 10: Import of Goods (SOP-10) [Revised Method Call]
        # Use updated method that supports PDF aggregation
        # Prioritize GSTR-2B Analyzer if available
        analyzer_to_use = gstr2b_analyzer if gstr2b_analyzer else gstr2a_analyzer
        if analyzer_to_use:
             res_sop10 = self._parse_import_itc_phase2(file_path, gstr2a_analyzer=analyzer_to_use, gstr3b_pdf_paths=gstr3b_pdf_list)
             if isinstance(res_sop10, dict):
                 issues.append(res_sop10)
                 if res_sop10.get("status") != "info": analyzed_count += 1
        else:
             # No analyzer -> Info
             issues.append({
                 "issue_id": "IMPORT_ITC_MISMATCH",
                 "category": "Import of Goods (IMPG) vs 3B",
                 "description": "Point 10- Import of Goods (IMPG) vs 3B",
                 "status": "info",
                 "status_msg": "Data Not Available (Missing 2A/2B Data)",
                 "total_shortfall": 0.0
             })
'''

def patch_callsite():
    try:
        with open(TARGET_FILE, 'rb') as f:
            content = f.read().decode('utf-8')
        
        # Start Marker
        start_marker = "# 10. Point 10: Import of Goods (SOP-10) [Revised]"
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print("ERROR: Start marker not found!")
            return

        # End Marker
        # "if sop10_status != "info": analyzed_count += 1"
        end_marker = 'if sop10_status != "info": analyzed_count += 1'
        end_idx = content.find(end_marker, start_idx)
        if end_idx == -1:
            print("ERROR: End marker not found!")
            return
            
        # The end_marker itself should be removed.
        # Find newline after it.
        next_newline = content.find("\n", end_idx)
        
        pre = content[:start_idx]
        post = content[next_newline+1:]
        
        new_content = pre + NEW_BLOCK + post
        
        with open(TARGET_FILE, 'wb') as f:
            f.write(new_content.encode('utf-8'))
            
        print("SUCCESS: Call site patched.")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    patch_callsite()
