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
BACKGROUND_IMAGE = 'background_offer_1.png'

# UI Configuration
WINDOW_SIZE = "1600x1200"
TAX_RATE = 0.18  # 18% VAT

# Table columns configuration
TABLE_COLUMNS = ('PID', 'PNAME', 'QTY', 'U_PRICE', 'TOTAL')
TABLE_COLUMN_HEADERS = {
    'PID': 'Lp',
    'PNAME': 'ProductName',
    'QTY': 'Quantity',
    'U_PRICE': 'UNIT PRICE',
    'TOTAL': 'TOTAL'
}
