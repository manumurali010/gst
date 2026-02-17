import ast
import os

FILE_PATH = os.path.join("src", "services", "scrutiny_parser.py")

class IdAuditor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None

    def visit_Return(self, node):
        if isinstance(node.value, ast.Dict):
            keys = []
            for k in node.value.keys:
                if isinstance(k, ast.Constant):
                    keys.append(k.value)
                elif isinstance(k, ast.Str): # Python < 3.8
                    keys.append(k.s)
            
            if "issue_id" not in keys:
                # Check if it returns a 'category' key (likely a parser result)
                if "category" in keys:
                    self.errors.append({
                        "function": self.current_function,
                        "line": node.lineno,
                        "missing": "issue_id",
                        "keys": keys
                    })

def audit_file():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    auditor = IdAuditor()
    auditor.visit(tree)

    if auditor.errors:
        print(f"[FAIL] Found {len(auditor.errors)} potential violations in {FILE_PATH}:")
        for err in auditor.errors:
            print(f"  Line {err['line']} in {err['function']}: Missing 'issue_id' (Has keys: {err['keys']})")
    else:
        print(f"[PASS] No violations found in {FILE_PATH}.")

if __name__ == "__main__":
    audit_file()
