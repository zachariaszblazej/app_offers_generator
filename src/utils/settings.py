"""Settings management for the Offer Generator application"""

import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.config import DEFAULT_COMPANY_DATA, DEFAULT_OFFER_DETAILS, DEFAULT_APP_SETTINGS, get_data_dir

# Settings file should be in a persistent, writable location
SETTINGS_FILE = os.path.join(get_data_dir(), 'app_settings.json')

class SettingsManager:
    """Manages application settings"""
    
    def __init__(self):
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from file or create default settings"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Ensure all required keys exist
                    if 'company_data' not in settings:
                        settings['company_data'] = DEFAULT_COMPANY_DATA.copy()
                    if 'offer_details' not in settings:
                        settings['offer_details'] = DEFAULT_OFFER_DETAILS.copy()
                    if 'app_settings' not in settings:
                        settings['app_settings'] = DEFAULT_APP_SETTINGS.copy()
                    return settings
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading settings: {e}")
                return self.get_default_settings()
        else:
            return self.get_default_settings()
    
    def get_default_settings(self):
        """Get default application settings"""
        return {
            'company_data': DEFAULT_COMPANY_DATA.copy(),
            'offer_details': DEFAULT_OFFER_DETAILS.copy(),
            'app_settings': DEFAULT_APP_SETTINGS.copy()
        }
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"Error saving settings: {e}")
            return False
    
    # Company data methods
    def get_company_data_setting(self, key):
        """Get a specific company data setting"""
        return self.settings.get('company_data', {}).get(key, DEFAULT_COMPANY_DATA.get(key, ''))
    
    def set_company_data_setting(self, key, value):
        """Set a specific company data setting"""
        if 'company_data' not in self.settings:
            self.settings['company_data'] = {}
        self.settings['company_data'][key] = value
    
    def get_all_company_data_settings(self):
        """Get all company data settings"""
        return self.settings.get('company_data', DEFAULT_COMPANY_DATA.copy())
    
    def update_company_data_settings(self, new_settings):
        """Update multiple company data settings"""
        if 'company_data' not in self.settings:
            self.settings['company_data'] = {}
        self.settings['company_data'].update(new_settings)

    # Offer details methods
    def get_offer_details_setting(self, key):
        """Get a specific offer details setting"""
        return self.settings.get('offer_details', {}).get(key, DEFAULT_OFFER_DETAILS.get(key, ''))
    
    def set_offer_details_setting(self, key, value):
        """Set a specific offer details setting"""
        if 'offer_details' not in self.settings:
            self.settings['offer_details'] = {}
        self.settings['offer_details'][key] = value
    
    def get_all_offer_details_settings(self):
        """Get all offer details settings"""
        return self.settings.get('offer_details', DEFAULT_OFFER_DETAILS.copy())
    
    def update_offer_details_settings(self, new_settings):
        """Update multiple offer details settings"""
        if 'offer_details' not in self.settings:
            self.settings['offer_details'] = {}
        self.settings['offer_details'].update(new_settings)

    # App settings methods
    def get_app_setting(self, key):
        """Get a specific app setting"""
        return self.settings.get('app_settings', {}).get(key, DEFAULT_APP_SETTINGS.get(key, ''))
    
    def set_app_setting(self, key, value):
        """Set a specific app setting"""
        if 'app_settings' not in self.settings:
            self.settings['app_settings'] = {}
        self.settings['app_settings'][key] = value
    
    def get_all_app_settings(self):
        """Get all app settings"""
        return self.settings.get('app_settings', DEFAULT_APP_SETTINGS.copy())
    
    def update_app_settings(self, new_settings):
        """Update multiple app settings"""
        if 'app_settings' not in self.settings:
            self.settings['app_settings'] = {}
        self.settings['app_settings'].update(new_settings)
        
        # If database_path is updated, also update the config.py file
        if 'database_path' in new_settings:
            self.update_database_path_in_config(new_settings['database_path'])
    
    def get_database_path(self):
        """Get current database path"""
        return self.get_app_setting('database_path')
    
    def update_database_path_in_config(self, new_path):
        """Update DATABASE_PATH in config.py file"""
        try:
            config_file_path = os.path.join(os.path.dirname(__file__), 'config.py')
            
            # Read the current config file
            with open(config_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace the DATABASE_PATH line
            import re
            pattern = r"DATABASE_PATH = ['\"][^'\"]*['\"]"
            replacement = f"DATABASE_PATH = '{new_path}'"
            new_content = re.sub(pattern, replacement, content)
            
            # Write back to file
            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            print(f"Updated DATABASE_PATH in config.py to: {new_path}")
            
        except Exception as e:
            print(f"Error updating DATABASE_PATH in config.py: {e}")
            try:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Uwaga", 
                    f"Nie udało się zaktualizować ścieżki do bazy danych w pliku config.py.\n"
                    f"Musisz ręcznie zrestartować aplikację żeby zmiany zaczęły obowiązywać.\n\n"
                    f"Błąd: {e}")
            except ImportError:
                # If tkinter is not available, just print the error
                print(f"Warning: Could not update DATABASE_PATH in config.py: {e}")

# Global settings manager instance
settings_manager = SettingsManager()
