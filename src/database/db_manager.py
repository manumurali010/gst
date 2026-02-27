import sqlite3
import pandas as pd
import os
import json
import uuid
from datetime import datetime
from src.utils.constants import TAXPAYERS_FILE, CASES_FILE, CASE_FILES_FILE, WorkflowStage

class DatabaseError(Exception): pass
class ConcurrencyError(DatabaseError): pass

class DatabaseManager:
    _initialized = False

    def __init__(self, db_path=None):
        self.db_path = db_path
        self.ensure_files_exist()
        self.init_sqlite()

    def ensure_files_exist(self):
        if not os.path.exists(TAXPAYERS_FILE):
            df = pd.DataFrame(columns=["GSTIN", "Legal Name", "Trade Name", "Address", "State", "Email", "Mobile", "Status", "Constitution"])
            df.to_csv(TAXPAYERS_FILE, index=False)
        
        if not os.path.exists(CASES_FILE):
            df = pd.DataFrame(columns=["CaseID", "GSTIN", "Legal Name", "Proceeding Type", "Form Type", "Date", "Status", "FilePath"])
            df.to_csv(CASES_FILE, index=False)

    def get_taxpayer(self, gstin):
        try:
            df = pd.read_csv(TAXPAYERS_FILE)
            # Clean column names to remove whitespace
            df.columns = df.columns.str.strip()
            
            # Case insensitive search
            taxpayer = df[df['GSTIN'].astype(str).str.upper() == gstin.upper()]
            
            if not taxpayer.empty:
                return taxpayer.iloc[0].to_dict()
            return None
        except Exception as e:
            print(f"Error reading taxpayers file: {e}")
            return None

    def get_all_gstins(self):
        try:
            df = pd.read_csv(TAXPAYERS_FILE)
            df.columns = df.columns.str.strip()
            return df['GSTIN'].astype(str).tolist()
        except Exception as e:
            print(f"Error fetching all GSTINs: {e}")
            return []

    def get_all_taxpayers(self):
        """Get all taxpayer records from the CSV"""
        try:
            if not os.path.exists(TAXPAYERS_FILE):
                return []
            
            df = pd.read_csv(TAXPAYERS_FILE)
            df.columns = df.columns.str.strip()
            df = df.fillna("") # Handle NaNs for UI safety
            return df.to_dict('records')
        except Exception as e:
            print(f"Error fetching all taxpayers: {e}")
            return []

    def search_taxpayers(self, query):
        try:
            df = pd.read_csv(TAXPAYERS_FILE)
            df.columns = df.columns.str.strip()
            
            # Search in GSTIN or Legal Name or Trade Name
            mask = (df['GSTIN'].astype(str).str.contains(query, case=False, na=False)) | \
                   (df['Legal Name'].astype(str).str.contains(query, case=False, na=False)) | \
                   (df['Trade Name'].astype(str).str.contains(query, case=False, na=False))
            
            # Ensure all columns are present in the result
            result = df[mask].copy()
            for col in ["Email", "Mobile", "Constitution"]:
                if col not in result.columns:
                    result[col] = ""
                    
            return result.to_dict('records')
        except Exception as e:
            print(f"Error searching taxpayers: {e}")
            return []


    def import_taxpayers_bulk(self, files_map):
        """
        Import taxpayers from multiple files (Active, Suspended, Cancelled).
        files_map: {'Active': path, 'Suspended': path, 'Cancelled': path}
        """
        try:
            dfs = []
            
            # Helper to normalize columns
            def normalize_col(name):
                return str(name).strip().replace('\n', ' ')

            for status, file_path in files_map.items():
                if not file_path or not os.path.exists(file_path):
                    continue
                
                try:
                    # Read Excel
                    df = pd.read_excel(file_path)
                    
                    # Normalize Headers
                    df.columns = [normalize_col(c) for c in df.columns]
                    
                    # Map Columns
                    # Expected: 'GSTIN', 'Trade Name/ Legal Name', 'Address of Principal Place of Business', 
                    # 'Email Id', 'Mobile No.', 'Constitution of Business'
                    
                    rename_map = {
                        'GSTIN': 'GSTIN',
                        'Trade Name/ Legal Name': 'Legal Name', # Primary Name
                        'Address of Principal Place of Business': 'Address',
                        'Email Id': 'Email',
                        'Mobile No.': 'Mobile',
                        'Constitution of Business': 'Constitution'
                    }
                    
                    # Fuzzy match rename (e.g. trailing spaces)
                    final_rename = {}
                    for col in df.columns:
                        for k, v in rename_map.items():
                            if k in col: # Check if keyword in column name (e.g. "Mobile No. ")
                                final_rename[col] = v
                    
                    df = df.rename(columns=final_rename)
                    
                    # Add Status
                    df['Status'] = status
                    
                    # Copy Legal Name to Trade Name if missing
                    if 'Legal Name' in df.columns:
                        df['Trade Name'] = df['Legal Name']
                    
                    # Ensure all required columns exist
                    required = ["GSTIN", "Legal Name", "Trade Name", "Address", "State", "Email", "Mobile", "Status", "Constitution"]
                    for col in required:
                        if col not in df.columns:
                            df[col] = "" # Fill missing
                            
                    # Select only schema columns
                    df = df[required]
                    dfs.append(df)
                    
                except Exception as e:
                    print(f"Error processing {status} file: {e}")
                    return False, f"Error in {status} file: {e}"

            if not dfs:
                return False, "No valid data found to import."
            
            # 1. Combine New Data
            new_combined = pd.concat(dfs)
            
            # 2. Read Existing Data
            current_df = pd.read_csv(TAXPAYERS_FILE)
            
            # Ensure schema compatibility (if adding new columns to old CSV)
            for col in new_combined.columns:
                if col not in current_df.columns:
                    current_df[col] = "" # Add new schema cols to old df
            
            # 3. Upsert Logic
            # Concatenate [New, Old]. Drop duplicates on GSTIN keeping FIRST (New).
            final_df = pd.concat([new_combined, current_df])
            final_df = final_df.drop_duplicates(subset=['GSTIN'], keep='first')
            
            final_df.to_csv(TAXPAYERS_FILE, index=False)
            return True, f"Successfully processed {len(new_combined)} records. Total Database: {len(final_df)}."

        except Exception as e:
            print(f"Bulk Import Error: {e}")
            return False, str(e)

    def reset_taxpayers_database(self):
        """Reset the taxpayers database to empty"""
        try:
            df = pd.DataFrame(columns=["GSTIN", "Legal Name", "Trade Name", "Address", "State", "Email", "Mobile", "Status", "Constitution"])
            df.to_csv(TAXPAYERS_FILE, index=False)
            return True, "Database reset successfully."
        except Exception as e:
            return False, str(e)

    def add_case(self, case_data):
        try:
            # Check if file is empty or just header
            file_exists = os.path.isfile(CASES_FILE)
            
            with open(CASES_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["CaseID", "GSTIN", "Legal Name", "Proceeding Type", "Form Type", "Date", "Status", "FilePath"])
                if not file_exists or os.stat(CASES_FILE).st_size == 0:
                    writer.writeheader()
                writer.writerow(case_data)
            return True
        except Exception as e:
            print(f"Error adding case: {e}")
            return False

    def get_pending_cases(self):
        try:
            df = pd.read_csv(CASES_FILE)
            return df[df['Status'] == 'Draft'].to_dict('records')
        except Exception as e:
            return []

    def get_all_cases(self):
        try:
            df = pd.read_csv(CASES_FILE)
            return df.to_dict('records')
        except Exception as e:
            return []

    def delete_csv_case(self, case_id):
        """Delete a legacy case from CSV files (both cases.csv and case_files.csv)"""
        success = False
        try:
            # 1. Delete from CASES_FILE
            if os.path.exists(CASES_FILE):
                df = pd.read_csv(CASES_FILE)
                if case_id in df['CaseID'].astype(str).values:
                    df = df[df['CaseID'].astype(str) != str(case_id)]
                    df.to_csv(CASES_FILE, index=False)
                    success = True

            # 2. Delete from CASE_FILES_FILE (This is likely where the UUID case is)
            if os.path.exists(CASE_FILES_FILE):
                df2 = pd.read_csv(CASE_FILES_FILE)
                if case_id in df2['CaseID'].astype(str).values:
                    df2 = df2[df2['CaseID'].astype(str) != str(case_id)]
                    df2.to_csv(CASE_FILES_FILE, index=False)
                    success = True
            
            return success
        except Exception as e:
            print(f"Error deleting CSV case: {e}")
            return False

    # ---------------- Case File Register Methods ----------------

    def _legacy_create_case_file_csv(self, data):
        """
        [LEGACY] Creates a new entry in the Case File Register (CSV).
        renamed to prevent accidental usage in modern flows.
        """
        try:
            import uuid
            from datetime import datetime
            
            case_id = str(uuid.uuid4())
            data['CaseID'] = case_id
            data['Created_At'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data['Updated_At'] = data['Created_At']
            
            # Ensure all columns exist
            required_cols = [
                "CaseID", "GSTIN", "Legal Name", "Trade Name", "Section", "Status", 
                "DRC01A_Path", "DRC01_Path", "DRC07_Path", "Created_At", "Updated_At",
                "OC_Number", "OC_Content", "OC_Date", "OC_To", "OC_Copy_To",
                "SCN_Number", "SCN_Date", "OIO_Number", "OIO_Date",
                "CGST_Demand", "SGST_Demand", "IGST_Demand", "Total_Demand",
                "Financial_Year", "Issue_Description", "Remarks"
            ]
            
            # Check if file exists and read existing header
            file_exists = os.path.isfile(CASE_FILES_FILE)
            existing_header = []
            if file_exists and os.stat(CASE_FILES_FILE).st_size > 0:
                with open(CASE_FILES_FILE, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    existing_header = next(reader, [])
            
            # If new columns are needed, we might need to rewrite the file or append columns
            # For simplicity, let's use pandas to handle schema evolution if file exists
            if file_exists and existing_header:
                df = pd.read_csv(CASE_FILES_FILE)
                # Add missing columns
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = ""
                
                # Add new row
                new_row = {k: data.get(k, "") for k in required_cols}
                new_row['CaseID'] = case_id
                new_row['Created_At'] = data['Created_At']
                new_row['Updated_At'] = data['Updated_At']
                
                # Append using concat
                new_df = pd.DataFrame([new_row])
                df = pd.concat([df, new_df], ignore_index=True)
                df.to_csv(CASE_FILES_FILE, index=False)
                
            else:
                # Create new file with all columns
                row_data = {k: data.get(k, "") for k in required_cols}
                row_data['CaseID'] = case_id
                row_data['Created_At'] = data['Created_At']
                row_data['Updated_At'] = data['Updated_At']
                
                with open(CASE_FILES_FILE, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=required_cols)
                    writer.writeheader()
                    writer.writerow(row_data)
                
            return case_id
        except Exception as e:
            print(f"Error creating case file: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_case_file(self, case_id, updates):
        """
        Updates an existing case file entry.
        case_id: str
        updates: dict containing fields to update
        """
        try:
            from datetime import datetime
            
            df = pd.read_csv(CASE_FILES_FILE)
            
            # Check if case exists
            if case_id not in df['CaseID'].values:
                return False, "Case ID not found"
            # Update fields
            idx = df[df['CaseID'] == case_id].index[0]
            
            for key, value in updates.items():
                # If column doesn't exist, create it
                if key not in df.columns:
                    df[key] = ""
                
                df.at[idx, key] = value
            
            df.at[idx, 'Updated_At'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            df.to_csv(CASE_FILES_FILE, index=False)
            return True, "Case updated successfully"
            
        except Exception as e:
            print(f"Error updating case file: {e}")
            return False, str(e)

    def get_case_file(self, case_id):
        """Retrieve a single case file by ID"""
        try:
            df = pd.read_csv(CASE_FILES_FILE)
            case = df[df['CaseID'] == case_id]
            if not case.empty:
                return case.iloc[0].to_dict()
            return None
        except Exception as e:
            print(f"Error getting case file: {e}")
            return None

    def get_all_case_files(self):
        """Retrieve all case files"""
        try:
            if not os.path.exists(CASE_FILES_FILE):
                return []
            df = pd.read_csv(CASE_FILES_FILE)
            # Replace NaN with empty string
            df = df.fillna("")
            return df.to_dict('records')
        except Exception as e:
            print(f"Error getting all case files: {e}")
            return []

    def find_active_case(self, gstin, section):
        """
        Finds the most recent active case for a GSTIN and Section.
        Useful for linking Order to existing proceedings.
        """
        try:
            df = pd.read_csv(CASE_FILES_FILE)
            
            # Filter by GSTIN and Section (loose match for section if needed, but exact is better for now)
            # We might need to handle section string variations, but let's assume consistency for now
            mask = (df['GSTIN'] == gstin) & (df['Section'] == section)
            results = df[mask]
            
            if not results.empty:
                # Sort by Updated_At descending to get the latest
                results = results.sort_values(by='Updated_At', ascending=False)
                return results.iloc[0].to_dict()
            return None
        except Exception as e:
            print(f"Error finding active case: {e}")
            return None

    def get_cases_by_gstin(self, gstin):
        """Retrieve all cases for a specific GSTIN"""
        try:
            if not os.path.exists(CASE_FILES_FILE):
                return []
            df = pd.read_csv(CASE_FILES_FILE)
            df = df.fillna("")
            
            # Filter by GSTIN
            cases = df[df['GSTIN'] == gstin]
            
            if not cases.empty:
                # Sort by Updated_At descending
                if 'Updated_At' in cases.columns:
                    cases = cases.sort_values(by='Updated_At', ascending=False)
                return cases.to_dict('records')
            return []
        except Exception as e:
            print(f"Error getting cases by GSTIN: {e}")
            return []
    
    def get_next_oc_number(self, year_suffix):
        """
        Get the next available OC number for a given year suffix (e.g., '2025' or '25').
        Expected DB Format: 'SEQUENCE/YEAR' (e.g. '123/2025')
        Returns: Integer (next sequence number)
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Filter entries ending with /year_suffix
            # Use LIKE '%/2025'
            query = f"%/{year_suffix}"
            cursor.execute("SELECT oc_number FROM oc_register WHERE oc_number LIKE ?", (query,))
            rows = cursor.fetchall()
            conn.close()
            
            max_seq = 0
            for row in rows:
                oc_str = str(row[0]).strip()
                if '/' in oc_str:
                    try:
                        # Split '123/2025' -> takes '123'
                        seq_part = oc_str.split('/')[0]
                        seq = int(seq_part)
                        if seq > max_seq:
                            max_seq = seq
                    except ValueError:
                        pass
            
            return max_seq + 1
            
        except Exception as e:
            print(f"Error getting next OC number: {e}")
            return 1
    
    def get_oc_register_entries(self):
        """Get all OC register entries from SQLite"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM oc_register ORDER BY oc_date DESC, created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                d = dict(row)
                # Map SQLite columns to UI expected keys (CamelCase/Underscore mix in UI)
                results.append({
                    'id': d['id'], # Critical for deletion
                    'OC_Number': d['oc_number'],
                    'OC_Content': d['oc_content'],
                    'OC_Date': d['oc_date'],
                    'OC_To': d['oc_to'],
                    'OC_Copy_To': '' # Not in new schema yet, default empty
                })
            return results
        except Exception as e:
            print(f"Error getting OC register entries: {e}")
            return []
    
    def get_scn_register_cases(self):
        """Get all SCN register cases"""
        try:
            if not os.path.exists(CASE_FILES_FILE):
                return []
            df = pd.read_csv(CASE_FILES_FILE)
            
            # Ensure all columns exist
            expected_cols = [
                "GSTIN", "Legal Name", "Issue_Description", "Financial_Year", "Section", 
                "SCN_Number", "SCN_Date", "CGST_Demand", "SGST_Demand", "IGST_Demand", 
                "Total_Demand", "Remarks"
            ]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            
            df = df.fillna("")
            
            # Filter for cases with SCN
            mask = (df['Status'].str.contains('SCN', case=False, na=False)) | (df['SCN_Number'].astype(str) != "")
            results = df[mask]
            if 'SCN_Date' in results.columns:
                results = results.sort_values(by='SCN_Date', ascending=False)
            return results.to_dict('records')
        except Exception as e:
            print(f"Error getting SCN register cases: {e}")
            return []
    
    def get_oio_register_cases(self):
        """Get all OIO register cases (DRC-07)"""
        try:
            if not os.path.exists(CASE_FILES_FILE):
                return []
            df = pd.read_csv(CASE_FILES_FILE)
            
            # Ensure all columns exist
            expected_cols = [
                "GSTIN", "Legal Name", "Issue_Description", "Financial_Year", "Section", 
                "SCN_Number", "SCN_Date", "OIO_Number", "OIO_Date",
                "CGST_Demand", "SGST_Demand", "IGST_Demand", "Cess_Demand", "Total_Demand", "Remarks"
            ]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            
            df = df.fillna("")
            
            # Filter for cases with OIO/DRC-07
            mask = (df['Status'].str.contains('ORDER', case=False, na=False)) | (df['OIO_Number'].astype(str) != "")
            results = df[mask]
            if 'OIO_Date' in results.columns:
                results = results.sort_values(by='OIO_Date', ascending=False)
            return results.to_dict('records')
        except Exception as e:
            print(f"Error getting OIO register cases: {e}")
            return []

    def get_drc01a_register_cases(self):
        """Get all DRC-01A register cases"""
        try:
            if not os.path.exists(CASE_FILES_FILE):
                return []
            df = pd.read_csv(CASE_FILES_FILE)
            
            # Ensure all columns exist
            expected_cols = [
                "GSTIN", "Legal Name", "Issue_Description", "Financial_Year", "Section", 
                "OC_Date", "CGST_Demand", "SGST_Demand", "IGST_Demand", "Cess_Demand", "Total_Demand", "Remarks"
            ]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            
            df = df.fillna("")
            
            # Filter for cases with DRC-01A
            # Either status contains DRC-01A or DRC01A_Path is not empty
            mask = (df['Status'].str.contains('DRC-01A', case=False, na=False)) | (df['DRC01A_Path'].astype(str) != "")
            results = df[mask]
            if 'OC_Date' in results.columns:
                results = results.sort_values(by='OC_Date', ascending=False)
            return results.to_dict('records')
        except Exception as e:
            print(f"Error getting DRC-01A register cases: {e}")
            return []

    def _insert_oc_entry(self, cursor, case_id, oc_data, is_issuance=False):
        """
        Internal: Write to OC Register using an existing cursor.
        """
        # 1. Enforce Issuance Flag
        if not is_issuance:
             print(f"Blocked Ghost OC Write: {oc_data.get('OC_Number')}")
             raise ValueError("Illegal OC Register Write: Called without is_issuance=True")

        # 2. Validate OC Number Format (Anti-Ghost)
        oc_number = str(oc_data.get('OC_Number', '')).strip()
        
        # Valid: "1/2026", "123/2025" - MUST have '/'
        if oc_number.upper().startswith("OC-") or len(oc_number) > 20: 
             # Logic: Block "OC-" prefix (randoms) OR too long
             if "OC-" in oc_number.upper(): 
                 raise ValueError(f"Invalid OC Number Format: {oc_number}.")
        
        # Check if OC Number already exists
        cursor.execute("SELECT id FROM oc_register WHERE oc_number = ?", (oc_number,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute("""
                UPDATE oc_register 
                SET oc_content = ?, oc_date = ?, oc_to = ?
                WHERE id = ?
            """, (
                oc_data.get('OC_Content'),
                oc_data.get('OC_Date'),
                oc_data.get('OC_To'),
                existing[0]
            ))
        else:
            # Insert new entry
            cursor.execute("""
                INSERT INTO oc_register (case_id, oc_number, oc_content, oc_date, oc_to)
                VALUES (?, ?, ?, ?, ?)
            """, (
                case_id,
                oc_number,
                oc_data.get('OC_Content'),
                oc_data.get('OC_Date'),
                oc_data.get('OC_To')
            ))
        return oc_number

    def add_oc_entry(self, case_id, oc_data, is_issuance=False):
        """
        Add an entry to the OC Register (SQLite).
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            self._insert_oc_entry(cursor, case_id, oc_data, is_issuance)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding OC entry: {e}")
            if "Illegal OC Register Write" in str(e) or "Invalid OC Number" in str(e):
                raise e # Propagate crucial validation errors
            return False
        except Exception as e:
            print(f"Error adding OC entry: {e}")
            if "Illegal OC Register Write" in str(e) or "Invalid OC Number" in str(e):
                raise e # Propagate crucial validation errors
            return False

    def delete_all_case_issues(self, proceeding_id, stage):
        """Delete all issues for a proceeding and stage."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ? AND stage = ?", (proceeding_id, stage))
            rows = cursor.rowcount
            conn.commit()
            conn.close()
            return rows
        except Exception as e:
            print(f"Error deleting case issues: {e}")
            return 0

    def save_case_issues(self, proceeding_id, issues_list, stage='DRC-01A'):
        """
        Save a list of issues to the case_issues table.
        Replaces existing issues for the proceeding and STAGE to ensure consistency.
        issues_list: List of dicts, each containing 'issue_id' and 'data' (the full JSON state)
        stage: 'DRC-01A' or 'SCN'
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Delete existing issues for this proceeding AND stage
            cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ? AND stage = ?", (proceeding_id, stage))
            
            # 2. Insert new issues
            for issue in issues_list:
                issue_id = issue.get('issue_id')
                data = issue.get('data', {})
                data_json = json.dumps(data)
                
                # Extract metadata if available
                category = data.get('category')
                description = data.get('issue') or data.get('description')
                amount = data.get('amount') or data.get('total_shortfall', 0)
                
                cursor.execute("""
                    INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json, category, description, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (proceeding_id, issue_id, stage, data_json, category, description, amount))
                
                # [TRACE Checkpoint B] Dump raw data_json of the DRC-01A record immediately after write
                if stage == 'DRC-01A':
                     print(f"[TRACE B] DB Write Complete for {issue_id} (DRC-01A). Payload size: {len(data_json)} bytes.")
                     try:
                         d = json.loads(data_json)
                         st = d.get('summary_table', {})
                         rows = st.get('rows', []) if st else []
                         print(f"[TRACE B] Readback {issue_id}: summary_table rows: {len(rows)}")
                     except:
                         print(f"[TRACE B] Readback {issue_id}: FAILED TO PARSE JSON")
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving case issues: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_case_issues(self, proceeding_id, stage='DRC-01A'):
        """
        Retrieve all issues for a proceeding.
        Returns a list of dicts with 'issue_id', 'data' (parsed JSON), and SCN metadata.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Updated to fetch SCN metadata columns
            cursor.execute("""
                SELECT issue_id, data_json, origin, source_proceeding_id, added_by, id
                FROM case_issues 
                WHERE proceeding_id = ? AND stage = ?
                ORDER BY id ASC
            """, (proceeding_id, stage))
            
            rows = cursor.fetchall()
            issues = []
            
            for row in rows:
                try:
                    data = json.loads(row[1])
                except:
                    data = {}
                    
                issues.append({
                    'issue_id': row[0],
                    'data': data,
                    'origin': row[2] or 'SCRUTINY', # Default for legacy records
                    'source_proceeding_id': row[3],
                    'added_by': row[4],
                    'id': row[5] # Primary Key (Needed for updates)
                })
            
            conn.close()
            return issues
        except Exception as e:
            print(f"Error getting case issues: {e}")
            return []

    # save_scn_issue_snapshot moved to line 1730s for V2 Architecture Integration

    def get_scrutiny_case_data(self, proceeding_id):
        """
        Get full scrutiny case data including snapshot.
        """
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM proceedings WHERE id = ?", (proceeding_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                d = dict(row)
                # Fix for 'None' string literal if present (legacy artifact)
                if d.get('asmt10_snapshot') == 'None': d['asmt10_snapshot'] = None
                return d
            return None
        except Exception as e:
            print(f"Error getting scrutiny case data: {e}")
            return None

    def update_case_issue_origin(self, row_id, new_origin):
        """Update the origin of a specific issue record (used for legacy data repair)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE case_issues SET origin = ? WHERE id = ?", (new_origin, row_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating case issue origin: {e}")
            return False

    def update_case_issue(self, row_id, updates):

        """Update the origin of a specific issue record (used for legacy data repair)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE case_issues SET origin = ? WHERE id = ?", (new_origin, row_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating case issue origin: {e}")
            return False

    def update_case_issue(self, row_id, updates):
        """
        Generic update for a case_issue record.
        updates: dict of column_name -> value (e.g. {'data_json': '...'})
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            set_clauses = []
            values = []
            for col, val in updates.items():
                set_clauses.append(f"{col} = ?")
                values.append(val)
            
            values.append(row_id)
            query = f"UPDATE case_issues SET {', '.join(set_clauses)} WHERE id = ?"
            
            cursor.execute(query, tuple(values))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating case issue: {e}")
            return False

    def clone_issues_for_scn(self, proceeding_id, source_proceeding_id=None):
        """
        Clone issues to SCN stage from finalized upstream artifacts.
        Priority: DRC-01A (Direct) > ASMT-10 (Scrutiny)
        source_proceeding_id: Optional ID of the source scrutiny case. If provided, clones from Source -> Dest.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 0. Idempotency Check (On DESTINATION)
            cursor.execute("SELECT count(*) FROM case_issues WHERE proceeding_id = ? AND stage = 'SCN'", (proceeding_id,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return False # Already exists, don't overwrite
            
            # Determine Source ID (defaults to same if not cross-linked)
            src_id = source_proceeding_id if source_proceeding_id else proceeding_id
                
            # 1. Strategy A: Try DRC-01A (Direct Adjudication or Scrutiny with DRC-01A issued)
            source_stage = 'DRC-01A'
            cursor.execute("""
                SELECT issue_id, data_json 
                FROM case_issues 
                WHERE proceeding_id = ? AND stage = ?
            """, (src_id, source_stage))
            
            source_issues = cursor.fetchall()
            
            # 2. Strategy B: Try ASMT-10 (Scrutiny Finalized) if DRC-01A empty
            if not source_issues:
                source_stage = 'ASMT-10'
                cursor.execute("""
                    SELECT issue_id, data_json 
                    FROM case_issues 
                    WHERE proceeding_id = ? AND stage = ?
                """, (src_id, source_stage))
                source_issues = cursor.fetchall()
            
            if not source_issues:
                print(f"Propagate Failed: No upstream artifacts found for {src_id} (Checked DRC-01A, ASMT-10)")
                conn.close()
                return False

            # 3. Clone to SCN (Destination)
            count = 0
            for row in source_issues:
                # [Governance] Verify Frozen Artifact Presence & Normalize Schema
                try:
                    data = json.loads(row[1])
                    
                    # Schema Normalization: Promote summary_table to grid_data if needed
                    # Scrutiny artifacts often store the baked table in 'summary_table'.
                    # SCN Replay requires 'grid_data' (Canonical Dict).
                    if not data.get('grid_data') and data.get('summary_table'):
                         print(f"Normalizing Issue {row[0]}: Promoting summary_table to grid_data.")
                         data['grid_data'] = data['summary_table']
                    
                    # Validation
                    if 'grid_data' not in data or not isinstance(data['grid_data'], dict):
                         print(f"Skipping Issue {row[0]}: Missing Frozen Artifact (grid_data/summary_table)")
                         continue
                         
                    # [Replay Blocker Fix] Ensure 'columns' key exists
                    # Older artifacts might only have 'rows' or 'headers'
                    gd = data['grid_data']
                    if 'columns' not in gd:
                         # Attempt to retro-fit columns
                         if 'headers' in gd:
                              gd['columns'] = [{'id': f'col{i}', 'title': h} for i, h in enumerate(gd['headers'])]
                         elif 'rows' in gd and gd['rows']:
                              # Infer from first row keys
                              first_row = gd['rows'][0]
                              gd['columns'] = [{'id': k, 'title': k.upper()} for k in first_row.keys()]
                         else:
                              gd['columns'] = [] # Empty schema
                    
                    # Re-serialize normalized payload
                    final_json = json.dumps(data)
                    
                except Exception as e:
                    print(f"Normalization Error for {row[0]}: {e}")
                    continue

                cursor.execute("""
                    INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json)
                    VALUES (?, ?, 'SCN', ?)
                """, (proceeding_id, row[0], final_json)) # Normalized Copy
                count += 1
                
            conn.commit()
            conn.close()
            print(f"Successfully cloned {count} issues from {source_stage} (Src: {src_id}) to SCN (Dest: {proceeding_id}).")
            return count > 0
        except Exception as e:
            print(f"Error cloning issues for SCN: {e}")
            return False

    def generate_single_issue_demand_text(self, issue_data, index):
        """Generates demand text clauses for a single issue"""
        try:
            from src.utils.number_utils import amount_to_words
            
            data = issue_data
            breakdown = data.get('tax_breakdown', {})
            
            # Calculate Totals
            total_demand = 0.0
            cgst_demand = 0.0
            sgst_demand = 0.0
            igst_demand = 0.0
            cess_demand = 0.0
            
            for act, vals in breakdown.items():
                tax = float(vals.get('tax', 0))
                total_demand += tax 
                
                if act == 'CGST': cgst_demand += tax
                elif act == 'SGST': sgst_demand += tax
                elif act == 'IGST': igst_demand += tax
                elif act == 'Cess': cess_demand += tax
            
            def format_indian_currency(n):
                try:
                    d = float(n)
                    is_negative = d < 0
                    d = abs(d)
                    s = "{:.2f}".format(d)
                    parts = s.split('.')
                    integer_part = parts[0]
                    decimal_part = parts[1]
                    
                    if len(integer_part) > 3:
                        last_three = integer_part[-3:]
                        rest = integer_part[:-3]
                        
                        # Add commas to the rest (every 2 digits)
                        formatted_rest = ""
                        for i, digit in enumerate(reversed(rest)):
                            if i > 0 and i % 2 == 0:
                                formatted_rest = "," + formatted_rest
                            formatted_rest = digit + formatted_rest
                            
                        integer_part = formatted_rest + "," + last_three
                        
                    formatted = integer_part + "." + decimal_part
                    return f"-{formatted}" if is_negative else formatted
                except:
                    return str(n)

            formatted_total = format_indian_currency(total_demand)
            formatted_cgst = format_indian_currency(cgst_demand)
            formatted_sgst = format_indian_currency(sgst_demand)
            formatted_igst = format_indian_currency(igst_demand)
            amount_words = amount_to_words(total_demand)
                    # Construct Tax Cause (Clause i)
            # Use dynamic roman numeral passed in 'index' argument if possible, or just plain text lists
            # For now, we return the text content. The prefixes (i., ii.) can be managed by the UI or kept here.
            
            clause_tax = f"{self.to_roman(index).lower()}. An amount of Rs. {formatted_total}/- ({amount_words}) (IGST Rs. {formatted_igst}/-, CGST- Rs. {formatted_cgst}/- and SGST- Rs. {formatted_sgst}/-) for the contraventions mentioned in issue {index} should not be demanded and recovered from them under the provisions of Section 73(1) of CGST Act 2017 /Kerala SGST Act, 2017 read with Section 20 of the IGST Act, 2017;"
            
            return clause_tax
        except Exception as e:
            print(f"Error generating single issue text: {e}")
            return f"Error: {e}"

    def to_roman(self, n):
        """Helper to convert integer to Roman numeral"""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
            ]
        syb = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
            ]
        roman_num = ''
        i = 0
        while  n > 0:
            for _ in range(n // val[i]):
                roman_num += syb[i]
                n -= val[i]
            i += 1
        return roman_num

    def generate_scn_demand_text(self, proceeding_id):
        """
        Generates SCN demand text based on stored issues.
        Returns a formatted string with 3 clauses per issue.
        """
        try:
            issues = self.get_case_issues(proceeding_id)
            if not issues:
                return "No issues found to generate demand text."
            
            text_blocks = []
            for i, issue in enumerate(issues, 1):
                data = issue.get('data', {})
                # Use helper
                issue_block = self.generate_single_issue_demand_text(data, i)
                text_blocks.append(issue_block)
                
            return "\n\n".join(text_blocks)
            
        except Exception as e:
            print(f"Error generating SCN demand text: {e}")
            import traceback
            traceback.print_exc()
            return f"Error generation demand text: {str(e)}"

    def init_sqlite(self):
        """Initialize SQLite database"""
        from src.database.schema import init_db, DB_FILE
        
        # Use injected path or default
        self.db_file = self.db_path if self.db_path else DB_FILE
        
        if not DatabaseManager._initialized:
            init_db(self.db_file)
            
            # [MIGRATION] Schema Update for Scrutiny Dashboard (Strategic Refactor)
            # Ensure 'description' column exists in issues_master
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(issues_master)")
                columns = [info[1] for info in cursor.fetchall()]
                
                if "description" not in columns:
                    print("[MIGRATION] Adding 'description' column to issues_master...")
                    cursor.execute("ALTER TABLE issues_master ADD COLUMN description TEXT NOT NULL DEFAULT ''")
                    conn.commit()
                    print("[MIGRATION] Success. 'description' column added.")
                    
                # --- OFFICER REGISTRY MIGRATION (V2) ---
                # 1. Provide strict single-row schema_meta definition
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_meta (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        version INTEGER NOT NULL
                    )
                ''')

                # 2. Check current version, initialize if empty
                cursor.execute("SELECT version FROM schema_meta WHERE id = 1")
                row = cursor.fetchone()

                if not row:
                    # Initialize fresh DB or pre-V2 legacy DB to V1
                    cursor.execute("INSERT INTO schema_meta (id, version) VALUES (1, 1)")
                    current_version = 1
                else:
                    current_version = row[0]

                # 3. Apply V2 Migration (Officer Registry) safely
                if current_version < 2:
                    print("[MIGRATION] Running Database Schema V2 Update (Officer Registry)...")
                    
                    # Create officers table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS officers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            designation TEXT NOT NULL,
                            jurisdiction TEXT NOT NULL,
                            office_address TEXT,
                            is_active BOOLEAN DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Create indexing
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_officer_active ON officers(is_active)")
                    
                    # Safely add columns to proceedings
                    cursor.execute("PRAGMA table_info(proceedings)")
                    proc_cols = [info[1] for info in cursor.fetchall()]
                    
                    if "issuing_officer_id" not in proc_cols:
                        print("[MIGRATION] Adding 'issuing_officer_id' to proceedings...")
                        cursor.execute("ALTER TABLE proceedings ADD COLUMN issuing_officer_id INTEGER REFERENCES officers(id)")
                        
                    if "issuing_officer_snapshot" not in proc_cols:
                        print("[MIGRATION] Adding 'issuing_officer_snapshot' to proceedings...")
                        cursor.execute("ALTER TABLE proceedings ADD COLUMN issuing_officer_snapshot TEXT")
                    
                    cursor.execute("UPDATE schema_meta SET version = 2 WHERE id = 1")
                    print("[MIGRATION] V2 Update Complete.")
                
                # Commit all schema changes
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[CRITICAL] Schema Migration Failed: {e}")
                # We enforce a hard crash if schema is invalid to prevent silent data corruption
                raise RuntimeError(f"Database Schema Migration Failed: {e}")

            DatabaseManager._initialized = True

    def _get_conn(self):
        """Returns a configured SQLite connection instance using the active db_file."""
        if not hasattr(self, 'db_file') or not self.db_file:
            self.init_sqlite()
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        
        # Enforce foreign key constraints at connection level
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_dashboard_catalog(self):
        """
        [REPOSITORY PATTERN] Content Catalog for Scrutiny Dashboard.
        Single Source of Truth: issues_master
        Strict Validation: Fails loudly if content is missing.
        """
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # [STRICT ORDERING] Enforce SOP sequence
            cursor.execute("""
                SELECT issue_id, issue_name, description, sop_point 
                FROM issues_master 
                WHERE active = 1 
                ORDER BY sop_point ASC
            """)
            rows = cursor.fetchall()
            conn.close()
            
            # [STATIC FALLBACK] Map for missing DB points
            SOP_FALLBACK_MAP = {
                "LIABILITY_3B_R1": 1,
                "RCM_LIABILITY_ITC": 2,
                "ISD_CREDIT_MISMATCH": 3,
                "ITC_3B_2B_OTHER": 4,
                "TDS_TCS_MISMATCH": 5,
                "EWAY_BILL_MISMATCH": 6,
                "CANCELLED_SUPPLIERS": 7,
                "NON_FILER_SUPPLIERS": 8,
                "INELIGIBLE_ITC_16_4": 9,
                "IMPORT_ITC_MISMATCH": 10,
                "RULE_42_43_VIOLATION": 11,
                "ITC_3B_2B_9X4": 12,
                "RCM_CASH_VS_2B": 13,
                "RCM_3B_VS_CASH": 13,
                "RCM_ITC_VS_CASH": 13,
                "RCM_ITC_VS_2B": 13
            }

            result = []
            for row in rows:
                item = dict(row)
                
                # [VALIDATION] Fail Loudly on Empty Description
                desc = item.get("description")
                if not desc or not str(desc).strip():
                    raise RuntimeError(f"Data Integrity Violation: Issue '{item['issue_id']}' has missing/empty description.")
                
                # [TYPE NORMALIZATION] DB Regression Guard (SOP_POINT IS NULL)
                raw_sop = item.get("sop_point")
                if raw_sop is None or str(raw_sop).lower() == "null" or str(raw_sop).strip() == "":
                    fallback_val = SOP_FALLBACK_MAP.get(item["issue_id"])
                    if fallback_val is None:
                        raise RuntimeError(f"Data Error: Cannot determine sop_point for {item['issue_id']}")
                    print(f"WARNING: issues_master DB missing sop_point for {item['issue_id']}. Using static fallback {fallback_val}.")
                    raw_sop = fallback_val
                
                # Enforce literal integer extraction
                item["sop_point"] = int(float(raw_sop))
                
                result.append(item)
                
            if not result:
                raise RuntimeError("Dashboard Catalog is empty! Database may need seeding.")
                
            return result
            
        except Exception as e:
            print(f"[CRITICAL] Failed to load Dashboard Catalog: {e}")
            raise e


    # ---------------- SQLite Methods for New Architecture ----------------

    @staticmethod
    def generate_canonical_hash(data: dict) -> str:
        """
        Generate a deterministic SHA256 hash from a dictionary.
        Uses canonical JSON serialization (sorted keys) and UTF-8 encoding.
        """
        import hashlib
        import json
        if not data: return ""
        # Canonical string: sorted keys, no extra whitespace
        canonical_str = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(canonical_str).hexdigest()

    def save_proceeding_draft(self, proceeding_id, snapshot_data):
        """
        Save a full snapshot to proceeding_drafts with 5-version rotation.
        Transaction-safe pruning and insertion.
        Deduplication: Skips save if hash matches the latest snapshot.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Generate snapshot hash
            snapshot_json = json.dumps(snapshot_data)
            snapshot_hash = self.generate_canonical_hash(snapshot_data)
            
            # Deduplication Check: Fetch latest hash for this proceeding
            cursor.execute("""
                SELECT hash FROM proceeding_drafts 
                WHERE proceeding_id = ? 
                ORDER BY created_at DESC LIMIT 1
            """, (proceeding_id,))
            latest_hash_row = cursor.fetchone()
            if latest_hash_row and latest_hash_row[0] == snapshot_hash:
                print(f"SCN Governance: Snapshot for {proceeding_id} is identical to latest. Skipping redundant save.")
                return True # Success (No-op)
            
            cursor.execute("BEGIN TRANSACTION;")
            
            # 2. Pruning Logic: Keep only last 5 snapshots per proceeding
            cursor.execute("""
                SELECT draft_id FROM proceeding_drafts 
                WHERE proceeding_id = ? 
                ORDER BY created_at ASC
            """, (proceeding_id,))
            
            existing_drafts = cursor.fetchall()
            
            # If we already have 5, delete the oldest
            if len(existing_drafts) >= 5:
                # Prune until we have 4 (allowing 1 new insert)
                to_remove_count = len(existing_drafts) - 4
                to_delete = existing_drafts[:to_remove_count]
                for draft in to_delete:
                    cursor.execute("DELETE FROM proceeding_drafts WHERE draft_id = ?", (draft[0],))
            
            # 3. Insert New Draft
            cursor.execute("""
                INSERT INTO proceeding_drafts (proceeding_id, snapshot_json, hash)
                VALUES (?, ?, ?)
            """, (proceeding_id, snapshot_json, snapshot_hash))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving proceeding draft: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False

    def _get_conn(self):
        import sqlite3
        conn = sqlite3.connect(self.db_file)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def generate_case_id(self, cursor):
        """Generate a unique Case ID: CASE/YYYY/ADJ/XXXX"""
        import datetime
        year = datetime.date.today().year
        
        # Find max ID for current year
        cursor.execute("SELECT case_id FROM proceedings WHERE case_id LIKE ?", (f"CASE/{year}/ADJ/%",))
        rows = cursor.fetchall()
        
        max_seq = 0
        for row in rows:
            try:
                seq = int(row[0].split('/')[-1])
                if seq > max_seq:
                    max_seq = seq
            except:
                pass
                
        new_seq = max_seq + 1
        return f"CASE/{year}/ADJ/{new_seq:04d}"

    def create_proceeding(self, data, source_type='SCRUTINY'):
        """
        Create a new proceeding with Transactional Registry Constraints.
        source_type: 'SCRUTINY' (Default) or 'ADJUDICATION'.
        """
        import uuid
        import json
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            pid = str(uuid.uuid4())
            
            # 1. Transaction Start (Implicit via first INSERT)
            
            # 2. Registry Insert (The Anchor)
            if source_type not in ['SCRUTINY', 'ADJUDICATION']:
                raise ValueError("Invalid source_type")
                
            cursor.execute("""
                INSERT INTO case_registry (id, source_type) VALUES (?, ?)
            """, (pid, source_type))
            
            # 3. Branching Insert Logic
            if source_type == 'SCRUTINY':
                case_id = self.generate_case_id(cursor) # Scrutiny uses generated IDs
                tp_details = data.get('taxpayer_details', {})
                if isinstance(tp_details, str):
                    try: tp_details = json.loads(tp_details)
                    except: tp_details = {}

                cursor.execute("""
                    INSERT INTO proceedings (
                        id, case_id, gstin, legal_name, trade_name, address, financial_year, 
                        initiating_section, form_type, status, demand_details, selected_issues, 
                        taxpayer_details, additional_details, last_date_to_reply, created_by,
                        asmt10_status, adjudication_case_id, version_no, workflow_stage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (
                    pid,
                    case_id,
                    data.get('gstin'),
                    data.get('legal_name'),
                    data.get('trade_name'),
                    data.get('address'),
                    data.get('financial_year'),
                    data.get('initiating_section'),
                    data.get('form_type'),
                    data.get('status', 'Draft'),
                    json.dumps(data.get('demand_details', [])),
                    json.dumps(data.get('selected_issues', [])),
                    json.dumps(tp_details),
                    json.dumps(data.get('additional_details', {})),
                    data.get('last_date_to_reply'),
                    data.get('created_by', 'System'),
                    'Draft',
                    None,
                    WorkflowStage.ASMT10_DRAFT.value # Default for Scrutiny
                ))
                self.log_event(pid, "CASE_CREATED", f"Proceeding created. Case ID: {case_id}", conn)
                
            elif source_type == 'ADJUDICATION':
                # Deep Copy / Validation for Direct Adjudication
                required = ['gstin', 'financial_year', 'section'] # Section maps to adjudication_section
                for f in required:
                    if not data.get(f):
                        raise ValueError(f"Missing mandatory Adjudication field: {f}")

                cursor.execute("""
                    INSERT INTO adjudication_cases (
                        id, source_scrutiny_id, gstin, legal_name, financial_year, 
                        adjudication_section, status, created_at, 
                        additional_details, taxpayer_details, demand_details, 
                        selected_issues, version_no, is_active, workflow_stage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, 1, 1, ?)
                """, (
                    pid,
                    None, # Direct Adjudication has no source scrutiny
                    data.get('gstin'),
                    data.get('legal_name'),
                    data.get('financial_year'),
                    data.get('section'), # Mapped from inputs
                    'Pending',
                    json.dumps(data.get('additional_details', {})),
                    json.dumps(data.get('taxpayer_details', {})),
                    json.dumps(data.get('demand_details', [])),
                    json.dumps(data.get('selected_issues', [])),
                    WorkflowStage.DRC01A_DRAFT.value # Default for Direct Adjudication
                ))
                self.log_event(pid, "ADJ_CASE_CREATED", f"Direct Adjudication created via {data.get('section')}", conn)

            conn.commit()
            conn.close()
            return pid
        except Exception as e:
            print(f"Error creating proceeding: {e}")
            if 'conn' in locals():
                conn.rollback()
            return None
        except Exception as e:
            print(f"Error creating proceeding: {e}")
            if 'conn' in locals():
                conn.rollback()
            return None

    def get_proceeding(self, pid):
        """
        Get proceeding details via Registry-First Resolution.
        Determine source_type from case_registry, then fetch from appropriate table.
        """
        import json
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Registry Lookup (The Truth)
            cursor.execute("SELECT source_type FROM case_registry WHERE id = ?", (pid,))
            reg_row = cursor.fetchone()
            
            if not reg_row:
                conn.close()
                return None # Registration missing = Case doesn't exist mainly
                
            source_type = reg_row['source_type']
            
            # 2. Branch Logic
            if source_type == 'SCRUTINY':
                cursor.execute("SELECT * FROM proceedings WHERE id = ?", (pid,))
                row = cursor.fetchone()
                if row:
                    d = dict(row)
                    d['source_type'] = 'SCRUTINY' # Explicitly set
                    self._parse_proceeding_json_fields(d)
                    conn.close()
                    return d
                    
            elif source_type == 'ADJUDICATION':
                cursor.execute("SELECT * FROM adjudication_cases WHERE id = ?", (pid,))
                row = cursor.fetchone()
                if row:
                    d = dict(row)
                    d['source_type'] = 'ADJUDICATION' # Explicitly set
                    
                    # If this is a linked adjudication case (Scrutiny Origin), we might want some source context
                    # BUT we do not merge blindly. We allow the UI to request source data if needed.
                    # This ensures "Snapshot Integrity".
                    
                    self._parse_proceeding_json_fields(d)
                    conn.close()
                    return d
                    
            conn.close()
            return None
        except Exception as e:
            print(f"Error getting proceeding: {e}")
            return None

    def get_scrutiny_case_data(self, source_scrutiny_id):
        """
        Explicitly fetch structured Scrutiny data (ASMT-10).
        Used to ensure we are reading from the canonical source.
        """
        try:
            return self.get_proceeding(source_scrutiny_id)
        except Exception:
            return None

    def _parse_proceeding_json_fields(self, d):
        """Helper to parse JSON fields in proceeding dict"""
        import json
        for field in ['demand_details', 'selected_issues', 'taxpayer_details', 'additional_details', 'asmt10_snapshot']:
            val = d.get(field)
            if val and isinstance(val, str):
                try:
                    d[field] = json.loads(val)
                except:
                    d[field] = {} if field in ['taxpayer_details', 'additional_details'] else []
            elif val is None:
                d[field] = {} if field in ['taxpayer_details', 'additional_details'] else []

    def update_proceeding(self, pid, data, version_no=None):
        """Update proceeding details (Canonical: Branches by Registry source_type)"""
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Determine Source Table via Registry
            cursor.execute("SELECT source_type FROM case_registry WHERE id = ?", (pid,))
            registry_row = cursor.fetchone()
            
            if not registry_row:
                print(f"DB Error: Registry entry missing for ID {pid}")
                conn.close()
                return False
            
            source_type = registry_row[0]
            
            # BACKEND LOCK ENFORCEMENT - Single Source of Truth
            from src.utils.constants import WorkflowStage
            if source_type == 'SCRUTINY':
                cursor.execute("SELECT workflow_stage FROM proceedings WHERE id=?", (pid,))
                lock_row = cursor.fetchone()
                if lock_row and lock_row[0] is not None and lock_row[0] >= WorkflowStage.DRC01A_ISSUED.value:
                    raise RuntimeError(f"Database Modification Rejected: Proceeding {pid} is Finalized and Locked.")
            elif source_type == 'ADJUDICATION':
                cursor.execute("SELECT workflow_stage FROM adjudication_cases WHERE id=?", (pid,))
                lock_row = cursor.fetchone()
                if lock_row and lock_row[0] is not None and lock_row[0] >= WorkflowStage.DRC01A_ISSUED.value:
                    raise RuntimeError(f"Database Modification Rejected: Adjudication Case {pid} is Finalized and Locked.")
            
            if source_type == 'ADJUDICATION':
                conn.close()
                return self.update_adjudication_case(pid, data, version_no=version_no)
            
            # 2. Update PROCEEDINGS (SCRUTINY)
            fields = []
            values = []
            for k, v in data.items():
                if k in ['demand_details', 'selected_issues', 'taxpayer_details', 'additional_details']:
                    v = json.dumps(v)
                fields.append(f"{k} = ?")
                values.append(v)
            
            # Optimistic Locking Increment
            fields.append("version_no = version_no + 1")
            
            values.append(pid)
            where_clause = "WHERE id = ?"
            if version_no is not None:
                where_clause += " AND version_no = ?"
                values.append(version_no)
            
            query = f"UPDATE proceedings SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP {where_clause}"
            
            cursor.execute(query, values)
            
            if cursor.rowcount == 0:
                if version_no is not None:
                     raise ConcurrencyError(f"Update failed for {pid}: Version mismatch.")
                return False
            
            conn.commit()
            return True

        except Exception as e:
            if 'conn' in locals():
                try:
                    conn.rollback()
                except sqlite3.ProgrammingError:
                    pass # Ignore if closed
            print(f"Error updating proceeding: {e}")
            raise e
        finally:
            if 'conn' in locals():
                 conn.close()

    def delete_proceeding(self, pid):
        """Delete a proceeding and all related data, including orphan adjudication cases."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Check for linked adjudication case
            cursor.execute("SELECT adjudication_case_id FROM proceedings WHERE id = ?", (pid,))
            row = cursor.fetchone()
            if row and row[0]:
                adj_id = row[0]
                # Delete the linked adjudication case to prevent orphans
                cursor.execute("DELETE FROM adjudication_cases WHERE id = ?", (adj_id,))
            
            # 2. Delete related documents
            cursor.execute("DELETE FROM documents WHERE proceeding_id = ?", (pid,))
            
            # 3. Delete related events
            cursor.execute("DELETE FROM events WHERE proceeding_id = ?", (pid,))
            
            # 4. Delete case issues
            cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ?", (pid,))
            
            # 5. Delete from Registers (explicit cleanup required as FK is SET NULL or missing)
            # Find associated case_id
            cursor.execute("SELECT case_id FROM proceedings WHERE id = ?", (pid,))
            c_row = cursor.fetchone()
            if c_row and c_row[0]:
                cid = c_row[0]
                cursor.execute("DELETE FROM oc_register WHERE case_id = ?", (cid,))
                cursor.execute("DELETE FROM asmt10_register WHERE case_id = ?", (cid,))
            
            # 6. Delete the proceeding itself
            cursor.execute("DELETE FROM proceedings WHERE id = ?", (pid,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting proceeding: {e}")
            return False

    def update_adjudication_case(self, adj_id, data, version_no=None):
        """
        Update adjudication_cases with Optimistic Locking & Active State Management.
        version_no: Required for concurrency control.
        """
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Expanded allowed fields to support full SCN drafting
            json_fields = ['additional_details', 'taxpayer_details', 'demand_details', 'selected_issues']
            
            updates = []
            values = []
            
            # 1. Automatic is_active Management
            if 'status' in data:
                CLOSURE_STATUSES = ['Order Issued', 'Dropped', 'Closed']
                is_active = 0 if data['status'] in CLOSURE_STATUSES else 1
                updates.append("is_active = ?")
                values.append(is_active)

            for k, v in data.items():
                if k in json_fields and isinstance(v, (dict, list)):
                    v = json.dumps(v)
                
                # Filter out immutable fields if passed by mistake (Trigger will also catch this)
                if k in ['gstin', 'financial_year', 'adjudication_section']:
                    continue
                    
                updates.append(f"{k} = ?")
                values.append(v)
            
            # Optimistic Locking Increment
            updates.append("version_no = version_no + 1")
            
            if not updates:
                conn.close()
                return False
                
            values.append(adj_id)
            
            # Concurrency Check Clause
            where_clause = "WHERE id = ?"
            if version_no is not None:
                where_clause += " AND version_no = ?"
                values.append(version_no)
            
            query = f"UPDATE adjudication_cases SET {', '.join(updates)} {where_clause}"
            
            cursor.execute(query, tuple(values))
            
            # Check for Optimistic Lock Failure
            if cursor.rowcount == 0:
                if version_no is not None:
                     raise ConcurrencyError(f"Update failed for {adj_id}: Version mismatch.")
                return False
            
            conn.commit()
            return True
        except Exception as e:
            if 'conn' in locals():
                 conn.rollback()
            print(f"Error updating adjudication case: {e}")
            raise e
        finally:
            if 'conn' in locals():
                 conn.close()

    def save_document(self, data):
        """Save a document draft or final version"""
        import uuid
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Check if document exists for this type and proceeding (if we are updating a draft)
            # For simplicity, let's assume we are passing 'id' if updating, or creating new if not
            
            doc_id = data.get('id')
            if not doc_id:
                doc_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO documents (
                        id, proceeding_id, doc_type, content_html, 
                        template_id, template_version, version_no, is_final, snapshot_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    data.get('proceeding_id'),
                    data.get('doc_type'),
                    data.get('content_html'),
                    data.get('template_id'),
                    data.get('template_version'),
                    data.get('version_no', 1),
                    data.get('is_final', 0),
                    data.get('snapshot_path')
                ))
            else:
                cursor.execute("""
                    UPDATE documents SET 
                        content_html = ?, 
                        updated_at = CURRENT_TIMESTAMP,
                        is_final = ?,
                        snapshot_path = ?
                    WHERE id = ?
                """, (
                    data.get('content_html'),
                    data.get('is_final', 0),
                    data.get('snapshot_path'),
                    doc_id
                ))
            
            conn.commit()
            conn.close()
            return doc_id
        except Exception as e:
            print(f"Error saving document: {e}")
            return None

    def get_documents(self, proceeding_id):
        """Get all documents for a proceeding"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM documents WHERE proceeding_id = ? ORDER BY created_at DESC", (proceeding_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []

    def log_event(self, proceeding_id, event_type, description, conn=None):
        """Log an event to the timeline"""
        import uuid
        should_close = False
        try:
            if not conn:
                conn = self._get_conn()
                should_close = True
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (id, proceeding_id, event_type, description)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), proceeding_id, event_type, description))
            
            if should_close:
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Error logging event: {e}")

    def get_timeline(self, proceeding_id):
        """Get timeline events"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM events WHERE proceeding_id = ? ORDER BY timestamp DESC", (proceeding_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting timeline: {e}")
            return []
            
    def get_all_proceedings(self):
        """Get all proceedings for list view"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM proceedings ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting all proceedings: {e}")
            return []

    def get_all_templates(self):
        """Get all templates from the database"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, type, version FROM templates ORDER BY name")
            columns = [col[0] for col in cursor.description]
            templates = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            return templates
        except Exception as e:
            print(f"Error fetching templates: {e}")
            return []

    def get_template(self, template_id):
        """Get a specific template by ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            print(f"Error fetching template {template_id}: {e}")
            return None

    def save_template(self, data):
        """Save or update a template"""
        import uuid
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            if not data.get('id'):
                data['id'] = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO templates (id, name, type, content, version, is_default)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    data['id'], data['name'], data['type'], 
                    data['content'], data.get('version', '1.0'), 
                    data.get('is_default', 0)
                ))
            else:
                cursor.execute("""
                    UPDATE templates 
                    SET name=?, type=?, content=?, version=?, is_default=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (
                    data['name'], data['type'], data['content'], 
                    data.get('version', '1.0'), data.get('is_default', 0),
                    data['id']
                ))
                
            conn.commit()
            conn.close()
            return data['id']
        except Exception as e:
            print(f"Error saving template: {e}")
            return None

    def delete_template(self, template_id):
        """Delete a template"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting template: {e}")
            return False

    def get_issue_templates(self):
        """
        Load issue templates. 
        First tries to fetch active issues from DB.
        If none, falls back to JSON file (legacy support).
        """
        try:
            # Try DB first
            db_issues = self.get_active_issues()
            if db_issues:
                return db_issues
                
            # Fallback to JSON
            import json
            file_path = os.path.join("data", "issues_templates.json")
            if not os.path.exists(file_path):
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return data.get('issues', [])
        except Exception as e:
            print(f"Error loading issue templates: {e}")
            return []

    # ---------------- Issue Management (Developer Module) ----------------

    def save_issue(self, issue_json):
        """
        Save an issue to the database.
        Updates both issues_master and issues_data.
        issue_json: dict containing the full issue object
        """
        import json
        from datetime import datetime
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Extract Core Fields
            issue_id = issue_json.get('issue_id')
            issue_name = issue_json.get('issue_name')
            category = issue_json.get('category')
            sop_point = issue_json.get('sop_point')
            
            if not issue_id:
                return False, "Issue ID is required"
            
            # Serialize complex fields
            templates_json = json.dumps(issue_json.get('templates', {}))
            grid_data_json = json.dumps(issue_json.get('grid_data', {}))
            table_def_json = json.dumps(issue_json.get('table_definition', {}))
            
            analysis_type = issue_json.get('analysis_type', 'auto')
            sop_version = issue_json.get('sop_version')
            app_fy = issue_json.get('applicable_from_fy')
            
            # Upsert into issues_master
            # Note: We are now driving everything from issues_master. 
            # We don't need issues_data table anymore for the strict binding, 
            # but legacy code might expect it? 
            # Safe bet: Update issues_master.
            
            cursor.execute("""
                INSERT INTO issues_master (
                    issue_id, issue_name, category, sop_point, templates, grid_data, 
                    table_definition, analysis_type, sop_version, applicable_from_fy,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(issue_id) DO UPDATE SET
                    issue_name=excluded.issue_name,
                    category=excluded.category,
                    sop_point=excluded.sop_point,
                    templates=excluded.templates,
                    grid_data=excluded.grid_data,
                    table_definition=excluded.table_definition,
                    analysis_type=excluded.analysis_type,
                    sop_version=excluded.sop_version,
                    applicable_from_fy=excluded.applicable_from_fy,
                    updated_at=excluded.updated_at
            """, (
                issue_id, issue_name, category, sop_point, templates_json, grid_data_json, 
                table_def_json, analysis_type, sop_version, app_fy,
                datetime.now()
            ))
            
            # Legacy compatibility (optional, but good for safety)
            # cursor.execute("INSERT OR REPLACE INTO issues_data (issue_id, issue_json) VALUES (?, ?)", (issue_id, json.dumps(issue_json)))
            
            conn.commit()
            conn.close()
            return True, "Issue Saved Successfully"
            
        except Exception as e:
            print(f"Error saving issue {issue_json.get('issue_id')}: {e}")
            return False, str(e)

    def update_master_template_description(self, issue_id, new_brief_facts):
        """
        Updates the 'brief_facts' template for a specific master issue in issues_master.
        This allows users to customize legal text globally.
        """
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Fetch current templates from issues_master
            cursor.execute("SELECT templates FROM issues_master WHERE issue_id = ?", (issue_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False, "Issue template not found in master database."
            
            templates = json.loads(row[0]) if row[0] else {}
            
            # 2. Update the template
            # PRESERVE ALL EXISTING KEYS (brief_facts_scn, brief_facts_drc01a, grounds, etc.)
            templates['brief_facts'] = new_brief_facts
            
            # 3. Save back to issues_master
            cursor.execute("""
                UPDATE issues_master 
                SET templates = ?, 
                    description = ?,
                    updated_at = CURRENT_TIMESTAMP 
                WHERE issue_id = ?
            """, (json.dumps(templates), new_brief_facts, issue_id))
            
            conn.commit()
            conn.close()
            return True, "Master template updated successfully."
            
        except Exception as e:
            print(f"Error updating master template: {e}")
            return False, str(e)

    def get_active_issues(self):
        """Get all active issues reconstructed from issues_master normalized columns"""
        import sqlite3
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Select directly from issues_master
            cursor.execute("SELECT * FROM issues_master WHERE active = 1")
            rows = cursor.fetchall()
            conn.close()
            
            issues = []
            for row in rows:
                issues.append(self._reconstruct_issue_json(row))
            return issues
        except Exception as e:
            print(f"Error getting active issues: {e}")
            return []

    def _reconstruct_issue_json(self, row):
        """
        Helper to reconstruct the legacy issue_json structure from issues_master columns.
        Ensures exact backward compatibility for IssueCard and ScrutinyTab.
        """
        import json
        if not row:
            return None
            
        # Convert sqlite3.Row if needed
        d = dict(row) if not isinstance(row, dict) else row
        
        # Parse JSON columns
        def safe_json_load(val):
            if not val: return {}
            if isinstance(val, (dict, list)): return val # Already parsed
            try: return json.loads(val)
            except: return {}

        templates = safe_json_load(d.get('templates'))
        grid_data = safe_json_load(d.get('grid_data'))
        liability_config = safe_json_load(d.get('liability_config'))
        tax_demand_mapping = safe_json_load(d.get('tax_demand_mapping'))
        
        # Construct the legacy blob structure
        return {
            "issue_id": d.get('issue_id'),
            "issue_name": d.get('issue_name'),
            "description": d.get('description') or templates.get('brief_facts', ''),
            "category": d.get('category', 'General'),
            "sop_point": d.get('sop_point'),
            "grid_data": grid_data,
            "templates": templates,
            "liability_config": liability_config,
            "tax_demand_mapping": tax_demand_mapping,
            "analysis_type": d.get('analysis_type', 'auto'),
            "sop_version": d.get('sop_version'),
            "applicable_from_fy": d.get('applicable_from_fy')
        }

    def get_all_issues_metadata(self):
        """Get metadata for all issues (for Developer List View)"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM issues_master ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting all issues: {e}")
            return []

    def get_issue(self, issue_id):
        """
        Retrieve a single Master Issue record by Semantic ID.
        Returns a dict including 'sop_point', 'templates', etc.
        """
        import json
        import sqlite3
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # EXPLICIT SELECTION to force cached schema refresh/bypass
            cursor.execute("""
                SELECT issue_id, issue_name, category, sop_point, templates, grid_data, 
                       table_definition, analysis_type, sop_version, applicable_from_fy,
                       liability_config, tax_demand_mapping
                FROM issues_master 
                WHERE issue_id = ?
            """, (issue_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                d = dict(row)
                
                # Helper to parse JSON safely
                def parse_json_field(key):
                    if d.get(key):
                        if isinstance(d[key], str):
                            try: 
                                d[key] = json.loads(d[key])
                            except Exception as e: 
                                print(f"[DB ERROR] JSON parse failed for issue '{d.get('issue_id')}' field '{key}': {e}")
                                d[key] = {} # Default to dict for all schema fields
                    else:
                         d[key] = {}

                parse_json_field('templates')
                parse_json_field('grid_data')
                parse_json_field('table_definition')
                parse_json_field('liability_config')
                parse_json_field('tax_demand_mapping')
                
                return d
            return None
        except Exception as e:
            print(f"Error getting issue {issue_id}: {e}")
            return None

    def get_issue_by_name(self, name):
        """Fetch an issue by its name reconstructed from issues_master"""
        import sqlite3
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM issues_master WHERE issue_name = ?", (name,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._reconstruct_issue_json(row)
            return None
        except Exception as e:
            print(f"Error getting issue by name {name}: {e}")
            return None

    def get_issue_templates(self):
        """
        Fetch all available Issue Templates (SOPs, Custom SCN, etc.) from Master.
        Returns detailed list for the Template Selection Dialog.
        """
        import json
        import sqlite3
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            
            # Fetch all active templates with FULL DATA
            cursor.execute("""
                SELECT * FROM issues_master 
                WHERE active = 1 
                ORDER BY issue_id
            """)
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                d = dict(row)
                
                # Helper to parse JSON safely
                def parse_json_field(key):
                    if d.get(key):
                        if isinstance(d[key], str):
                            try: 
                                d[key] = json.loads(d[key])
                            except: 
                                d[key] = {}
                    else:
                         d[key] = {}

                parse_json_field('templates')
                parse_json_field('grid_data')
                parse_json_field('table_definition')
                parse_json_field('liability_config')
                parse_json_field('tax_demand_mapping')
                
                # Determine Type (SOP vs Custom)
                if d['issue_id'].startswith('SOP-'):
                    d['type'] = 'SOP'
                else:
                    d['type'] = 'SCN'
                results.append(d)
                
            return results
            
        except Exception as e:
            print(f"Error fetching issue templates: {e}")
            return []

    def get_case_issues(self, proceeding_id, stage='SCN'):
        """
        Fetch issues for a specific case/proceeding at a specific stage.
        Returns a list of issue records (dictionaries).
        """
        try:
             conn = self._get_conn()
             conn.row_factory = sqlite3.Row
             cursor = conn.cursor()
             
             # Table 'case_issues' structure: id, proceeding_id, issue_id, stage, data_json, origin, added_by...
             # Assuming 'stage' column exists? Or is it implicit in 'data_json'?
             # ProceedingsWorkspace calls it with stage='SCN' or 'DRC-01A'.
             # Let's check schema assumption. In finalize_proceeding_transaction (1753), it inserts into asmt10_register.
             # Wait, `persist_scn_issues` calls `save_scn_issue_snapshot`.
             # `save_scn_issue_snapshot` handles writing to `case_issues`.
             # I should check `save_scn_issue_snapshot` to see the schema.
             # But I can't check it easily without grep.
             # Let's assume standard schema: proceeding_id, stage, ...
             
             cursor.execute("""
                 SELECT ci.*, im.sop_point
                 FROM case_issues ci
                 LEFT JOIN issues_master im ON ci.issue_id = im.issue_id
                 WHERE ci.proceeding_id = ? AND ci.stage = ?
             """, (proceeding_id, stage))
             rows = cursor.fetchall()
             conn.close()
             
             results = []
             import json
             for row in rows:
                 r = dict(row)

                 # Parse data_json if it exists
                 if 'data_json' in r and isinstance(r['data_json'], str):
                     try:
                         r['data'] = json.loads(r['data_json'])
                     except:
                         r['data'] = {}
                 results.append(r)
             return results
             
        except Exception as e:
             # Make resilient if table/column missing (dev env)
             print(f"Error getting case issues: {e}")
             return []

    def save_scn_issue_snapshot(self, proceeding_id, issue_list):
        """
        Persist full snapshot of SCN issues for a proceeding.
        Strategy: Delete all existing 'SCN' stage issues for this PID, then insert new.
        Enforces 'Snapshot' integrity (what you see is what you save).
        """
        import json
        import uuid
        try:
             conn = self._get_conn()
             cursor = conn.cursor()
             
            # 1. Clear existing SCN issues for this proceeding
             # Guard: Only delete stage='SCN' to avoid wiping other stages if any
             # [FIX] Type Safety: Ensure proceeding_id is string
             pid_str = str(proceeding_id)
             cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ? AND stage = 'SCN'", (pid_str,))
             
             # 2. Insert new issues
             print(f"[DB DIAG] save_scn_issue_snapshot: Saving {len(issue_list)} issues. IDs: {[i.get('issue_id') for i in issue_list]}")
             for issue in issue_list:
                 issue_id = issue.get('issue_id')
                 origin = issue.get('origin', 'SCN')
                 source_pid = issue.get('source_proceeding_id') # For ASMT10
                 added_by = issue.get('added_by', 'User')
                 data = issue.get('data', {})
                 
                 # Prepare JSON payload
                 data_json = json.dumps(data)
                 
                 print(f"[DB DIAG] Inserting {issue_id} | PID: {pid_str} | SrcPID: {source_pid}")

                 cursor.execute("""
                     INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json, origin, added_by, source_proceeding_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?)
                 """, (pid_str, issue_id, 'SCN', data_json, origin, added_by, source_pid))
             
             conn.commit()
             # Verify immediately
             chk = cursor.execute("SELECT count(*) FROM case_issues WHERE proceeding_id=? AND stage='SCN'", (pid_str,)).fetchone()
             print(f"[DB DIAG] Post-Commit Count: {chk[0]}")
             return True
             
        except Exception as e:
             print(f"Error saving SCN snapshot: {e}")
             return False
        finally:
             if conn:
                 conn.close()

    def delete_proceeding(self, pid):
        """Delete a proceeding by ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Delete related issues first
            cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ?", (pid,))
            
            # Delete linked adjudication case (CRITICAL FIX for Orphans)
            cursor.execute("DELETE FROM adjudication_cases WHERE source_scrutiny_id = ?", (pid,))
            
            # Delete proceeding
            cursor.execute("DELETE FROM proceedings WHERE id = ?", (pid,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting proceeding: {e}")
            return False

    def publish_issue(self, issue_id, active=True):
        """Set the active status of an issue"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("UPDATE issues_master SET active = ?, updated_at=CURRENT_TIMESTAMP WHERE issue_id = ?", (1 if active else 0, issue_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error publishing issue: {e}")
            return False

    def delete_issue(self, issue_id):
        """Delete an issue"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Cascade delete should handle issues_data, but let's be safe
            cursor.execute("DELETE FROM issues_master WHERE issue_id = ?", (issue_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting issue: {e}")
            return False

    def add_asmt10_entry(self, data):
        """
        DEPRECATED: Add an entry to the ASMT-10 Register.
        Use finalize_proceeding_transaction instead.
        """
        print("ERROR: add_asmt10_entry is disabled.")
        return False
        
        # Legacy code below disabled
        # try:
        #     conn = self._get_conn()
        #     ...
        #     return True
        # except Exception as e:
        #     print(f"Error adding ASMT-10 entry: {e}")
        #     return False

    def finalize_proceeding_transaction(self, pid, oc_data, asmt_data, adj_data, user_id='System', snapshot=None):
        """
        Atomically finalize a proceeding (ASMT-10).
        1. Lock proceeding (status=finalised)
        2. Create OC Register Entry
        3. Create ASMT-10 Register Entry
        4. Create Linked Adjudication Case
        5. Persist Immutable ASMT-10 Snapshot [New]
        """
        import uuid
        import datetime
        import json
        from src.utils.constants import WorkflowStage
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # [Schema Migration] Ensure snapshot column exists (Robustness)
            try:
                cursor.execute("SELECT asmt10_snapshot FROM proceedings LIMIT 1")
            except Exception:
                # Column likely missing, add it
                print("Schema Migration: Adding asmt10_snapshot column to proceedings table.")
                try:
                    cursor.execute("ALTER TABLE proceedings ADD COLUMN asmt10_snapshot TEXT")
                    conn.commit() # Commit schema change
                except Exception as e:
                    print(f"Schema Migration Failed: {e}")

            # [STRICT GUARD] Verify if snapshot already exists
            cursor.execute("SELECT asmt10_snapshot FROM proceedings WHERE id = ?", (pid,))
            existing = cursor.fetchone()
            if existing and existing[0]:
                 print(f"Finalize [GUARD]: Snapshot already exists for {pid}. Aborting re-write.")
                 conn.close()
                 return False, "Snapshot already exists. Mutation blocked."

            # 1. Generate Adjudication ID
            adj_id = str(uuid.uuid4())
            
            # Prepare Snapshot JSON
            snapshot_json = json.dumps(snapshot) if snapshot else None
            
            # 2. Update Proceeding Status & Snapshot & Workflow Stage
            cursor.execute("""
                UPDATE proceedings 
                SET asmt10_status = 'finalised', 
                    asmt10_finalised_on = CURRENT_TIMESTAMP, 
                    asmt10_finalised_by = ?,
                    adjudication_case_id = ?,
                    asmt10_snapshot = ?,
                    workflow_stage = ?
                WHERE id = ?
            """, (
                user_id, 
                adj_id, 
                snapshot_json, 
                WorkflowStage.ASMT10_ISSUED.value, # Explicit Stage Set
                pid
            ))
            
            if cursor.rowcount == 0:
                raise Exception(f"Proceeding {pid} not found or update failed.")
            
            # 3. OC Register
            # Use shared logic with STRICT issuance
            valid_oc_num = self._insert_oc_entry(cursor, asmt_data.get('case_id'), oc_data, is_issuance=True)
            
            # 4. ASMT-10 Register
            cursor.execute("""
                INSERT INTO asmt10_register (gstin, financial_year, issue_date, case_id, oc_number)
                VALUES (?, ?, ?, ?, ?)
            """, (
                asmt_data.get('gstin'),
                asmt_data.get('financial_year'),
                asmt_data.get('issue_date'),
                asmt_data.get('case_id'),
                valid_oc_num # Use the validated OC Num
            ))
            
            # 5. Adjudication Case
            cursor.execute("""
                INSERT INTO adjudication_cases (
                    id, source_scrutiny_id, gstin, legal_name, financial_year, status,
                    workflow_stage
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                adj_id,
                adj_data.get('source_scrutiny_id'), # This is the pid
                adj_data.get('gstin'),
                adj_data.get('legal_name'),
                adj_data.get('financial_year'),
                'Pending',
                WorkflowStage.SCN_DRAFT.value # Default: Scrutiny Origin starts at SCN Draft
            ))
            
            conn.commit()
            conn.close()
            return True, adj_id
            
        except Exception as e:
            print(f"Transaction Error: {e}")
            if 'conn' in locals(): conn.close()
            return False, str(e)

    def save_asmt10_snapshot(self, pid, snapshot_data):
        """
        Standalone method to save an ASMT10 snapshot (used mainly for migration).
        Includes strict Write-Once guard.
        """
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Ensure column exists
            try: cursor.execute("SELECT asmt10_snapshot FROM proceedings LIMIT 1")
            except: cursor.execute("ALTER TABLE proceedings ADD COLUMN asmt10_snapshot TEXT")

            # Check existing
            cursor.execute("SELECT asmt10_snapshot FROM proceedings WHERE id = ?", (pid,))
            row = cursor.fetchone()
            if row and row[0]:
                conn.close()
                return False, "Snapshot already exists. ASMT-10 is immutable."

            cursor.execute("UPDATE proceedings SET asmt10_snapshot = ? WHERE id = ?", (json.dumps(snapshot_data), pid))
            conn.commit()
            conn.close()
            return True, "Saved"
        except Exception as e:
            print(f"Error saving snapshot: {e}")
            return False, str(e)
    def delete_oc_entry(self, entry_id):
        """Delete specific entry from OC register."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM oc_register WHERE id = ?", (entry_id,))
            rows_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_deleted == 0:
                print(f"Warning: delete_oc_entry failed. ID {entry_id} not found.")
                return False
                
            return True
        except Exception as e:
            print(f"Error deleting OC entry: {e}")
            return False

    def delete_asmt10_entry(self, entry_id):
        """Delete specific entry from ASMT-10 register."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM asmt10_register WHERE id = ?", (entry_id,))
            rows_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if rows_deleted == 0:
                print(f"Warning: delete_asmt10_entry failed. ID {entry_id} not found.")
                return False
                
            return True
        except Exception as e:
            print(f"Error deleting ASMT-10 entry: {e}")
            return False
        
    def reset_registers_for_dev(self):
        """
        DEV ONLY: Clear OC, ASMT-10 Registers, and reset associated proceedings/adjudication.
        1. Deletes all rows from oc_register.
        2. Deletes all rows from asmt10_register.
        3. Deletes all rows from adjudication_cases.
        4. Resets ASMT-10 status fields in proceedings table.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Clear Registers
            cursor.execute("DELETE FROM oc_register")
            cursor.execute("DELETE FROM asmt10_register")
            
            # 2. Clear Adjudication Cases
            cursor.execute("DELETE FROM adjudication_cases")
            
            # 3. Reset Proceedings Status
            # Reset all ASMT-10 related fields and unlink adjudication cases
            cursor.execute("""
                UPDATE proceedings 
                SET asmt10_status = NULL, 
                    asmt10_finalised_on = NULL, 
                    asmt10_finalised_by = NULL,
                    adjudication_case_id = NULL
            """)
            
            conn.commit()
            conn.close()
            return True, "Registers reset successfully."
        except Exception as e:
            print(f"Dev Reset Error: {e}")
            if conn: conn.rollback()
            return False, str(e)
            return False, str(e)

    def create_adjudication_case(self, data):
        """Create a linked Adjudication Case from Scrutiny with Registry Anchor"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            adj_id = str(uuid.uuid4())
            
            # 1. Transaction Start
            cursor.execute("BEGIN TRANSACTION;")
            
            # 2. Registry First (Anchor)
            cursor.execute("""
                INSERT INTO case_registry (id, source_type) VALUES (?, 'ADJUDICATION')
            """, (adj_id,))
            
            # 3. Main Adjudication Entry
            cursor.execute("""
                INSERT INTO adjudication_cases (id, source_scrutiny_id, gstin, legal_name, financial_year, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                adj_id,
                data.get('source_scrutiny_id'),
                data.get('gstin'),
                data.get('legal_name'),
                data.get('financial_year'),
                'Pending'
            ))
            
            conn.commit()
            conn.close()
            return adj_id
        except Exception as e:
            print(f"Error creating adjudication case: {e}")
            if 'conn' in locals():
                conn.rollback()
            return None

    def get_valid_adjudication_cases(self):
        """
        Fetch valid adjudication cases with strict filtering.
        Rules:
        1. Scrutiny Origin: source_scrutiny_id IS NOT NULL AND Linked Proceeding is Finalised.
        2. Direct Origin: source_scrutiny_id IS NULL.
        """
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    ac.*,
                    p.asmt10_status as source_status,
                    p.financial_year as source_fy,
                    p.legal_name as source_legal_name,
                    p.gstin as source_gstin
                FROM adjudication_cases ac
                LEFT JOIN proceedings p ON ac.source_scrutiny_id = p.id
                WHERE 
                    (ac.source_scrutiny_id IS NOT NULL AND LOWER(p.asmt10_status) = 'finalised')
                    OR 
                    (ac.source_scrutiny_id IS NULL)
                ORDER BY ac.created_at DESC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting valid adjudication cases: {e}")
            return []



    def get_gst_acts(self):
        """Get all GST Acts from DB"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gst_acts ORDER BY title")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting GST Acts: {e}")
            return []



    def get_asmt10_register_entries(self):
        """Get all entries from asmt10_register."""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM asmt10_register ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting ASMT-10 register: {e}")
            return []


    def get_act_sections(self, act_id, chapter_id=None):
        """Get all sections for a specific Act from DB, optionally filtered by chapter"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if chapter_id:
                cursor.execute("SELECT * FROM gst_sections WHERE act_id = ? AND chapter_id = ? ORDER BY id", (act_id, chapter_id))
            else:
                cursor.execute("SELECT * FROM gst_sections WHERE act_id = ? ORDER BY id", (act_id,))
            
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting Act sections: {e}")
            return []
    
    def get_act_chapters(self, act_id):
        """Get all unique chapters for a specific Act"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT chapter_id, chapter_name 
                FROM gst_sections 
                WHERE act_id = ? AND chapter_id IS NOT NULL
                ORDER BY chapter_id
            """, (act_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting Act chapters: {e}")
            return []
    
    def search_handbook(self, query, act_id=None):
        """Search across all acts and sections"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            search_pattern = f"%{query}%"
            
            if act_id:
                cursor.execute("""
                    SELECT s.*, a.title as act_title 
                    FROM gst_sections s
                    JOIN gst_acts a ON s.act_id = a.act_id
                    WHERE s.act_id = ? AND (s.title LIKE ? OR s.content LIKE ?)
                    ORDER BY s.id
                    LIMIT 50
                """, (act_id, search_pattern, search_pattern))
            else:
                cursor.execute("""
                    SELECT s.*, a.title as act_title 
                    FROM gst_sections s
                    JOIN gst_acts a ON s.act_id = a.act_id
                    WHERE s.title LIKE ? OR s.content LIKE ?
                    ORDER BY s.id
                    LIMIT 50
                """, (search_pattern, search_pattern))
            
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error searching handbook: {e}")
            return []


    def get_cgst_sections(self):
        """
        Retrieves sections from the Central Goods and Services Tax Act, 2017
        from the SQLite database.
        """
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find CGST Act ID
            cursor.execute("SELECT act_id FROM gst_acts WHERE title LIKE '%Central Goods and Services Tax Act%' LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                return []
                
            act_id = row['act_id']
            
            # Get Sections
            cursor.execute("SELECT section_number, title, content FROM gst_sections WHERE act_id = ?", (act_id,))
            rows = cursor.fetchall()
            conn.close()
            
            return [{'section_number': r['section_number'], 'title': r['title'], 'content': r['content']} for r in rows]

        except Exception as e:
            print(f"Error fetching CGST sections: {e}")
            return []

    def get_scrutiny_cases(self):
        """Get all ASMT-10 cases from proceedings table"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, case_id, gstin, legal_name, financial_year, status, created_at 
                FROM proceedings 
                WHERE form_type = 'ASMT-10' 
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting scrutiny cases: {e}")
            return []

    # ---------------- Officer Registry Methods ----------------

    def get_active_officers(self):
        """Fetch all active officers for UI dropdowns"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, designation, jurisdiction, office_address FROM officers WHERE is_active = 1 ORDER BY name")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching active officers: {e}")
            return []

    def get_officer_by_id(self, officer_id):
        """Fetch a specific officer's complete metadata by ID"""
        if not officer_id: return None
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM officers WHERE id = ?", (officer_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching officer {officer_id}: {e}")
            return None

    def get_all_officers(self):
        """Fetch all officers (active and inactive) for Settings table"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, designation, jurisdiction, office_address, is_active FROM officers ORDER BY name")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error fetching all officers: {e}")
            return []

    def add_officer(self, name, designation, jurisdiction, office_address):
        """Add a new officer to the registry"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO officers (name, designation, jurisdiction, office_address, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (name, designation, jurisdiction, office_address))
            conn.commit()
            officer_id = cursor.lastrowid
            conn.close()
            return officer_id
        except Exception as e:
            print(f"Error adding officer: {e}")
            return None

    def update_officer(self, officer_id, name, designation, jurisdiction, office_address):
        """Update an existing officer's details"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE officers 
                SET name = ?, designation = ?, jurisdiction = ?, office_address = ?
                WHERE id = ?
            ''', (name, designation, jurisdiction, office_address, officer_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating officer {officer_id}: {e}")
            return False

    def toggle_officer_status(self, officer_id, is_active):
        """Enable or disable an officer (0 or 1)"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute('UPDATE officers SET is_active = ? WHERE id = ?', (is_active, officer_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error toggling officer status: {e}")
            return False

    def delete_officer(self, officer_id):
        """
        Delete an officer ONLY IF they are not referenced by any proceeding.
        Explicitly checks usage count before attempting DELETE.
        Returns: (Success: bool, ErrorMessage: str)
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # --- Deletion Safety Enhancement (Required) ---
            cursor.execute('SELECT COUNT(*) FROM proceedings WHERE issuing_officer_id = ?', (officer_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                conn.close()
                return False, f"Cannot delete officer. They are currently acting as the Issuing Authority for {count} proceeding(s)."
                
            # If safe, proceed with deletion
            cursor.execute('DELETE FROM officers WHERE id = ?', (officer_id,))
            conn.commit()
            conn.close()
            return True, "Officer successfully deleted."
            
        except sqlite3.IntegrityError as e:
            # Fallback catch for strict DB-level enforcement
            return False, "Database constraint error: This officer is actively linked to protected records."
        except Exception as e:
            print(f"Error deleting officer: {e}")
            return False, f"An unexpected error occurred: {str(e)}"
