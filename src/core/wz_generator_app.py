"""
Core WZ generator application logic
"""
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ui.components.wz_ui_components import WzUIComponents
from src.ui.windows.client_search_window import ClientSearchWindow
from src.ui.windows.supplier_search_window import SupplierSearchWindow
from src.ui.windows.wz_product_add_window import WzProductAddWindow
from src.ui.windows.wz_product_edit_window import WzProductEditWindow
from src.ui.components.wz_product_table import WzProductTable
from src.services.wz_generator_service import generate_wz_document
from src.data.database_service import get_next_wz_number, save_wz_to_db


class WzGeneratorApp:
    """WZ generator application embedded within a frame"""
    
    def __init__(self, parent_frame, nav_manager, template_context=None, source_frame=None):
        self.parent_frame = parent_frame
        self.nav_manager = nav_manager
        self.template_context = template_context  # Context data to use as template
        self.source_frame = source_frame  # Track where we came from ('browse_wz' or None for main menu)
        # Use content_container instead of wz_container
        self.window = parent_frame.content_container
        
        # Track if user has made any modifications after template load
        self.user_modifications_made = False
        
        # Initialize components
        self.setup_ui()
        
        # Clear client and supplier NIP fields if this is a new WZ (no template context)
        if not self.template_context:
            self.clear_client_supplier_data()
        
        # Initialize calculation variables
        self.count = 0
        
        # For WZ, we don't need to load template context
        # Reset modification flag
        self.user_modifications_made = False
    
    def setup_ui(self):
        """Setup all UI components within the parent frame"""
        # Set minimum height for content container to ensure scrolling works
        self.window.configure(height=1200)  # Set explicit height for scrolling
        
        # Set background - use WZ background
        try:
            bg = PhotoImage(file="/Users/blzc/Apka_Oferty/background_wz_1.png")
            label_BG = Label(self.window, image=bg)
            label_BG.place(x=0, y=0)
            label_BG.image = bg  # Keep a reference
        except Exception as e:
            print(f"Could not load WZ background image: {e}")
            # If background image fails, use a clean professional color
            self.window.configure(bg='#f5f5f5')
        
        # Initialize UI components (WZ version)
        # Create product table with edit and delete callbacks
        self.product_table = WzProductTable(self.window, self.parent_frame, self.edit_product, self.on_product_deleted)
        self.ui = WzUIComponents(self.window, self.product_table)
        
        # Set modification callback so UI components can notify about user changes
        self.ui.set_modification_callback(self.mark_as_modified)
        
        self.client_search = ClientSearchWindow(self.window, self.ui.fill_client_data)
        self.supplier_search = SupplierSearchWindow(self.window, self.ui.fill_supplier_data)
        self.product_add = WzProductAddWindow(self.window, self.insert_product)
        self.product_edit = WzProductEditWindow(self.window, self.update_product)
        
        # Connect search buttons to search windows
        self.ui.supplier_search_btn.config(command=self.supplier_search.open_supplier_search)
        self.ui.client_search_btn.config(command=self.client_search.open_client_search)
        self.ui.add_product_btn.config(command=self.product_add.show)
        
        # Connect move buttons to move methods
        self.ui.move_up_btn.config(command=self.move_product_up)
        self.ui.move_down_btn.config(command=self.move_product_down)
        
        if hasattr(self.ui, 'generate_btn'):
            self.ui.generate_btn.config(command=self.generate_wz)
    
    def mark_as_modified(self):
        """Mark that user has made modifications"""
        self.user_modifications_made = True
    
    def clear_client_supplier_data(self):
        """Clear client and supplier data fields"""
        # Clear supplier data
        supplier_fields = ['supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_nip']
        for field in supplier_fields:
            if field in self.ui.entries:
                self.ui.entries[field].config(state='normal')
                self.ui.entries[field].delete(0, END)
                if field == 'supplier_nip':
                    self.ui.entries[field].config(state='readonly')
        
        # Clear client data
        client_fields = ['client_name', 'client_address_1', 'client_address_2', 'client_nip']
        for field in client_fields:
            if field in self.ui.entries:
                self.ui.entries[field].config(state='normal')
                self.ui.entries[field].delete(0, END)
                if field == 'client_nip':
                    self.ui.entries[field].config(state='readonly')
    
    def insert_product(self, product_data):
        """Insert product data into table"""
        self.product_table.insert_product(product_data)
    
    def update_product(self, item_id, product_data):
        """Update product in table"""
        self.product_table.update_product(item_id, product_data)
    
    def edit_product(self, item_id):
        """Edit selected product"""
        if not item_id:
            tkinter.messagebox.showwarning("Uwaga", "Proszę wybrać produkt do edycji.")
            return
        
        # Get product data
        product_data = self.product_table.get_product_data(item_id)
        
        # Show edit window
        self.product_edit.show(item_id, product_data)
    
    def on_product_deleted(self):
        """Handle product deletion - for WZ we don't need to calculate totals"""
        pass
    
    def generate_wz(self):
        """Generate WZ document"""
        try:
            # Validate required fields
            if not self.validate_form():
                return
            
            # Get form data
            context_data = self.ui.get_all_data()
            
            # Get products data
            products_data = self.product_table.get_all_products()
            context_data['products'] = products_data
            
            # Generate WZ number in proper format
            wz_order_number = get_next_wz_number()
            date_str = context_data.get('date', '')
            client_alias = self.ui.selected_client_alias or 'KLIENT'
            
            # Extract year from date
            try:
                from datetime import datetime
                if date_str:
                    # Parse date in format "DD MM YYYY" 
                    date_parts = date_str.split()
                    if len(date_parts) == 3:
                        year = date_parts[2]
                    else:
                        year = str(datetime.now().year)
                else:
                    year = str(datetime.now().year)
            except:
                year = str(datetime.now().year)
            
            # Format WZ number: WZ_{number}_{year}_{alias}
            wz_number = f"WZ_{wz_order_number}_{year}_{client_alias}"
            context_data['wz_number'] = wz_number
            
            # Generate document
            file_path = generate_wz_document(context_data)
            
            if file_path:
                # Save to database
                success, message = save_wz_to_db(wz_order_number, file_path, context_data)
                
                if success:
                    tkinter.messagebox.showinfo("Sukces", 
                                              f"WZ zostało wygenerowane pomyślnie!\n"
                                              f"Numer WZ: {wz_number}\n"
                                              f"Plik zapisany w: {file_path}")
                    
                    # Ask if user wants to create another WZ
                    if tkinter.messagebox.askyesno("Kolejne WZ", "Czy chcesz utworzyć kolejne WZ?"):
                        # Clear form for next WZ
                        self.ui.clear_all_fields()
                        self.product_table.clear_table()
                        self.user_modifications_made = False
                    else:
                        # Return to main menu or browse WZ
                        if self.source_frame == 'browse_wz':
                            self.nav_manager.show_frame('browse_wz')
                        else:
                            self.nav_manager.show_frame('main_menu')
                else:
                    tkinter.messagebox.showerror("Błąd", f"WZ zostało wygenerowane, ale nie udało się zapisać do bazy danych:\n{message}")
            else:
                tkinter.messagebox.showerror("Błąd", "Nie udało się wygenerować pliku WZ.")
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Wystąpił błąd podczas generowania WZ:\n{e}")
            print(f"Error generating WZ: {e}")
    
    def validate_form(self):
        """Validate form data before generating WZ"""
        # Check if client is selected
        if not self.ui.get_field_value('client_name'):
            tkinter.messagebox.showerror("Błąd", "Proszę wybrać klienta.")
            return False
        
        # Check if supplier is selected
        if not self.ui.get_field_value('supplier_name'):
            tkinter.messagebox.showerror("Błąd", "Proszę wybrać dostawcę.")
            return False
        
        # Check if date is set
        if not self.ui.get_field_value('date'):
            tkinter.messagebox.showerror("Błąd", "Proszę ustawić datę.")
            return False
        
        # Check if products are added
        if len(self.product_table.get_all_products()) == 0:
            tkinter.messagebox.showerror("Błąd", "Proszę dodać przynajmniej jeden produkt.")
            return False
        
        return True

    def move_product_up(self):
        """Move selected product up in the table"""
        if self.product_table.move_product_up():
            # Mark user modifications
            self.user_modifications_made = True
            # No need to recalculate total as order change doesn't affect sums

    def move_product_down(self):
        """Move selected product down in the table"""
        if self.product_table.move_product_down():
            # Mark user modifications
            self.user_modifications_made = True
            # No need to recalculate total as order change doesn't affect sums
