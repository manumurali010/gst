from src.services.scrutiny_parser import ScrutinyParser
import json

parser = ScrutinyParser()
file_path = "2022-23_32AFWPD9794D1Z0_Tax liability and ITC comparison.xlsx"

result = parser.parse_file(file_path)

if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(f"Total Issues: {result['summary']['total_issues']}")
    # print(f"Total Tax Shortfall: {result['summary']['total_tax_shortfall']}")
    
    for issue in result["issues"]:
        if issue['template_type'] == "itc_yearly_summary":
            print(f"\n--- {issue['description']} ---")
            for row in issue["rows"]:
                print(f"Row: {row['description']}")
                print(f"Vals: {row['vals']}")
