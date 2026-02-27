import sys
import re

def patch_file(target_file, revised_drc_file, revised_model_file):
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open(revised_drc_file, 'r', encoding='utf-8') as f:
        new_drc_body = f.read()
    
    with open(revised_model_file, 'r', encoding='utf-8') as f:
        new_model_body = f.read()
        
    new_content = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Match create_drc01a_tab
        if line.strip().startswith("def create_drc01a_tab(self):"):
            new_content += new_drc_body + "\n"
            # Skip until next function or significant dedent
            i += 1
            while i < len(lines) and not (lines[i].startswith("    def ") and not lines[i].startswith("        def ")):
                # Be careful not to skip everything. create_drc01a_tab ends around 1684.
                # The next function is create_drc01a_finalization_panel at 1686.
                if lines[i].strip().startswith("def create_drc01a_finalization_panel"):
                    break
                i += 1
            continue
            
        # Match _get_drc01a_model
        if line.strip().startswith("def _get_drc01a_model(self):"):
            new_content += new_model_body + "\n"
            i += 1
            while i < len(lines) and not (lines[i].startswith("    def ") and not lines[i].startswith("        def ")):
                if lines[i].strip().startswith("def validate_drc01a_model"):
                    break
                i += 1
            continue
            
        new_content += line
        i += 1
        
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patch applied successfully.")

if __name__ == "__main__":
    patch_file(
        "D:/gst/src/ui/proceedings_workspace.py",
        "D:/gst/revised_create_drc01a.txt",
        "D:/gst/revised_model_logic.txt"
    )
