
import sys
print(f"Python version: {sys.version}")
try:
    import fitz
    print("SUCCESS: fitz (PyMuPDF) imported.")
    doc = fitz.open()
    print(f"SUCCESS: Created empty PDF. PyMuPDF version: {fitz.VersionBind}")
except Exception as e:
    print(f"FAILURE: Could not import or use fitz.")
    import traceback
    traceback.print_exc()
