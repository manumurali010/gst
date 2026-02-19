import re

FILE_PATH = r"D:\gst\src\ui\proceedings_workspace.py"

def verify_refactoring():
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    errors = []
    
    # Patterns that suggest string-based status logic
    # 1. "Str" in status
    p1 = re.compile(r'["\'].*["\']\s+in\s+.*status')
    # 2. status == "Str"
    p2 = re.compile(r'status\s*==\s*["\'].*["\']')
    # 3. .get('status') usage in if/elif
    p3 = re.compile(r'(if|elif)\s+.*\.get\([\'"]status[\'"]')
    
    in_get_current_stage = False
    
    for i, line in enumerate(lines):
        line_num = i + 1
        stripped = line.strip()
        
        # Detect method context (crude)
        if "def get_current_stage" in stripped:
            in_get_current_stage = True
        elif stripped.startswith("def ") and in_get_current_stage:
            in_get_current_stage = False
            
        if in_get_current_stage:
            continue
            
        # exclude comments
        if stripped.startswith("#"):
            continue
            
        # check patterns
        if p1.search(stripped):
            # Exclude specific banner text assignment lines if they use 'in' (unlikely for assignment, but check)
            if "banner_text" not in stripped:
                errors.append(f"Line {line_num}: Potential substring check: {stripped}")
            
        if p2.search(stripped):
             errors.append(f"Line {line_num}: Potential equality check: {stripped}")
             
        if p3.search(stripped):
             # Exclude if just assigning to variable (handled by other checks)
             # But if used in condition directly, flag it.
             errors.append(f"Line {line_num}: Direct .get('status') in condition: {stripped}")

    if not errors:
        print("SUCCESS: No forbidden patterns found outside get_current_stage.")
    else:
        print(f"FAILURE: Found {len(errors)} potential issues:")
        for e in errors:
            print(e)
            
if __name__ == "__main__":
    verify_refactoring()
