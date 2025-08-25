"""
Service for generating offers with template selection based on client name/address length
and whether the warranty (gwarancja) field is provided. Maps to four templates:
 - Small names + with gwarancja -> offer_template.docx
 - Small names + empty gwarancja -> offer_template_no_gwarancja.docx
 - Long names  + with gwarancja -> offer_template_long_names.docx
 - Long names  + empty gwarancja -> offer_template_long_names_no_gwarancja.docx
"""
import os
from docx import Document
from datetime import datetime
from src.utils.date_utils import format_polish_date


def select_template(supplier_name: str, supplier_address1: str, client_name: str, client_address1: str, gwarancja: str) -> str:
    """
    Select offer template based on client name/address length and warranty field.

    Criteria:
    - "Small" sum (client_name + client_address1) AND gwarancja non-empty -> offer_template.docx
    - "Small" sum AND gwarancja empty -> offer_template_no_gwarancja.docx
    - "Large" sum (>= threshold) AND gwarancja non-empty -> offer_template_long_names.docx
    - "Large" sum AND gwarancja empty -> offer_template_long_names_no_gwarancja.docx

    Note: Threshold kept at 95 characters for client_name + client_address1.
    """
    client_total_length = len(client_name or "") + len(client_address1 or "")
    is_long = client_total_length >= 95
    has_warranty = bool((gwarancja or "").strip())

    if is_long and has_warranty:
        return "offer_template_long_names.docx"
    if is_long and not has_warranty:
        return "offer_template_long_names_no_gwarancja.docx"
    if not is_long and has_warranty:
        return "offer_template.docx"
    return "offer_template_no_gwarancja.docx"
from docxtpl import DocxTemplate, RichText
import tkinter.messagebox
import datetime
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import TEMPLATE_PATH, get_offers_folder
from src.data.database_service import (
    get_next_offer_number_for_year,
    save_offer_to_db,
    normalize_offer_db_path,
)


def convert_date(date: datetime.datetime) -> str:
    """Convert datetime to Polish formatted string (manual month mapping)."""
    return format_polish_date(date)


def generate_offer_number(date: datetime.datetime, client_alias: str) -> tuple:
    """Generate year-scoped offer number and file path.
    New rules:
    - Sequential counter resets per year.
    - Display number format: <seq>/OF/<year>_<alias>
    - Stored filename: <seq>_OF_<year>_<alias>.docx (no slashes to avoid path conflicts)
    - Directory: {offers_root}/{year}/
    """
    try:
        year = date.year
        seq_number = get_next_offer_number_for_year(year)
        offer_number = f"{seq_number}/OF/{year}_{client_alias}"
        # For filesystem, avoid slashes in base name
        filename = f"{seq_number}_OF_{year}_{client_alias}.docx"
        year_dir = os.path.join(get_offers_folder(), str(year))
        file_path = os.path.join(year_dir, filename)
        return offer_number, file_path, seq_number
    except Exception as e:
        tkinter.messagebox.showerror("Error", f"Failed to generate offer number: {e}")
        return None, None, None


def extract_client_alias_from_context(context_data):
    """Extract client alias from context data"""
    # First try to get alias from database selection
    client_alias = context_data.get('client_alias')
    if client_alias:
        return client_alias
    
    # Fallback: try to get client name and create alias
    client_name = context_data.get('client_name', '')
    
    if not client_name:
        return "UNKNOWN"
    
    # Simple alias generation - take first letters of words, max 6 chars
    words = client_name.upper().split()
    if len(words) == 1:
        alias = words[0][:6]
    else:
        alias = ''.join(word[:2] for word in words[:3])[:6]
    
    # Remove special characters
    alias = ''.join(c for c in alias if c.isalnum())
    
    return alias if alias else "CLIENT"


