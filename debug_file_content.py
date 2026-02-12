
with open(r"c:\Users\manum\.gemini\antigravity\gst\src\ui\proceedings_workspace.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i in range(3107, 3113):
        print(f"{i+1}: {repr(lines[i])}")
