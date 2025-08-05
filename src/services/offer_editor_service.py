"""
Service for updating existing offer documents
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


def update_offer_document(context_data, existing_file_path):
    """Update an existing offer document and database context"""
    try:
        # Create backup of original file
        backup_path = existing_file_path + ".backup"
        shutil.copy2(existing_file_path, backup_path)
        
        # Load template
        doc = DocxTemplate(TEMPLATE_PATH)
        
        # Convert date for display
        context_data["date"] = convert_date(context_data["date"])
        
        # Render template with new data
        doc.render(context_data)
        
        # Save to the same location (overwrite)
        doc.save(existing_file_path)
        
        # Update context in database
        update_offer_context_in_db(existing_file_path, context_data)
        
        # Remove backup if successful
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        print(f"Offer updated successfully: {existing_file_path}")
        return True
        
    except Exception as e:
        # Restore backup if update failed
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, existing_file_path)
            os.remove(backup_path)
        
        tkinter.messagebox.showerror("Błąd", 
            f"Nie udało się zaktualizować oferty:\\n{e}")
        print(f"Error updating offer: {e}")  # Debug info
        return False
