
import re

def filter_logs():
    try:
        # Try finding the file encoding or just try utf-16 then utf-8
        content = ""
        try:
            with open('diag_log.txt', 'r', encoding='utf-16') as f:
                content = f.read()
        except:
            with open('diag_log.txt', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        patterns = ["[GLOBAL]", "[SOP-5]", "[SOP-10]", "[SOP-11]", "[FIRE]"]
        
        print("--- EXTRACTED LOGS ---")
        for line in content.splitlines():
            if any(p in line for p in patterns):
                print(line)
        print("--- END EXTRACT ---")

    except Exception as e:
        print(f"Error reading log: {e}")

if __name__ == "__main__":
    filter_logs()
