import re
import json

log_file = 'sop10_audit_verify.log'

with open(log_file, 'r', encoding='utf-16', errors='ignore') as f:
    for line in f:
        if "[SOP-10 CREATE] Summary Table:" in line:
            # Extract the dict part
            match = re.search(r"Summary Table: ({.*})", line)
            if match:
                payload_str = match.group(1).replace("'", '"') # Basic fix for python dict string to json
                # Note: Python dict string is not valid JSON (True/False, None, single quotes)
                # Better to use eval since we trust the source (our own code)
                try:
                    payload = eval(match.group(1))
                    print(json.dumps(payload, indent=2))
                except Exception as e:
                    print(f"Error parsing: {e}")
                    print(line)
