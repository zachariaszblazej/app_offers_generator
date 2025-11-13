"""
WZ Editor App - Main application logic for editing existing WZ documents
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os
import json
from datetime import datetime

# Add project root to Python path  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ui.components.wz_ui_components import WzUIComponents
from src.ui.components.wz_product_table import WzProductTable
from src.ui.windows.wz_product_add_window import WzProductAddWindow
from src.ui.windows.wz_product_edit_window import WzProductEditWindow
from src.ui.windows.client_search_window import ClientSearchWindow
from src.ui.windows.supplier_search_window import SupplierSearchWindow
from src.data.database_service import get_wz_context_from_db
from src.services.wz_editor_service import update_wz_document
from src.services.wz_editor_service import update_wz_document
from src.data.database_service import get_wz_context_from_db
from src.utils.config import WZ_BACKGROUND_IMAGE
from src.utils.os_utils import open_document


class WzEditorApp:
    """WZ editor app - modified version for editing existing WZ documents"""
    
    def __init__(self, parent_frame, nav_manager, wz_path):
        self.parent_frame = parent_frame
        self.nav_manager = nav_manager
        self.wz_path = wz_path
        # Use content_container instead of wz_container
        self.window = parent_frame.content_container
        
        # Initialize components
        self.setup_ui()
        
        # Initialize calculation variables
        self.count = 0
        
        # Load existing WZ data
        self.load_wz_data()
    
    def setup_ui(self):
        """Setup all UI components within the parent frame"""
        # Set minimum height for content container to ensure scrolling works
        self.window.configure(height=1200)  # Set explicit height for scrolling
        
        # Set background
        try:
            bg = None
            try:
                bg = PhotoImage(file=WZ_BACKGROUND_IMAGE)
            except Exception as te:
                print(f"Primary PhotoImage load failed for WZ editor background: {te}. Trying Pillow fallback.")
                try:
                    from PIL import Image, ImageTk
                    pil_img = Image.open(WZ_BACKGROUND_IMAGE)
                    bg = ImageTk.PhotoImage(pil_img)
                except Exception as pe:
                    raise pe
            label_BG = Label(self.window, image=bg)
            label_BG.place(x=0, y=0)
            label_BG.image = bg
        except Exception as e:
            print(f"Could not load WZ editor background image: {e}")
            self.window.configure(bg='#f5f5f5')
        
        # Initialize UI components
        # Create product table with edit and delete callbacks
        self.product_table = WzProductTable(self.window, self.parent_frame, self.edit_product, self.on_product_deleted)
        self.ui = WzUIComponents(self.window, self.product_table, show_generate_button=False)  # Hide generate button in editor
        self.product_add = WzProductAddWindow(self.window, self.insert_product)
        self.product_edit = WzProductEditWindow(self.window, self.update_product)
        
        # Initialize search windows
        self.client_search = ClientSearchWindow(self.window, self.ui.fill_client_data)
        self.supplier_search = SupplierSearchWindow(self.window, self.ui.fill_supplier_data)
        
        # Create UI sections using existing methods
        self.ui.create_upper_section(show_wz_number=True)  # Show WZ number in editor
        self.ui.create_wz_section()  # WZ-specific supplier/client section

        # Create action buttons from WZ UI components (add / move / generate)
        self.ui.create_action_buttons()

        # Rewire buttons (override generate to update, hide if not needed)
        if hasattr(self.ui, 'generate_btn'):
            # Hide generate (we use save/update button at bottom)
            try:
                self.ui.generate_btn.place_forget()
            except:
                pass

        # Assign commands to product management buttons
        if hasattr(self.ui, 'add_product_btn'):
            self.ui.add_product_btn.config(command=self.product_add.show)
        if hasattr(self.ui, 'move_up_btn'):
            self.ui.move_up_btn.config(command=self.move_product_up)
        if hasattr(self.ui, 'move_down_btn'):
            self.ui.move_down_btn.config(command=self.move_product_down)

        # Create supplier search button only (client search removed per requirements)
        supplier_search_btn = Button(self.window, text="Szukaj dostawcy", font=("Arial", 10),
                                     command=self.supplier_search.open_supplier_search)
        supplier_search_btn.place(x=300, y=360)

        # Expose for potential external use
        self.ui.supplier_search_btn = supplier_search_btn

        # Note: Save button moved to top bar in WzEditorFrame; no bottom button here
    def load_wz_data(self):
        """Load data from existing WZ context stored in database"""
        try:
            # Get WZ context from database
            context_data = get_wz_context_from_db(self.wz_path)
            
            if not context_data:
                tkinter.messagebox.showwarning("Brak danych w bazie", 
                    f"Nie znaleziono danych w bazie dla WZ: {os.path.basename(self.wz_path)}" +
                    "Ta WZka została prawdopodobnie utworzona poza aplikacją.")

                # Still set editor mode for consistent UI
                self.ui.set_editor_mode()
                return
                
            # Load data into UI components
            self.populate_ui_from_context(context_data)
            
            # Set editor mode (read-only for certain fields)
            self.ui.set_editor_mode()
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", 
                f"Nie udało się wczytać danych WZ:\n{e}")
    
    def populate_ui_from_context(self, context_data):
        """Populate UI fields with data from context"""
        try:
            # Load and preserve original WZ number
            if 'wz_number' in context_data:
                self.ui.wz_number = context_data['wz_number']
                print(f"Preserved WZ number: {self.ui.wz_number}")
            else:
                # For older WZ without wz_number, try to extract from filename
                filename = os.path.basename(self.wz_path)
                # Try to extract number from filename like "123_WZ_2025_KLIENT.docx"
                import re
                match = re.match(r'(\d+_WZ_\d+_[A-Z]+)', filename.replace('.docx', ''))
                if match:
                    self.ui.wz_number = match.group(1)
                    print(f"Extracted WZ number from filename: {self.ui.wz_number}")
                else:
                    print("Warning: Could not determine WZ number")
            
            # Update WZ number display field if it exists
            if self.ui.wz_number and 'wz_number_display' in self.ui.entries:
                self.ui.entries['wz_number_display'].config(state='normal')
                self.ui.entries['wz_number_display'].delete(0, END)
                self.ui.entries['wz_number_display'].insert(0, self.ui.wz_number)
                self.ui.entries['wz_number_display'].config(state='readonly')
            
            # Load client data
            client_fields = ['client_name', 'client_address_1', 'client_address_2', 'client_phone_number']
            for field in client_fields:
                if field in context_data and field in self.ui.entries:
                    widget = self.ui.entries[field]
                    value = context_data.get(field, '')
                    # Convert literal \n to real newlines for display in Text
                    if hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Text':
                        widget.delete('1.0', END)
                        widget.insert('1.0', str(value or '').replace('\\n', '\n'))
                    else:
                        widget.delete(0, END)
                        widget.insert(0, value)
            
            # Load client NIP separately (needs temporary unlock)
            if 'client_nip' in context_data and 'client_nip' in self.ui.entries:
                self.ui.entries['client_nip'].config(state='normal')
                self.ui.entries['client_nip'].delete(0, END)
                raw_client_nip = context_data.get('client_nip', '')
                digits = ''.join(ch for ch in str(raw_client_nip) if ch.isdigit())
                if len(digits) == 10:
                    formatted_client_nip = f"{digits[0:3]}-{digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
                else:
                    formatted_client_nip = raw_client_nip
                self.ui.entries['client_nip'].insert(0, formatted_client_nip)
                self.ui.entries['client_nip'].config(state='readonly')
            
            # Load supplier data
            supplier_fields = ['supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_phone_number']
            for field in supplier_fields:
                if field in context_data and field in self.ui.entries:
                    widget = self.ui.entries[field]
                    value = context_data.get(field, '')
                    if hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Text':
                        widget.delete('1.0', END)
                        widget.insert('1.0', str(value or '').replace('\\n', '\n'))
                    else:
                        widget.delete(0, END)
                        widget.insert(0, value)
            
            # Load supplier NIP separately (needs temporary unlock)
            if 'supplier_nip' in context_data and 'supplier_nip' in self.ui.entries:
                self.ui.entries['supplier_nip'].config(state='normal')
                self.ui.entries['supplier_nip'].delete(0, END)
                raw_supplier_nip = context_data.get('supplier_nip', '')
                digits = ''.join(ch for ch in str(raw_supplier_nip) if ch.isdigit())
                if len(digits) == 10:
                    formatted_supplier_nip = f"{digits[0:3]}-{digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
                else:
                    formatted_supplier_nip = raw_supplier_nip
                self.ui.entries['supplier_nip'].insert(0, formatted_supplier_nip)
                self.ui.entries['supplier_nip'].config(state='readonly')
            
            # Load town
            if 'town' in context_data and 'town' in self.ui.entries:
                self.ui.entries['town'].delete(0, END)
                self.ui.entries['town'].insert(0, context_data.get('town', ''))

            # Load language selection
            if 'language' in context_data and 'language' in self.ui.entries:
                language_value = context_data.get('language', 'PL')
                self.ui.entries['language'].set(language_value)
                print(f"Loaded language: {language_value}")

            # Load company header fields from context (editor mode) overriding settings
            company_keys = ['address_1', 'address_2', 'nip', 'regon', 'email', 'phone_number', 'bank_name', 'account_number']
            for key in company_keys:
                if key in self.ui.entries:
                    self.ui.entries[key].delete(0, END)
                    self.ui.entries[key].insert(0, context_data.get(key, ''))
            
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
            # Lock year after setting date
            try:
                parsed = datetime.strptime(self.ui.date_var.get(), "%d %m %Y")
                if hasattr(self.ui, 'lock_year'):
                    self.ui.lock_year(parsed.year)
                else:
                    self.ui.locked_year = parsed.year  # fallback
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
                    if isinstance(product, list) and len(product) >= 4:
                        # WZ product format: [lp, name, unit, quantity] (no pricing)
                        # Create tuple for input_record (expects 4 elements for WZ)
                        product_tuple = (
                            str(product[0]),    # lp
                            str(product[1]),    # name
                            str(product[2]),    # unit
                            str(product[3])     # quantity
                        )
                        
                        try:
                            self.product_table.input_record(product_tuple)
                            print(f"Added product: {product_tuple}")
                        except Exception as e:
                            print(f"Error adding product {product}: {e}")
                
            # Update scroll region after all data is loaded
            self.update_scroll_region()
                
        except Exception as e:
            tkinter.messagebox.showerror("Błąd ładowania danych", 
                f"Wystąpił błąd podczas ładowania danych z kontekstu:\n{e}")
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
        # Convert dict format from WzProductAddWindow to list format expected by input_record
        if isinstance(product_data, dict):
            # WzProductAddWindow sends dict: {'name': ..., 'unit': ..., 'quantity': ...}
            # Convert to list format: [name, unit, quantity]
            product_list = [
                product_data.get('name', ''),
                product_data.get('unit', ''),
                product_data.get('quantity', '')
            ]
        else:
            # Already in list format
            product_list = product_data
            
        if self.product_table.input_record(product_list):
            return True
        return False
    
    def on_product_deleted(self):
        """Called when product is deleted via inline delete button"""
        # No calculations needed for WZ (no pricing)
        pass
    
    def move_product_up(self):
        """Move selected product up in the table"""
        if self.product_table.move_product_up():
            pass
    
    def move_product_down(self):
        """Move selected product down in the table"""
        if self.product_table.move_product_down():
            pass

    def edit_product(self, item_id):
        """Edit selected product from the table"""
        try:
            # Get product data from the table using item_id
            product_data = self.product_table.get_product_data(item_id)
            if product_data:
                self.product_edit.show(item_id, product_data)
            else:
                tkinter.messagebox.showwarning("Uwaga", "Nie można pobrać danych produktu!")
        except Exception as e:
            print(f"Error in edit_product: {e}")
            tkinter.messagebox.showerror("Błąd", f"Wystąpił błąd podczas edytowania produktu: {e}")
    
    def update_product(self, item_id, product_data):
        """Update existing product in the table"""
        self.product_table.update_product(item_id, product_data)
        return True
    
    def update_wz(self):
        """Update the existing WZ document"""
        try:
            # Get form data
            context_data = self.ui.get_context_data()
            print(f"Context data collected: {list(context_data.keys())}")  # Debug
            
            # Confirm update
            result = tkinter.messagebox.askyesno(
                "Potwierdzenie", 
                f"Czy na pewno chcesz nadpisać istniejące WZ?\n\n" +
                f"Plik: {os.path.basename(self.wz_path)}\n\n" +
                "Ta operacja nie może być cofnięta!"
            )
            
            if result:
                print(f"Updating WZ: {self.wz_path}")  # Debug
                
                # Update document using specialized service
                success = update_wz_document(context_data, self.wz_path)
                
                if success:
                    # Return to browse WZ
                    tkinter.messagebox.showinfo("Sukces", 
                        "WZ zostało pomyślnie zaktualizowane!\n\n" +
                        "Dokument Word oraz kontekst w bazie danych zostały nadpisane.")
                    # Auto-open updated document
                    try:
                        open_document(self.wz_path)
                    except Exception as _e:
                        print(f"Auto-open failed: {_e}")
                    self.nav_manager.show_frame('browse_wz')
                else:
                    tkinter.messagebox.showerror("Błąd", 
                        "Nie udało się zaktualizować WZ. Sprawdź logi w konsoli.")
                        
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", 
                f"Wystąpił błąd podczas aktualizacji WZ:\n{e}")
            print(f"Error in update_wz: {e}")  # Debug
