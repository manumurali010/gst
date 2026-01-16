import sys
import os
import pandas as pd

# Add src to path
sys.path.append(r"c:\Users\manum\.gemini\antigravity\scratch\gst")
sys.path.append(r"c:\Users\manum\.gemini\antigravity\scratch\gst\src")

from src.services.scrutiny_parser import ScrutinyParser
from src.services.gstr_2a_analyzer import GSTR2AAnalyzer

def reproduce():
    print("DISPATCH_MARKER: Phase-2 parser starting")
    
    primary_file = r"c:\Users\manum\.gemini\antigravity\scratch\gst\2022-23_32AAMFM4610Q1Z0_Tax liability and ITC comparison.xlsx"
    gstr2a_file = r"c:\Users\manum\.gemini\antigravity\scratch\gst\GSTR2A_32AAMFM4610Q1_2022-23_Apr-Mar.xlsx"
    
    if not os.path.exists(primary_file):
        print(f"Error: Primary file not found: {primary_file}")
        return
    if not os.path.exists(gstr2a_file):
        print(f"Error: GSTR-2A file not found: {gstr2a_file}")
        return

    # Initialize Analyzer
    print("Initializing GSTR2AAnalyzer...")
    analyzer = GSTR2AAnalyzer(gstr2a_file)
    # Check if parse_data is needed or auto-called. 
    # Usually __init__ might just set path. 
    # Let's try calling parse_data if method exists, or just proceed.
    # Looking at typical usage, it might be lazy or explicit.
    # I'll Assume it's better to access a property to trigger load if lazy, or call parse_data.
    try:
        analyzer.parse_data()
    except Exception as e:
        print(f"Warning: analyzer.parse_data() failed or not needed: {e}")
    
    # Initialize Parser
    print("Initializing ScrutinyParser...")
    parser = ScrutinyParser()
    
    # Run Parse
    print("Running parse_file...")
    try:
        results = parser.parse_file(
            file_path=primary_file,
            extra_files={},
            configs={'gstr3b_freq': 'Yearly'},
            gstr2a_analyzer=analyzer
        )
        print("Analysis completed.")
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    reproduce()
