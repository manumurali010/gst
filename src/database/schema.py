import sqlite3
import os
import json


# Define DB Path relative to the project root
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "adjudication.db")

def init_db(db_file=None):
    """Initialize the SQLite database with the required schema."""
    target_db = db_file if db_file else DB_FILE
    os.makedirs(os.path.dirname(target_db), exist_ok=True)
    
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    
    # Enable Foreign Keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 0. Case Registry (Canonical Anchor)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_registry (
        id TEXT PRIMARY KEY,
        source_type TEXT NOT NULL CHECK(source_type IN ('SCRUTINY', 'ADJUDICATION')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 1. Proceedings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proceedings (
        id TEXT PRIMARY KEY,
        case_id TEXT UNIQUE, -- Formatted ID: CASE/2025/ADJ/XXXX
        gstin TEXT NOT NULL,
        legal_name TEXT,
        trade_name TEXT,
        address TEXT,
        financial_year TEXT,
        initiating_section TEXT,
        form_type TEXT, -- DRC-01A, DRC-01, etc.
        status TEXT DEFAULT 'Draft',
        demand_details TEXT, -- JSON string for demand table
        selected_issues TEXT, -- JSON string for selected issue IDs
        taxpayer_details TEXT, -- JSON string for full taxpayer snapshot
        last_date_to_reply TEXT,
        created_by TEXT,
        additional_details TEXT,
        asmt10_status TEXT,
        adjudication_case_id TEXT,
        workflow_stage INTEGER CHECK(workflow_stage IN (10,20,30,40,50,60,70,75,80)),
        drc01a_skipped BOOLEAN DEFAULT 0,
        version_no INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)
    
    # Migration: Add new columns if not exist
    # Note: These should be safe to run even if columns exist (using try/except)
    migration_cols = [
        "case_id TEXT",
        "form_type TEXT",
        "created_by TEXT",
        "taxpayer_details TEXT",
        "additional_details TEXT",
        "oc_number TEXT",
        "notice_date TEXT",
        "asmt10_status TEXT",
        "asmt10_finalised_on TIMESTAMP",
        "asmt10_finalised_by TEXT",
        "adjudication_case_id TEXT",
        "asmt10_snapshot TEXT"
    ]
    
    for col_def in migration_cols:
        try: cursor.execute(f"ALTER TABLE proceedings ADD COLUMN {col_def}")
        except: pass
    
    # Add chapter_name to gst_sections if not exists
    try: 
        cursor.execute("ALTER TABLE gst_sections ADD COLUMN chapter_name TEXT")
    except: 
        pass
        
    try: cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_case_id ON proceedings(case_id)")
    except: pass
    
    # 2. Documents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        proceeding_id TEXT NOT NULL,
        doc_type TEXT NOT NULL, -- DRC01A, SCN, PH, ORDER
        content_html TEXT,
        template_id TEXT,
        template_version TEXT,
        version_no INTEGER DEFAULT 1,
        is_final BOOLEAN DEFAULT 0,
        snapshot_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proceeding_id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)
    
    # 3. Issues Table (Master Data)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        default_section_ids TEXT -- JSON list of section IDs
    );
    """)
    
    # 4. Events / Timeline Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        proceeding_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        description TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proceeding_id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)

    # 5. Templates Table (for Template Management)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- DRC01A, SCN, etc.
        content TEXT NOT NULL,
        version TEXT DEFAULT '1.0',
        is_default BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Issues Master Table (Metadata)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues_master (
        issue_id TEXT PRIMARY KEY,
        issue_name TEXT NOT NULL,
        category TEXT,
        severity TEXT,
        tags TEXT, -- JSON Array
        version TEXT,
        active BOOLEAN DEFAULT 0,
        liability_config TEXT,
        tax_demand_mapping TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. Issues Data Table (Full JSON)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id TEXT NOT NULL,
        issue_json TEXT NOT NULL, -- Full JSON Object
        FOREIGN KEY (issue_id) REFERENCES issues_master(issue_id) ON DELETE CASCADE
    );
    """)

    # 8. OC Register Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS oc_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT,
        oc_number TEXT,
        oc_content TEXT,
        oc_date DATE,
        oc_to TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)
    try: cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_oc_number_unique ON oc_register(oc_number)")
    except: pass

    # 9. Case Issues Table (Source of Truth for Issue Data)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proceeding_id TEXT NOT NULL,
        issue_id TEXT NOT NULL, -- Template ID e.g. ITC_MISMATCH
        stage TEXT DEFAULT 'DRC-01A', -- 'DRC-01A' or 'SCN'
        data_json TEXT, -- Stores all variables, content, and table rows
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proceeding_id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)
    
    
    # Migration: Add stage column to case_issues if not exists
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN stage TEXT DEFAULT 'DRC-01A'")
    except: pass

    # Migration: Add structured columns for ASMT-10/Adjudication
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN category TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN description TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN amount DECIMAL(15,2) DEFAULT 0")
    except: pass

    # Migration: Add columns for SCN Manual Issue Insertion (Step 159)
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN origin TEXT DEFAULT 'SCRUTINY'")
    except: pass
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN source_proceeding_id TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE case_issues ADD COLUMN added_by TEXT")
    except: pass

    
    # Migration: Add liability columns if missing
    lib_cols = [
        ("issues_master", "liability_config TEXT"),
        ("issues_master", "tax_demand_mapping TEXT"),
        ("issues_data", "liability_config TEXT"),
        ("issues_data", "tax_demand_mapping TEXT")
    ]
    for table, col_def in lib_cols:
        try: cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        except: pass

    # 10. GST Acts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gst_acts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        act_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        year INTEGER
    );
    """)

    # 11. GST Sections Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gst_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        act_id TEXT NOT NULL,
        section_number TEXT,
        title TEXT,
        content TEXT,
        chapter_id TEXT,
        chapter_name TEXT,
        FOREIGN KEY (act_id) REFERENCES gst_acts(act_id) ON DELETE CASCADE
    );
    """)

    # 12. ASMT-10 Register (Finalized Notices)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asmt10_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT, -- Sl. No.
        gstin TEXT,
        financial_year TEXT,
        issue_date DATE,
        case_id TEXT, -- Link back to scrutiny case
        oc_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    try: cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_asmt10_case_id ON asmt10_register(case_id)")
    except: pass

    # 13. Adjudication Cases (Downstream from Finalized Scrutiny)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS adjudication_cases (
        id TEXT PRIMARY KEY, -- Unique Adjudication Case ID
        source_scrutiny_id TEXT, -- Link to source ASMT-10 case
        gstin TEXT,
        legal_name TEXT,
        financial_year TEXT,
        adjudication_section TEXT, -- 73, 74, or 74A
        status TEXT DEFAULT 'Pending', -- Pending, SCN Issued, Order Passed
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        additional_details TEXT, -- JSON: SCN Metadata (No, OC, Date)
        taxpayer_details TEXT, -- JSON: Snapshot
        demand_details TEXT,   -- JSON: Demand Table
        selected_issues TEXT,   -- JSON: Issue IDs
        workflow_stage INTEGER CHECK(workflow_stage IN (10,20,30,40,50,60,70,75,80)),
        drc01a_skipped BOOLEAN DEFAULT 0,
        version_no INTEGER DEFAULT 1, -- Optimistic Locking
        is_active INTEGER DEFAULT 1, -- Active Status for Uniqueness
        FOREIGN KEY (id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)

    # Migration: Add columns to adjudication_cases if not exists
    adj_cols = [
        "additional_details TEXT",
        "taxpayer_details TEXT",
        "demand_details TEXT",
        "selected_issues TEXT",
        "version_no INTEGER DEFAULT 1",
        "is_active INTEGER DEFAULT 1"
    ]
    for col_def in adj_cols:
        try: cursor.execute(f"ALTER TABLE adjudication_cases ADD COLUMN {col_def}")
        except: pass

    # Migration: Add version_no to proceedings if not exists
    try: cursor.execute("ALTER TABLE proceedings ADD COLUMN version_no INTEGER DEFAULT 1")
    except: pass

    # Refactor Migration: Workflow Stage & Skip Logic
    _migrate_workflow_stages(cursor)

    # Hardening: Forward-Only Transition Triggers
    try:
        cursor.execute("DROP TRIGGER IF EXISTS trg_proceedings_forward_flow")
        cursor.execute("""
            CREATE TRIGGER trg_proceedings_forward_flow
            BEFORE UPDATE OF workflow_stage ON proceedings
            FOR EACH ROW
            WHEN NEW.workflow_stage < OLD.workflow_stage
            BEGIN
                SELECT RAISE(FAIL, 'Illegal Backward Transition: Workflow cannot move backwards.');
            END;
        """)
        
        cursor.execute("DROP TRIGGER IF EXISTS trg_adj_forward_flow")
        cursor.execute("""
            CREATE TRIGGER trg_adj_forward_flow
            BEFORE UPDATE OF workflow_stage ON adjudication_cases
            FOR EACH ROW
            WHEN NEW.workflow_stage < OLD.workflow_stage
            BEGIN
                SELECT RAISE(FAIL, 'Illegal Backward Transition: Workflow cannot move backwards.');
            END;
        """)
    except Exception as e:
        print(f"Warning creating workflow triggers: {e}")

    # Hardening: Immutability Trigger
    try:
        cursor.execute("DROP TRIGGER IF EXISTS trg_adj_immutable_fields")
        cursor.execute("""
            CREATE TRIGGER trg_adj_immutable_fields
            BEFORE UPDATE ON adjudication_cases
            BEGIN
                SELECT
                    CASE
                        WHEN OLD.gstin != NEW.gstin THEN RAISE(ABORT, 'Immutable field modification: gstin')
                        WHEN OLD.financial_year != NEW.financial_year THEN RAISE(ABORT, 'Immutable field modification: financial_year')
                        WHEN OLD.adjudication_section != NEW.adjudication_section THEN RAISE(ABORT, 'Immutable field modification: adjudication_section')
                    END;
            END;
        """)
        
        # [PHASE 5] Strict DRC-01A Immutability
        cursor.execute("DROP TRIGGER IF EXISTS block_drc01a_modification")
        cursor.execute("""
            CREATE TRIGGER block_drc01a_modification
            BEFORE INSERT OR UPDATE OR DELETE ON case_issues
            FOR EACH ROW
            WHEN NEW.stage = 'DRC-01A' OR OLD.stage = 'DRC-01A'
            BEGIN
                SELECT
                    CASE
                        WHEN (SELECT workflow_stage FROM adjudication_cases WHERE id = COALESCE(NEW.proceeding_id, OLD.proceeding_id)) >= 40 
                        THEN RAISE(FAIL, 'Modification Blocked: DRC-01A is already issued.')
                    END;
            END;
        """)
    except Exception as e:
        print(f"Warning creating immutability triggers: {e}")

    # 14. Proceeding Drafts (Version History)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proceeding_drafts (
        draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
        proceeding_id TEXT NOT NULL,
        snapshot_json TEXT NOT NULL,
        hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (proceeding_id) REFERENCES case_registry(id) ON DELETE RESTRICT
    );
    """)
    try: cursor.execute("CREATE INDEX IF NOT EXISTS idx_draft_proceeding_id ON proceeding_drafts(proceeding_id)")
    except: pass
    try: cursor.execute("CREATE INDEX IF NOT EXISTS idx_draft_created_at ON proceeding_drafts(created_at)")
    except: pass
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_FILE}")

def _migrate_workflow_stages(cursor):
    """
    Migration to populate workflow_stage from legacy status strings.
    Strict Priority Order: Order Issued > PH > SCN > DRC-01A > Drafts.
    """
    from src.utils.constants import WorkflowStage
    
    # 1. Add Columns
    try: cursor.execute("ALTER TABLE proceedings ADD COLUMN workflow_stage INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE proceedings ADD COLUMN drc01a_skipped BOOLEAN DEFAULT 0")
    except: pass
    
    try: cursor.execute("ALTER TABLE adjudication_cases ADD COLUMN workflow_stage INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE adjudication_cases ADD COLUMN drc01a_skipped BOOLEAN DEFAULT 0")
    except: pass
    
    # 2. Migration Logic (Idempotent: WHERE workflow_stage IS NULL)
    
    # --- Adjudication Cases ---
    
    # Priority 1: Order Issued
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.ORDER_ISSUED} WHERE status = 'Order Issued' AND workflow_stage IS NULL")
    
    # Priority 2: PH Scheduled (mapped from 'PH Intimated')
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.PH_SCHEDULED} WHERE status = 'PH Intimated' AND workflow_stage IS NULL")
    
    # Priority 3: SCN Issued
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.SCN_ISSUED} WHERE status = 'SCN Issued' AND workflow_stage IS NULL")
    
    # Priority 4: SCN Draft (Scrutiny Origin Pending)
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.SCN_DRAFT} WHERE status = 'Pending' AND source_scrutiny_id IS NOT NULL AND workflow_stage IS NULL")
    
    # Priority 5: DRC-01A Issued
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.DRC01A_ISSUED} WHERE status = 'DRC-01A Issued' AND workflow_stage IS NULL")
    
    # Priority 6: DRC-01A Draft (Direct Origin Pending)
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.DRC01A_DRAFT} WHERE status = 'Pending' AND source_scrutiny_id IS NULL AND workflow_stage IS NULL")
    
    # Fallback: Default based on Source Type if still NULL
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.SCN_DRAFT} WHERE source_scrutiny_id IS NOT NULL AND workflow_stage IS NULL")
    cursor.execute(f"UPDATE adjudication_cases SET workflow_stage = {WorkflowStage.DRC01A_DRAFT} WHERE source_scrutiny_id IS NULL AND workflow_stage IS NULL")


    # --- Proceedings (Scrutiny) ---
    
    # Priority 1: ASMT-10 Issued (Authoritative: asmt10_status)
    cursor.execute(f"UPDATE proceedings SET workflow_stage = {WorkflowStage.ASMT10_ISSUED} WHERE asmt10_status = 'finalised' AND workflow_stage IS NULL")
    
    # Priority 2: ASMT-10 Draft (Everything else)
    cursor.execute(f"UPDATE proceedings SET workflow_stage = {WorkflowStage.ASMT10_DRAFT} WHERE workflow_stage IS NULL")

if __name__ == "__main__":
    init_db()
