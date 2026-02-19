
import zipfile
import xml.etree.ElementTree as ET
import re

class XLSXLight:
    """
    Lightweight XLSX parser using standard library zipfile and xml.
    Useful when pandas/openpyxl are unavailable or failing (e.g. OpenBLAS errors).
    """
    
    @staticmethod
    def read_sheet(file_path, sheet_name_pattern):
        """
        Reads a specific sheet matching the pattern.
        Returns a list of rows, where each row is a list of cell values (strings).
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # 1. Parse Shared Strings
                shared_strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    with z.open('xl/sharedStrings.xml') as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        ns = {'mq': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                        for si in root.findall('mq:si', ns):
                            t = si.find('mq:t', ns)
                            if t is not None:
                                shared_strings.append(t.text if t.text else "")
                            else:
                                shared_strings.append("")
                                
                # 2. Find Sheet ID
                target_r_id = None
                if 'xl/workbook.xml' not in z.namelist():
                    return None
                    
                with z.open('xl/workbook.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'mq': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    sheets = root.findall('.//mq:sheet', ns)
                    for sheet in sheets:
                        name = sheet.get('name')
                        r_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                        # Loose match for sheet name
                        if sheet_name_pattern.lower() in name.lower():
                            target_r_id = r_id
                            break
                            
                if not target_r_id:
                    return None
                    
                # 3. Map rID to filename via _rels
                # Usually rIdX -> worksheets/sheetX.xml, but strict way is to check xl/_rels/workbook.xml.rels
                # For simplicity/speed, we'll try to find the path in workbook.xml.rels or assume standard
                sheet_xml_path = None
                if 'xl/_rels/workbook.xml.rels' in z.namelist():
                     with z.open('xl/_rels/workbook.xml.rels') as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        ns = {'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                        for rel in root.findall('rel:Relationship', ns):
                            if rel.get('Id') == target_r_id:
                                params = rel.get('Target')
                                # Target is usually "worksheets/sheet2.xml", so prepent "xl/"
                                sheet_xml_path = f"xl/{params}"
                                break
                
                if not sheet_xml_path or sheet_xml_path not in z.namelist():
                    # Fallback assumption
                    sheet_index = target_r_id.replace("rId", "")
                    sheet_xml_path = f"xl/worksheets/sheet{sheet_index}.xml"
                    if sheet_xml_path not in z.namelist():
                        return None

                # 4. Parse Sheet Data
                rows_data = []
                with z.open(sheet_xml_path) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'mq': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    
                    sheet_data = root.find('mq:sheetData', ns)
                    if sheet_data is None: return []
                    
                    for row in sheet_data.findall('mq:row', ns):
                        # row entry
                        cell_values = []
                        # Sparse matrix handling? We just read cols as they come.
                        # Ideally verify 'r' attribute like 'A1', 'B1' but simple append works for dense tables
                        
                        cols = row.findall('mq:c', ns)
                        # We need to handle empty columns if we rely on index.
                        # This parser assumes 'dense' row for simplicity or handled by caller logic
                        # Better: Parse 'r' attribute (e.g. "A1") to determine column index? 
                        # For GSTR-2B, checks are text based or header based. Dense list is okay-ish if we are careful.
                        # But wait, empty cells might be skipped in XML!
                        # Safest is to just extract text and process.
                        # But for Quarterly, we need index 15.
                        # If parsed list has fewer items, we pad?
                        
                        # Let's try to respect Column Index from 'r' attribute
                        # A=1, B=2 ... P=16
                        
                        vals_map = {}
                        max_col = 0
                        
                        for c in cols:
                            r_attr = c.get('r') # e.g. A1, P5
                            # Extract column letters
                            col_letters = "".join([ch for ch in r_attr if ch.isalpha()])
                            col_idx = 0
                            for char in col_letters:
                                col_idx = col_idx * 26 + (ord(char.upper()) - ord('A')) + 1
                            col_idx -= 1 # 0-indexed
                            
                            t = c.get('t')
                            v = c.find('mq:v', ns)
                            val = ""
                            if v is not None:
                                if t == 's':
                                    idx = int(v.text)
                                    if idx < len(shared_strings):
                                        val = shared_strings[idx]
                                else:
                                    val = v.text
                            
                            vals_map[col_idx] = val
                            if col_idx > max_col: max_col = col_idx
                            
                        # Reconstruct list with padding
                        dense_row = []
                        for i in range(max_col + 1):
                            dense_row.append(vals_map.get(i, ""))
                            
                        rows_data.append(dense_row)
                        
                return rows_data

        except Exception as e:
            print(f"XLSXLight Error: {e}")
            return None
