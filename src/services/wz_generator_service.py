"""
Service for generating WZ documents
"""
import os
import locale  # kept only if elsewhere needed; will not be used for date formatting now
from docx import Document
from datetime import datetime
from docxtpl import DocxTemplate, RichText
from jinja2 import Environment
import tkinter.messagebox
import datetime
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import get_wz_folder
from src.utils.resources import get_resource_path
from src.utils.date_utils import format_polish_date
from src.data.database_service import get_next_wz_number, save_wz_to_db
import re


def convert_date(date: datetime.datetime) -> str:
    """Return Polish formatted date (manual month mapping, no locale)."""
    return format_polish_date(date)


def generate_wz_document(context_data, custom_output_path=None):
    """
    Generate WZ document using template and provided data
    
    Args:
        context_data: Dictionary containing all form data
        custom_output_path: Optional custom path for output file (for editing existing WZ)
        
    Returns:
        str: Path to generated WZ file, or None if failed
    """
    try:
        # Resolve template path in a PyInstaller-friendly way via helper
        template_path = get_wz_template_path()
        if not template_path:
            tkinter.messagebox.showerror("Błąd", "Szablon WZ nie został znaleziony (wz_template.docx)")
            return None

        # Load template
        doc = DocxTemplate(template_path)

        # Prepare context data for template
        template_context = prepare_wz_context(context_data)

        # Render document with Jinja2 autoescape to preserve XML entities
        from jinja2 import Environment
        jinja_env = Environment(autoescape=True)
        doc.render(template_context, jinja_env=jinja_env)

        # Determine output path
        if custom_output_path:
            # Editing existing WZ – keep original path
            output_path = custom_output_path
        else:
            # New WZ: ensure year-scoped directory just like offers
            wz_number = context_data.get('wz_number', 'WZ_1')
            # Extract year from wz_number pattern WZ_<seq>_<year>_... ; fallback to current year
            year_match = re.search(r'^WZ_\d+_(\d{4})', wz_number)
            if year_match:
                year = year_match.group(1)
            else:
                year = str(datetime.datetime.now().year)
            # Build filesystem-safe filename (already safe – wz_number has no slashes)
            output_filename = f"{wz_number}.docx"
            wz_root = get_wz_folder()
            if not wz_root or not os.path.isdir(wz_root):
                tkinter.messagebox.showerror(
                    "Błąd",
                    "Folder WZ nie istnieje. Ustaw poprawny folder w zakładce Ustawienia przed generowaniem WZ."
                )
                return None
            year_dir = os.path.join(wz_root, year)
            if not os.path.isdir(year_dir):
                try:
                    os.makedirs(year_dir, exist_ok=True)
                except OSError as e:
                    tkinter.messagebox.showerror("Błąd", f"Nie udało się utworzyć folderu roku dla WZ: {e}")
                    return None
            output_path = os.path.join(year_dir, output_filename)

        # Save document
        doc.save(output_path)

        print(f"WZ document generated: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error generating WZ document: {e}")
        tkinter.messagebox.showerror("Błąd", f"Wystąpił błąd podczas generowania WZ:\n{e}")
        return None


