import fitz
import re
import sys

# Windows console encoding fix
sys.stdout.reconfigure(encoding='utf-8')

def analyze_pdf(path):
    print(f"Analyzing {path}...")
    try:
        doc = fitz.open(path)
        full_text = ""
        for i, page in enumerate(doc):
            if i >= 5: break
            print(f"--- Page {i+1} ---")
            text = page.get_text()
            # Clean non-printable chars for safe printing if needed, but UTF-8 reconfig should handle it
            print(text[:500].replace('\n', '\\n')) 
            full_text += text + "\n"
        
        doc.close()

        print("\n--- Extraction Tests ---")
        
        # Test 1: Original Regex
        print("Test 1: Original Label Regex")
        orig_match = re.search(r"(?:GSTIN)\s*[:\.]?\s*([0-9A-Z]{15})", full_text, re.IGNORECASE)
        print(f"Match: {orig_match.group(1) if orig_match else 'None'}")

        # Test 2: Proposed Label Regex variants
        print("Test 2: Proposed Label Regex (GSTIN of the supplier)")
        lbl_match = re.search(r"(?:GSTIN|GSTIN of the supplier)\s*[:\.]?\s*([0-9A-Z]{15})", full_text, re.IGNORECASE)
        print(f"Match: {lbl_match.group(1) if lbl_match else 'None'}")

        # Test 3: Structural Regex
        print("Test 3: Structural unique Search")
        struct_pattern = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"
        matches = re.findall(struct_pattern, full_text)
        unique = set(matches)
        print(f"All Matches: {matches}")
        print(f"Unique Matches: {unique}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    path = r"C:\Users\manum\.gemini\antigravity\scratch\gst\GSTR3B_32AADFW8764E1Z1_042022.pdf"
    import os
    if os.path.exists(path):
        analyze_pdf(path)
    else:
        print(f"File not found: {path}")
