import sqlite3
import json
import uuid
import os

DB_PATH = "data/adjudication.db"

def seed_issues():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # The 13 Scrutiny Issues based on SOP 02/2022
    issues = [
        {
            "name": "Outward Liability Mismatch (GSTR-1 vs 3B)",
            "category": "Outward Liability",
            "tags": ["gstr1", "gstr3b", "mismatch"],
            "desc": "Tax liability declared in GSTR-1 exceeds liability paid in GSTR-3B."
        },
        {
            "name": "RCM Liability Mismatch",
            "category": "RCM",
            "tags": ["rcm", "liability"],
            "desc": "RCM Liability paid in GSTR-3B is less than that auto-drafted in GSTR-2A/2B."
        },
        {
            "name": "ISD ITC Mismatch",
            "category": "ITC Mismatch",
            "tags": ["isd", "itc"],
            "desc": "ITC from ISD claimed in GSTR-3B exceeds credit available in GSTR-2A."
        },
        {
            "name": "Excess ITC Claimed (3B vs 2B)",
            "category": "ITC Mismatch",
            "tags": ["itc", "gstr2b", "gstr3b"],
            "desc": "ITC claimed in GSTR-3B exceeds the auto-drafted credit in GSTR-2B."
        },
        {
            "name": "TDS/TCS Credit Mismatch",
            "category": "TDS/TCS",
            "tags": ["tds", "tcs"],
            "desc": "Taxable value in GSTR-3B is less than the value on which TDS/TCS was deducted."
        },
        {
            "name": "E-Way Bill vs GSTR-1 Mismatch",
            "category": "E-Way Bill",
            "tags": ["ewaybill", "gstr1"],
            "desc": "Liability in GSTR-1 is less than the tax liability reflected in E-Way Bills."
        },
        {
            "name": "ITC from Cancelled Suppliers",
            "category": "Ineligible ITC",
            "tags": ["cancelled", "itc"],
            "desc": "ITC claimed from suppliers whose registrations were cancelled retrospectively."
        },
        {
            "name": "ITC from Non-Filing Suppliers",
            "category": "Ineligible ITC",
            "tags": ["non-filer", "itc"],
            "desc": "ITC claimed from suppliers who haven't filed their GSTR-3B for the period."
        },
        {
            "name": "Section 16(4) ITC Violation",
            "category": "Ineligible ITC",
            "tags": ["16(4)", "time-limit"],
            "desc": "ITC claimed after the statutory time limit (Nov of next FY or Annual Return)."
        },
        {
            "name": "Import ITC Mismatch (3B vs ICEGATE)",
            "category": "ITC Mismatch",
            "tags": ["imports", "icegate", "itc"],
            "desc": "ITC on imports in GSTR-3B exceeds data from ICEGATE/GSTR-2B."
        },
        {
            "name": "Rule 42/43 Reversal Mismatch",
            "category": "ITC Reversal",
            "tags": ["rule42", "rule43", "reversal"],
            "desc": "Inadequate reversal of ITC for exempt supplies or personal use."
        },
        {
            "name": "Interest on Delayed Filing",
            "category": "Interest",
            "tags": ["interest", "delay"],
            "desc": "Interest not paid on tax liability discharged after the due date."
        },
        {
            "name": "Late Fee Payment Under Section 47",
            "category": "Late Fee",
            "tags": ["late-fee"],
            "desc": "Non-payment or short payment of late fees for delayed returns."
        }
    ]

    print("Seeding SOP 02/2022 issues...")

    for i in issues:
        # Check if exists by name
        cursor.execute("SELECT issue_id FROM issues_master WHERE issue_name = ?", (i['name'],))
        row = cursor.fetchone()
        
        if row:
            print(f"Skipping {i['name']} (Already exists)")
            continue

        issue_id = f"SOP-{uuid.uuid4().hex[:8].upper()}"
        
        # Insert Master
        cursor.execute("""
            INSERT INTO issues_master (issue_id, issue_name, category, severity, tags, version, active)
            VALUES (?, ?, ?, 'Medium', ?, '1.0', 1)
        """, (issue_id, i['name'], i['category'], json.dumps(i['tags'])))

        # Insert Data
        issue_json = {
            "issue_id": issue_id,
            "issue_name": i['name'],
            "category": i['category'],
            "severity": "Medium",
            "version": "1.0",
            "tags": i['tags'],
            "templates": {
                "brief_facts": f"Upon scrutiny of your GST returns for the period in accordance with SOP 02/2022, it is observed that:<br><b>{i['desc']}</b>.<br><br>Detailed discrepancy for <b>{i['name']}</b> is as follows:",
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
