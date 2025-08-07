"""
Service for editing offers
"""
from docxtpl import DocxTemplate
import tkinter.messagebox
import datetime
import os
import sys
import shutil

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import TEMPLATE_PATH
from src.services.offer_generator_service import convert_date
from src.data.database_service import update_offer_context_in_db


def select_template_based_on_name_length(supplier_name, supplier_address1, client_name, client_address1):
    """
    Wybiera szablon na podstawie długości nazw i adresów
    
    Args:
        supplier_name: Nazwa dostawcy
        supplier_address1: Adres 1 dostawcy  
        client_name: Nazwa klienta
        client_address1: Adres 1 klienta
        
    Returns:
        str: Nazwa pliku szablonu do użycia
    """
    # Sprawdź długość nazwy i adresu dostawcy
    supplier_total_length = len(supplier_name or "") + len(supplier_address1 or "")
    
    # Sprawdź długość nazwy i adresu klienta
    client_total_length = len(client_name or "") + len(client_address1 or "")
    
    # Jeśli któraś z sum przekracza lub równa się 95 znaków, użyj długiego szablonu
    if supplier_total_length >= 95 or client_total_length >= 95:
        return "offer_template_long_names.docx"
    else:
        return "offer_template.docx"


def update_offer_document(context_data, offer_file_path):
    """Update an existing offer document and database context"""
    try:
        # Sprawdź czy plik istnieje
        if not offer_file_path or not os.path.exists(offer_file_path):
            raise ValueError("Offer file not found")
        
        # Wyodrębnij dane klienta i dostawcy z context_data
        client_data = {
            'name': context_data.get('client_name', ''),
            'address1': context_data.get('client_address_1', ''),  # Uwaga: z podkreślnikiem
        }
        
        supplier_data = {
            'name': context_data.get('supplier_name', ''),
            'address1': context_data.get('supplier_address_1', ''),  # Uwaga: z podkreślnikiem
        }
        
        # Pobierz produkty z context_data
        products = context_data.get('products', [])
        
        # Wybierz odpowiedni szablon na podstawie długości nazw
        template_filename = select_template_based_on_name_length(
            supplier_data.get('name', ''),
            supplier_data.get('address1', ''),
            client_data.get('name', ''),
            client_data.get('address1', '')
        )
        
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', template_filename)
        
        # Create backup of original file
        backup_path = offer_file_path + ".backup"
        shutil.copy2(offer_file_path, backup_path)
        
        # Load template
        doc = DocxTemplate(template_path)
        
        # Przygotuj pełne dane kontekstowe dla szablonu
        template_context = context_data.copy()
        template_context.update({
            'client_name': client_data.get('name', ''),
            'client_address1': client_data.get('address1', ''),
            'supplier_name': supplier_data.get('name', ''),
            'supplier_address1': supplier_data.get('address1', ''),
            'products': products
        })
        
        # Convert date for display if needed
        if 'date' in template_context:
            template_context["date"] = convert_date(template_context["date"])
        
        # Render template with new data
        doc.render(template_context)
        
        # Save to the same location (overwrite)
        doc.save(offer_file_path)
        
        # Update context in database
        update_offer_context_in_db(offer_file_path, template_context)
        
        # Remove backup if successful
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        print(f"Offer updated successfully: {offer_file_path}")
        return True
        
    except Exception as e:
        # Restore backup if update failed
        if 'backup_path' in locals() and os.path.exists(backup_path):
            shutil.copy2(backup_path, offer_file_path)
            os.remove(backup_path)
        
        tkinter.messagebox.showerror("Błąd", 
            f"Nie udało się zaktualizować oferty:\n{e}")
        print(f"Error updating offer: {e}")  # Debug info
        return False
