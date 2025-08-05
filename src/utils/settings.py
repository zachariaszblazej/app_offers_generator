"""Settings management for the Offer Generator application"""

import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.config import DEFAULT_COMPANY_DATA, DEFAULT_OFFER_DETAILS, DEFAULT_APP_SETTINGS

SETTINGS_FILE = 'app_settings.json'

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

# Global settings manager instance
settings_manager = SettingsManager()
