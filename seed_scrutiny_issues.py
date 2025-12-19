import sqlite3
import json
import uuid
import os

DB_PATH = "data/adjudication.db"

def seed_issues():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # The 8 Scrutiny Issues based on Sheets
    # Columns: issue_id, issue_name, category, severity, tags, version, active
    issues = [
        {
            "name": "Tax Liability Summary Report",
            "category": "Scrutiny Summary",
            "tags": ["summary", "liability"],
            "desc": "Summary of Tax Liability Mismatches"
        },
        {
            "name": "Comparison Summary",
            "category": "Scrutiny Summary",
            "tags": ["summary", "comparison"],
            "desc": "Overview of GSTR-1, 3B and 2B"
        },
        {
            "name": "Tax Liability Mismatch (GSTR-1 vs 3B)",
            "category": "Tax Liability",
            "tags": ["gstr1", "gstr3b", "mismatch"],
            "desc": "Liability declared in GSTR-1 exceeds GSTR-3B"
        },
        {
            "name": "Reverse Charge Liability Mismatch",
            "category": "RCM",
            "tags": ["rcm", "liability"],
            "desc": "RCM Liability mismatch between GSTR-3B and Books/GSTR-2A"
        },
        {
            "name": "Export and SEZ Liability Mismatch",
            "category": "Exports",
            "tags": ["export", "sez"],
            "desc": "Discrepancy in Export/SEZ turnover or tax payment"
        },
        {
            "name": "ITC Mismatch (Domestic)",
            "category": "ITC Mismatch",
            "tags": ["itc", "gstr2b", "gstr3b", "domestic"],
            "desc": "Excess ITC claimed in GSTR-3B vs GSTR-2B (Domestic)"
        },
        {
            "name": "ITC Mismatch (Imports)",
            "category": "ITC Mismatch",
            "tags": ["itc", "imports", "icegate"],
            "desc": "Excess ITC claimed on Imports vs ICEGATE/GSTR-2B"
        },
        {
            "name": "RCM ITC Mismatch",
            "category": "RCM",
            "tags": ["itc", "rcm"],
            "desc": "Excess ITC claimed on RCM supplies"
        }
    ]

    print("Seeding issues...")

    for i in issues:
        # Check if exists by name
        cursor.execute("SELECT issue_id FROM issues_master WHERE issue_name = ?", (i['name'],))
        row = cursor.fetchone()
        
        if row:
            print(f"Skipping {i['name']} (Already exists)")
            continue

        issue_id = f"SCR-{uuid.uuid4().hex[:8].upper()}"
        
        # Insert Master
        cursor.execute("""
            INSERT INTO issues_master (issue_id, issue_name, category, severity, tags, version, active)
            VALUES (?, ?, ?, 'Medium', ?, '1.0', 1)
        """, (issue_id, i['name'], i['category'], json.dumps(i['tags'])))

        # Insert Data (Empty templates for now, user will fill)
        issue_json = {
            "issue_id": issue_id,
            "issue_name": i['name'],
            "category": i['category'],
            "severity": "Medium",
            "version": "1.0",
            "tags": i['tags'],
            "templates": {
                "brief_facts": f"It is observed that during the scrutiny of returns... <br><b>{i['desc']}</b>.<br><br>The total discrepancy is calculated as: <b>{{{{ total_shortfall }}}}</b>.",
                "scn": "",
                "grounds": "",
                "legal": "",
                "conclusion": ""
            },
            "placeholders": [
                {"name": "total_shortfall", "type": "currency", "required": True, "computed": True},
                {"name": "period", "type": "string", "required": True, "computed": True}
            ],
            "active": True
        }

        cursor.execute("""
            INSERT INTO issues_data (issue_id, issue_json)
            VALUES (?, ?)
        """, (issue_id, json.dumps(issue_json)))
        
        print(f"Created {i['name']} ({issue_id})")

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    seed_issues()
