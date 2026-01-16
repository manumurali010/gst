import sqlite3
import os

DB_PATH = 'data/adjudication.db'

# Mapping provided by user
MAPPING = {
    "SOP-1925D69B": "LIABILITY_3B_R1",
    "SOP-1A4E8A27": "RCM_LIABILITY_ITC",
    "SOP-643E26D5": "ISD_CREDIT_MISMATCH",
    "SOP-76CB395D": "ITC_3B_2B_OTHER",
    "SOP-A4E847E9": "TDS_TCS_MISMATCH",
    "SOP-AC2C13C3": "IMPORT_ITC_MISMATCH",
    "SOP-360EDAD3": "ITC_3B_2B_9X4",
    "SOP-C4969EE7": "EWAY_BILL_MISMATCH",
    "SOP-B9618191": "CANCELLED_SUPPLIERS",
    "SOP-6677D35C": "NON_FILER_SUPPLIERS",
    "SOP-AEA26C26": "SEC_16_4_VIOLATION",
    "SOP-FD40E50F": "RULE_42_43_VIOLATION"
}

# Reverse mapping for SOP Points (1-12)
# Based on the order in initialize_scrutiny_master (which I updated)
# Or I can just manual map points to be safe.
SOP_POINTS = {
    "LIABILITY_3B_R1": 1,
    "RCM_LIABILITY_ITC": 2,
    "ISD_CREDIT_MISMATCH": 3,
    "ITC_3B_2B_OTHER": 4,
    "TDS_TCS_MISMATCH": 5,
    "EWAY_BILL_MISMATCH": 6,
    "CANCELLED_SUPPLIERS": 7,
    "NON_FILER_SUPPLIERS": 8,
    "SEC_16_4_VIOLATION": 9,
    "IMPORT_ITC_MISMATCH": 10,
    "RULE_42_43_VIOLATION": 11,
    "ITC_3B_2B_9X4": 12
}

def migrate():
    print("--- Migrating Master Keys (SOP- -> Semantic) ---")
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Check current IDs
        cursor.execute("SELECT issue_id FROM issues_master")
        current_ids = [r[0] for r in cursor.fetchall()]
        
        updated_count = 0
        
        for sop_id, sem_id in MAPPING.items():
            if sop_id in current_ids:
                print(f"Migrating {sop_id} -> {sem_id}")
                # Update ID
                cursor.execute("UPDATE issues_master SET issue_id = ? WHERE issue_id = ?", (sem_id, sop_id))
                updated_count += 1
            elif sem_id in current_ids:
                print(f"ID {sem_id} already exists (skipping key migration).")
            else:
                print(f"Warning: neither {sop_id} nor {sem_id} found in DB.")
        
        print("-" * 30)
        
        # 2. Update SOP Points
        for sem_id, point in SOP_POINTS.items():
            print(f"Setting {sem_id} -> SOP Point {point}")
            cursor.execute("UPDATE issues_master SET sop_point = ? WHERE issue_id = ?", (point, sem_id))

        conn.commit()
        print(f"Migration Complete. {updated_count} IDs updated.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
