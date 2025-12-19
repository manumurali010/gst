import json
import os

class ConfigManager:
    """Manages application configuration and user preferences"""
    
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
        self.config_file = os.path.join(self.config_dir, 'settings.json')
        self.letterheads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', 'letterheads')
        
        # Ensure config directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        # Default settings
        self.default_settings = {
            "pdf_letterhead": "default.html",  # HTML letterhead for PDF
            "word_letterhead": "default.html",  # Can be HTML or DOCX for Word
            "office_name": "GST Department",
            "jurisdiction": ""
        }
        
        # Load or create settings
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**self.default_settings, **settings}
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self.default_settings.copy()
        else:
            # Create default settings file
            self.save_settings(self.default_settings)
            return self.default_settings.copy()
    
    def save_settings(self, settings=None):
        """Save settings to JSON file"""
        if settings is None:
            settings = self.settings
        else:
            self.settings = settings
            
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_letterhead_path(self, output_format='pdf'):
        """Get the full path to the letterhead for specified output format"""
        if output_format == 'pdf':
            letterhead_name = self.settings.get('pdf_letterhead', 'default.html')
        else:  # word
            letterhead_name = self.settings.get('word_letterhead', 'default.html')
        
        letterhead_path = os.path.join(self.letterheads_dir, letterhead_name)
        
        # Fall back to default if file doesn't exist
        if not os.path.exists(letterhead_path):
            letterhead_path = os.path.join(self.letterheads_dir, 'default.html')
            
        return letterhead_path
    
    def get_available_letterheads(self):
        """Get list of available letterhead files (HTML and DOCX)"""
        if not os.path.exists(self.letterheads_dir):
            return []
            
        letterheads = []
        for file in os.listdir(self.letterheads_dir):
            if file.endswith('.html') or file.endswith('.docx'):
                letterheads.append(file)
        return sorted(letterheads)
    
    def get_letterhead_type(self, letterhead_name=None):
        """Get the type of letterhead (html or docx)"""
        if letterhead_name is None:
            letterhead_name = self.settings.get('pdf_letterhead', 'default.html')
        
        if letterhead_name.endswith('.docx'):
            return 'docx'
        else:
            return 'html'
    
    def set_pdf_letterhead(self, letterhead_name):
        """Set the letterhead for PDF generation"""
        self.settings['pdf_letterhead'] = letterhead_name
        return self.save_settings()
    
    def set_word_letterhead(self, letterhead_name):
        """Set the letterhead for Word generation"""
        self.settings['word_letterhead'] = letterhead_name
        return self.save_settings()
    
    def get_pdf_letterhead(self):
        """Get the current PDF letterhead name"""
        return self.settings.get('pdf_letterhead', 'default.html')
    
    def get_word_letterhead(self):
        """Get the current Word letterhead name"""
        return self.settings.get('word_letterhead', 'default.html')
    
    def get_setting(self, key, default=None):
        """Get a specific setting value"""
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """Set a specific setting value"""
        self.settings[key] = value
        return self.save_settings()

    def get_letterhead_adjustments(self, filename):
        """Get visual adjustments for a specific letterhead"""
        adjustments = self.settings.get('lh_adjustments', {})
        return adjustments.get(filename, {
            "width": 100,      # percentage
            "padding_top": 0,  # pixels
            "margin_bottom": 20 # pixels
        })

    def set_letterhead_adjustments(self, filename, width, padding_top, margin_bottom):
        """Save visual adjustments for a specific letterhead"""
        if 'lh_adjustments' not in self.settings:
            self.settings['lh_adjustments'] = {}
        
        self.settings['lh_adjustments'][filename] = {
            "width": width,
            "padding_top": padding_top,
            "margin_bottom": margin_bottom
        }
        return self.save_settings()
