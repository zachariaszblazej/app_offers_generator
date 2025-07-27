"""Configuration settings for the Offer Generator application"""

# Database configuration
DATABASE_PATH = '../FakeHantechServer/DocumentsCreationData.db'

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

# File paths
TEMPLATE_PATH = 'templates/offer_template.docx'
OUTPUT_FOLDER = 'generated_docs'
OFFERS_FOLDER = '../FakeHantechServer/Oferty'
BACKGROUND_IMAGE = 'background_offer_1.png'

# UI Configuration
WINDOW_SIZE = "1600x1200"
TAX_RATE = 0.18  # 18% VAT

# Color Theme Configuration - High Contrast Professional Theme
COLOR_THEME = {
    # Background colors
    'bg_primary': '#FFFFFF',      # Pure white main background
    'bg_secondary': '#F8F9FA',    # Light gray secondary background
    'bg_accent': '#E9ECEF',       # Accent background for panels
    'bg_dark': '#212529',         # Dark background for contrast areas
    
    # Text colors
    'text_primary': '#212529',    # Dark text for high contrast
    'text_secondary': '#495057',  # Medium gray for secondary text
    'text_muted': '#6C757D',      # Muted text for labels
    'text_light': '#FFFFFF',      # White text for dark backgrounds
    
    # Button colors - Professional and accessible
    'btn_primary': '#0D6EFD',     # Professional blue
    'btn_primary_hover': '#0B5ED7',
    'btn_success': '#198754',     # Green for success actions
    'btn_success_hover': '#157347',
    'btn_danger': '#DC3545',      # Red for delete/danger actions
    'btn_danger_hover': '#BB2D3B',
    'btn_warning': '#FD7E14',     # Orange for warning actions
    'btn_warning_hover': '#E55A0B',
    'btn_info': '#0DCAF0',        # Light blue for info actions
    'btn_info_hover': '#0BB2D4',
    'btn_secondary': '#6C757D',   # Gray for secondary actions
    'btn_secondary_hover': '#5C636A',
    'btn_neutral': '#6C757D',     # Neutral gray for neutral actions
    'btn_accent': '#DC3545',      # Accent color for special actions
    'btn_text': '#FFFFFF',        # White text for buttons
    'btn_text_dark': '#212529',   # Dark text for light buttons
    
    # Form colors
    'input_bg': '#FFFFFF',        # White input background
    'input_border': '#CED4DA',    # Light gray border
    'input_focus': '#86B7FE',     # Blue focus highlight
    'input_readonly': '#E9ECEF',  # Light gray for readonly fields
    'input_disabled': '#E9ECEF',  # Light gray for disabled fields
    
    # Status colors
    'success': '#D1E7DD',         # Light green for success messages
    'error': '#F8D7DA',           # Light red for error messages
    'warning': '#FFF3CD',         # Light yellow for warnings
    'info': '#D1ECF1',            # Light blue for info messages
}

# Application Info
APP_VERSION = "2.0"
APP_TITLE = "Generator Ofert - System tworzenia ofert"

# Table columns configuration
TABLE_COLUMNS = ('PID', 'PNAME', 'QTY', 'U_PRICE', 'TOTAL')
TABLE_COLUMN_HEADERS = {
    'PID': 'Lp',
    'PNAME': 'ProductName',
    'QTY': 'Quantity',
    'U_PRICE': 'UNIT PRICE',
    'TOTAL': 'TOTAL'
}
