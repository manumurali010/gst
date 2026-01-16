import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DatabaseManager

def main():
    print("WARNING: This script will reset OC, ASMT-10, and Adjudication registers.")
    print("All finalisation data will be LOST.")
    print("Proceedings will be reverted to 'Draft'/'Not Finalised' status.")
    
    confirm = input("Type 'RESET' to continue: ")
    
    if confirm != "RESET":
        print("Operation cancelled.")
        return

    db = DatabaseManager()
    success, message = db.reset_registers_for_dev()
    
    if success:
        print(f"SUCCESS: {message}")
    else:
        print(f"FAILED: {message}")

if __name__ == "__main__":
    main()
