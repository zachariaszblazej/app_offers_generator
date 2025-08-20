"""
Resource path utilities for PyInstaller compatibility
"""
import os
import sys

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_data_dir():
    """
    Get the data directory for the application
    This should be persistent and writable
    """
    if getattr(sys, 'frozen', False):
        # We're running in a PyInstaller bundle
        # Use the directory where the executable is located
        return os.path.dirname(sys.executable)
    else:
        # We're running in a normal Python environment
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_settings_file_path():
    """Get the path to the settings file"""
    return os.path.join(get_data_dir(), 'app_settings.json')

def get_background_image_path():
    """Get the path to the background image"""
    return get_resource_path('background_offer_1.png')

def get_wz_background_image_path():
    """Get the path to the WZ background image"""
    return get_resource_path('background_wz_1.png')

def get_templates_dir():
    """Get the path to the templates directory"""
    return get_resource_path('templates')
