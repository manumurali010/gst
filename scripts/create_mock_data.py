import pandas as pd

data = {
    "GSTIN of supplier": ["32AAACG1234A1Z1", "32AAACF4321B1Z2", "32AAACH5678C1Z3"],
    "Legal name of supplier": ["Supplier A (Cancelled)", "Supplier B (Non-Filer)", "Supplier C (Clean)"],
    "Supplier Registration Status": ["Cancelled", "Active", "Active"],
    "GSTR-3B Filing Status": ["Yes", "No", "Yes"],
    "IGST": [1000, 2000, 3000]
}

df = pd.DataFrame(data)
df.to_excel("mock_gstr2a_invoices.xlsx", index=False)
print("Created mock_gstr2a_invoices.xlsx")
