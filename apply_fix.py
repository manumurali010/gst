
import os

file_path = r"c:\Users\manum\.gemini\antigravity\gst\src\ui\proceedings_workspace.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

anchor = "for i, s_row in enumerate(s_rows):"
idx = content.find(anchor)

if idx != -1:
    line_start = content.rfind('\n', 0, idx) + 1
    indentation = content[line_start:idx]
    
    rest = content[idx:]
    lines = rest.split('\n')
    
    # Verify context
    # lines[0] is header
    # lines[1] should be if i < len(m_rows):
    # lines[2] should be m_row = m_rows[i]
    
    print(f"Line 0: {repr(lines[0])}")
    print(f"Line 1: {repr(lines[1])}")
    print(f"Line 2: {repr(lines[2])}")
    
    if "if i < len(m_rows):" in lines[1] and "m_row = m_rows[i]" in lines[2]:
        original_chunk = '\n'.join(lines[:3])
        
        # Indentation for inner blocks (4 spaces deeper)
        inner_indent = indentation + "    "
        # Indentation for double inner (8 spaces deeper)
        double_indent = inner_indent + "    "
        triple_indent = double_indent + "    "
        quad_indent = triple_indent + "    "
        
        new_block_lines = [
            f"{indentation}row_policy = master_grid.get('row_policy', 'fixed')",
            "", 
            f"{indentation}for i, s_row in enumerate(s_rows):",
            f"{inner_indent}m_row = None",
            "",
            f"{inner_indent}if i < len(m_rows):",
            f"{double_indent}m_row = m_rows[i]",
            f"{inner_indent}elif row_policy == 'dynamic' and len(m_rows) > 0:",
            f"{double_indent}# [FIX] Expand Master for Dynamic Rows",
            f"{double_indent}import copy",
            f"{double_indent}prototype = m_rows[0]",
            f"{double_indent}if isinstance(prototype, dict):",
            f"{triple_indent}try:",
            f"{quad_indent}new_row = copy.deepcopy(prototype)",
            f"{quad_indent}new_row['id'] = f\"r{{i+1}}_hydrated\"",
            f"{quad_indent}m_rows.append(new_row)",
            f"{quad_indent}m_row = new_row",
            f"{triple_indent}except Exception as e:",
            f"{quad_indent}print(f\"[HYDRATION ERROR] Failed to clone dynamic row: {{e}}\")",
            "",
            f"{inner_indent}if m_row:"
        ]
        
        new_chunk = '\n'.join(new_block_lines)
        
        # Perform replacement
        # Note: we need to be careful if original_chunk appears multiple times.
        # But this code is specific enough.
        
        # We replace only the first occurrence after the found index (which is likely unique anyway or we process from idx)
        # Actually content.replace checks whole string.
        # Better to slice and rebuild.
        
        before = content[:idx]
        # remove original chunk from rest
        # original_chunk length?
        # we can't just strip len(original_chunk) because of newlines logic in split/join?
        # lines[:3] joined by \n.
        
        original_chunk_with_indent = indentation + original_chunk[len(indentation):] # indentation is already in lines[0]
        # Wait, lines[0] has indentation? No, content[idx:] starts at anchor "for..."
        # So lines[0] is "for i, s_row..." NO.
        # indent is before idx.
        # content[idx] is 'f'.
        # lines[0] is "for i, s_row in enumerate(s_rows):" (without indentation)
        # Ah! lines = rest.split('\n')
        # So lines[1] will have indentation!
        
        # So original_chunk constructed from lines[:3] will have indentation on lines 1 and 2, but NOT line 0.
        
        # Let's reconstruct the exact string to replace.
        match_len = len(lines[0]) + 1 + len(lines[1]) + 1 + len(lines[2])
        # +1 for wild guess on \r\n vs \n?
        # Safer to locate the end of line 2 in 'rest'.
        
        end_pos = 0
        newline_count = 0
        for i, char in enumerate(rest):
            if char == '\n':
                newline_count += 1
            if newline_count == 3:
                end_pos = i # This is position of 3rd newline
                break
        
        # Actually, let's just use string replacement on the snippet if it's unique enough.
        full_original_snippet = content[line_start : idx + end_pos] 
        # line_start includes indentation of first line.
        # idx is start of 'for'.
        # rest starts at 'for'.
        # end_pos is end of 3rd line relative to rest.
        
        # Let's verify logic.
        # content[line_start] is space.
        # string to replace is content[line_start : idx + end_pos] ?
        # rest[0:end_pos] covers line 0, 1, 2 (excluding 3rd newline).
        
        # Let's construct `to_replace` accurately.
        to_replace = indentation + lines[0] + '\n' + lines[1] + '\n' + lines[2]
        
        # Check if to_replace is in content
        if to_replace in content:
            new_content = content.replace(to_replace, new_chunk)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("SUCCESS: Replaced via direct string match.")
        else:
            print("ERROR: Constructed string check failed.")
            print("Expected:")
            print(repr(to_replace))
            print("Actual in file:")
            print(repr(content[line_start : line_start + len(to_replace)]))
            
    else:
        print("ERROR: Context mismatch.")
else:
    print("ERROR: Anchor not found.")
