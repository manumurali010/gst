import sys
import os
import inspect
import hashlib

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from ui.proceedings_workspace import ProceedingsWorkspace
    print("Successfully imported ProceedingsWorkspace")
    
    # Check method source
    method = ProceedingsWorkspace.build_scn_issue_from_asmt10
    source = inspect.getsource(method)
    
    print("\n--- Source of build_scn_issue_from_asmt10 ---")
    print(source)
    print("---------------------------------------------")
    
    if "[STAGE 1]" in source:
        print("VERIFIED: [STAGE 1] trace is present in loaded code.")
    else:
        print("FAILED: [STAGE 1] trace is MISSING from loaded code.")
        
    # Check file on disk
    file_path = inspect.getfile(ProceedingsWorkspace)
    print(f"\nLoaded from file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"File Size on Disk: {len(content)} bytes")
        if "[STAGE 1]" in content:
            print("VERIFIED: [STAGE 1] trace is present in file on disk.")
        else:
            print("FAILED: [STAGE 1] trace is MISSING from file on disk.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
