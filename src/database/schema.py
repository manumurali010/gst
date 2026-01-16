import sqlite3
import os
import json

# Define DB Path relative to the project root
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "adjudication.db")

def init_db():
    """Initialize the SQLite database with the required schema."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Enable Foreign Keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        "adjudication_case_id TEXT"
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
        FOREIGN KEY (proceeding_id) REFERENCES proceedings(id) ON DELETE CASCADE
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
        FOREIGN KEY (proceeding_id) REFERENCES proceedings(id) ON DELETE CASCADE
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
        FOREIGN KEY (case_id) REFERENCES proceedings(case_id) ON DELETE SET NULL
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
        FOREIGN KEY (proceeding_id) REFERENCES proceedings(id) ON DELETE CASCADE
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
        selected_issues TEXT   -- JSON: Issue IDs
    );
    """)

    # Migration: Add columns to adjudication_cases if not exists
    adj_cols = [
        "additional_details TEXT",
        "taxpayer_details TEXT",
        "demand_details TEXT",
        "selected_issues TEXT"
    ]
    for col_def in adj_cols:
        try: cursor.execute(f"ALTER TABLE adjudication_cases ADD COLUMN {col_def}")
        except: pass
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_FILE}")

if __name__ == "__main__":
    init_db()
