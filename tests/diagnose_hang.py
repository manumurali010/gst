
import sys
import os
# Add root to path
sys.path.append(os.getcwd())

print("1. Starting diagnosis...", flush=True)

print("2. Importing json, uuid, datetime...", flush=True)
import json
import uuid
from datetime import datetime
print("   -> Stdlibs imported.", flush=True)

print("3. Importing pandas...", flush=True)
try:
    import pandas as pd
    print("   -> Pandas imported.", flush=True)
except Exception as e:
    print(f"   -> Pandas failed: {e}", flush=True)

print("4. Importing constants...", flush=True)
try:
    from src.utils.constants import TAXPAYERS_FILE
    print("   -> Constants imported.", flush=True)
except Exception as e:
    print(f"   -> Constants failed: {e}", flush=True)

print("5. Importing db_manager...", flush=True)
try:
    from src.database.db_manager import DatabaseManager
    print("   -> DatabaseManager imported.", flush=True)
except Exception as e:
    print(f"   -> DatabaseManager failed: {e}", flush=True)

print("6. Done.", flush=True)
