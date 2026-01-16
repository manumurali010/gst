
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.issue_card import IssueCard
import inspect

print(f"IssueCard file: {inspect.getfile(IssueCard)}")
print(f"IssueCard init args: {inspect.signature(IssueCard.__init__)}")

try:
    card = IssueCard({}, issue_number=1)
    print("SUCCESS: IssueCard accepted issue_number")
except Exception as e:
    print(f"FAIL: {e}")
