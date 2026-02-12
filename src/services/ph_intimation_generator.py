import os
import json
from jinja2 import Environment, FileSystemLoader
from src.utils.config_manager import ConfigManager

class PHIntimationGenerator:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.config = ConfigManager()

    def generate_html(self, case_data, ph_entry, for_preview=False, for_pdf=False):
        """
        Generate PH Intimation HTML.
        :param case_data: Dict containing taxpayer and SCN metadata
        :param ph_entry: Dict containing specific PH date/time/venue
        :param for_preview: Boolean for Qt-specific styling
        :param for_pdf: Boolean for WeasyPrint (static) rendering
        """
        try:
            template = self.env.get_template('ph_intimation.html')
            
            # 1. Gather Metadata
            model = {
                'oc_no': ph_entry.get('oc_no', 'DRAFT'),
                'issue_date': ph_entry.get('issue_date', '-'),
                'legal_name': case_data.get('legal_name', '-'),
                'gstin': case_data.get('gstin', '-'),
                'address': case_data.get('address', '-'),
                'scn_no': case_data.get('scn_no', '-'),
                'scn_date': case_data.get('scn_date', '-'),
                'ph_date': ph_entry.get('ph_date', '-'),
                'ph_time': ph_entry.get('ph_time', '-'),
                'officer_designation': "Superintendent",
                'office_address': "Paravur Range Office",
                'officer_name': "VISHNU V",
                'copy_to': ph_entry.get('copy_to', 'The Assistant Commissioner, Central Tax, Paravur Division')
            }

            # 2. CSS and Styling
            css_dir = os.path.join(self.template_dir, 'css')
            def read_css(filename):
                path = os.path.join(css_dir, filename)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()
                return ""

            base_css = read_css('doc_base.css')
            renderer_css = read_css('doc_qt.css') if for_preview else ""
            model['full_styles_html'] = f"<style>\n{base_css}\n{renderer_css}\n</style>"

            # 3. Letterhead
            model['letter_head'] = ""
            if ph_entry.get('show_letterhead', True):
                try:
                    lh_path = self.config.get_letterhead_path('pdf')
                    if lh_path and os.path.exists(lh_path):
                        with open(lh_path, 'r', encoding='utf-8') as f:
                            # Simple HTML letterhead injection
                            model['letter_head'] = f.read()
                except Exception as e:
                    print(f"PH Generator: Letterhead failed: {e}")

            model['for_pdf'] = for_pdf
            return template.render(**model)

        except Exception as e:
            print(f"Error generating PH Intimation: {e}")
            return f"<h3>Render Error: {str(e)}</h3>"
