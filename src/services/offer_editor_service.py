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
from src.services.offer_generator_service import convert_date, select_template
from src.data.database_service import update_offer_context_in_db


# Template selection is centralized in offer_generator_service.select_template


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

        # Wybierz odpowiedni szablon na podstawie długości nazw i pola gwarancji
        template_filename = select_template(
            supplier_data.get('name', ''),
            supplier_data.get('address1', ''),
            client_data.get('name', ''),
            client_data.get('address1', ''),
            context_data.get('gwarancja', ''),
        )

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'templates',
            template_filename,
        )

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
            'products': products,
        })

        # Convert date for display if needed
        if 'date' in template_context:
            template_context['date'] = convert_date(template_context['date'])

        # Convert client_name '/n' markers to real line breaks using RichText for Word rendering
        try:
            from docxtpl import RichText
            name_val = template_context.get('client_name', '')
            if isinstance(name_val, str) and '/n' in name_val:
                rt = RichText()
                rt.add(name_val.replace('/n', '\n'))
                template_context['client_name'] = rt
        except Exception:
            # Fallback: leave as plain text if RichText unavailable
            pass

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

        tkinter.messagebox.showerror(
            "Błąd", f"Nie udało się zaktualizować oferty:\n{e}"
        )
        print(f"Error updating offer: {e}")  # Debug info
        return False
