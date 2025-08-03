from docxtpl import DocxTemplate
import tkinter.messagebox
import datetime
import os
from config import TEMPLATE_PATH, OUTPUT_FOLDER, OFFERS_FOLDER
from database import get_next_offer_number, save_offer_to_db

def convert_date(date: datetime.datetime) -> str:
    """Convert datetime to formatted string"""
    return date.strftime("%d %B %Y")

def generate_offer_number(date: datetime.datetime, client_alias: str) -> tuple:
    """Generate offer number and file path"""
    # Auto-generate offer number
    try:
        order_number = get_next_offer_number()
        year = date.year
        
        # Format: <order_number>/OF/<year>_<client_alias>
        offer_number = f"{order_number}/OF/{year}_{client_alias}"
        
        # Create filename: <order_number>_OF_<year>_<client_alias>.docx
        filename = f"{order_number}_OF_{year}_{client_alias}.docx"
        file_path = os.path.join(OFFERS_FOLDER, filename)
        
        return offer_number, file_path, order_number
        
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
        
        # Debug: Print products to see if they're being passed
        products = context_data.get('products', [])
        print(f"Products to be included in offer: {len(products)} items")
        for i, product in enumerate(products):
            print(f"Product {i+1}: {product}")
        
        # Generate document
        doc = DocxTemplate(TEMPLATE_PATH)
        doc.render(context_data)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save to offers folder
        doc.save(file_path)
        
        # Also save to local generated_docs folder for backup
        backup_filename = f"last_generated_offer_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        backup_path = os.path.join(OUTPUT_FOLDER, backup_filename)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        doc.save(backup_path)
        
        # Save to database only if we auto-generated the number
        if order_number is not None:
            if not save_offer_to_db(order_number, file_path):
                tkinter.messagebox.showwarning("Warning", "Offer generated but failed to save to database")
        
        tkinter.messagebox.showinfo("Success", 
                                  f"Offer generated successfully!\n"
                                  f"Offer number: {offer_number}\n"
                                  f"File saved to: {file_path}")
        return True
        
    except Exception as e:
        tkinter.messagebox.showerror("Error", f"Failed to generate offer: {e}")
        return False
