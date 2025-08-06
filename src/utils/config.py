"""Configuration settings for the Offer Generator application"""
import os
import sys

# Add compatibility for PyInstaller
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_dir():
    """Get data directory that's persistent and writable"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Database configuration
DATABASE_PATH = '/Users/blzc/FakeHantechServer/DocumentsCreationData.db'

# Default application settings
DEFAULT_APP_SETTINGS = {
    'offers_folder': '../FakeHantechServer/Oferty',
    'database_path': '../FakeHantechServer/DocumentsCreationData.db'
}

# Default company data
DEFAULT_COMPANY_DATA = {
    'town': 'Wałbrzych',
    'address_1': 'ul. Truskawiecka 14/4',
    'address_2': '58-301 Wałbrzych',
    'nip': '886-301-82-63',
    'regon': '520101773',
    'email': 'g.ciesla@hantech.net.pl',
    'phone_number': '+48 796 996 912',
    'bank_name': 'Pekao S.A.',
    'account_number': '37 1240 1952 1111 0011 3033 5600',
    'offer_number': ''
}

# Default offer details data
DEFAULT_OFFER_DETAILS = {
    'termin_realizacji': 'p1',
    'termin_platnosci': 'p1',
    'warunki_dostawy': 'p1',
    'waznosc_oferty': 'p1',
    'gwarancja': 'p1',
    'cena': 'p1'
}

# File paths
TEMPLATE_PATH = get_resource_path('templates/offer_template.docx')
OFFERS_FOLDER = '../FakeHantechServer/Oferty'  # Fallback default
BACKGROUND_IMAGE = get_resource_path('background_offer_1.png')

def get_offers_folder():
    """Get the current offers folder from settings or return default"""
    try:
        from src.utils.settings import settings_manager
        return settings_manager.get_app_setting('offers_folder')
    except ImportError:
        # Fallback to default if settings not available
        return OFFERS_FOLDER

# UI Configuration
WINDOW_SIZE = "1600x1200"
TAX_RATE = 0.18  # 18% VAT

# Application Info
APP_VERSION = "2.0"
APP_TITLE = "Generator Ofert - System tworzenia ofert"

# Table columns configuration
TABLE_COLUMNS = ('PID', 'PNAME', 'UNIT', 'QTY', 'U_PRICE', 'TOTAL', 'EDIT', 'DELETE')
TABLE_COLUMN_HEADERS = {
    'PID': 'Lp.',
    'PNAME': 'Nazwa',
    'UNIT': 'j.m.',
    'QTY': 'ilość',
    'U_PRICE': 'Cena\n jednostkowa\n netto [PLN]',
    'TOTAL': 'Wartość\n Netto\n [PLN]',
    'EDIT': 'Edytuj',
    'DELETE': 'Usuń'
}
