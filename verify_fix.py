from src.services.scrutiny_parser import ScrutinyParser

file_path = r"2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"
parser = ScrutinyParser()
results = parser.parse_file(file_path)

print(f"Total Issues Detected: {results['summary']['total_issues']}")
for issue in results['issues']:
    print(f"\nIssue: {issue['category']}")
    print(f"Description: {issue['description']}")
    print(f"Total Shortfall: {issue['total_shortfall']}")
    # Print RCM specific rows if found
    if "RCM" in issue['category'] or "Reverse Charge" in issue['description']:
        print(f"RCM Rows:")
        for r in issue['rows']:
            print(f"  {r['period']}: {r['diff']}")

if not any("RCM" in i['category'] for i in results['issues']):
    print("\nFAIL: Reverse Charge issue still NOT detected!")
else:
    print("\nSUCCESS: Reverse Charge issue detected!")
