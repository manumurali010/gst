import os

file_path = r"src\services\scrutiny_parser.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "def _parse_group_b_itc_summary" in line:
            print(f"Found at line {i+1}: {line.strip()}")
