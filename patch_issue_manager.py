
import os

target_file = r"c:\Users\manum\.gemini\antigravity\gst\src\ui\developer\issue_manager.py"

with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the block start and end anchors
legacy_block_start = "        # Try to load existing table design\n        tables_data = issue.get('tables', {})"
legacy_block_end = "        self.table_builder.set_data(tables_data)"

new_logic = """        # Try to load existing table design
        # tables_data = issue.get('tables', {}) # [Deprecated]
        
        # Phase 0/1: Grid Adapter Hydration (Read-Only)
        grid_data = issue.get('grid_data')
        
        # Hydrate via Adapter
        adapted_data = GridAdapter.hydrate_from_grid_schema(grid_data)
        
        # Safely extract and store metadata
        self.current_grid_meta = adapted_data.get('_meta', {})
        
        # Populate UI
        self.table_builder.set_data(adapted_data)
        
        # HARD LOCK: Read-Only Mode
        self.table_builder.setEnabled(False)
        self.table_builder.setStatusTip("Table editing is disabled in Phase 1 (Visual Inspection Only)")"""

# Construct the full block to replace - Using string finding logic to handle the inner body
start_idx = content.find(legacy_block_start)
end_idx = content.find(legacy_block_end)

if start_idx == -1 or end_idx == -1:
    print("FAILED: Could not locate start or end anchor.")
    print(f"Start found: {start_idx}, End found: {end_idx}")
    exit(1)

# Adjust end_idx to include the line
end_idx += len(legacy_block_end)

# Extract original block to double check
original_block = content[start_idx:end_idx]
print(f"Replacing block of length: {len(original_block)}")

# Replace
new_content = content[:start_idx] + new_logic + content[end_idx:]

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"SUCCESS: Patched {target_file}")
