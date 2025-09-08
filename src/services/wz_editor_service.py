"""
WZ editor service for updating existing WZ documents
"""
import os
import json
from datetime import datetime
from docx import Document
from docx.shared import Inches
import tkinter.messagebox

from src.utils.config import get_wz_folder
from src.data.database_service import DatabaseService, update_wz_context_in_db


def update_wz_document(context_data, wz_path):
    """
    Update existing WZ document with new data
    
    Args:
        context_data (dict): Form data from UI
        wz_path (str): Path to existing WZ document to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Starting WZ update process for: {wz_path}")
        
        # Validate input
        if not wz_path or not os.path.exists(wz_path):
            print(f"WZ file does not exist: {wz_path}")
            return False
        
        if not context_data:
            print("No context data provided")
            return False
        
        # Get WZ number (should be preserved from original)
        wz_number = context_data.get('wz_number', 'WZ_UNKNOWN')
        print(f"Updating WZ number: {wz_number}")
        
        # Sanitize plain versions first (avoid storing Word tags) then convert to RichText only for rendering
        def _sanitize_plain(val):
            try:
                if val is None:
                    return ''
                if val.__class__.__name__ == 'RichText':
                    val = str(val)
                txt = str(val)
                if '<w:r>' in txt or '<w:t' in txt:
                    import re as _re
                    txt = _re.sub(r'<w:[^>]+>', '', txt)
                    txt = txt.replace('</w:t>', '').replace('</w:r>', '')
                return txt
            except Exception:
                return str(val)
        plain_client = _sanitize_plain(context_data.get('client_name',''))
        context_data['client_name'] = plain_client
        try:
            from docxtpl import RichText
            if '\\n' in plain_client:
                rt = RichText()
                rt.add(plain_client.replace('\\n','\n'))
                context_data['client_name'] = rt
        except Exception:
            pass

        # Update WZ document using template
        success = generate_wz_document_from_template(context_data, wz_path)
        
        if success:
            # Update context in database
            db_success = update_wz_context_in_db(wz_path, context_data)
            if not db_success:
                print("Warning: WZ document updated but database context update failed")
                # Don't fail the entire operation for database issues
            
            print(f"Successfully updated WZ: {wz_path}")
            return True
        else:
            print(f"Failed to update WZ document: {wz_path}")
            return False
        
    except Exception as e:
        print(f"Error in update_wz_document: {e}")
        return False


def generate_wz_document_from_template(context_data, output_path):
    """
    Generate WZ document from template and save to specified path
    
    Args:
        context_data (dict): Context data with form values
        output_path (str): Path where to save the updated document
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from src.services.wz_generator_service import generate_wz_document
        
        # Use the existing WZ generator but save to the specific path
        return generate_wz_document(context_data, output_path)
        
    except Exception as e:
        print(f"Error generating WZ document from template: {e}")
        return False
