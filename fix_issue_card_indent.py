
import os

file_path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\src\ui\issue_card.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start and end of the bad block
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "content_hash = hashlib.md5(content_str.encode()).hexdigest()[:8]" in line:
        start_idx = i
    if "print(f\"WARNING: Recovered Identity for Snapshot. Surrogate ID: {issue_id}\")" in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found block: {start_idx} to {end_idx}")
    
    # We keep the start line (content_hash calculation)
    # We want to replace everything AFTER start_idx up to (and including) end_idx
    # with clean code.
    
    clean_code = [
        '                 \n',
        '                 # [Fix-22] Authoritative Identity Priority\n',
        '                 # 1. Check Template Reference first\n',
        '                 if tmpl_ref.get(\'issue_id\'):\n',
        '                      issue_id = tmpl_ref.get(\'issue_id\')\n',
        '                      print(f"INFO: Recovered authoritative issue_id \'{issue_id}\' from template reference.")\n',
        '                 \n',
        '                 # 2. Check ASMT-10 Origin\n',
        '                 elif snapshot.get(\'origin\') == \'ASMT10\':\n',
        '                      pass\n',
        '                 \n',
        '                 # 3. Fallback to Surrogate ID (Deterministic)\n',
        '                 if not issue_id:\n',
        '                      issue_id = f"LEGACY-RECOVERED-{content_hash}"\n',
        '                 \n',
        '                 if not issue_name:\n',
        '                      if tmpl_ref.get(\'issue_name\'):\n',
        '                           issue_name = tmpl_ref.get(\'issue_name\')\n',
        '                      else:\n',
        '                           issue_name = f"Recovered Issue ({content_hash})"\n',
        '                      \n',
        '                 print(f"WARNING: Recovered Identity for Snapshot. Surrogate ID: {issue_id}")\n'
    ]
    
    # Slice replaces lines lines[start_idx+1 : end_idx+1]
    lines[start_idx+1 : end_idx+1] = clean_code
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully patched IssueCard.py")
else:
    print("Could not find block indices.")
