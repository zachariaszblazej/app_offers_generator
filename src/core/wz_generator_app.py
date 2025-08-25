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
from src.data.database_service import get_next_wz_number, save_wz_to_db, normalize_wz_db_path
from src.utils.config import WZ_BACKGROUND_IMAGE


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
            # Auto-load default supplier like in offer creator
            self.load_default_supplier()
        
        # Initialize calculation variables
        self.count = 0
        
       # Load template data if provided
        if self.template_context:
            self.load_template_context()
            # Reset modification flag after template load
            self.user_modifications_made = False
    
    def setup_ui(self):
        """Setup all UI components within the parent frame"""
        # Set minimum height for content container to ensure scrolling works
        self.window.configure(height=1200)  # Set explicit height for scrolling
        
        # Set background - use WZ background
        try:
            bg = None
            try:
                bg = PhotoImage(file=WZ_BACKGROUND_IMAGE)
            except Exception as te:
                print(f"Primary PhotoImage load failed for WZ background: {te}. Trying Pillow fallback.")
                try:
                    from PIL import Image, ImageTk  # Pillow fallback
                    pil_img = Image.open(WZ_BACKGROUND_IMAGE)
                    bg = ImageTk.PhotoImage(pil_img)
                except Exception as pe:
                    raise pe
            label_BG = Label(self.window, image=bg)
            label_BG.place(x=0, y=0)
            label_BG.image = bg
        except Exception as e:
            print(f"Could not load WZ background image: {e}")
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


        # Create UI sections
        self.ui.create_upper_section()
        self.ui.create_wz_section()
        
        # Create buttons
        self.create_buttons()

    def create_buttons(self):
        """Create all buttons"""
        # Product management buttons
        Button(self.window, text="DODAJ POZYCJĘ", 
               font=("Arial", 12, "bold"),
               bg='#28a745', fg='black',
               padx=15, pady=8,
               command=self.product_add.show,
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
        
        # Client search button
        search_client_button = Button(self.window, text="Szukaj klienta", 
                                    font=("Arial", 10),
                                    command=self.client_search.open_client_search)
        search_client_button.place(x=900, y=360)
        
        # Supplier search button
        search_supplier_button = Button(self.window, text="Szukaj dostawcy", 
                                      font=("Arial", 10),
                                      command=self.supplier_search.open_supplier_search)
        search_supplier_button.place(x=300, y=360)
        
        # Generate offer button
        generate_offer_button = Button(self.window, text="Generuj WZ", 
                                     font=("Arial", 12, "bold"),
                                     command=self.generate_wz)
        generate_offer_button.place(x=700, y=740)
        
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

    def load_default_supplier(self):
        """Load default supplier into WZ creator (only for fresh creation)"""
        try:
            from src.data.database_service import get_default_supplier
            supplier = get_default_supplier()
            if supplier:
                # supplier tuple: (Nip, CompanyName, AddressP1, AddressP2, IsDefault)
                nip, company_name, address1, address2, _ = supplier
                # Fill fields
                if 'supplier_name' in self.ui.entries:
                    self.ui.entries['supplier_name'].delete(0, END)
                    self.ui.entries['supplier_name'].insert(0, company_name)
                if 'supplier_address_1' in self.ui.entries:
                    self.ui.entries['supplier_address_1'].delete(0, END)
                    self.ui.entries['supplier_address_1'].insert(0, address1)
                if 'supplier_address_2' in self.ui.entries:
                    self.ui.entries['supplier_address_2'].delete(0, END)
                    self.ui.entries['supplier_address_2'].insert(0, address2)
                if 'supplier_nip' in self.ui.entries:
                    self.ui.entries['supplier_nip'].config(state='normal')
                    self.ui.entries['supplier_nip'].delete(0, END)
                    self.ui.entries['supplier_nip'].insert(0, str(nip))
                    self.ui.entries['supplier_nip'].config(state='readonly')
                # Store alias substitute (company name) for potential usage
                self.ui.selected_supplier_alias = company_name
        except Exception as e:
            print(f"Could not load default supplier for WZ: {e}")
    
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

            # Gather context
            context_data = self.ui.get_all_data()
            context_data['client_alias'] = self.ui.selected_client_alias
            context_data['supplier_alias'] = self.ui.selected_supplier_alias
            context_data['products'] = self.product_table.get_all_products()

            # Determine year from date string if possible
            from datetime import datetime as _dt
            year_val = None
            date_str = context_data.get('date', '')
            if isinstance(date_str, str):
                parts = date_str.split()
                if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) == 4:
                    year_val = parts[-1]
            if year_val is None:
                year_val = str(_dt.now().year)

            # Next sequential number per year and full WZ number
            wz_order_number = get_next_wz_number(int(year_val))
            client_alias = self.ui.selected_client_alias or 'KLIENT'
            wz_number = f"WZ_{wz_order_number}_{year_val}_{client_alias}"
            context_data['wz_number'] = wz_number

            # Generate document to disk
            output_path = generate_wz_document(context_data)
            if not output_path:
                tkinter.messagebox.showerror("Błąd", "Nie udało się wygenerować pliku WZ.")
                return

            # Store relative path in DB
            rel_wz = normalize_wz_db_path(output_path)
            save_wz_to_db(wz_order_number, rel_wz, context_data)

            tkinter.messagebox.showinfo(
                "Sukces",
                f"WZ zostało wygenerowane i zapisane do: {output_path}"
            )
            if self.source_frame == 'browse_wz':
                self.nav_manager.show_frame('browse_wz')
            else:
                self.nav_manager.show_frame('main_menu')

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

    def load_template_context(self):
        """Load data from template context for creating similar WZ"""
        try:
            if self.template_context:
                # Load data into UI (without WZ number)
                success = self.ui.load_context_for_new_wz(self.template_context)
                
                if not success:
                    import tkinter.messagebox
                    tkinter.messagebox.showwarning("Błąd ładowania", 
                        "Wystąpił problem podczas ładowania danych z szablonu.")
            else:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Brak danych", 
                    "Nie znaleziono danych kontekstu dla wybranej WZ-ki.")
                    
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Wystąpił błąd podczas ładowania danych: {e}")