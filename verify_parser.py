from src.services.scrutiny_parser import ScrutinyParser
import json

parser = ScrutinyParser()
file_path = "c:\\Users\\manum\\.gemini\\antigravity\\scratch\\GST_Adjudication_System\\2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"

try:
    results = parser.parse_file(file_path)
    
    # Custom encoder for sets or non-serializable stuff if needed, but dicts should be fine
    print(json.dumps(results, indent=2, default=str))

except Exception as e:
    print(f"Verification Error: {e}")
