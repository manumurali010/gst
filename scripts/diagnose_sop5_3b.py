
import sys
import os

# Adjust path to find src
sys.path.append(os.path.abspath("c:\\Users\\manum\\.gemini\\antigravity\\scratch\\gst"))

from src.utils.pdf_parsers import parse_gstr3b_pdf_table_3_1_a

def run_diagnostic():
    # File found in previous step
    # Note: 'GSTR3B_32AAMFM4610Q1Z0_032023.pdf' is relative, assuming it's in the scratch folder or subdir.
    # verify_sop5_fix.py used os.path.abspath, let's look for the file we found.
    # It was in "c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AAMFM4610Q1Z0_032023.pdf" roughly?
    # find_by_name returns relative paths usually if not asked for full.
    # Let's assume it is in the root of scratch/gst based on typical setup.
    
    file_path = "c:\\Users\\manum\\.gemini\\antigravity\\scratch\\gst\\GSTR3B_32AAMFM4610Q1Z0_032023.pdf"
    
    if not os.path.exists(file_path):
        # Try finding it again if path is wrong, or walk
        import glob
        files = glob.glob("c:\\Users\\manum\\.gemini\\antigravity\\scratch\\gst\\**\\GSTR3B*.pdf", recursive=True)
        if files:
            file_path = files[0]
            print(f"Found file at: {file_path}")
        else:
            print("Error: Test PDF not found.")
            return

    print(f"Running diagnostic on: {file_path}")
    result = parse_gstr3b_pdf_table_3_1_a(file_path)
    print(f"\nParser Result: {result}")

if __name__ == "__main__":
    run_diagnostic()
