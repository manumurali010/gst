import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.database.db_manager import DatabaseManager

def verify_sections():
    print("Initializing DatabaseManager...")
    db = DatabaseManager()
    
    print("Fetching CGST Sections...")
    sections = db.get_cgst_sections()
    
    if not sections:
        print("❌ No sections found! Check gst_acts_checkpointed.json")
        return False
        
    print(f"✅ Found {len(sections)} sections.")
    
    print("\nSample Sections:")
    for i, section in enumerate(sections[:5]):
        print(f"{i+1}. {section['title']}")
        
    return True

if __name__ == "__main__":
    if verify_sections():
        print("\nVerification Successful!")
        sys.exit(0)
    else:
        print("\nVerification Failed!")
        sys.exit(1)
