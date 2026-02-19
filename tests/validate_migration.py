
import sys
import os
import sqlite3

# Setup path
sys.path.append(os.getcwd())

def check_migration_status():
    print("=== Checking Migration Status (Pure SQLite) ===", flush=True)
    # Be more robust about path
    cwd = os.getcwd()
    db_path = os.path.join(cwd, 'data', 'gst.db')
    
    # Fallback search if running from subdirectory? 
    if not os.path.exists(db_path):
        db_path = os.path.join(cwd, '..', 'data', 'gst.db')
        
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}", flush=True)
        return False
        
    print(f"Database found: {db_path}", flush=True)
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Count Legacy Proceedings
        cursor.execute("SELECT COUNT(*) FROM proceedings")
        total_proceedings = cursor.fetchone()[0]
        print(f"Total Legacy Proceedings: {total_proceedings}", flush=True)

        # 2. Count Registry Scrutiny Entries
        try:
            cursor.execute("SELECT COUNT(*) FROM case_registry WHERE source_type='SCRUTINY'")
            total_registry_scrutiny = cursor.fetchone()[0]
            print(f"Registry Scrutiny Entries: {total_registry_scrutiny}", flush=True)
        except sqlite3.OperationalError:
            print("[ERROR] 'case_registry' table DOES NOT EXIST.", flush=True)
            return False

        # 3. Gap Analysis
        if total_registry_scrutiny < total_proceedings:
            gap = total_proceedings - total_registry_scrutiny
            print(f"[FAIL] CRITICAL GAP: {gap} proceedings are missing from case_registry!", flush=True)
            return False
        else:
            print("[PASS] Migration looks consistent. (Registry count >= Proceedings count)", flush=True)
            return True
            
    except Exception as e:
        print(f"[ERROR] Exception: {e}", flush=True)
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if check_migration_status():
        print("Migration Check: PASS")
        sys.exit(0)
    else:
        print("Migration Check: FAIL")
        sys.exit(1)
