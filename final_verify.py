from src.services.scrutiny_parser import ScrutinyParser
import json

file_path = r"2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"
parser = ScrutinyParser()
results = parser.parse_file(file_path)

print(f"Total Issues Detected: {results['summary']['total_issues']}")
for issue in results['issues']:
    print(f"\n--- Issue: {issue['category']} ---")
    if 'labels' in issue:
        print(f"Dynamic Labels Found:")
        print(json.dumps(issue['labels'], indent=2))
    else:
        print("No dynamic labels (Group B/ITC usually)")

# Check RCM specifically
rcm_issue = next((i for i in results['issues'] if "RCM" in i['category']), None)
if rcm_issue:
    print("\nSUCCESS: RCM detected.")
    print(f"Labels for RCM: {rcm_issue.get('labels')}")
else:
    print("\nFAIL: RCM NOT detected.")
