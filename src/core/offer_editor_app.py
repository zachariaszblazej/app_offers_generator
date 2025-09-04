"""
Offer editor application logic - modified version of OfferGeneratorApp for editing existing offers
"""
from tkinter import *
import tkinter.messagebox
import sys
import os
import json
import re
from docx import Document
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ui.components.ui_components import UIComponents
from src.ui.windows.product_add_window import ProductAddWindow
from src.ui.windows.product_edit_window import ProductEditWindow
from src.ui.windows.supplier_search_window import SupplierSearchWindow
from src.ui.components.product_table import ProductTable
from src.services.offer_editor_service import update_offer_document
from src.data.database_service import get_offer_context_from_db
from src.utils.config import BACKGROUND_IMAGE
from src.utils.os_utils import open_document


class OfferEditorApp:
    """Offer editor app - modified version for editing existing offers"""
    
    def __init__(self, parent_frame, nav_manager, offer_path):
        self.parent_frame = parent_frame
        self.nav_manager = nav_manager
        self.offer_path = offer_path
        # Use content_container instead of offer_container
        self.window = parent_frame.content_container
        
        # Initialize components
        self.setup_ui()
        
        # Initialize calculation variables
        self.count = 0
        
        # Load existing offer data
        self.load_offer_data()
    
    def setup_ui(self):
        """Setup all UI components within the parent frame"""
        # Set minimum height for content container to ensure scrolling works
        self.window.configure(height=1200)  # Set explicit height for scrolling
        
        # Set background
        try:
            bg = PhotoImage(file=BACKGROUND_IMAGE)
            label_BG = Label(self.window, image=bg)
            label_BG.place(x=0, y=0)
            label_BG.image = bg  # Keep a reference
        except Exception as e:
            print(f"Could not load background image: {e}")
            # If background image fails, use a clean professional color
            self.window.configure(bg='#f5f5f5')
        
        # Initialize UI components
        # Create product table with edit and delete callbacks
        self.product_table = ProductTable(self.window, self.parent_frame, self.edit_product, self.on_product_deleted)
        self.ui = UIComponents(self.window, self.product_table)
        self.product_add = ProductAddWindow(self.window, self.insert_product)
        self.product_edit = ProductEditWindow(self.window, self.update_product)
        
        # Create supplier search window (for editing existing offers)
        self.supplier_search = SupplierSearchWindow(self.window, self.ui.fill_supplier_data)
        
        # Create UI sections
        self.ui.create_upper_section(show_offer_number=True)  # Show offer number in editor
        self.ui.create_offer_section()
        self.ui.create_offer_details_section()
        self.ui.create_totals_section()
        
        # Create buttons (modified for editor)
        self.create_buttons()
    
    def create_buttons(self):
        """Create all buttons for editor mode"""
        # Supplier search button (like in creator)
        search_supplier_button = Button(self.window, text="Szukaj dostawcy", 
                                      font=("Arial", 10),
                                      fg='black',
                                      command=self.supplier_search.open_supplier_search,
                                      cursor='hand2')
        search_supplier_button.place(x=300, y=360)
        
        # Product management buttons
        Button(self.window, text="DODAJ POZYCJĘ", 
               font=("Arial", 12, "bold"),
               bg='#28a745', fg='black',
               padx=15, pady=8,
               command=self.product_add.open_product_add_window,
               cursor='hand2').place(x=50, y=740)
        
        # Product movement buttons
        Button(self.window, text="▲", anchor='center',
               font=("Arial", 16, "bold"),
               bg='#6c757d', fg='black',
               width=3, height=1,
               command=self.move_product_up,
               cursor='hand2').place(x=250, y=740)
        
        Button(self.window, text="▼", anchor='center',
               font=("Arial", 16, "bold"),
               bg='#6c757d', fg='black',
               width=3, height=1,
               command=self.move_product_down,
               cursor='hand2').place(x=320, y=740)
        
    # Save button moved to header in OfferEditorFrame
    
    def load_offer_data(self):
        """Load data from existing offer context stored in database"""
        try:
            # Get offer context from database
            context_data = get_offer_context_from_db(self.offer_path)
            
            if not context_data:
                tkinter.messagebox.showwarning("Brak danych w bazie", 
                    f"Nie znaleziono danych w bazie dla oferty {os.path.basename(self.offer_path)}" +
                    "Ta oferta została prawdopodobnie utworzona poza aplikacją.")
                
                # Still set editor mode for consistent UI
                self.ui.set_editor_mode()
                return
                
            # Load data into UI components
            self.populate_ui_from_context(context_data)
            
            # Set editor mode (read-only for certain fields)
            self.ui.set_editor_mode()
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", 
                f"Nie udało się wczytać danych oferty:\\n{e}")
    
    def populate_ui_from_context(self, context_data):
        """Populate UI fields with data from context"""
        try:
            # Load and preserve original offer number
            if 'offer_number' in context_data:
                self.ui.offer_number = context_data['offer_number']
                print(f"Preserved offer number: {self.ui.offer_number}")
            else:
                # For older offers without offer_number, try to extract from filename
                filename = os.path.basename(self.offer_path)
                # Try to extract number from filename like "289_OF_2025_LUCZ.docx"
                import re
                match = re.match(r'(\d+_OF_\d+_[A-Z]+)', filename.replace('.docx', ''))
                if match:
                    self.ui.offer_number = match.group(1)
                    print(f"Extracted offer number from filename: {self.ui.offer_number}")
                else:
                    print("Warning: Could not determine offer number")
            
            # Update offer number display field if it exists
            if self.ui.offer_number and 'offer_number_display' in self.ui.entries:
                self.ui.entries['offer_number_display'].config(state='normal')
                self.ui.entries['offer_number_display'].delete(0, END)
                self.ui.entries['offer_number_display'].insert(0, self.ui.offer_number)
                self.ui.entries['offer_number_display'].config(state='readonly')
            
            # Load client data
            client_fields = ['client_name', 'client_address_1', 'client_address_2', 'client_nip']
            for field in client_fields:
                if field in context_data and field in self.ui.entries:
                    # Handle readonly NIP field
                    if field == 'client_nip':
                        self.ui.entries[field].config(state='normal')
                        self.ui.entries[field].delete(0, END)
                        self.ui.entries[field].insert(0, context_data.get(field, ''))
                        self.ui.entries[field].config(state='readonly')
                    else:
                        self.ui.entries[field].delete(0, END)
                        self.ui.entries[field].insert(0, context_data.get(field, ''))
            
            # Load supplier data
            supplier_fields = ['supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_nip']
            for field in supplier_fields:
                if field in context_data and field in self.ui.entries:
                    # Handle readonly NIP field
                    if field == 'supplier_nip':
                        self.ui.entries[field].config(state='normal')
                        self.ui.entries[field].delete(0, END)
                        self.ui.entries[field].insert(0, context_data.get(field, ''))
                        self.ui.entries[field].config(state='readonly')
                    else:
                        self.ui.entries[field].delete(0, END)
                        self.ui.entries[field].insert(0, context_data.get(field, ''))
            
            # Load offer details
            offer_fields = ['termin_realizacji', 'termin_platnosci', 'warunki_dostawy', 
                          'waznosc_oferty', 'gwarancja', 'cena']
            for field in offer_fields:
                if field in context_data and field in self.ui.entries:
                    self.ui.entries[field].delete(0, END)
                    self.ui.entries[field].insert(0, context_data.get(field, ''))
            
            # Load town
            if 'town' in context_data and 'town' in self.ui.entries:
                self.ui.entries['town'].delete(0, END)
                self.ui.entries['town'].insert(0, context_data.get('town', ''))

            # Load company (supplier self) header data from context instead of settings (editor mode requirement)
            company_map = {
                'address1': 'address_1',
                'address2': 'address_2',
                'nip': 'nip',
                'regon': 'regon',
                'email': 'email',
                'phone': 'phone_number',
                'bank_name': 'bank_name',
                'account_number': 'account_number',
            }
            for entry_key, ctx_key in company_map.items():
                if entry_key in self.ui.entries:
                    self.ui.entries[entry_key].delete(0, END)
                    self.ui.entries[entry_key].insert(0, context_data.get(ctx_key, ''))
            
            # Load notes (Text widget, not Entry)
            if 'uwagi' in context_data and 'uwagi' in self.ui.entries:
                self.ui.entries['uwagi'].delete(1.0, END)
                self.ui.entries['uwagi'].insert(1.0, context_data.get('uwagi', ''))
            
            # Load date
            if 'date' in context_data:
                try:
                    date_value = context_data['date']
                    if isinstance(date_value, str):
                        # Try to parse the date and convert to expected format
                        try:
                            # Try parsing date with full month name format (from database)
                            parsed_date = datetime.strptime(date_value, "%d %B %Y")
                            # Convert to the format expected by the application
                            formatted_date = parsed_date.strftime("%d %m %Y")
                            self.ui.date_var.set(formatted_date)
                            print(f"Date converted from '{date_value}' to '{formatted_date}'")
                        except ValueError:
                            # If parsing fails, try with numeric format
                            try:
                                parsed_date = datetime.strptime(date_value, "%d %m %Y")
                                self.ui.date_var.set(date_value)
                                print(f"Date kept as '{date_value}'")
                            except ValueError:
                                print(f"Could not parse date '{date_value}', keeping as is")
                                self.ui.date_var.set(date_value)
                    else:
                        # If date is not string, convert to string
                        if hasattr(date_value, 'strftime'):
                            formatted_date = date_value.strftime("%d %m %Y")
                            self.ui.date_var.set(formatted_date)
                except Exception as e:
                    print(f"Error setting date: {e}")
            # After date set, lock year for editor (prevent changing year)
            try:
                parsed = datetime.strptime(self.ui.date_var.get(), "%d %m %Y")
                self.ui.lock_year(parsed.year)
            except Exception:
                pass
            
            # Load products data
            if 'products' in context_data:
                products = context_data.get('products', [])
                # Clear existing products - remove all items from tree
                if self.product_table.tree:
                    for item in self.product_table.tree.get_children():
                        self.product_table.tree.delete(item)
                
                # Add products from context
                for product in products:
                    if isinstance(product, list) and len(product) >= 5:
                        # product format: [pid, pname, unit, qty, unit_price, total]
                        # Convert prices from Polish format (comma) to English format (dot)
                        unit_price = str(product[4]).replace(',', '.')
                        
                        # Create tuple for input_record (expects 5 elements)
                        product_tuple = (
                            str(product[0]),    # pid
                            str(product[1]),    # pname
                            str(product[2]),    # unit
                            str(product[3]),    # qty
                            unit_price          # unit_price (converted to dot format)
                        )
                        
                        try:
                            self.product_table.input_record(product_tuple)
                            print(f"Added product: {product_tuple}")
                        except Exception as e:
                            print(f"Error adding product {product}: {e}")
                
                # Recalculate totals
                self.calc_total()
                
            # Update scroll region after all data is loaded
            self.update_scroll_region()
                
        except Exception as e:
            tkinter.messagebox.showerror("Błąd ładowania danych", 
                f"Wystąpił błąd podczas ładowania danych z kontekstu:\\n{e}")
            print(f"Error loading context data: {e}")  # For debugging
    
    def update_scroll_region(self):
        """Update scroll region if parent frame has scrolling capability"""
        try:
            if hasattr(self.parent_frame, 'update_scroll_region'):
                self.parent_frame.update_scroll_region()
        except Exception as e:
            print(f"Could not update scroll region: {e}")
    
    def insert_product(self, product_data):
        """Insert a new product into the table"""
        if self.product_table.input_record(product_data):
            # Automatically recalculate total
            self.calc_total()
            return True
        return False
    
    def on_product_deleted(self):
        """Called when product is deleted via inline delete button"""
        # Automatically recalculate total after deletion
        self.calc_total()
    
    def move_product_up(self):
        """Move selected product up in the table"""
        if self.product_table.move_product_up():
            # No need to recalculate total as order change doesn't affect sums
            pass
    
    def move_product_down(self):
        """Move selected product down in the table"""
        if self.product_table.move_product_down():
            # No need to recalculate total as order change doesn't affect sums
            pass

    def edit_product(self, product_data=None):
        """Edit selected product from the table"""
        if product_data:
            # New system: called from EDIT column click with product data
            self.product_edit.open_product_edit_window(product_data)
        else:
            # Legacy system: get selected product (fallback)
            selected_product = self.product_table.get_selected_product()
            if selected_product:
                self.product_edit.open_product_edit_window(selected_product)
            else:
                tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do edycji!")
    
    def update_product(self, item_id, product_data):
        """Update existing product in the table"""
        if self.product_table.update_record(item_id, product_data):
            # Automatically recalculate total after update
            self.calc_total()
            return True
        return False
    
    def calc_total(self):
        """Calculate and display totals"""
        # Calculate totals from product table
        total = self.product_table.calculate_totals()
        
        # Update the suma field using the new method
        self.ui.update_suma(total)
    
    def update_offer(self):
        """Update the existing offer document"""
        try:
            # Get form data
            context_data = self.ui.get_context_data()
            print(f"Context data collected: {list(context_data.keys())}")  # Debug
            
            # Confirm update
            result = tkinter.messagebox.askyesno(
                "Potwierdzenie", 
                f"Czy na pewno chcesz nadpisać istniejącą ofertę?\\n\\n" +
                f"Plik: {os.path.basename(self.offer_path)}\\n\\n" +
                "Ta operacja nie może być cofnięta!"
            )
            
            if result:
                print(f"Updating offer: {self.offer_path}")  # Debug
                
                # Update document using specialized service
                success = update_offer_document(context_data, self.offer_path)
                
                if success:
                    # Return to browse offers
                    tkinter.messagebox.showinfo("Sukces", 
                        "Oferta została pomyślnie zaktualizowana!\\n\\n" +
                        "Dokument Word oraz kontekst w bazie danych zostały nadpisane.")
                    # Auto-open updated document
                    try:
                        open_document(self.offer_path)
                    except Exception as _e:
                        print(f"Auto-open failed: {_e}")
                    self.nav_manager.show_frame('browse_offers')
                else:
                    tkinter.messagebox.showerror("Błąd", 
                        "Nie udało się zaktualizować oferty. Sprawdź logi w konsoli.")
                        
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", 
                f"Wystąpił błąd podczas aktualizacji oferty:\\n{e}")
            print(f"Error in update_offer: {e}")  # Debug
