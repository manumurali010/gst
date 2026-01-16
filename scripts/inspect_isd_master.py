import os
import sys
import json

BASE_DIR = os.getcwd() # C:\Users\manum\.gemini\antigravity\scratch\gst
sys.path.insert(0, BASE_DIR)

from src.database.db_manager import DatabaseManager

db = DatabaseManager()
res = db.get_issue("ISD_CREDIT_MISMATCH")

print(json.dumps(res, indent=4))
