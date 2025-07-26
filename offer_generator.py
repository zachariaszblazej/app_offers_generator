from docxtpl import DocxTemplate
import tkinter.messagebox
import datetime
import os
from config import TEMPLATE_PATH, OUTPUT_FOLDER

def convert_date(date: datetime.datetime) -> str:
    """Convert datetime to formatted string"""
    return date.strftime("%d %B %Y")

def generate_offer_document(context_data):
    """Generate offer document using the provided context data"""
    try:
        doc = DocxTemplate(TEMPLATE_PATH)
        doc.render(context_data)
        output_path = os.path.join(OUTPUT_FOLDER, 'last_generated_offer.docx')
        doc.save(output_path)
        tkinter.messagebox.showinfo("Success", "Offer generated successfully!")
        return True
    except Exception as e:
        tkinter.messagebox.showerror("Error", f"Failed to generate offer: {e}")
        return False
