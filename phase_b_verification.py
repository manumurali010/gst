import sys
from src.database.db_manager import DatabaseManager

def test_phase_b_logic():
    db = DatabaseManager()
    
    print("\n--- TEST 1: Deterministic Hashing ---")
    template1 = {"id": "test", "content": "hello", "vars": [1, 2]}
    template2 = {"vars": [1, 2], "content": "hello", "id": "test"} # Reordered keys
    
    hash1 = db.generate_canonical_hash(template1)
    hash2 = db.generate_canonical_hash(template2)
    
    print(f"  Template 1 Hash: {hash1}")
    print(f"  Template 2 Hash: {hash2}")
    
    if hash1 == hash2:
        print("  [SUCCESS] Hashing is deterministic (sorted keys).")
    else:
        print("  [FAILURE] Hashing is NOT deterministic.")

    print("\n--- TEST 2: Transaction-Safe Rotation (Last 5) ---")
    proceeding_id = "test_case_phase_b"
    
    # 1. Clear existing for clean test
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proceeding_drafts WHERE proceeding_id = ?", (proceeding_id,))
    conn.commit()
    
    # 2. Save 7 drafts
    for i in range(1, 8):
        snapshot = {"version": i, "data": "dummy"}
        success = db.save_proceeding_draft(proceeding_id, snapshot)
        print(f"  Saving Draft {i}: {'Success' if success else 'Failed'}")
        
    # 3. Verify count
    cursor.execute("SELECT draft_id, snapshot_json FROM proceeding_drafts WHERE proceeding_id = ? ORDER BY created_at ASC", (proceeding_id,))
    drafts = cursor.fetchall()
    
    print(f"\n  Final Draft Count: {len(drafts)}")
    for d_id, d_json in drafts:
        import json
        data = json.loads(d_json)
        print(f"    - Draft ID: {d_id}, Version in JSON: {data.get('version')}")
        
    if len(drafts) == 5:
        print("  [SUCCESS] Rotation logic successfully maintained last 5 versions.")
    else:
        print(f"  [FAILURE] Draft count is {len(drafts)} instead of 5.")

    conn.close()

if __name__ == "__main__":
    test_phase_b_logic()