def generate_offer_document(context_data):
    """Generate offer document using the provided context data"""
    try:
        # Extract necessary data
        date_obj = context_data.get('date')
        if isinstance(date_obj, str):
            # If date is already converted to string, we need to parse it back
            # This shouldn't happen with current flow, but safety check
            date_obj = datetime.datetime.now()
        
        client_alias = extract_client_alias_from_context(context_data)
        
        # Generate offer number and file path
        offer_number, file_path, order_number = generate_offer_number(
            date_obj, client_alias)
        
        if not offer_number or not file_path:
            return False
        
        # Update context with the generated offer number
        context_data['offer_number'] = offer_number
        
        # Convert date to string for template
        context_data['date'] = convert_date(date_obj)
        
        # Debug: Print products to see if they're being passed as list of lists
        products = context_data.get('products', [])
        product_headers = context_data.get('product_headers', [])
        
        print(f"Products to be included in offer: {len(products)} items")
        print(f"Product format: {'List of lists' if products and isinstance(products[0], list) else 'Other format'}")
        
        if product_headers:
            print(f"Product table headers: {product_headers}")
        
        for i, product in enumerate(products):
            if isinstance(product, list):
                print(f"Product row {i+1}: {product}")
                # Each row contains: [pid, pname, unit, qty, unit_price, total]
                if len(product) >= 6:
                    print(f"  - Lp: {product[0]}")
                    print(f"  - Nazwa: {product[1]}")
                    print(f"  - Jednostka: {product[2]}")
                    print(f"  - Ilość: {product[3]}")
                    print(f"  - Cena jedn.: {product[4]}")
                    print(f"  - Suma: {product[5]}")
            else:
                print(f"Product {i+1}: {product}")
        
        # Products are now in format expected by Word template
        # Each product is a list: [pid, pname, unit, qty, unit_price, total]
        # This can be directly used in Word template as table rows
        # Headers are available in context['product_headers']
        
    # Wybierz odpowiedni szablon na podstawie długości nazw i pola gwarancji
        supplier_name = context_data.get('supplier_name', '')
        supplier_address1 = context_data.get('supplier_address_1', '')
        client_name = context_data.get('client_name', '')
        client_address1 = context_data.get('client_address_1', '')
        gwarancja = context_data.get('gwarancja', '')
        
        template_filename = select_template(
            supplier_name, supplier_address1, client_name, client_address1, gwarancja
        )
        
        # Utwórz ścieżkę do wybranego szablonu
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', template_filename)
        
    # Convert client_name '\n' markers to real line breaks using RichText
        def _to_richtext_with_newlines(value):
            if value is None:
                return ""
            text = str(value)
            if '\\n' not in text:
                return text
            # Add as a single run with embedded line breaks to preserve style
            rt = RichText()
            rt.add(text.replace('\\n', '\n'))
            return rt

        context_data['client_name'] = _to_richtext_with_newlines(context_data.get('client_name', ''))

        # Generate document
        doc = DocxTemplate(template_path)
        doc.render(context_data)
        
        # Ensure base offers root exists (do NOT auto-create root to enforce startup validation)
        offers_root = get_offers_folder()
        if not os.path.isdir(offers_root):
            tkinter.messagebox.showerror(
                "Błąd",
                "Folder ofert nie istnieje. Ustaw poprawny folder w zakładce Ustawienia przed generowaniem oferty."
            )
            return {'success': False, 'error': 'Offers root folder missing'}

        # Ensure year subdirectory exists (safe to create under existing root)
        year_dir = os.path.dirname(file_path)
        if not os.path.isdir(year_dir):
            try:
                os.makedirs(year_dir, exist_ok=True)
            except OSError as e:
                tkinter.messagebox.showerror("Błąd", f"Nie udało się utworzyć folderu roku: {e}")
                return {'success': False, 'error': f'Cannot create year folder: {e}'}
        
        # Save to offers folder
        doc.save(file_path)
        
        # Save to database only if we auto-generated the number
        if order_number is not None:
            # Make a copy of context data for storage (exclude template-specific conversions)
            storage_context = context_data.copy()
            # Convert date back to timestamp for storage
            if isinstance(date_obj, datetime.datetime):
                storage_context['date'] = date_obj.isoformat()
            
            rel_db_path = normalize_offer_db_path(file_path)
            if not save_offer_to_db(order_number, rel_db_path, storage_context):
                tkinter.messagebox.showwarning("Warning", "Offer generated but failed to save to database")
        
        # Return success status and details instead of showing message here
        return {
            'success': True,
            'offer_number': offer_number,
            'file_path': file_path
        }
        
    except Exception as e:
        tkinter.messagebox.showerror("Error", f"Failed to generate offer: {e}")
        return {'success': False, 'error': str(e)}
