from src.database.db_manager import DatabaseManager
import sys

def verify_dashboard_catalog():
    print("[VERIFY] Initializing DatabaseManager...")
    db = DatabaseManager()
    
    print("[VERIFY] Calling get_dashboard_catalog()...")
    try:
        catalog = db.get_dashboard_catalog()
        print(f"[VERIFY] Success. Retrieved {len(catalog)} items.")
        
        for item in catalog:
            print(f"  - [{item['sop_point']}] {item['issue_name']}")
            print(f"    Desc: {item['description']}")
            
            if not item['description']:
                print("[FAIL] Empty description found!")
                sys.exit(1)
                
        # Check Order
        points = [item['sop_point'] for item in catalog]
        if points != sorted(points):
             print(f"[FAIL] Ordering mismatch! {points}")
             sys.exit(1)
             
        print("[VERIFY] Ordering is correct (ASC).")
        print("[VERIFY] Verification COMPLETED SUCCESS.")
        
    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_dashboard_catalog()
