import openpyxl
import os

files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
print(f"Found Excel files: {files}")

target_file = "2022-23_32AABCL1984A1Z0_Tax liability and ITC comparison.xlsx"

if os.path.exists(target_file):
    try:
        wb = openpyxl.load_workbook(target_file, read_only=True)
        print(f"File: {target_file}")
        print("Sheets:", wb.sheetnames)
        wb.close()
    except Exception as e:
        print(f"Error reading {target_file}: {e}")
else:
    print(f"File {target_file} not found")
