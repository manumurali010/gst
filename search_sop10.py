
def search_file():
    try:
        content = ""
        try:
            with open('src/services/scrutiny_parser.py', 'r', encoding='utf-8') as f:
                content = f.read()
        except:
             with open('src/services/scrutiny_parser.py', 'r', encoding='utf-16') as f:
                content = f.read()
                
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "_parse_import_itc_phase2" in line or "IMPORT_ITC_MISMATCH" in line:
                print(f"{i+1}: {line.strip()}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_file()
