
import sys
import os
from PyQt6.QtWidgets import QApplication

# Same flags as main.py
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-d3d11 --no-sandbox"
os.environ["QT_OPENGL"] = "software"

print("Starting PyQt6 app...")
app = QApplication(sys.argv)
print("QApplication initialized.")

print("Attempting to import fitz (PyMuPDF)...")
try:
    import fitz
    print("SUCCESS: fitz imported.")
except Exception as e:
    print("FAILURE: fitz import failed.")
    import traceback
    traceback.print_exc()
