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

from src.utils.config import TEMPLATE_PATH, get_offers_folder
from src.data.database_service import get_next_wz_number, save_wz_to_db


def convert_date(date: datetime.datetime) -> str:
    """Convert datetime to formatted string"""
    return date.strftime("%d %B %Y")


def generate_wz_document(context_data):
    """
    Generate WZ document using template and provided data
    
    Args:
        context_data: Dictionary containing all form data
        
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
        
        # Generate output filename
        wz_number = context_data.get('wz_number', 'WZ_1')
        output_filename = f"{wz_number}.docx"
        
        # Get output directory (use same as offers for now)
        output_dir = get_offers_folder()
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
        'address1': '',
        'address2': '',
        'nip': '',
        'regon': '',
        'email': '',
        'phone': '',
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
        if isinstance(product, (list, tuple)) and len(product) >= 6:
            processed_product = {
                'lp': i + 1,
                'name': product[0] or '',
                'unit': product[1] or '',
                'quantity': product[2] or '0',
                'price': product[3] or '0.00',
                'tax': product[4] or '23%',
                'total': product[5] or '0.00'
            }
            processed_products.append(processed_product)
    
    template_context['products'] = processed_products
    
    # Calculate totals
    total_net = 0
    total_tax = 0
    total_gross = 0
    
    try:
        for product in processed_products:
            quantity = float(product['quantity']) if product['quantity'] else 0
            price = float(product['price']) if product['price'] else 0
            net_value = quantity * price
            
            # Extract tax percentage
            tax_str = product['tax'].replace('%', '')
            tax_rate = float(tax_str) / 100 if tax_str else 0
            
            tax_value = net_value * tax_rate
            gross_value = net_value + tax_value
            
            total_net += net_value
            total_tax += tax_value
            total_gross += gross_value
            
    except Exception as e:
        print(f"Error calculating totals: {e}")
    
    template_context['total_net'] = f"{total_net:.2f}"
    template_context['total_tax'] = f"{total_tax:.2f}"
    template_context['total_gross'] = f"{total_gross:.2f}"
    
    return template_context


def get_wz_template_path():
    """Get the path to WZ template file"""
    template_path = os.path.join("/Users/blzc/Apka_Oferty/templates", "wz_template.docx")
    return template_path if os.path.exists(template_path) else None
