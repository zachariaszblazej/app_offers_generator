"""
Supplier search window for selecting suppliers from database
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import get_suppliers_from_db


class SupplierSearchWindow:
    """Handles supplier search and selection functionality"""
    
    def __init__(self, parent_window, supplier_fill_callback):
        self.parent_window = parent_window
        self.supplier_fill_callback = supplier_fill_callback
    
    def open_supplier_search(self):
        """Open supplier search window"""
        suppliers = get_suppliers_from_db()
        if not suppliers:
            tkinter.messagebox.showinfo("No Suppliers", "No suppliers found in database.")
            return
        
        # Create search window
        search_window = Toplevel(self.parent_window)
        search_window.title("Wybierz dostawcę")
        search_window.geometry("600x400")
        search_window.grab_set()  # Make window modal
        
        # Search label
        Label(search_window, text="Wybierz dostawcę z listy:", font=("Arial", 12)).pack(pady=10)
        
        # Create listbox with scrollbar
        frame = Frame(search_window)
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = Scrollbar(frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        supplier_listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        supplier_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=supplier_listbox.yview)
        
        # Populate listbox with supplier data
        for supplier in suppliers:
            nip, company_name, address1, address2 = supplier
            display_text = f"{company_name} (NIP: {nip})"
            supplier_listbox.insert(END, display_text)
        
        # Bind double-click to select supplier
        supplier_listbox.bind('<Double-1>', lambda event: self._on_supplier_select(event, search_window, supplier_listbox, suppliers))
        
        # Add select button
        button_frame = Frame(search_window)
        button_frame.pack(pady=10)
        
        select_button = Button(button_frame, text="Wybierz", 
                              command=lambda: self._on_supplier_select(None, search_window, supplier_listbox, suppliers))
        select_button.pack(side=LEFT, padx=5)
        
        cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)

    def _on_supplier_select(self, event, search_window, supplier_listbox, suppliers):
        """Handle supplier selection from the listbox"""
        selection = supplier_listbox.curselection()
        if selection:
            selected_supplier = suppliers[selection[0]]
            self.supplier_fill_callback(selected_supplier)
            search_window.destroy()
