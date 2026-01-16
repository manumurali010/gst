import pandas as pd
import sys
import re
import datetime
from PyQt6.QtCore import QObject, pyqtSignal

class AmbiguityError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details

class GSTR2AAnalyzer(QObject):
    """
    Deterministic GSTR-2A Analyzer for Scrutiny SOPs 3, 5, 7, 8, 10.
    Enforces strict scope, deterministic header parsing, and ambiguity handling.
    """
    
    # Signal emitted when header ambiguity is detected and requires user resolution
    # args: sop_name, canonical_key, options_list, callback_id
    ambiguity_detected = pyqtSignal(str, str, list, str)

    # Hardcoded Registry of Canonical Keys and their acceptable aliases
    # Usage: 'canonical_key': ['alias1', 'alias2', ...]
    # Aliases are normalized (lowercase, punctuation removed) before matching.
    HEADER_REGISTRY = {
        # Common
        'gstin': [r'gstin', r'gstin.*supplier', r'gstin.*deductor', r'gstin.*operator', r'gstin.*isd'],
        'invoice_num': [r'invoice.*number', r'invoice.*no', r'invoice.*details.*invoice.*number', r'isd.*invoice.*number', r'^number$'],
        'invoice_date': [r'invoice.*date', r'invoice.*details.*invoice.*date', r'isd.*invoice.*date', r'^date$'],
        'place_of_supply': [r'place.*of.*supply', r'^pos$'],
        
        # Taxes
        # SOP-5 TCS: 'Net Amount Liable' is often the taxable value column
        'taxable_value': [r'taxable.*value', r'taxable\s+value', r'taxable.*value.*inr', r'gross.*value.*supplies', r'net.*amount.*liable'],
        # SOP-10: 'Integrated Tax Amount' is valid
        'igst': [r'integrated.*tax', r'integrated\s+tax', r'integrated.*tax.*inr', r'integrated.*tax.*amount', r'igst.*paid', r'igst.*amount', r'igst'],
        'cgst': [r'central.*tax', r'central.*tax.*inr', r'central.*tax.*amount', r'cgst'],
        'sgst': [r'state.*tax', r'state.*tax.*inr', r'state.*tax.*amount', r'sgst'],
        'cess': [r'cess', r'cess.*inr', r'cess.*amount'],
        'tds_amount': [r'tds.*amount', r'tcs.*amount', r'amount.*paid', r'tax.*deducted', r'tax.*collected'],
        
        # Specifics
        'cancellation_date': [r'effective.*date.*cancellation'],
        'filing_status': [r'gstr.*3b.*filing.*status'],
        'return_period': [r'gstr.*2a.*period', r'return.*period', r'^period$'],
        'itc_eligibility': [r'eligibility.*itc'], 
        'isd_doc_type': [r'isd.*document.*type'],
        
        # SOP-10 IMPG Specifics
        'boe_num': [r'bill.*of.*entry', r'boe.*no', r'boe.*number'],
        'boe_date': [r'boe.*date', r'bill.*of.*entry.*date'],
        'port_code': [r'port.*code'],
        'assessable_value': [r'assessable.*value']
    }
    
    # Scoped Sheets for SOPs
    SOP_SHEET_MAP = {
        'sop_3': ['ITC Available', 'ISD', 'ISD Credit'],
        'sop_5': ['TDS', 'TCS'], # Sum both
        'sop_7': ['B2B'],
        'sop_8': ['B2B'],
        'sop_10': ['IMPG', 'Input Tax Credit (Imports)', 'Input Tax Credit (IMPG)', 'ITC (IMPG)']
    }

    def __init__(self, file_path, cached_selections=None):
        super().__init__()
        self.file_path = file_path
        self.cached_selections = cached_selections or {} # { 'sop_id:canonical_key': 'selected_header' }
        self.xl_file = None
        self.sheet_cache = {}
        self.header_cache = {} # { sheet_name: { canonical: actual_col_name } }
        self.ambiguity_flags = [] # List of pending ambiguities to block execution

    def load_file(self):
        try:
            self.xl_file = pd.ExcelFile(self.file_path)
            return True
        except Exception as e:
            print(f"GSTR2A Load Error: {e}")
            return False

    def _normalize_header(self, header):
        if not isinstance(header, str): return ""
        # Remove currency symbols, punctuation, spaces
        h = header.lower()
        h = re.sub(r'[₹().,\-\s]', '', h)
        return h

    def _scan_headers(self, sheet_name, sop_id=None):
        """
        Structural Scanner (Phase-2 Hardening).
        Scans with rolling window to detect Header Block (Parent + Child).
        Implements Secondary Probe (Rows 0-30) for SOP-5/10 if primary scan fails.
        STRICT CONSTRAINT: Secondary Probe triggers ONLY based on sop_id (5/10) and ONLY if Pass 1 fails.
        """
        if sheet_name not in self.xl_file.sheet_names:
            return {}, -1

        # SOP-10 Override: Structural Scan (Parent="Amount of tax", Child="Integrated Tax")
        if sop_id and 'sop_10' in str(sop_id):
             return self._scan_headers_sop_10(sheet_name)

        # Pass 1: Standard Scan (Rows 0-15)
        print(f"DEBUG: Primary Scan (0-15) for {sheet_name}")
        df_scan = self.xl_file.parse(sheet_name, header=None, nrows=15)
        
        # Debug Dump
        print("RAW ROWS (0–9):")
        for i in range(min(10, len(df_scan))):
            print(f"ROW {i}:", df_scan.iloc[i].tolist())
        print("DEBUG: Passed RAW ROWS")
        sys.stdout.flush()
        
        if sop_id:
             # Ensure sop_string is safe
             sop_str = str(sop_id)
        else:
             sop_str = ""

        headers, row_idx = self._scan_headers_in_df(df_scan, sop_str)
        
        # Pass 2: Secondary Probe (Condition: Pass 1 failed AND SOP is 5 or 10)
        # STRICT RULE: No keyword matching. Only explicit SOP ID.
        if not headers and sop_id and any(x in str(sop_id) for x in ['sop_5', 'sop_10']):
            print(f"DEBUG: Secondary Probe (0-30) triggered for {sop_id} on {sheet_name}")
            sys.stdout.flush()
            df_scan_30 = self.xl_file.parse(sheet_name, header=None, nrows=30)
            headers, row_idx = self._scan_headers_in_df(df_scan_30, sop_str)
            
            if headers:
                print(f"DEBUG: Secondary Probe SUCCESS for {sheet_name}")
            else:
                print(f"DEBUG: Secondary Probe FAILED for {sheet_name}")
        
        return headers, row_idx

    def _scan_headers_sop_10(self, sheet_name):
        """
        Dedicated Structural Scanner for SOP-10 (IMPG).
        Logic:
        1. Find Parent Header: "Amount of tax" (Row P)
        2. Verify Child Header: "Integrated Tax" (Row C = P + 1)
        3. Bind 'igst' to the column index of "Integrated Tax".
        """
        print(f"DEBUG: Structural Scan SOP-10 for {sheet_name}")
        df_scan = self.xl_file.parse(sheet_name, header=None, nrows=30)
        
        parent_row_idx = -1
        # 1. Search for Parent Anchor
        for i in range(len(df_scan)):
            row_str = " ".join([str(x).strip() for x in df_scan.iloc[i] if pd.notna(x)]).lower()
            
            # [SOP-10 DIAG] Row Scan
            safe_str = row_str.encode('ascii', 'replace').decode('ascii')
            print(f"[SOP-10 DIAG] Row {i} Scan: {safe_str}")
            if "import of goods from overseas" in row_str:
                 print(f"[SOP-10 DIAG] MATCH: 'Import of goods from overseas' at Row {i}")
            if "import of goods from sez" in row_str:
                 print(f"[SOP-10 DIAG] MATCH: 'Import of goods from SEZ' at Row {i}")
            
            if "amount" in row_str and "tax" in row_str:
                # Potential Parent
                parent_row_idx = i
                print(f"[SOP-10 DIAG] Parent Candidate 'Amount of tax' found at Row {i}")
                break
        
        if parent_row_idx == -1:
             print("[SOP-10 DIAG] FAIL: Parent 'Amount of tax' not found in first 30 rows.")
             return {}, -1
             
        # 2. Search for Child in next row
        child_row_idx = parent_row_idx + 1
        if child_row_idx >= len(df_scan):
             return {}, -1
             
        child_row = df_scan.iloc[child_row_idx]
        header_map = {}
        
        # Scan columns in child row
        found_igst = False
        numeric_col_count = 0
        
        for col_idx, cell_val in enumerate(child_row):
             val_str = str(cell_val).strip().lower()
             
             # Metric: Count potential numeric columns (dummy check logic for now or just log val)
             
             # Match "Integrated Tax" or "IGST"
             if "integrated" in val_str or "igst" in val_str:
                 # Map normalized key 'igst' to this column
                 header_map['igst'] = col_idx
                 found_igst = True
                 safe_val = str(cell_val).encode('ascii', 'replace').decode('ascii')
                 print(f"[SOP-10 DIAG] FOUND IGST at Col {col_idx} (Row {child_row_idx}) - Value: '{safe_val}'")
                 break # One match sufficient
        
        if found_igst:
             # Data starts after child row
             return {'igst': [{'idx': header_map['igst'], 'original': 'Integrated Tax (Structure)'}]}, child_row_idx + 1
        else:
             print(f"[SOP-10 DIAG] FAIL: Child Row {child_row_idx} content: {child_row.tolist()}")
             print("[SOP-10 DIAG] FAIL: Child 'Integrated Tax' not found under Parent.")
             return {}, -1

    def _scan_headers_in_df(self, df_scan, sop_str=""):
        """
        Internal helper to scan a given DataFrame for headers.
        Returns (header_map, data_start_row_idx).
        """
        # Helper: Check if row is candidate (Not fully numeric, has text, useful length)
        def is_candidate(row_idx):
            if row_idx >= len(df_scan): return False
            row = df_scan.iloc[row_idx]
            # Convert to string, ignore NaNs
            strs = [str(x).strip() for x in row if pd.notna(x) and str(x).strip() != '']
            
            # CONDITION: Relaxed check only for SOP-5 and SOP-10
            min_len = 1 if any(x in sop_str for x in ['sop_5', 'sop_10']) else 2
            
            if len(strs) < min_len: return False
            
            # Check for numeric dominance (avoid data rows being mistook as headers if they have text)
            nums = pd.to_numeric(row, errors='coerce').notna().sum()
            total_filled = len(strs)
            if total_filled > 0 and (nums / total_filled) > 0.6: 
                return False # >60% numbers = Data row
            return True

        # Helper: Merge Parent + Child
        def merge_rows(p_idx, c_idx):
            parent = df_scan.iloc[p_idx].fillna('').astype(str).tolist() if p_idx < len(df_scan) else []
            child = df_scan.iloc[c_idx].fillna('').astype(str).tolist() if c_idx < len(df_scan) else []
            
            # Normalize lengths
            max_len = max(len(parent), len(child))
            parent += [''] * (max_len - len(parent))
            child += [''] * (max_len - len(child))
            
            merged = []
            last_p = ""
            for p, c in zip(parent, child):
                p_clean = p.strip()
                c_clean = c.strip()
                
                if p_clean and "unnamed" not in p_clean.lower():
                    last_p = p_clean
                
                parts = []
                if last_p: parts.append(last_p)
                if c_clean and "unnamed" not in c_clean.lower(): parts.append(c_clean)
                
                merged.append(" ".join(parts))
            return merged

        # Helper: Count Canonical Matches
        def count_matches(headers):
            matched_keys = set()
            mapping = {}
            for idx, h in enumerate(headers):
                norm = self._normalize_header(h)
                if not norm: continue
                
                for key, aliases in self.HEADER_REGISTRY.items():
                    for alias in aliases:
                        if re.search(alias, norm, re.IGNORECASE):
                            matched_keys.add(key)
                            if norm not in mapping: mapping[norm] = []
                            mapping[norm].append({'idx': idx, 'original': h})
                            break
            return len(matched_keys), mapping

        # Scan Loop
        print(f"DEBUG: Process Scan Loop. Length={len(df_scan)}")
        sys.stdout.flush()
        try:
            for i in range(len(df_scan)):
                if not is_candidate(i): continue
                
                merged_headers = merge_rows(i, i+1)
                match_cnt, current_map = count_matches(merged_headers)
                
                # Validation Logic
                if match_cnt >= 2:
                    probe_idx = i+2
                    is_valid_probe = False
                    
                    if probe_idx < len(df_scan):
                       row_probe = df_scan.iloc[probe_idx].dropna()
                       nums_probe = pd.to_numeric(row_probe, errors='coerce').notna().sum()
                       if nums_probe > 0: is_valid_probe = True
                    else:
                        if match_cnt >= 3: is_valid_probe = True
                    
                    if is_valid_probe or match_cnt >= 3:
                         print(f"DEBUG: Header detected at Row {i} (Merged with {i+1}). Canonical Matches: {match_cnt}")
                         sys.stdout.flush()
                         return current_map, i + 2
        except Exception as e:
            print(f"DEBUG: CRASH IN LOOP: {e}")
            sys.stdout.flush()
            
        return {}, -1

    def _resolve_column_idx(self, sheet_map, canonical_key, sop_id, allow_ambiguity=True, require_unique=False):
        """
        Returns the Column Index (int) or None.
        Signals Ambiguity if multiple matches found and not cached.
        """
        aliases = self.HEADER_REGISTRY.get(canonical_key, [])
        matches = []
        
        # Debug Logging for SOP-3 Investigation
        if sop_id == 'sop_3' and canonical_key == 'igst':
             print(f"DEBUG: Resolving IGST for SOP-3. Sheet Map Keys: {list(sheet_map.keys())}")
        
        # Check regex/alias match
        for norm_h, items in sheet_map.items():
             for alias in aliases:
                 # Treat alias as a pattern (or substring)
                 if re.search(alias, norm_h, re.IGNORECASE):
                     for item in items:
                        idx = item['idx']
                        original = item['original']
                        # Avoid duplicates if multiple aliases match same header
                        # Store entry as (norm_h, idx, original)
                        if not any(m[1] == idx for m in matches):
                            matches.append((norm_h, idx, original))
                     break # Found valid alias for this header, move to next header

        if sop_id == 'sop_3' and canonical_key == 'igst':
             print(f"DEBUG: IGST Matches: {matches}")
             
        if not matches:
            return None
            
        if len(matches) == 1:
            return matches[0][1] # Return index

        if require_unique:
             # Strict Determinism Limit: Ambiguity not allowed for this key
             print(f"DEBUG: Ambiguity found but require_unique=True. Found: {matches}")
             return None

        if not allow_ambiguity:
             # Deterministic fallback (first match)
             return matches[0][1]
            
        # Ambiguity Handling
        # 1. Check Cache
        cache_key = f"{sop_id}:{canonical_key}"
        if cache_key in self.cached_selections:
            selected_header = self.cached_selections[cache_key]
            # Try to match the selected header (normalized key)
            for norm_h, idx, original in matches:
                if norm_h == selected_header:
                    return idx
        
        # 2. If not cached, Signal Ambiguity (Blocking in UI)
        # Options: List of structured dicts
        raw_options = []
        seen = set()
        for norm_h, idx, original in matches:
            if norm_h not in seen:
                raw_options.append(self._categorize_option(original, norm_h, sop_id))
                seen.add(norm_h)
        
        # Requirements: "Only one column may be marked as Recommended."
        # If multiple recommended, downgrade all to "Potential Matches" (still better than Other)
        # or keep them as Recommended but Dialog ensures no pre-selection.
        # User said: "If multiple high-confidence matches exist, no default is selected".
        # We'll handle this by count.
        rec_count = sum(1 for o in raw_options if o['category'] == 'recommended')
        
        # Sort: Recommended first, then Others
        options = sorted(raw_options, key=lambda x: (x['category'] != 'recommended', x['label']))
        
        self.ambiguity_detected.emit(sop_id, canonical_key, options, cache_key)
        
        # 3. Re-Check Cache (Assuming Signal Slot was Blocking and updated cache)
        if cache_key in self.cached_selections:
            selected_header = self.cached_selections[cache_key]
            for norm_h, idx, original in matches:
                if norm_h == selected_header:
                    return idx
        
        # ABSOLUTE BLOCKING: Failure to resolve -> Raise Exception
        raise AmbiguityError(f"Ambiguity detected for {canonical_key}", {'sop_id': sop_id, 'key': canonical_key})

    def _categorize_option(self, original, normalized, sop_id):
        """
        Classifies option as 'recommended' or 'other'.
        Returns dict with enhanced metadata.
        """
        norm = normalized.lower()
        orig_clean = str(original).strip().lower()
        orig = str(original).strip()
        
        # Default
        category = "other"
        
        # Keywords (Use regex for word boundaries on Original Text to avoid 'rate' in 'integrated')
        def has_kw(text, keywords):
            for k in keywords:
                # \b matches word boundary. Escape k just in case.
                if re.search(r'\b' + re.escape(k) + r'\b', text):
                    return True
            return False

        # Value Keywords (Loose matching ok for tax/cess, but robust for others)
        val_kws = ['tax', 'cess', 'amt', 'amount', 'val', 'value', 'igst', 'cgst', 'sgst', 'tot', 'credit', 'paid', 'taxable']
        # Meta Keywords (Strict word boundary)
        meta_kws = ['gstin', 'date', 'period', 'status', 'invoice', 'supply', 'type', 'rate', 'note', 'ref', 'source', 'filing', 'remarks']
        
        is_val = has_kw(orig_clean, val_kws) or any(x in norm for x in ['igst', 'cgst', 'sgst']) # keys often mashed
        is_meta = has_kw(orig_clean, meta_kws)
        
        # SOP Specific Checks
        # Identify specific sub-variant if passed (e.g. sop_5_tds)
        sop_str = str(sop_id)
        
        if 'sop_5' in sop_str:
             if 'tds' in sop_str or sop_str == 'sop_5':
                 # SOP-5A: TDS - Explicitly wants Taxable Value
                 if has_kw(orig_clean, ['taxable']) and has_kw(orig_clean, ['value']):
                     category = "recommended"
                 elif 'taxable' in norm and 'value' in norm: 
                     category = "recommended"
                 
                 # STRICT DETECTOR: Exclude tax components
                 if is_val and (has_kw(orig_clean, ['tax', 'deducted']) or 'igst' in norm or 'cgst' in norm or 'sgst' in norm):
                     category = "other"
             
             if 'tcs' in sop_str:
                 # SOP-5B: TCS (Net Amount Liable)
                 # 'Net Amount Liable' or 'Taxable Value' are accepted
                 if has_kw(orig_clean, ['net']) and has_kw(orig_clean, ['liable']):
                      category = "recommended"
                 elif has_kw(orig_clean, ['net']) and has_kw(orig_clean, ['value']):
                      category = "recommended"
                 elif has_kw(orig_clean, ['taxable']) and has_kw(orig_clean, ['value']):
                      category = "recommended" # Fallback if TCS uses same header
                 
                 # Exclude tax components
                 if has_kw(orig_clean, ['tax', 'collected']) or has_kw(orig_clean, ['tcs']):
                      category = "other"
                      
                 # Specific Semantic Adapter for TCS Ambiguity:
                 # 'Net Amount Liable' should be strongly preferred.
                 if has_kw(orig_clean, ['net']) and has_kw(orig_clean, ['liable']):
                      # Force Upgrade
                      category = "recommended"

        elif 'sop_10' in sop_str: # Import - Wants IGST (Integrated Tax)
             if 'igst' in norm or 'integrated' in norm:
                 category = "recommended"
             if 'amount' in norm and 'tax' in norm and 'integrated' in norm:
                 category = "recommended"
             
             # Adapter for "Integrated Tax Amount"
             if has_kw(orig_clean, ['integrated']) and has_kw(orig_clean, ['tax']) and has_kw(orig_clean, ['amount']):
                  category = "recommended"

        elif 'sop_3' in sop_str: # ISD - Wants Input/Distributed Taxes (IGST/CGST/SGST)
             # SOP-3 is looking for tax headers.
             # If mapping is resolving IGST, we recommend IGST headers.
             # Since _categorize_option is generic for the LOOP of matches,
             # we check broadly.
             if 'integrated' in norm or 'central' in norm or 'state' in norm:
                  category = "recommended"
             elif 'igst' in norm or 'cgst' in norm or 'sgst' in norm:
                  category = "recommended"
                  
             if has_kw(orig_clean, ['input', 'credit', 'distribut']):
                 category = "recommended"

        else:
             # Generic fallbacks
             if is_val and not is_meta:
                 category = "recommended"
        
        # Refine: Structure check (downgrade matches that look like Tax but are explicitly Rate/Status)
        if category == "recommended" and is_meta:
             category = "other" 
             
        if category == "recommended":
             label = f"{orig} – ✅ Recommended"
        else:
             # Defensive labeling for Others
             if is_val:
                 label = f"{orig} – ❌ Not a Tax Amount"
             elif is_meta:
                 label = f"{orig} – ❌ Metadata/Info"
             else:
                 label = f"{orig} – (Unknown)"
             
        return {
            'label': label,
            'value': normalized,
            'category': category,
            'original_text': str(original)
        }

    def _get_column_values(self, df, sheet_map, canonical_key, sop_id, allow_ambiguity=True, require_unique=False):
        """Helper to safely get column data."""
        idx = self._resolve_column_idx(sheet_map, canonical_key, sop_id, allow_ambiguity, require_unique)
        if idx is not None and idx < len(df.columns):
            return df.iloc[:, idx]
        return None

    def analyze_sop(self, sop_id):
        """
        Main Entry Point for SOP Analysis.
        """
        if not self.xl_file and not self.load_file():
            return {'error': "Could not load GSTR-2A file"}

        # Handle 'sop_3' vs '3' inputs
        sid = str(sop_id)
        if sid.startswith('sop_'):
             method_name = f"_compute_{sid}"
        else:
             method_name = f"_compute_sop_{sid}"

        if hasattr(self, method_name):
            try:
                # ISOLATION: Each SOP execution is wrapped
                return getattr(self, method_name)()
            except AmbiguityError:
               # Propagate up to UI Signal Handler
               raise
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {'error': f"SOP-{sop_id} Analysis Crash: {str(e)}"}
        return {'error': f"SOP {sop_id} not implemented"}

    def _compute_sop_3(self):
        """
        SOP-3: ISD Credit Logic (Revised locked design).
        Priority: 
        1. 'ITC Available' Summary Sheet (Netting Logic: Inward - CN - CN_Amend)
        2. 'ISD' Invoice Sheet (Legacy Summation) - Only if Summary Sheet missing.
        """
        # 1. Summary Sheet Strategy
        summary_sheet = next((s for s in self.xl_file.sheet_names if "itc available" in s.lower()), None)
        
        if summary_sheet:
            print(f"DEBUG: SOP-3 using Summary Sheet: {summary_sheet}")
            return self._analyze_sop_3_summary_structure(summary_sheet)

        # 2. Legacy Strategy (Invoice Summation) if Summary missing
        print("DEBUG: SOP-3 Summary Sheet not found. Falling back to Legacy Invoice Summation.")
        target_sheets = [s for s in self.SOP_SHEET_MAP.get('sop_3', []) if s in self.xl_file.sheet_names and "itc available" not in s.lower()]
        
        if not target_sheets:
             return {'status': 'info', 'reason': 'ISD data not available (No Summary or ISD sheets)'}
        
        val_igst, val_cgst, val_sgst, val_cess = 0.0, 0.0, 0.0, 0.0
        found_data = False
        
        for sheet in target_sheets:
            header_map, start_row = self._scan_headers(sheet, sop_id='sop_3')
            if not header_map: continue
            
            # Found a valid sheet
            df = self.xl_file.parse(sheet, header=None, skiprows=start_row)
            found_data = True
            
            # Simple Sum (Legacy)
            igst = self._get_column_values(df, header_map, 'igst', 'sop_3')
            cgst = self._get_column_values(df, header_map, 'cgst', 'sop_3')
            sgst = self._get_column_values(df, header_map, 'sgst', 'sop_3')
            cess = self._get_column_values(df, header_map, 'cess', 'sop_3') # Attempt cess
            
            if igst is not None: val_igst += pd.to_numeric(igst, errors='coerce').fillna(0.0).sum()
            if cgst is not None: val_cgst += pd.to_numeric(cgst, errors='coerce').fillna(0.0).sum()
            if sgst is not None: val_sgst += pd.to_numeric(sgst, errors='coerce').fillna(0.0).sum()
            if cess is not None: val_cess += pd.to_numeric(cess, errors='coerce').fillna(0.0).sum()
            
        return {
            'status': 'pass' if found_data else 'info',
            'igst': float(val_igst),
            'cgst': float(val_cgst),
            'sgst': float(val_sgst),
            'cess': float(val_cess)
        }

    def _analyze_sop_3_summary_structure(self, sheet_name):
        """
        Summary Sheet Parser for SOP-3 (Row-Name Driven).
        Logic: Net ISD = Inward - (Credit Notes + Credit Note Amendments)
        Constraints: No "Part B" dependency.
        """
        # Load reasonable chunk - Summary usually at top
        df = self.xl_file.parse(sheet_name, header=None, nrows=60)
        
        # 1. Header Detection (Tax Columns)
        # Look for row having: Integrated Tax, Central Tax (and maybe Total)
        header_row_idx = -1
        col_map = {} # 'igst': idx, 'cgst': idx ...
        
        for i, row in df.iterrows():
            r_str = " ".join([str(x).lower() for x in row if pd.notna(x)])
            if "integrated" in r_str and "tax" in r_str and "central" in r_str:
                header_row_idx = i
                # Map columns (First Pass)
                for col_idx, val in enumerate(row):
                    v_clean = str(val).strip().lower()
                    if "integrated" in v_clean: col_map['igst'] = col_idx
                    elif "central" in v_clean: col_map['cgst'] = col_idx
                    elif "state" in v_clean: col_map['sgst'] = col_idx
                    elif "cess" in v_clean: col_map['cess'] = col_idx
                break
                
        if header_row_idx == -1:
            return {'status': 'warn', 'reason': 'Tax columns ambiguous in ITC Available sheet'}
            
        # Refined Header Scan (Monthly vs Yearly)
        # If multiple IGST columns exist (Yearly), we want the LAST block (Total).
        h_row = df.iloc[header_row_idx]
        igst_indices = []
        for col_idx, val in enumerate(h_row):
            if "integrated" in str(val).lower():
                igst_indices.append(col_idx)
        
        if len(igst_indices) > 1:
             print(f"DEBUG: Multiple IGST columns found {igst_indices}. Using LAST one (Consolidated).")
             target_igst_idx = igst_indices[-1]
             # Re-map adjacent columns relative to the Target IGST
             col_map = {} # Reset
             col_map['igst'] = target_igst_idx
             # Assuming standard order: I, C, S, Cess follow each other
             # Scan forward from target_igst_idx
             for offset in range(1, 5): 
                if target_igst_idx + offset >= len(h_row): break
                val = str(h_row.iloc[target_igst_idx + offset]).lower()
                if "central" in val: col_map['cgst'] = target_igst_idx + offset
                elif "state" in val: col_map['sgst'] = target_igst_idx + offset
                elif "cess" in val: col_map['cess'] = target_igst_idx + offset
        
        # 2. Row Detection (Fuzzy Match by Name)
        row_map = {} # 'inward': idx, 'cn': idx, 'cn_amend': idx
        
        def clean_row_text(r):
            # Concatenate first few string columns to get label (usually col 0-2)
            return " ".join([str(x) for x in r[:3] if pd.notna(x)]).lower()

        for i in range(header_row_idx + 1, len(df)):
            row_text = clean_row_text(df.iloc[i])
            
            # Robust Keyword Matching
            if "inward supplies from isd" in row_text:
                row_map['inward'] = i
            elif "isd" in row_text and "credit notes" in row_text and "amendment" not in row_text:
                row_map['cn'] = i
            elif "isd" in row_text and "credit notes" in row_text and "amendment" in row_text:
                row_map['cn_amend'] = i
                
        # Failure Semantics
        if 'inward' not in row_map:
             return {'status': 'warn', 'reason': 'Row "Inward Supplies from ISD" not found'}

        # 3. Extraction & Computation
        res = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
        
        def get_val(r_idx, c_key):
            if c_key not in col_map: return 0.0
            c_idx = col_map[c_key]
            val = df.iloc[r_idx, c_idx]
            return pd.to_numeric(val, errors='coerce') or 0.0

        for tax in ['igst', 'cgst', 'sgst', 'cess']:
            inward = get_val(row_map['inward'], tax)
            cn = get_val(row_map.get('cn'), tax) if 'cn' in row_map else 0.0
            cn_amend = get_val(row_map.get('cn_amend'), tax) if 'cn_amend' in row_map else 0.0
            
            # Netting Rule: Inward - (CN + CN_Amend)
            # Assumption: Excel values are absolute positive.
            # If they are negative, we flip them to positive to subtract.
            if cn < 0: cn = abs(cn)
            if cn_amend < 0: cn_amend = abs(cn_amend)
            
            net = inward - (cn + cn_amend)
            res[tax] = max(0.0, net) # Floor at 0 for "Available Credit"
            
        res['status'] = 'pass'
        return res

    def _compute_sop_5(self):
        """
        SOP-5: TDS/TCS (Section 51 & 52) Aggregator.
        Executes TDS and TCS independently.
        Returns composite results.
        """
        # Execute TDS
        res_tds = {"status": "info", "reason": "Not checked"}
        try:
            res_tds = self._compute_sop_5_tds()
        except AmbiguityError:
            # If TDS raises, we re-raise to stop and allow UI resolution.
            # Upon retry, TDS should be cached and succeed.
            raise

        # Execute TCS
        res_tcs = {"status": "info", "reason": "Not checked"}
        try:
            res_tcs = self._compute_sop_5_tcs()
        except AmbiguityError:
            raise
        
        return {
            'tds': res_tds,
            'tcs': res_tcs
        }

    def _compute_sop_5_tds(self):
        """SOP-5A: TDS (Section 51). Target Sheet: 'TDS'. Ambiguity Allowed."""
        target_sheet = next((s for s in self.xl_file.sheet_names if s.lower() == 'tds'), None)
        
        if not target_sheet:
             return {"status": "info", "reason": "TDS sheet not available"}

        header_map, start_row = self._scan_headers(target_sheet, sop_id='sop_5')
        
        # DEBUG: Log Header Keys for SOP-5 (User Request)
        print(f"DEBUG: SOP-5 TDS Header Keys: {list(header_map.keys())}")
        
        if not header_map:
             return {"status": "info", "reason": "TDS sheet headers not found"}

        df = self.xl_file.parse(target_sheet, header=None, skiprows=start_row)
        
        # Column: Taxable Value (Ambiguity Allowed)
        # Use sub-id 'sop_5_tds' for precise categorization
        taxable_val = self._get_column_values(df, header_map, 'taxable_value', 'sop_5_tds', allow_ambiguity=True)
        
        if taxable_val is None:
             print("SOP5_TDS_DEBUG: header_map keys =", header_map.keys())
             print("SOP5_TDS_DEBUG: taxable_value resolved =", taxable_val is not None)
             return {"status": "info", "reason": "TDS: Taxable Value column not found"}

        print("SOP5_TDS_DEBUG: header_map keys =", header_map.keys())
        print("SOP5_TDS_DEBUG: taxable_value resolved =", taxable_val is not None)

        return {
            "status": "pass", 
            "base_value": pd.to_numeric(taxable_val, errors='coerce').fillna(0.0).sum()
        }

    def _compute_sop_5_tcs(self):
        """SOP-5B: TCS (Section 52). Target Sheet: 'TCS'. Ambiguity Dialog Enabled."""
        target_sheet = next((s for s in self.xl_file.sheet_names if s.lower() == 'tcs'), None)
        
        if not target_sheet:
             return {"status": "info", "reason": "TCS sheet not available"}

        header_map, start_row = self._scan_headers(target_sheet, sop_id='sop_5')

        # DEBUG: Log Header Keys for SOP-5 (User Request)
        print(f"DEBUG: SOP-5 TCS Header Keys: {list(header_map.keys())}")

        if not header_map:
             return {"status": "info", "reason": "TCS sheet headers not found"}

        df = self.xl_file.parse(target_sheet, header=None, skiprows=start_row)
        
        # Column: Net Amount Liable
        # Use 'taxable_value' canonical key because HEADER_REGISTRY maps 'net.*amount.*liable' to it.
        # Use sub-id 'sop_5_tcs' for precise categorization
        # Enable Ambiguity: allow_ambiguity=True, require_unique=False (Logic Fix)
        net_amt = self._get_column_values(df, header_map, 'taxable_value', 'sop_5_tcs', allow_ambiguity=True, require_unique=False)
        
        if net_amt is None:
             print("SOP5_TCS_DEBUG: header_map keys =", header_map.keys())
             print("SOP5_TCS_DEBUG: net_amount_liable resolved =", net_amt is not None)
             return {"status": "info", "reason": "TCS: Net Amount Liable column ambiguous or missing"}

        print("SOP5_TCS_DEBUG: header_map keys =", header_map.keys())
        print("SOP5_TCS_DEBUG: net_amount_liable resolved =", net_amt is not None)

        return {
            "status": "pass", 
            "base_value": pd.to_numeric(net_amt, errors='coerce').fillna(0.0).sum()
        }


    def _compute_sop_10(self):
        """
        SOP-10: Import of Goods (3B vs ICEGATE).
        Target Sheet: IMPG (Priority 1).
        Column: Integrated Tax / IGST.
        Ambiguity: Allowed.
        Blank Rows: 0.0.
        """
        target_sheets = self.SOP_SHEET_MAP.get('sop_10', [])
        sheet = None
        header_map = None
        start_row = -1
        
        # Priority Search (IMPG first)
        for s in target_sheets:
             # [SOP-10 DIAG] Sheet Availability
             print(f"[SOP-10 DIAG] Checking Target Sheet: '{s}'")
             
             if s in self.xl_file.sheet_names:
                 print(f"[SOP-10 DIAG] Sheet '{s}' FOUND in Excel.")
                 hm, sr = self._scan_headers(s, sop_id='sop_10')
                 if hm:
                     print(f"[SOP-10 DIAG] Headers Resolved for '{s}': {hm}")
                     sheet = s
                     header_map = hm
                     start_row = sr
                     break
                 else:
                     print(f"[SOP-10 DIAG] Headers FAILED for '{s}'")
             else:
                 print(f"[SOP-10 DIAG] Sheet '{s}' NOT FOUND in Excel.")
                      
        if not header_map:
             print("[SOP-10 DIAG] All target sheets failed. Available sheets:", self.xl_file.sheet_names)
             return {'status': 'info', 'reason': 'Import (IMPG) data not available'}
             
        df = self.xl_file.parse(sheet, header=None, skiprows=start_row)
        
        # Column: IGST
        # Semantic Binding: "Amount of tax" (Parent) -> "Integrated Tax" (Child)
        # Resolved via parent-child merging in _scan_headers
        igst_col = self._get_column_values(df, header_map, 'igst', 'sop_10', allow_ambiguity=True)
        
        if igst_col is None:
             # Column missing in Data Block but Header was found (Masked/Blank Column) -> Treat as 0.0
             # This fulfills the "Robust Fallback" requirement.
             val = 0.0
        else:
             val = pd.to_numeric(igst_col, errors='coerce').fillna(0.0).sum()
        
        # --- USER DEBUG SOP-10 ---
        print("SOP10_DEBUG: sheet tried =", sheet)
        print("SOP10_DEBUG: header_map keys =", header_map.keys())
        print("SOP10_DEBUG: igst resolved =", igst_col is not None)
        # -------------------------
        
        return {'status': 'pass', 'igst': float(val)}

    def _compute_sop_7(self):
        """
        Cancelled Taxpayer: Invoice Date > Cancellation Date
        Target Sheet: 'B2B' (Strict Scope).
        """
        target_sheets = self.SOP_SHEET_MAP.get('sop_7', ['B2B'])
        sheet = None
        header_map = None
        start_row = -1
        
        for s in target_sheets:
             if s in self.xl_file.sheet_names:
                 hm, sr = self._scan_headers(s, sop_id='sop_7')
                 if hm:
                     sheet = s
                     header_map = hm
                     start_row = sr
                     break
        
        # Standardized Error Return Structure
        if not header_map: 
             return {'rows': [], 'total_liability': 0, 'status': 'info', 'error': "B2B Sheet missing in GSTR-2A"}
        
        df = self.xl_file.parse(sheet, header=None, skiprows=start_row)
        
        # Required Columns (Strict Validation)
        required_cols = {
            'gstin': 'GSTIN of Supplier',
            'invoice_num': 'Invoice Number',
            'invoice_date': 'Invoice Date',
            'cancellation_date': 'Effective Date of Cancellation',
            'igst': 'IGST',
            'cgst': 'CGST',
            'sgst': 'SGST'
        }
        
        col_values = {}
        missing = []
        
        for key, label in required_cols.items():
            # Use specific sub-id for precise col resolution if needed, but generic works for taxes
            val = self._get_column_values(df, header_map, key, 'sop_7')
            if val is None:
                missing.append(label)
            else:
                col_values[key] = val
        
        if missing:
             return {
                 'rows': [], 
                 'total_liability': 0, 
                 'status': 'info', 
                 'error': f"Missing required columns: {', '.join(missing)}"
             }

        # Combine into a temp DF for filtering & Sorting
        temp = pd.DataFrame({
            'gstin': col_values['gstin'],
            'inv_no': col_values['invoice_num'],
            'inv_date': col_values['invoice_date'],
            'cancel_date': col_values['cancellation_date'],
            'igst': col_values['igst'],
            'cgst': col_values['cgst'],
            'sgst': col_values['sgst']
        })
        
        # Parse Dates
        temp['inv_date'] = pd.to_datetime(temp['inv_date'], dayfirst=True, errors='coerce')
        temp['cancel_date'] = pd.to_datetime(temp['cancel_date'], dayfirst=True, errors='coerce')
        
        # Filter: Cancel Date is Valid AND Inv Date > Cancel Date
        mask = (temp['cancel_date'].notna()) & (temp['inv_date'] > temp['cancel_date'])
        issues = temp[mask].copy()
        
        if issues.empty:
            return {'rows': [], 'total_liability': 0, 'status': 'pass'}
            
        # Sort: GSTIN (Asc), Invoice Date (Asc)
        issues.sort_values(by=['gstin', 'inv_date'], inplace=True)
            
        # Format Result Rows
        rows = []
        total_p7 = 0.0
        
        for _, r in issues.iterrows():
            i_val = float(pd.to_numeric(r.get('igst', 0), errors='coerce') or 0)
            c_val = float(pd.to_numeric(r.get('cgst', 0), errors='coerce') or 0)
            s_val = float(pd.to_numeric(r.get('sgst', 0), errors='coerce') or 0)
            
            liab = i_val + c_val + s_val
            total_p7 += liab
            
            # Format Date safely
            try: fmt_inv_date = r['inv_date'].strftime('%d-%b-%Y')
            except: fmt_inv_date = str(r['inv_date'])
            
            try: fmt_cancel_date = r['cancel_date'].strftime('%d-%b-%Y')
            except: fmt_cancel_date = str(r['cancel_date'])

            rows.append({
                'gstin': str(r['gstin']).strip(),
                'invoice_no': str(r['inv_no']).strip(),
                'invoice_date': fmt_inv_date,
                'cancellation_date': fmt_cancel_date,
                'igst': i_val, 
                'cgst': c_val, 
                'sgst': s_val,
                'liability': liab
            })
            
        return {
            'rows': rows, 
            'total_liability': total_p7, 
            'status': 'fail' if total_p7 > 0 else 'pass'
        }

    def _compute_sop_8(self):
        """Non-Filer: Filing Status == 'N'"""
        target_sheets = self.SOP_SHEET_MAP.get('sop_8', ['B2B'])
        sheet = None
        header_map = None
        start_row = -1
        
        for s in target_sheets:
             hm, sr = self._scan_headers(s, sop_id='sop_8')
             if hm:
                 sheet = s
                 header_map = hm
                 start_row = sr
                 break

        if not header_map: return {'error': "B2B Sheet missing"}
        
        df = self.xl_file.parse(sheet, header=None, skiprows=start_row)
        
        # 1. Resolve Filing Status (Metadata - No Ambiguity)
        c_status = self._get_column_values(df, header_map, 'filing_status', 'sop_8', allow_ambiguity=False)
        
        if c_status is None:
             print("DEBUG: SOP-8 Filing Status Column NOT FOUND.")
             return {'error': "Filing Status column missing"}
        
        # 2. Filter Non-Filers
        status_series = c_status.astype(str).str.strip().str.upper()
        print(f"DEBUG: SOP-8 Status Series: {status_series.tolist()}")
        mask = status_series.isin(['N', 'NO'])
        print(f"DEBUG: SOP-8 Mask: {mask.tolist()}")
        
        if not mask.any():
             return {'rows': [], 'total_liability': 0}
             
        # 3. Resolve Tax Columns (Ambiguity Dialog triggers ONLY here)
        igst = self._get_column_values(df, header_map, 'igst', 'sop_8', allow_ambiguity=True)
        cgst = self._get_column_values(df, header_map, 'cgst', 'sop_8', allow_ambiguity=True)
        sgst = self._get_column_values(df, header_map, 'sgst', 'sop_8', allow_ambiguity=True)
        
        # Atomicity: All tax columns required
        missing = []
        if igst is None: missing.append("IGST")
        if cgst is None: missing.append("CGST")
        if sgst is None: missing.append("SGST")

        if missing:
             return {'error': f"SOP-8 Atomic Failure: Unresolved columns: {', '.join(missing)}."}
        
        # 4. Construct Result
        # We process filtered index
        issues = df.loc[mask].copy()
        c_gstin = self._get_column_values(df, header_map, 'gstin', 'sop_8', allow_ambiguity=False)
        c_inv = self._get_column_values(df, header_map, 'invoice_num', 'sop_8', allow_ambiguity=False)
        c_inv_date = self._get_column_values(df, header_map, 'invoice_date', 'sop_8', allow_ambiguity=False)
        c_period = self._get_column_values(df, header_map, 'return_period', 'sop_8', allow_ambiguity=False)
        c_taxable = self._get_column_values(df, header_map, 'taxable_value', 'sop_8', allow_ambiguity=True)
        
        filtered_status = status_series.loc[mask]
        
        rows = []
        total_p8 = 0
        
        for idx in issues.index:
            gstin = str(c_gstin[idx]) if c_gstin is not None else ""
            inv = str(c_inv[idx]) if c_inv is not None else ""
            
            # Period (Optional fallbacks)
            period = str(c_period[idx]) if c_period is not None else ""
            
            # Date
            inv_date = str(c_inv_date[idx]) if c_inv_date is not None else ""
            try: 
                 d = pd.to_datetime(inv_date, dayfirst=True, errors='coerce')
                 if pd.notna(d): inv_date = d.strftime('%d-%b-%Y')
            except: pass
            
            # Values
            taxable = pd.to_numeric(c_taxable[idx], errors='coerce') or 0 if c_taxable is not None else 0
            i_val = pd.to_numeric(igst[idx], errors='coerce') or 0
            c_val = pd.to_numeric(cgst[idx], errors='coerce') or 0
            s_val = pd.to_numeric(sgst[idx], errors='coerce') or 0
            
            liab = i_val + c_val + s_val
            total_p8 += liab
            
            rows.append({
                'period': period,
                'gstin': gstin,
                'invoice_no': inv,
                'invoice_date': inv_date,
                'taxable_value': float(taxable),
                'igst': float(i_val), 'cgst': float(c_val), 'sgst': float(s_val),
                'liability': float(liab)
            })
            
        return {'rows': rows, 'total_liability': total_p8}
