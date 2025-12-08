import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

EXCEL_FILE = "TAX PAYERS DETAILS PARAVUR RANGE.xlsx"

if os.path.exists(EXCEL_FILE):
    print(f"Importing from {EXCEL_FILE}...")
    db = DatabaseManager()
    success, msg = db.import_taxpayers(EXCEL_FILE)
    print(f"Result: {success}, {msg}")
    
    # Verify one record
    res = db.search_taxpayers("32AAAAC2146E1ZI")
    if res:
        print("Sample Record:")
        print(res[0])
    else:
        print("Sample record not found.")
else:
    print(f"{EXCEL_FILE} not found.")
