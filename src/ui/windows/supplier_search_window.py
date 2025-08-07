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
        
        # Sort suppliers alphabetically by company name (index 1)
        suppliers_sorted = sorted(suppliers, key=lambda x: x[1].lower() if x[1] else "")
        
        # Create search window
        search_window = Toplevel(self.parent_window)
        search_window.title("Wybierz dostawcę")
        search_window.geometry("700x450")
        search_window.grab_set()  # Make window modal
        
        # Main container
        main_frame = Frame(search_window)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Header
        Label(main_frame, text="Wybierz dostawcę z listy:", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Sorting options
        sort_frame = Frame(main_frame)
        sort_frame.pack(fill=X, pady=(0, 10))
        
        Label(sort_frame, text="Sortowanie:", font=("Arial", 10)).pack(side=LEFT)
        
        self.sort_var = StringVar(value="name")
        sort_options = [
            ("Nazwa firmy", "name"),
            ("NIP", "nip")
        ]
        
        for text, value in sort_options:
            rb = Radiobutton(sort_frame, text=text, variable=self.sort_var, value=value,
                           command=lambda: self._update_supplier_list(suppliers, supplier_listbox))
            rb.pack(side=LEFT, padx=10)
        
        # Create listbox with scrollbar
        list_frame = Frame(main_frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        supplier_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        supplier_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=supplier_listbox.yview)
        
        # Store suppliers data and listbox for sorting
        self.current_suppliers = suppliers
        self.current_listbox = supplier_listbox
        
        # Populate listbox with sorted supplier data
        self._update_supplier_list(suppliers, supplier_listbox)
        
        # Bind double-click to select supplier
        supplier_listbox.bind('<Double-1>', lambda event: self._on_supplier_select(event, search_window, supplier_listbox, self.current_suppliers))
        
        # Add select button
        button_frame = Frame(main_frame)
        button_frame.pack(pady=10)
        
        select_button = Button(button_frame, text="Wybierz", 
                              command=lambda: self._on_supplier_select(None, search_window, supplier_listbox, self.current_suppliers))
        select_button.pack(side=LEFT, padx=5)
        
        cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)
    
    def _update_supplier_list(self, suppliers, listbox):
        """Update supplier list based on selected sorting"""
        sort_by = self.sort_var.get()
        
        # Sort suppliers based on selection
        if sort_by == "name":
            sorted_suppliers = sorted(suppliers, key=lambda x: x[1].lower() if x[1] else "")
        elif sort_by == "nip":
            sorted_suppliers = sorted(suppliers, key=lambda x: x[0] if x[0] else "")
        else:
            sorted_suppliers = suppliers
        
        # Update stored suppliers list
        self.current_suppliers = sorted_suppliers
        
        # Clear and repopulate listbox
        listbox.delete(0, END)
        for supplier in sorted_suppliers:
            nip, company_name, address1, address2, is_default = supplier
            display_text = f"{company_name} (NIP: {nip})"
            listbox.insert(END, display_text)

    def _on_supplier_select(self, event, search_window, supplier_listbox, suppliers):
        """Handle supplier selection from the listbox"""
        selection = supplier_listbox.curselection()
        if selection:
            selected_supplier = self.current_suppliers[selection[0]]
            # Pass only the first 4 fields (exclude IsDefault) to maintain compatibility
            supplier_data = selected_supplier[:4]  # nip, company_name, address1, address2
            self.supplier_fill_callback(supplier_data)
            search_window.destroy()
