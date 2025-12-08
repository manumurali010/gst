from src.database.db_manager import DatabaseManager
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

def test_get_taxpayer():
    db = DatabaseManager()
    # Pick a GSTIN from the CSV file I saw earlier
    # 32AAAAC2146E1ZI
    gstin = "32AAAAC2146E1ZI"
    
    print(f"Testing get_taxpayer with GSTIN: {gstin}")
    taxpayer = db.get_taxpayer(gstin)
    
    if taxpayer:
        print("Success! Taxpayer found:")
        print(taxpayer)
    else:
        print("Failed! Taxpayer not found.")
        
    # Test non-existent
    print("\nTesting non-existent GSTIN...")
    taxpayer = db.get_taxpayer("INVALIDGSTIN123")
    if not taxpayer:
        print("Success! Non-existent GSTIN returned None.")
    else:
        print("Failed! Found something for invalid GSTIN.")

if __name__ == "__main__":
    test_get_taxpayer()
