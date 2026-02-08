import sys
import os
import json

# Add project root to path
sys.path.append(r'c:\Users\manum\.gemini\antigravity\gst')

from src.services.asmt10_generator import ASMT10Generator

# Simulated Snapshot from DB diagnostic
case_data = {
  "gstin": "32AADFW8764E1Z1",
  "legal_name": "WESTERN TRADING COMPANY",
  "financial_year": "2022-23",
  "oc_number": "3/2026",
  "issue_date": "2026-01-21",
  "taxpayer_details": {}
}

issues = [
  {
    "issue_id": "ITC_3B_2B_OTHER",
    "category": "All Other ITC (GSTR 3B vs GSTR 2B)",
    "description": "Point 4- All Other ITC (GSTR 3B vs GSTR 2B)",
    "total_shortfall": 1746718.0,
    "is_included": True,
    "brief_facts": "The ITC claimed in 3B exceeds 2B.",
    "summary_table": {
        "columns": ["Description", "Amount"],
        "rows": [{"col0": "GSTR-3B", "col1": "100"}]
    }
  },
  {
    "issue_id": "GSTR1_3B_MISMATCH",
    "category": "Outward Supply Mismatch",
    "total_shortfall": 5000.0,
    "is_included": True,
    "brief_facts": "Mismatch in returns."
  }
]

def test_gen():
    gen = ASMT10Generator()
    html = gen.generate_html(case_data, issues)
    
    output_path = r'c:\Users\manum\.gemini\antigravity\gst\debug_asmt10.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML generated and saved to {output_path}")
    print(f"HTML Length: {len(html)}")
    
    if "Issue 1" in html:
        print("SUCCESS: 'Issue 1' found in HTML.")
    else:
        print("FAILURE: 'Issue 1' NOT found in HTML.")

if __name__ == "__main__":
    test_gen()
