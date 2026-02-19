import os
import re

# Configuration
OLD_PATH_PART = r"C:[\\/]Users[\\/]manum[\\/]\.gemini[\\/]antigravity[\\/]gst"
NEW_PATH = os.getcwd().replace("\\", "/") # Normalized path

def fix_paths_in_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for matches
        # We look for the specific old project path
        # Also let's check for the 'scratch' path mentioned in debug scripts
        # "C:\\Users\\manum\\.gemini\\antigravity\\scratch" -> Assume it might be at D:\scratch or similar if moved relative
        
        modified_content = content
        
        # 1. Replace project root path
        # Naive string replace for both forward and backward slashes
        content_fixed = getattr(modified_content, "replace")("C:\\Users\\manum\\.gemini\\antigravity\\gst", NEW_PATH.replace("/", "\\"))
        content_fixed = content_fixed.replace("C:/Users/manum/.gemini/antigravity/gst", NEW_PATH)
        
        # 2. Heuristic for the 'scratch' folder if it was moved to D:\scratch or D:\antigravity\scratch
        # For now, let's just warn or replace if it's a direct sub
        # The user's specific case in debug_scrutiny_file.py:
        # "C:\\Users\\manum\\.gemini\\antigravity\\scratch\\..."
        # If we assume they moved the whole 'antigravity' folder or similar structure:
        # Let's verify if D:\scratch exists? We can't verify easily.
        # Let's just point it to a hardcoded guess or ask user.
        # Actually, let's just replace the drive letter if strict 'C:' is found? No, dangerous.
        
        if content_fixed != content:
            print(f"Updating paths in: {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_fixed)
                
    except Exception as e:
        print(f"Skipping {file_path}: {e}")

def main():
    print(f"Scanning for paths to update in {os.getcwd()}...")
    print(f"Replacing 'C:\\Users\\manum\\.gemini\\antigravity\\gst' with '{os.getcwd()}'")
    
    for root, dirs, files in os.walk("."):
        if "venv" in dirs:
            dirs.remove("venv") 
        if ".git" in dirs:
            dirs.remove(".git")
            
        for file in files:
            if file.endswith(".py") or file.endswith(".bat") or file.endswith(".txt"):
                if file == "fix_paths.py": continue
                fix_paths_in_file(os.path.join(root, file))

    print("Done. Please verify scripts/debug_scrutiny_file.py manually if it points to external folders like 'scratch'.")

if __name__ == "__main__":
    main()
