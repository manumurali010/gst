from src.services.scrutiny_parser import ScrutinyParser
import os
import json

def test_sop_parsing():
    parser = ScrutinyParser()
    
    # Files
    main_file = '2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx'
    extra_files = {
        'gstr_2a_invoices': 'mock_gstr2a_invoices.xlsx'
    }
    
    print(f"Testing ScrutinyParser with main file: {main_file}")
    print(f"Extra files: {extra_files}")
    
    result = parser.parse_file(main_file, extra_files=extra_files)
    
    print("\n--- Summary ---")
    print(json.dumps(result.get("summary", {}), indent=2))
    
    print("\n--- Issues Found ---")
    for i in result.get("issues", []):
        print(f"- {i.get('category')}: {i.get('description')} (Shortfall: {i.get('total_shortfall')})")
        if i.get('rows'):
            print(f"  Rows: {len(i['rows'])}")

    # Check for Point 7 & 8 Specifically
    found_cancelled = any("Cancelled" in i.get('description', '') for i in result.get('issues', []))
    found_non_filer = any("Non-Filing" in i.get('description', '') for i in result.get('issues', []))
    
    if found_cancelled and found_non_filer:
        print("\n✅ Verification Success: Param 7 & 8 detected correctly!")
    else:
        print("\n❌ Verification Failed: Param 7 or 8 missing.")

if __name__ == "__main__":
    test_sop_parsing()
