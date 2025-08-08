"""
Service for generating WZ documents
"""
import os
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
    """Convert datetime to formatted string"""
    return date.strftime("%d %B %Y")


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
    
    # Format date if needed
    date_str = context_data.get('date', '')
    if date_str:
        try:
            # Parse date in format "DD MM YYYY"
            date_parts = date_str.split()
            if len(date_parts) == 3:
                day, month, year = date_parts
                # Convert month number to Polish month name
                month_names = {
                    '01': 'stycznia', '02': 'lutego', '03': 'marca',
                    '04': 'kwietnia', '05': 'maja', '06': 'czerwca',
                    '07': 'lipca', '08': 'sierpnia', '09': 'września',
                    '10': 'października', '11': 'listopada', '12': 'grudnia'
                }
                month_name = month_names.get(month.zfill(2), month)
                template_context['formatted_date'] = f"{day} {month_name} {year}"
            else:
                template_context['formatted_date'] = date_str
        except:
            template_context['formatted_date'] = date_str
    else:
        template_context['formatted_date'] = datetime.datetime.now().strftime("%d %B %Y")
    
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
