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
DATABASE_PATH = 'Y:/AplikacjaDokumenty/HantechDocumentsDatabase.db'

# Default application settings
DEFAULT_APP_SETTINGS = {
    'database_path': 'Y:/AplikacjaDokumenty/HantechDocumentsDatabase.db'
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
    'termin_realizacji': "30 dni roboczych",
    'termin_platnosci': "14 dni od wystawienia faktury",
    'warunki_dostawy': "DAP",
    'waznosc_oferty': "14 dni",
    'gwarancja': "",
    'cena': "Do ceny netto zostanie doliczony podatek VAT zgodnie z obowiązującymi przepisami."
}

# File paths
TEMPLATE_PATH = get_resource_path('templates/offer_template.docx')
BACKGROUND_IMAGE = get_resource_path('background_offer_1.png')
WZ_BACKGROUND_IMAGE = get_resource_path('background_wz_1.png')

def get_offers_folder():
    """Get the current offers folder.
    Order of precedence:
    1) DB table Paths (Name='Offers_Folder') if available,
    2) module fallback OFFERS_FOLDER.
    Does not read app_settings.json for offers folder.
    """
    # 1) Try DB Paths first
    try:
        import sqlite3
        from src.utils.settings import SettingsManager
        sm = SettingsManager()
        db_path = sm.get_database_path()
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT Path FROM Paths WHERE Name = ? LIMIT 1", ("Offers_Folder",))
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
    except Exception:
        # Silently fallback to default if DB not available or query fails
        pass

    # 2) Fallback to module default
    return ''


def get_wz_folder():
    """Get the current WZ folder.
    Order of precedence:
    1) DB table Paths (Name='Wz_Folder') if available,
    2) module fallback '../FakeHantechServer/WZ'.
    Does not read app_settings.json for WZ folder.
    """
    try:
        import sqlite3
        from src.utils.settings import SettingsManager
        sm = SettingsManager()
        db_path = sm.get_database_path()
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT Path FROM Paths WHERE Name = ? LIMIT 1", ("Wz_Folder",))
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
    except Exception:
        pass
    return ''


# UI Configuration
WINDOW_SIZE = "1600x1200"

# Application Info
from src.utils.version import get_version_string
APP_VERSION = get_version_string()
APP_TITLE = "Kreator Dokumentów Hantech"

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
