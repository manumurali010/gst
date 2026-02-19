import sys
from src.database.db_manager import DatabaseManager

def test_unified_save_deduplication():
    db = DatabaseManager()
    proceeding_id = "unified_save_test"
    
    # 1. Clear existing
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proceeding_drafts WHERE proceeding_id = ?", (proceeding_id,))
    conn.commit()
    
    print("\n--- Unified Save: Deduplication Test ---")
    snapshot = [{"issue_id": "TEST", "data": "payload"}]
    
    # Save once
    print("  Initial Save...")
    db.save_proceeding_draft(proceeding_id, snapshot)
    
    # Save identical again
    print("  Saving identical snapshot...")
    db.save_proceeding_draft(proceeding_id, snapshot)
    
    # Save different
    print("  Saving different snapshot...")
    db.save_proceeding_draft(proceeding_id, [{"issue_id": "TEST", "data": "changed"}])
    
    # Verify count (should be 2, not 3)
    cursor.execute("SELECT COUNT(*) FROM proceeding_drafts WHERE proceeding_id = ?", (proceeding_id,))
    count = cursor.fetchone()[0]
    
    print(f"  Final Record Count: {count}")
    if count == 2:
        print("  [SUCCESS] Indentical snapshot was correctly deduplicated.")
    else:
        print(f"  [FAILURE] Deduplication failed. Count is {count}.")

    conn.close()

if __name__ == "__main__":
    test_unified_save_deduplication()
