from src.services.asmt10_generator import ASMT10Generator

taxpayer = {
    "Legal Name": "Test Taxpayer",
    "Address": "123, Test Street, Test City, 123456",
    "GSTIN": "32AABCL1984A1Z0"
}

case_data = {
    "oc_number": "CASE/2025/ADJ/0001",
    "notice_date": "2025-12-19",
    "last_date_to_reply": "2026-01-19",
    "financial_year": "2022-23"
}

issues = [
    {
        "category": "Tax Liability Mismatch",
        "description": "Mismatch in GSTR-1 and GSTR-3B",
        "total_shortfall": 50000,
        "template_type": "liability_monthly",
        "rows": [
            {
                "period": "Apr-22",
                "3b": {"igst": 1000, "cgst": 0, "sgst": 0, "cess": 0},
                "ref": {"igst": 2000, "cgst": 0, "sgst": 0, "cess": 0},
                "diff": {"igst": 1000, "cgst": 0, "sgst": 0, "cess": 0}
            }
        ]
    }
]

def main():
    html = ASMT10Generator.generate_html(taxpayer, issues)
    
    print("--- HTML GENERATED ---")
    if 'padding: 0mm;' in html:
        print("SUCCESS: Padding set to 0mm for non-preview.")
    else:
        print("FAILURE: Padding not found.")

    if 'margin-top: -15mm;' in html:
        print("SUCCESS: First-page top margin offset present (-15mm).")
    else:
        print("FAILURE: Negative margin for first page not found.")

    if 'max-width: 380px;' in html:
        print("SUCCESS: Recipient block has professional max-width.")
    else:
        print("FAILURE: Recipient max-width not found.")

    if 'style="border: none; width: 50%;"' in html:
        print("SUCCESS: OC header columns have width 50% and no border.")
    else:
        print("FAILURE: OC header columns styling incorrect.")

    # Check for balanced tags
    open_divs = html.count('<div')
    close_divs = html.count('</div')
    print(f"Div count: Open={open_divs}, Close={close_divs}")
    
    if open_divs == close_divs:
        print("SUCCESS: Div tags are balanced.")
    else:
        print("FAILURE: Div tags are unbalanced.")

    with open("verify_asmt10.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved to verify_asmt10.html")

if __name__ == "__main__":
    main()
