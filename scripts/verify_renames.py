import sqlite3
import os

DB_PATH = 'data/adjudication.db'

EXPECTED_NAMES = {
    1: "Tax Liability Mismatch (GSTR-1 vs GSTR-3B)",
    2: "RCM (3.1(d) vs 4(A)(2) & 4(A)(3) of GSTR-3B)",
    3: "ISD Credit (GSTR-3B vs GSTR-2B)",
    4: "GSTR-3B vs GSTR-2B (excess availment i.r.o \"All other ITC\")",
    5: "TDS/TCS (GSTR-3B vs GSTR-2A)",
    8: "ITC passed on by suppliers who have not filed GSTR-3B",
    10: "Import of Goods (4(A)(1) of GSTR-3B vs Credit received in GSTR-2B)",
    12: "GSTR-3B vs GSTR-2B (discrepancy identified from GSTR-9)"
}

def verify():
    if not os.path.exists(DB_PATH):
        print(f"[FAIL] DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sop_point, issue_name FROM issues_master ORDER BY sop_point")
    rows = cursor.fetchall()
    conn.close()

    db_map = {row[0]: row[1] for row in rows}
    
    failures = []
    print(f"[VERIFY] Checking {len(EXPECTED_NAMES)} renamed points...")
    
    for sop, expected in EXPECTED_NAMES.items():
        actual = db_map.get(sop)
        if actual != expected:
            failures.append(f"SOP {sop}: Expected '{expected}', Got '{actual}'")
        else:
            print(f"  [OK] SOP {sop}: {actual}")

    if failures:
        print("\n[FAIL] Verification Failed:")
        for f in failures: print(f"  {f}")
        exit(1)
    else:
        print("\n[SUCCESS] All renames verified!")

if __name__ == "__main__":
    verify()
