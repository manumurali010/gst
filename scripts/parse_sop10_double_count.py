import re

log_file = 'sop10_double_count_verify.log'

with open(log_file, 'r', encoding='utf-16', errors='ignore') as f:
    for line in f:
        if "[SOP-10 DIAG] Candidate Row" in line:
            # Clean up the line for display
            clean_line = line.strip()
            print(clean_line)
