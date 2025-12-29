import sqlite3
import pandas as pd
import os
import json
from datetime import datetime
from src.utils.constants import TAXPAYERS_FILE, CASES_FILE, CASE_FILES_FILE

class DatabaseManager:
    def __init__(self):
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

    def create_case_file(self, data):
        """
        Creates a new entry in the Case File Register.
        data: dict containing GSTIN, Legal Name, Trade Name, Section, Status, etc.
        Returns: case_id (str) or None if failed
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

    def add_oc_entry(self, case_id, oc_data):
        """
        Add an entry to the OC Register (SQLite).
        oc_data: dict with keys 'OC_Number', 'OC_Content', 'OC_Date', 'OC_To'
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Check if OC Number already exists
            cursor.execute("SELECT id FROM oc_register WHERE oc_number = ?", (oc_data.get('OC_Number'),))
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
                    oc_data.get('OC_Number'),
                    oc_data.get('OC_Content'),
                    oc_data.get('OC_Date'),
                    oc_data.get('OC_To')
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding OC entry: {e}")
            return False

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
                data_json = json.dumps(issue.get('data', {}))
                
                cursor.execute("""
                    INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json)
                    VALUES (?, ?, ?, ?)
                """, (proceeding_id, issue_id, stage, data_json))
                
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
        Returns a list of dicts with 'issue_id' and 'data' (parsed JSON).
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT issue_id, data_json 
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
                    'data': data
                })
            
            conn.close()
            return issues
        except Exception as e:
            print(f"Error getting case issues: {e}")
            return []

    def clone_issues_for_scn(self, proceeding_id):
        """
        Clone DRC-01A issues to SCN stage if SCN issues don't exist yet.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Check if SCN issues already exist
            cursor.execute("SELECT count(*) FROM case_issues WHERE proceeding_id = ? AND stage = 'SCN'", (proceeding_id,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return False # Already exists, don't overwrite
                
            # Fetch DRC-01A issues
            cursor.execute("""
                SELECT issue_id, data_json 
                FROM case_issues 
                WHERE proceeding_id = ? AND stage = 'DRC-01A'
            """, (proceeding_id,))
            
            drc_issues = cursor.fetchall()
            
            # Insert as SCN issues
            for row in drc_issues:
                cursor.execute("""
                    INSERT INTO case_issues (proceeding_id, issue_id, stage, data_json)
                    VALUES (?, ?, 'SCN', ?)
                """, (proceeding_id, row[0], row[1]))
                
            conn.commit()
            conn.close()
            return True
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
            
            formatted_total = f"{total_demand:,.2f}"
            formatted_cgst = f"{cgst_demand:,.2f}"
            formatted_sgst = f"{sgst_demand:,.2f}"
            formatted_igst = f"{igst_demand:,.2f}"
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
        self.db_file = DB_FILE
        init_db()

    # ---------------- SQLite Methods for New Architecture ----------------

    def _get_conn(self):
        import sqlite3
        return sqlite3.connect(self.db_file)

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

    def create_proceeding(self, data):
        """Create a new proceeding in SQLite"""
        import uuid
        import json
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            pid = str(uuid.uuid4())
            case_id = self.generate_case_id(cursor)
            
            # Ensure taxpayer_details is a dict before dumping
            tp_details = data.get('taxpayer_details', {})
            if isinstance(tp_details, str):
                try: tp_details = json.loads(tp_details)
                except: tp_details = {}

            cursor.execute("""
                INSERT INTO proceedings (
                    id, case_id, gstin, legal_name, trade_name, address, financial_year, 
                    initiating_section, form_type, status, demand_details, selected_issues, 
                    taxpayer_details, additional_details, last_date_to_reply, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data.get('created_by', 'System')
            ))
            
            # Log creation event
            self.log_event(pid, "CASE_CREATED", f"Proceeding created. Case ID: {case_id}", conn)
            
            conn.commit()
            conn.close()
            return pid
        except Exception as e:
            print(f"Error creating proceeding: {e}")
            return None

    def get_proceeding(self, pid):
        """Get proceeding details"""
        import json
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM proceedings WHERE id = ?", (pid,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                d = dict(row)
                # Parse JSON fields
                for field in ['demand_details', 'selected_issues', 'taxpayer_details', 'additional_details']:
                    val = d.get(field)
                    if val and isinstance(val, str):
                        try:
                            d[field] = json.loads(val)
                        except:
                            d[field] = {} if field in ['taxpayer_details', 'additional_details'] else []
                    elif val is None:
                        d[field] = {} if field in ['taxpayer_details', 'additional_details'] else []
                        
                return d
            return None
        except Exception as e:
            print(f"Error getting proceeding: {e}")
            return None

    def update_proceeding(self, pid, data):
        """Update proceeding details"""
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            fields = []
            values = []
            
            for k, v in data.items():
                if k in ['demand_details', 'selected_issues', 'taxpayer_details', 'additional_details']:
                    v = json.dumps(v)
                fields.append(f"{k} = ?")
                values.append(v)
            
            values.append(pid)
            
            query = f"UPDATE proceedings SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating proceeding: {e}")
            return False

    def delete_proceeding(self, pid):
        """Delete a proceeding and all related data"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Delete related documents
            cursor.execute("DELETE FROM documents WHERE proceeding_id = ?", (pid,))
            
            # Delete related events
            cursor.execute("DELETE FROM events WHERE proceeding_id = ?", (pid,))
            
            # Delete the proceeding itself
            cursor.execute("DELETE FROM proceedings WHERE id = ?", (pid,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting proceeding: {e}")
            return False

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
        import datetime
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            issue_id = issue_json.get('issue_id')
            if not issue_id:
                return False, "Issue ID is required"
                
            # Extract metadata
            issue_name = issue_json.get('issue_name')
            category = issue_json.get('category')
            severity = issue_json.get('severity')
            tags = json.dumps(issue_json.get('tags', []))
            version = issue_json.get('version')
            
            # Check if exists
            cursor.execute("SELECT issue_id FROM issues_master WHERE issue_id = ?", (issue_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update Master
                cursor.execute("""
                    UPDATE issues_master 
                    SET issue_name=?, category=?, severity=?, tags=?, version=?, updated_at=CURRENT_TIMESTAMP
                    WHERE issue_id=?
                """, (issue_name, category, severity, tags, version, issue_id))
                
                # Update Data (Delete old data entry and insert new, or update)
                # We'll update the latest entry or just overwrite the single entry per issue_id
                # The schema allows multiple data entries per issue_id if we wanted history, 
                # but for now let's keep 1:1 for simplicity or 1:Many if we want versioning.
                # The user requirement implies "save issues to DB", doesn't explicitly ask for full history.
                # Let's update the existing data row.
                
                cursor.execute("UPDATE issues_data SET issue_json=? WHERE issue_id=?", (json.dumps(issue_json), issue_id))
                
            else:
                # Insert Master
                cursor.execute("""
                    INSERT INTO issues_master (issue_id, issue_name, category, severity, tags, version, active)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (issue_id, issue_name, category, severity, tags, version))
                
                # Insert Data
                cursor.execute("""
                    INSERT INTO issues_data (issue_id, issue_json)
                    VALUES (?, ?)
                """, (issue_id, json.dumps(issue_json)))
            
            conn.commit()
            conn.close()
            return True, "Issue saved successfully"
            
        except Exception as e:
            print(f"Error saving issue: {e}")
            return False, str(e)

    def get_active_issues(self):
        """Get all active issues as a list of JSON objects"""
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Join master and data to get the JSON
            query = """
                SELECT d.issue_json 
                FROM issues_master m
                JOIN issues_data d ON m.issue_id = d.issue_id
                WHERE m.active = 1
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            issues = []
            for row in rows:
                try:
                    issues.append(json.loads(row[0]))
                except:
                    pass
            return issues
        except Exception as e:
            print(f"Error getting active issues: {e}")
            return []

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
        """Get a single issue's full JSON"""
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT issue_json FROM issues_data WHERE issue_id = ?", (issue_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            print(f"Error getting issue {issue_id}: {e}")
            return None

    def get_issue_by_name(self, name):
        """Fetch an issue by its name from issues_master/data tables"""
        import json
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            query = """
                SELECT d.issue_json 
                FROM issues_master m
                JOIN issues_data d ON m.issue_id = d.issue_id
                WHERE m.issue_name = ?
            """
            cursor.execute(query, (name,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return [None, row[0]] # Returning tuple (None, json_str) to match usage in scrutiny_tab.py line 1559
            return None
        except Exception as e:
            print(f"Error getting issue by name {name}: {e}")
            return None

    def delete_proceeding(self, pid):
        """Delete a proceeding by ID"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Delete related issues first
            cursor.execute("DELETE FROM case_issues WHERE proceeding_id = ?", (pid,))
            
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
