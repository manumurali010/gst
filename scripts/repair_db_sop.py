import sqlite3

# [STATIC FALLBACK] Map for missing DB points
SOP_FALLBACK_MAP = {
    "LIABILITY_3B_R1": 1,
    "RCM_LIABILITY_ITC": 2,
    "ISD_CREDIT_MISMATCH": 3,
    "ITC_3B_2B_OTHER": 4,
    "TDS_TCS_MISMATCH": 5,
    "EWAY_BILL_MISMATCH": 6,
    "CANCELLED_SUPPLIERS": 7,
    "NON_FILER_SUPPLIERS": 8,
    "INELIGIBLE_ITC_16_4": 9,
    "IMPORT_ITC_MISMATCH": 10,
    "RULE_42_43_VIOLATION": 11,
    "ITC_3B_2B_9X4": 12,
    "RCM_CASH_VS_2B": 13,
    "RCM_3B_VS_CASH": 13,
    "RCM_ITC_VS_CASH": 13,
    "RCM_ITC_VS_2B": 13
}

def repair_db():
    conn = sqlite3.connect(r'D:\gst\data\adjudication.db')
    cursor = conn.cursor()
    
    repaired_count = 0
    for issue_id, sop_point in SOP_FALLBACK_MAP.items():
        # Check current value
        cursor.execute("SELECT sop_point FROM issues_master WHERE issue_id=?", (issue_id,))
        row = cursor.fetchone()
        
        if row:
            current_val = row[0]
            if current_val is None or str(current_val).lower() == "null" or str(current_val).strip() == "":
                cursor.execute("UPDATE issues_master SET sop_point=? WHERE issue_id=?", (sop_point, issue_id))
                print(f"Repaired missing sop_point for {issue_id} -> {sop_point}")
                repaired_count += 1
            else:
                # Force to INT type explicitly
                try:
                    int_val = int(float(current_val))
                    if current_val != int_val:
                        cursor.execute("UPDATE issues_master SET sop_point=? WHERE issue_id=?", (int_val, issue_id))
                        print(f"Cast sop_point to INT for {issue_id}: '{current_val}' -> {int_val}")
                        repaired_count += 1
                except:
                    pass
        else:
             print(f"WARN: issue_id {issue_id} not found in issues_master.")
             
    if repaired_count > 0:
        conn.commit()
        print(f"Successfully repaired {repaired_count} records.")
    else:
        print("No repairs needed. DB looks good.")
        
    conn.close()

if __name__ == '__main__':
    repair_db()
