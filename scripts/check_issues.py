from src.database.db_manager import DatabaseManager

db = DatabaseManager()

print("=== ALL ISSUES ===")
all_issues = db.get_all_issues_metadata()
for issue in all_issues:
    print(f"ID: {issue['issue_id']}")
    print(f"Name: {issue['issue_name']}")
    print(f"Active: {issue['active']}")
    print("-" * 40)

print("\n=== ACTIVE ISSUES ONLY ===")
active_issues = db.get_active_issues()
for issue in active_issues:
    print(f"ID: {issue['issue_id']}")
    print(f"Name: {issue['issue_name']}")
    print("-" * 40)

if len(active_issues) == 0:
    print("NO ACTIVE ISSUES FOUND!")
    print("\nThis is why your issue doesn't appear in the dropdown.")
    print("You need to check the 'Active / Published' checkbox when saving your issue.")
