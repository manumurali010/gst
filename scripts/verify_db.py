from src.database.db_manager import DatabaseManager
import json
import sys

def verify_db_methods():
    print("Initializing DatabaseManager...", flush=True)
    import src.database.db_manager
    print(f"DEBUG: Loaded db_manager from: {src.database.db_manager.__file__}", flush=True)
    
    db = DatabaseManager()
    db.init_sqlite()
    
    print("Testing create_proceeding...", flush=True)
    data = {
        "gstin": "32ABCDE1234F1Z5",
        "financial_year": "2023-24",
        "initiating_section": "73",
        "form_type": "DRC-01A",
        "taxpayer_details": {
            "Legal Name": "Test Trader",
            "Trade Name": "Test Enterprises",
            "Address": "123, Test Street, Kochi"
        },
        "legal_name": "Test Trader",
        "trade_name": "Test Enterprises",
        "address": "123, Test Street, Kochi"
    }
    
    pid = db.create_proceeding(data)
    
    if pid:
        print(f"Success! Created proceeding with ID: {pid}", flush=True)
    else:
        print("Failed to create proceeding.", flush=True)
        return
        
    print("\nTesting get_proceeding...", flush=True)
    proceeding = db.get_proceeding(pid)
    
    if proceeding:
        print(f"Success! Retrieved proceeding: {proceeding['case_id']}", flush=True)
        print(f"GSTIN: {proceeding['gstin']}", flush=True)
        print(f"Taxpayer Type: {type(proceeding['taxpayer_details'])}", flush=True)
        print(f"Taxpayer: {proceeding['taxpayer_details']}", flush=True)
        
        if proceeding['gstin'] == data['gstin'] and proceeding['taxpayer_details']['Legal Name'] == data['taxpayer_details']['Legal Name']:
            print("\nData verification passed!", flush=True)
        else:
            print("\nData verification failed!", flush=True)
    else:
        print("Failed to retrieve proceeding.", flush=True)

if __name__ == "__main__":
    verify_db_methods()
