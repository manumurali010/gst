import sqlite3
import os
import sys
import unittest

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.schema import init_db

class TestDRC01AImmutability(unittest.TestCase):
    def setUp(self):
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_immutability.db")
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        init_db(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Setup Test Case
        self.case_id = "CASE/2026/TEST/001"
        self.cursor.execute("INSERT INTO case_registry (id, source_type) VALUES (?, 'ADJUDICATION')", (self.case_id,))
        self.cursor.execute("""
            INSERT INTO adjudication_cases (id, gstin, financial_year, adjudication_section, workflow_stage)
            VALUES (?, '27AAAAA0000A1Z5', '2025-26', '73', 10)
        """, (self.case_id,))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def set_workflow_stage(self, stage):
        self.cursor.execute("UPDATE adjudication_cases SET workflow_stage = ? WHERE id = ?", (stage, self.case_id))
        self.conn.commit()

    def test_insert_allowed_below_40(self):
        self.set_workflow_stage(10) # Draft
        try:
            self.cursor.execute("INSERT INTO case_issues (proceeding_id, issue_id, stage) VALUES (?, 'TEST_ISSUE', 'DRC-01A')", (self.case_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            self.fail(f"Insert was blocked but should be allowed at stage 10: {e}")

    def test_insert_blocked_at_40(self):
        self.set_workflow_stage(40) # DRC-01A Issued
        with self.assertRaisesRegex(sqlite3.Error, "Modification Blocked"):
            self.cursor.execute("INSERT INTO case_issues (proceeding_id, issue_id, stage) VALUES (?, 'TEST_ISSUE', 'DRC-01A')", (self.case_id,))
            self.conn.commit()

    def test_update_blocked_at_40(self):
        # First insert at stage 10
        self.set_workflow_stage(10)
        self.cursor.execute("INSERT INTO case_issues (proceeding_id, issue_id, stage) VALUES (?, 'TEST_ISSUE', 'DRC-01A')", (self.case_id,))
        self.conn.commit()
        
        # Move to stage 40
        self.set_workflow_stage(40)
        with self.assertRaisesRegex(sqlite3.Error, "Modification Blocked"):
            self.cursor.execute("UPDATE case_issues SET issue_id = 'UPDATED' WHERE proceeding_id = ?", (self.case_id,))
            self.conn.commit()

    def test_delete_blocked_at_40(self):
        # First insert at stage 10
        self.set_workflow_stage(10)
        self.cursor.execute("INSERT INTO case_issues (proceeding_id, issue_id, stage) VALUES (?, 'TEST_ISSUE', 'DRC-01A')", (self.case_id,))
        self.conn.commit()
        
        # Move to stage 40
        self.set_workflow_stage(40)
        with self.assertRaisesRegex(sqlite3.Error, "Modification Blocked"):
            self.cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ?", (self.case_id,))
            self.conn.commit()

    def test_scn_stage_not_blocked(self):
        # Edits to SCN stage issues should NOT be blocked by this specific trigger (it targets DRC-01A stage)
        self.set_workflow_stage(40)
        try:
            self.cursor.execute("INSERT INTO case_issues (proceeding_id, issue_id, stage) VALUES (?, 'SCN_ISSUE', 'SCN')", (self.case_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            self.fail(f"SCN stage insert should be allowed even if workflow is at 40: {e}")

if __name__ == "__main__":
    unittest.main()
