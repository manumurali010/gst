import os
import pandas as pd
import sys

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager
from src.utils.constants import TAXPAYERS_FILE

def verify():
    print("--- Verifying Bulk Import ---")
    
    db = DatabaseManager()
    
    # Define test files (assuming they are in scratch root)
    base_dir = r"C:\Users\manum\.gemini\antigravity\scratch\GST_Adjudication_System"
    files_map = {
        'Active': os.path.join(base_dir, "List_of_Active_Taxpayer.xlsx"),
        'Suspended': os.path.join(base_dir, "List_of_Suspended_Taxpayer.xlsx"),
        'Cancelled': os.path.join(base_dir, "List_of_Cancelled_Taxpayer.xlsx")
    }
    
    # 1. Reset Database first (clean slate)
    print("Resetting DB...")
    db.reset_taxpayers_database()
    
    # 2. Run Import
    print("Running Bulk Import...")
    success, msg = db.import_taxpayers_bulk(files_map)
    print(f"Import Result: {success} - {msg}")
    
    if not success:
        print("FAIL: Import returned False")
        return
        
    # 3. Verify CSV Content
    if not os.path.exists(TAXPAYERS_FILE):
        print("FAIL: taxpayers.csv not found")
        return
        
    df = pd.read_csv(TAXPAYERS_FILE)
    print(f"\nFinal CSV Rows: {len(df)}")
    print("Columns:", list(df.columns))
    
    # Check Status Counts
    print("\nStatus Counts:")
    print(df['Status'].value_counts())
    
    # Check Sample Data
    print("\nSample Data:")
    print(df[['GSTIN', 'Legal Name', 'Status', 'Address']].head())
    
    if 'Status' not in df.columns:
        print("FAIL: Status column missing")
    elif len(df) == 0:
        print("FAIL: No records imported")
    else:
        print("\nSUCCESS: Bulk Import Verified")

if __name__ == "__main__":
    verify()
