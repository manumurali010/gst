
import os

file_path = r"c:\Users\manum\.gemini\antigravity\gst\src\ui\proceedings_workspace.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

anchor = "for i, s_row in enumerate(s_rows):"
idx = content.find(anchor)

if idx != -1:
    line_start = content.rfind('\n', 0, idx) + 1
    indentation = content[line_start:idx]
    
    # We want to insert "try:" before the loop, and indent the loop and subsequent lines.
    # But indenting subsequent lines is hard without parsing.
    # Alternative: Use a broad try-except around the call to hydrate? No, local loop.
    
    # Let's just wrap the inner block in try-except? No, the loop itself might crash?
    # enumerate(s_rows) crashes if s_rows is None.
    
    # Let's just replace the loop line with:
    # try:
    #     loop
    # except...
    
    # But indentation of the loop body needs to increase.
    # That's too risky to do with string replacement blindly.
    
    # Proper fix for potential s_rows crash:
    # Ensure s_rows is not None.
    # It is checked at line 3097.
    
    # Let's assume the crash is inside the loop.
    # I'll just look for "for i, s_row in enumerate(s_rows):"
    
    # Actually, maybe I should revert the logic slightly to be cleaner.
    
    # Let's read the lines again to be sure.
    pass

# I'll carry out a simpler fix: 
# Ensure s_rows is iterable before the loop.
# It seems s_rows could be None if snapshot_grid is None?
# line 3097: s_rows = snapshot_grid.get('rows', []) if isinstance(snapshot_grid, dict) else snapshot_grid
# If snapshot_grid is None, s_rows is None.
# If snapshot_grid is [], s_rows is [].

# If template_snapshot exists but has no 'grid_data', snapshot_grid is None.
# And s_rows becomes None.
# CRASH.

# Fix: Ensure s_rows is list or empty list.

target_line = "s_rows = snapshot_grid.get('rows', []) if isinstance(snapshot_grid, dict) else snapshot_grid"
replacement_line = "s_rows = snapshot_grid.get('rows', []) if isinstance(snapshot_grid, dict) else (snapshot_grid if snapshot_grid else [])"

if target_line in content:
    new_content = content.replace(target_line, replacement_line)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESS: Patched s_rows assignment.")
else:
    print("ERROR: Target line not found.")
