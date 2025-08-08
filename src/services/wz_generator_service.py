"""
Service for generating WZ documents
"""
import os
import locale
from docx import Document
from datetime import datetime
from docxtpl import DocxTemplate
import tkinter.messagebox
import datetime
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import TEMPLATE_PATH, get_wz_folder
from src.data.database_service import get_next_wz_number, save_wz_to_db


def convert_date(date: datetime.datetime) -> str:
    """Convert datetime to formatted string with Polish locale"""
    try:
        # Temporarily set Polish locale for date formatting
        current_locale = locale.getlocale()
        locale.setlocale(locale.LC_TIME, 'pl_PL.UTF-8')
        formatted = date.strftime("%d %B %Y")
        # Restore original locale
        locale.setlocale(locale.LC_TIME, current_locale)
        return formatted
    except:
        # Fallback to manual Polish months if locale fails
        polish_months = {
            1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia",
            5: "maja", 6: "czerwca", 7: "lipca", 8: "sierpnia",
            9: "września", 10: "października", 11: "listopada", 12: "grudnia"
        }
        day = date.day
        month = polish_months[date.month]
        year = date.year
        return f"{day} {month} {year}"


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
        # Get template path
        template_path = os.path.join("/Users/blzc/Apka_Oferty/templates", "wz_template.docx")
        
        if not os.path.exists(template_path):
            tkinter.messagebox.showerror("Błąd", f"Szablon WZ nie został znaleziony: {template_path}")
            return None
        
        # Load template
        doc = DocxTemplate(template_path)
        
        # Prepare context data for template
        template_context = prepare_wz_context(context_data)
        
        # Render document
        doc.render(template_context)
        
        # Determine output path
        if custom_output_path:
            # Use provided path (for editing existing WZ)
            output_path = custom_output_path
        else:
            # Generate new filename and path
            wz_number = context_data.get('wz_number', 'WZ_1')
            output_filename = f"{wz_number}.docx"
            
            # Get output directory (use WZ folder from settings)
            output_dir = get_wz_folder()
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Full output path
            output_path = os.path.join(output_dir, output_filename)
        
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
    """Get the path to WZ template file"""
    template_path = os.path.join("/Users/blzc/Apka_Oferty/templates", "wz_template.docx")
    return template_path if os.path.exists(template_path) else None
