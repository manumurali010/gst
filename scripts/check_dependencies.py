import os
import sys
import ctypes
from ctypes.util import find_library

def check_dll(name):
    print(f"Checking for {name}...", end=" ")
    lib_path = find_library(name)
    if lib_path:
        print(f"FOUND at {lib_path}")
        try:
            ctypes.CDLL(lib_path)
            print(f"  [SUCCESS] Successfully loaded {name}")
            return True
        except Exception as e:
            print(f"  [FAILURE] Could not load {name}: {e}")
            return False
    else:
        print("NOT FOUND")
        return False

def check_weasyprint():
    print("\nAttempting to import WeasyPrint...")
    try:
        from weasyprint import HTML
        print("  [SUCCESS] WeasyPrint imported successfully.")
        return True
    except Exception as e:
        print(f"  [FAILURE] WeasyPrint import failed: {e}")
        return False

def main():
    print("=== Rendering Dependency Audit ===\n")
    print(f"Python Version: {sys.version}")
    print(f"Operating System: {sys.platform}")
    print(f"Current Path: {os.environ.get('PATH', '')[:100]}...\n")

    dependencies = ["cairo", "pango-1.0", "gobject-2.0"]
    results = [check_dll(lib) for lib in dependencies]
    
    wp_result = check_weasyprint()
    
    print("\n=== Summary ===")
    if all(results) and wp_result:
        print("STATUS: HEALTHY. Rendering should work.")
    else:
        print("STATUS: ISSUES DETECTED. See instructions in docs/FIX_RENDERING.md")

if __name__ == "__main__":
    main()