def prepare_wz_context(context_data):
    """
    Prepare context data for WZ template rendering
    
    Args:
        context_data: Raw form data
        
    Returns:
        dict: Processed context data for template
    """
    # Start with the original context
    template_context = context_data.copy()
    
    # Format date if needed - use same approach as offers
    date_value = context_data.get('date', '')
    if date_value:
        try:
            # Check if date is already a datetime object
            if isinstance(date_value, (datetime.datetime, datetime.date)):
                # Convert datetime object to formatted string
                template_context['date'] = convert_date(date_value)
                template_context['formatted_date'] = convert_date(date_value)
            else:
                # Parse date string and convert to datetime, then format
                date_parts = str(date_value).split()
                if len(date_parts) == 3:
                    day, month, year = date_parts
                    # Create datetime object and use convert_date function
                    date_obj = datetime.datetime(int(year), int(month), int(day))
                    template_context['date'] = convert_date(date_obj)
                    template_context['formatted_date'] = convert_date(date_obj)
                else:
                    template_context['date'] = str(date_value)
                    template_context['formatted_date'] = str(date_value)
        except:
            template_context['date'] = str(date_value)
            template_context['formatted_date'] = str(date_value)
    else:
        # Use current date like offers do
        current_date = datetime.datetime.now()
        template_context['date'] = convert_date(current_date)
        template_context['formatted_date'] = convert_date(current_date)
    
    # Ensure all required fields have default values
    default_fields = {
        'town': '',
        'address_1': '',
        'address_2': '',
        'nip': '',
        'regon': '',
        'email': '',
        'phone_number': '',
        'bank_name': '',
        'account_number': '',
        'supplier_name': '',
        'supplier_address_1': '',
        'supplier_address_2': '',
        'supplier_nip': '',
        'client_name': '',
        'client_address_1': '',
        'client_address_2': '',
        'client_nip': '',
        'wz_number': '',
        'date': '',
        'products': []
    }
    
    # Fill missing fields with defaults
    for field, default_value in default_fields.items():
        if field not in template_context:
            template_context[field] = default_value
    # Sanitize and convert names only for template rendering; keep plain text in original context
    def _sanitize_plain(value):
        if value is None:
            return ''
        text = str(value)
        if '<w:r>' in text or '<w:t' in text:
            import re as _re
            text = _re.sub(r'<w:[^>]+>', '', text)
            text = text.replace('</w:t>', '').replace('</w:r>', '')
        return text

    raw_client_name = _sanitize_plain(template_context.get('client_name', ''))
    raw_supplier_name = _sanitize_plain(template_context.get('supplier_name', ''))

    def _to_richtext_with_newlines(value):
        if value is None:
            return ''
        txt = str(value)
        if '\\n' not in txt:
            return txt
        rt = RichText()
        rt.add(txt.replace('\\n', '\n'))
        return rt

    template_context['client_name'] = _to_richtext_with_newlines(raw_client_name)
    template_context['supplier_name'] = _to_richtext_with_newlines(raw_supplier_name)


    # Format NIPs (supplier & client) to XXX-XXX-XX-XX like offers
    def _format_nip(nip_value: str) -> str:
        if not nip_value:
            return nip_value
        digits = ''.join(ch for ch in str(nip_value) if ch.isdigit())
        if len(digits) == 10:
            return f"{digits[0:3]}-{digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
        return nip_value  # leave unchanged if not 10 digits

    template_context['supplier_nip'] = _format_nip(template_context.get('supplier_nip', ''))
    template_context['client_nip'] = _format_nip(template_context.get('client_nip', ''))
    
    # Process products data
    products = template_context.get('products', [])
    processed_products = []
    
    for i, product in enumerate(products):
        if isinstance(product, (list, tuple)) and len(product) >= 4:
            # WZ products have 4 elements: [pid, name, unit, quantity]
            # Keep as list for template compatibility with {{ row[0] }}, {{ row[1] }}, etc.
            processed_product = [
                str(i + 1),         # row[0] - Lp. (pozycja)
                str(product[1]),    # row[1] - name
                str(product[2]),    # row[2] - unit  
                str(product[3])     # row[3] - quantity
            ]
            processed_products.append(processed_product)
        elif isinstance(product, dict):
            # Handle dict format as fallback
            processed_product = [
                str(i + 1),                           # row[0] - Lp.
                str(product.get('name', '')),         # row[1] - name
                str(product.get('unit', '')),         # row[2] - unit
                str(product.get('quantity', '0'))     # row[3] - quantity
            ]
            processed_products.append(processed_product)
    
    template_context['products'] = processed_products
    
    # WZ doesn't have pricing, so no totals calculation needed
    template_context['total_net'] = ""
    template_context['total_tax'] = ""
    template_context['total_gross'] = ""
    
    return template_context


def get_wz_template_path():
    """Get the path to WZ template file (runtime safe)."""
    path = get_resource_path(os.path.join('templates', 'wz_template.docx'))
    return path if os.path.exists(path) else None
