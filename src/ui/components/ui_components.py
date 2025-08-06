"""
Main UI components for the offer creation interface
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
from datetime import datetime
from tkcalendar import DateEntry, Calendar
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.settings import settings_manager


def format_nip(nip_value):
    """Format NIP to XXX-XXX-XX-XX format"""
    if not nip_value:
        return ""
    
    # Remove any existing formatting (hyphens, spaces)
    clean_nip = ''.join(c for c in str(nip_value) if c.isdigit())
    
    # Check if we have exactly 10 digits
    if len(clean_nip) == 10:
        return f"{clean_nip[:3]}-{clean_nip[3:6]}-{clean_nip[6:8]}-{clean_nip[8:10]}"
    else:
        # Return original value if it's not a valid 10-digit NIP
        return str(nip_value)


class UIComponents:
    """Handles UI component creation and management"""
    
    def __init__(self, window, product_table=None):
        self.window = window
        self.entries = {}
        # Load company data from settings instead of config
        self.text_data = settings_manager.get_all_company_data_settings()
        self.offer_details_data = settings_manager.get_all_offer_details_settings()
        self.selected_client_alias = None  # Store selected client alias
        self.date_var = StringVar(value=datetime.now().strftime("%d %m %Y"))
        self.suma_var = StringVar(value="0")  # Add StringVar for suma field
        self.product_table = product_table  # Reference to product table
        self.offer_number = None  # Store original offer number for editing
        self.modification_callback = None  # Callback for tracking modifications
    
    def set_modification_callback(self, callback):
        """Set callback to be called when user modifies form fields"""
        self.modification_callback = callback
    
    def _on_field_modified(self, *args):
        """Called when any form field is modified"""
        if self.modification_callback:
            self.modification_callback()
    
    def refresh_company_data(self):
        """Refresh company data from settings"""
        self.text_data = settings_manager.get_all_company_data_settings()
        self.offer_details_data = settings_manager.get_all_offer_details_settings()
        # Update existing fields if they exist
        if hasattr(self, 'entries'):
            company_fields = ['town', 'address1', 'address2', 'nip', 'regon', 'email', 'phone', 'bank_name', 'account_number']
            for field in company_fields:
                if field in self.entries:
                    self.entries[field].delete(0, END)
                    # Map field names to data keys
                    data_key = 'address_1' if field == 'address1' else 'address_2' if field == 'address2' else 'phone_number' if field == 'phone' else field
                    value = self.text_data.get(data_key, '')
                    self.entries[field].insert(0, value)
            
            # Update offer details fields
            offer_fields = ['termin_realizacji', 'termin_platnosci', 'warunki_dostawy', 'waznosc_oferty', 'gwarancja', 'cena']
            for field in offer_fields:
                if field in self.entries:
                    self.entries[field].delete(0, END)
                    value = self.offer_details_data.get(field, '')
                    self.entries[field].insert(0, value)
    
    def create_upper_section(self, show_offer_number=False):
        """Create the upper section of the form"""
        # Town entry
        self.entries['town'] = Entry(self.window, width=10)
        self.entries['town'].place(x=640, y=90)
        self.entries['town'].insert(0, self.text_data['town'])

        # Date entry with custom popup solution
        self.entries['date'] = Entry(self.window, width=15, textvariable=self.date_var, state='readonly')
        self.entries['date'].place(x=740, y=90)
        
        # Date picker button
        date_btn = Button(self.window, text="📅", width=2, command=self.open_date_picker)
        date_btn.place(x=870, y=90)

        # Offer number field (only in editor mode) - positioned between supplier and client data
        if show_offer_number:
            self.entries['offer_number_display'] = Entry(self.window, width=20, state='readonly', 
                                                       font=("Arial", 12, "bold"), justify='center',
                                                       bg='#f8f9fa', relief='flat')
            self.entries['offer_number_display'].place(x=400, y=200)

        # Company info entries
        address1_value = StringVar(self.window, value=self.text_data['address_1'])
        self.entries['address1'] = Entry(self.window, width=17, textvariable=address1_value)
        self.entries['address1'].place(x=110, y=118)

        address2_value = StringVar(self.window, value=self.text_data['address_2'])
        self.entries['address2'] = Entry(self.window, width=17, textvariable=address2_value)
        self.entries['address2'].place(x=110, y=148)

        nip_value = StringVar(self.window, value=self.text_data['nip'])
        self.entries['nip'] = Entry(self.window, width=15, textvariable=nip_value)
        self.entries['nip'].place(x=300, y=118)

        regon_value = StringVar(self.window, value=self.text_data['regon'])
        self.entries['regon'] = Entry(self.window, width=15, textvariable=regon_value)
        self.entries['regon'].place(x=320, y=148)

        email_value = StringVar(self.window, value=self.text_data['email'])
        self.entries['email'] = Entry(self.window, width=20, textvariable=email_value)
        self.entries['email'].place(x=485, y=118)

        phone_value = StringVar(self.window, value=self.text_data['phone_number'])
        self.entries['phone'] = Entry(self.window, width=15, textvariable=phone_value)
        self.entries['phone'].place(x=485, y=148)

        bank_name_value = StringVar(self.window, value=self.text_data['bank_name'])
        self.entries['bank_name'] = Entry(self.window, width=15, textvariable=bank_name_value)
        self.entries['bank_name'].place(x=715, y=118)

        account_number_value = StringVar(self.window, value=self.text_data['account_number'])
        self.entries['account_number'] = Entry(self.window, width=25, textvariable=account_number_value)
        self.entries['account_number'].place(x=675, y=148)
    
    def create_offer_section(self):
        """Create the offer/supplier/client section"""

        # Supplier entries
        self.entries['supplier_name'] = Entry(self.window, width=25)
        self.entries['supplier_name'].place(x=60, y=270)
        self.entries['supplier_name'].bind('<KeyRelease>', self._on_field_modified)

        self.entries['supplier_address_1'] = Entry(self.window, width=25)
        self.entries['supplier_address_1'].place(x=60, y=300)
        self.entries['supplier_address_1'].bind('<KeyRelease>', self._on_field_modified)

        self.entries['supplier_address_2'] = Entry(self.window, width=25)
        self.entries['supplier_address_2'].place(x=60, y=330)
        self.entries['supplier_address_2'].bind('<KeyRelease>', self._on_field_modified)

        self.entries['supplier_nip'] = Entry(self.window, width=25, state='readonly', bg='#f0f0f0')
        self.entries['supplier_nip'].place(x=60, y=360)

        # Client entries
        self.entries['client_name'] = Entry(self.window, width=25)
        self.entries['client_name'].place(x=660, y=270)
        self.entries['client_name'].bind('<KeyRelease>', self._on_field_modified)

        self.entries['client_address_1'] = Entry(self.window, width=25)
        self.entries['client_address_1'].place(x=660, y=300)
        self.entries['client_address_1'].bind('<KeyRelease>', self._on_field_modified)

        self.entries['client_address_2'] = Entry(self.window, width=25)
        self.entries['client_address_2'].place(x=660, y=330)
        self.entries['client_address_2'].bind('<KeyRelease>', self._on_field_modified)

        self.entries['client_nip'] = Entry(self.window, width=25, state='readonly', bg='#f0f0f0')
        self.entries['client_nip'].place(x=660, y=360)
    
    def create_offer_details_section(self):
        """Create additional offer details section under EDYTUJ PRODUKT button"""
        self.entries['termin_realizacji'] = Entry(self.window, width=20)
        self.entries['termin_realizacji'].place(x=260, y=810)
        self.entries['termin_realizacji'].insert(0, self.offer_details_data.get('termin_realizacji', 'p1'))
        self.entries['termin_realizacji'].bind('<KeyRelease>', self._on_field_modified)
        
        self.entries['termin_platnosci'] = Entry(self.window, width=20)
        self.entries['termin_platnosci'].place(x=260, y=840)
        self.entries['termin_platnosci'].insert(0, self.offer_details_data.get('termin_platnosci', 'p1'))
        self.entries['termin_platnosci'].bind('<KeyRelease>', self._on_field_modified)
        
        self.entries['warunki_dostawy'] = Entry(self.window, width=20)
        self.entries['warunki_dostawy'].place(x=260, y=870)
        self.entries['warunki_dostawy'].insert(0, self.offer_details_data.get('warunki_dostawy', 'p1'))
        
        self.entries['waznosc_oferty'] = Entry(self.window, width=20)
        self.entries['waznosc_oferty'].place(x=260, y=900)
        self.entries['waznosc_oferty'].insert(0, self.offer_details_data.get('waznosc_oferty', 'p1'))
        
        self.entries['gwarancja'] = Entry(self.window, width=20)
        self.entries['gwarancja'].place(x=260, y=930)
        self.entries['gwarancja'].insert(0, self.offer_details_data.get('gwarancja', 'p1'))
        
        self.entries['cena'] = Entry(self.window, width=20)
        self.entries['cena'].place(x=260, y=960)
        self.entries['cena'].insert(0, self.offer_details_data.get('cena', 'p1'))
        
        # Multi-line text field for notes (no default value)
        self.entries['uwagi'] = Text(self.window, width=25, height=3)
        self.entries['uwagi'].place(x=260, y=990)
        self.entries['uwagi'].bind('<KeyRelease>', self._on_field_modified)
    
    def create_totals_section(self):
        """Create the totals section"""
        Label(self.window, text='SUMA', font="times 14").place(x=750, y=740)
        self.entries['suma'] = Entry(self.window, width=10, font=('Arial', 16), state='readonly', textvariable=self.suma_var)
        self.entries['suma'].place(x=850, y=740)
    
    def update_suma(self, value):
        """Update the suma field value with comma as decimal separator"""
        formatted_value = f"{float(value):.2f}".replace('.', ',')
        self.suma_var.set(formatted_value)
    
    def clear_suma(self):
        """Clear the suma field"""
        self.suma_var.set("0,00")

    def fill_client_data(self, client_data):
        """Fill client entry fields with selected client data"""
        nip, company_name, address1, address2, alias = client_data
        
        # Store the alias for offer number generation
        self.selected_client_alias = alias
        
        # Clear existing data
        self.entries['client_name'].delete(0, END)
        self.entries['client_address_1'].delete(0, END)
        self.entries['client_address_2'].delete(0, END)
        
        # Clear NIP field (temporarily enable it)
        self.entries['client_nip'].config(state='normal')
        self.entries['client_nip'].delete(0, END)
        
        # Fill with selected client data
        self.entries['client_name'].insert(0, company_name)
        self.entries['client_address_1'].insert(0, address1)
        self.entries['client_address_2'].insert(0, address2)
        self.entries['client_nip'].insert(0, str(nip))
        
        # Set NIP field back to readonly
        self.entries['client_nip'].config(state='readonly')
    
    def fill_supplier_data(self, supplier_data):
        """Fill supplier entry fields with selected supplier data"""
        nip, company_name, address1, address2 = supplier_data
        
        # Clear existing data
        self.entries['supplier_name'].delete(0, END)
        self.entries['supplier_address_1'].delete(0, END)
        self.entries['supplier_address_2'].delete(0, END)
        
        # Clear NIP field (temporarily enable it)
        self.entries['supplier_nip'].config(state='normal')
        self.entries['supplier_nip'].delete(0, END)
        
        # Fill with selected supplier data
        self.entries['supplier_name'].insert(0, company_name)
        self.entries['supplier_address_1'].insert(0, address1)
        self.entries['supplier_address_2'].insert(0, address2)
        self.entries['supplier_nip'].insert(0, str(nip))
        
        # Set NIP field back to readonly
        self.entries['supplier_nip'].config(state='readonly')
    
    def get_context_data(self):
        """Get all form data as context for document generation"""
        # Parse date with multiple format support
        date_str = self.date_var.get()
        try:
            # Try parsing with the expected format first
            parsed_date = datetime.strptime(date_str, "%d %m %Y").date()
        except ValueError:
            try:
                # Try parsing with month name format (Polish)
                parsed_date = datetime.strptime(date_str, "%d %B %Y").date()
            except ValueError:
                try:
                    # Try parsing with month name format (English)
                    parsed_date = datetime.strptime(date_str, "%d %B %Y").date()
                except ValueError:
                    # If all parsing fails, use current date
                    print(f"Warning: Could not parse date '{date_str}', using current date")
                    parsed_date = datetime.now().date()
        
        context = {
            'town': self.entries['town'].get(),
            'address_1': self.entries['address1'].get(),
            'address_2': self.entries['address2'].get(),
            'nip': self.entries['nip'].get(),
            'regon': self.entries['regon'].get(),
            'email': self.entries['email'].get(),
            'phone_number': self.entries['phone'].get(),
            'bank_name': self.entries['bank_name'].get(),
            'account_number': self.entries['account_number'].get(),
            'date': parsed_date,
            'supplier_name': self.entries['supplier_name'].get(),
            'supplier_address_1': self.entries['supplier_address_1'].get(),
            'supplier_address_2': self.entries['supplier_address_2'].get(),
            'supplier_nip': format_nip(self.entries['supplier_nip'].get()),
            'client_name': self.entries['client_name'].get(),
            'client_address_1': self.entries['client_address_1'].get(),
            'client_address_2': self.entries['client_address_2'].get(),
            'client_nip': format_nip(self.entries['client_nip'].get()),
            'client_alias': self.selected_client_alias,  # Add client alias
            'termin_realizacji': self.entries['termin_realizacji'].get(),
            'termin_platnosci': self.entries['termin_platnosci'].get(),
            'warunki_dostawy': self.entries['warunki_dostawy'].get(),
            'waznosc_oferty': self.entries['waznosc_oferty'].get(),
            'gwarancja': self.entries['gwarancja'].get(),
            'cena': self.entries['cena'].get(),
            'uwagi': self.entries['uwagi'].get("1.0", "end-1c"),  # Get text from Text widget
            'offer_number': self.offer_number,  # Preserve original offer number
            'products': []  # Initialize empty products list
        }
        
        # Add products from product table if available
        if self.product_table and hasattr(self.product_table, 'get_all_products'):
            context['products'] = self.product_table.get_all_products()
            # Calculate total sum of all products (netto) 
            products_total_netto = self.product_table.calculate_totals()
            context['products_total_netto'] = products_total_netto
            
            # Format the netto total with comma as decimal separator
            context['total_netto'] = f"{products_total_netto:.2f}".replace('.', ',')
            
            
        # Add product table headers for Word template
        from src.utils.config import TABLE_COLUMN_HEADERS
        context['product_headers'] = [
            TABLE_COLUMN_HEADERS['PID'],      # 'Lp'
            TABLE_COLUMN_HEADERS['PNAME'],    # 'Nazwa'
            TABLE_COLUMN_HEADERS['UNIT'],     # 'j.m.'
            TABLE_COLUMN_HEADERS['QTY'],      # 'ilość'
            TABLE_COLUMN_HEADERS['U_PRICE'],  # 'Cena jednostkowa netto [PLN]'
            TABLE_COLUMN_HEADERS['TOTAL']     # 'Wartość Netto [PLN]'
        ]
            
        return context
    
    def load_context_for_new_offer(self, context_data):
        """Load context data for creating new offer based on existing one (without offer number)"""
        try:
            # Load client data
            client_fields = ['client_name', 'client_address_1', 'client_address_2', 'client_nip']
            for field in client_fields:
                if field in context_data and field in self.entries:
                    # Handle readonly NIP field
                    if field == 'client_nip':
                        self.entries[field].config(state='normal')
                        self.entries[field].delete(0, END)
                        self.entries[field].insert(0, context_data.get(field, ''))
                        self.entries[field].config(state='readonly')
                    else:
                        self.entries[field].delete(0, END)
                        self.entries[field].insert(0, context_data.get(field, ''))
            
            # Store client alias for new offer generation
            if 'client_alias' in context_data:
                self.selected_client_alias = context_data['client_alias']
                
                # If client_alias is None, try to find it in database by client NIP
                if self.selected_client_alias is None:
                    client_nip = context_data.get('client_nip', '')
                    
                    if client_nip:
                        # Try to find client in database by NIP
                        from src.data.database_service import get_client_by_nip
                        try:
                            # Remove formatting from NIP for database lookup
                            clean_nip = ''.join(c for c in client_nip if c.isdigit())
                            client_data = get_client_by_nip(clean_nip)
                            if client_data:
                                # client_data format: (nip, company_name, address1, address2, alias)
                                self.selected_client_alias = client_data[4]  # alias is at index 4
                        except Exception as e:
                            print(f"Debug: Error looking up client in database: {e}")
            
            # Load supplier data
            supplier_fields = ['supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_nip']
            for field in supplier_fields:
                if field in context_data and field in self.entries:
                    # Handle readonly NIP field
                    if field == 'supplier_nip':
                        self.entries[field].config(state='normal')
                        self.entries[field].delete(0, END)
                        self.entries[field].insert(0, context_data.get(field, ''))
                        self.entries[field].config(state='readonly')
                    else:
                        self.entries[field].delete(0, END)
                        self.entries[field].insert(0, context_data.get(field, ''))
            
            # Load offer details
            offer_fields = ['termin_realizacji', 'termin_platnosci', 'warunki_dostawy', 
                          'waznosc_oferty', 'gwarancja', 'cena']
            for field in offer_fields:
                if field in context_data and field in self.entries:
                    self.entries[field].delete(0, END)
                    self.entries[field].insert(0, context_data.get(field, ''))
            
            # Load town
            if 'town' in context_data and 'town' in self.entries:
                self.entries['town'].delete(0, END)
                self.entries['town'].insert(0, context_data.get('town', ''))
            
            # Load notes (Text widget, not Entry)
            if 'uwagi' in context_data and 'uwagi' in self.entries:
                self.entries['uwagi'].delete(1.0, END)
                self.entries['uwagi'].insert(1.0, context_data.get('uwagi', ''))
            
            # Set current date (not the original date)
            from datetime import datetime
            current_date = datetime.now().strftime("%d %m %Y")
            self.date_var.set(current_date)
            
            # Load products data
            if 'products' in context_data and self.product_table:
                products = context_data.get('products', [])
                # Clear existing products
                if self.product_table.tree:
                    for item in self.product_table.tree.get_children():
                        self.product_table.tree.delete(item)
                
                # Add products from context
                for product in products:
                    if isinstance(product, list) and len(product) >= 5:
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
                        except Exception as e:
                            print(f"Error adding product {product}: {e}")
                
                # Recalculate totals
                if hasattr(self.product_table, 'calculate_totals'):
                    total = self.product_table.calculate_totals()
                    self.update_suma(total)
                    
            return True
            
        except Exception as e:
            print(f"Error loading context for new offer: {e}")
            return False
    
    def set_editor_mode(self):
        """Set fields to read-only mode for offer editing"""
        # Fields that should be read-only in editor mode
        readonly_fields = [
            'address1', 'address2', 'nip', 'regon', 'email', 'phone', 
            'bank_name', 'account_number',
            'supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_nip',
            'client_name', 'client_address_1', 'client_address_2', 'client_nip'
        ]
        
        for field in readonly_fields:
            if field in self.entries:
                self.entries[field].config(state='readonly')
                # Add visual indication for read-only fields
                self.entries[field].config(bg='#f0f0f0', fg='#666666')
        
        # Display offer number if available and field exists
        if self.offer_number and 'offer_number_display' in self.entries:
            self.entries['offer_number_display'].config(state='normal')
            self.entries['offer_number_display'].delete(0, END)
            self.entries['offer_number_display'].insert(0, self.offer_number)
            self.entries['offer_number_display'].config(state='readonly')
            self.entries['offer_number_display'].config(bg='#e9ecef', fg='#495057')
    
    def open_date_picker(self):
        """Open a calendar date picker dialog"""
        # Create a new toplevel window for date picker
        date_window = Toplevel(self.window.winfo_toplevel())
        date_window.title("Wybierz datę")
        date_window.geometry("280x250")
        date_window.resizable(False, False)
        date_window.transient(self.window.winfo_toplevel())
        date_window.grab_set()
        
        # Center the window
        date_window.geometry("+%d+%d" % (
            self.window.winfo_toplevel().winfo_rootx() + 100,
            self.window.winfo_toplevel().winfo_rooty() + 100
        ))
        
        # Get current date
        try:
            current_date = datetime.strptime(self.date_var.get(), "%d %m %Y")
        except:
            current_date = datetime.now()
        
        # Create calendar widget with proper configuration
        cal = Calendar(date_window, 
                      selectmode='day',
                      year=current_date.year,
                      month=current_date.month,
                      day=current_date.day,
                      showweeknumbers=False,
                      showothermonthdays=False,
                      date_pattern='dd/mm/yyyy')  # Use standard format internally
        cal.pack(pady=15)
        
        # Buttons frame
        btn_frame = Frame(date_window)
        btn_frame.pack(pady=10)
        
        def select_date():
            try:
                # Method 1: Try selection_get() first
                selected_date = cal.selection_get()
                print(f"selection_get() returned: {selected_date}")  # Debug
                
                if selected_date:
                    # Format to our required format
                    formatted_date = selected_date.strftime("%d %m %Y")
                    print(f"Formatted date: {formatted_date}")  # Debug
                    self.date_var.set(formatted_date)
                    print(f"Date set to: {self.date_var.get()}")  # Debug
                    date_window.destroy()
                    return
                
                # Method 2: Try get_date() as fallback
                date_str = cal.get_date()
                print(f"get_date() returned: {date_str}")  # Debug
                
                if date_str:
                    # Parse the date string and reformat
                    try:
                        # Calendar might return dd/mm/yyyy format
                        parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                        formatted_date = parsed_date.strftime("%d %m %Y")
                        print(f"Parsed and formatted: {formatted_date}")  # Debug
                        self.date_var.set(formatted_date)
                        print(f"Date set to: {self.date_var.get()}")  # Debug
                        date_window.destroy()
                        return
                    except ValueError:
                        # Try other formats
                        for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%d %m %Y"]:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                formatted_date = parsed_date.strftime("%d %m %Y")
                                print(f"Parsed with format {fmt}: {formatted_date}")  # Debug
                                self.date_var.set(formatted_date)
                                print(f"Date set to: {self.date_var.get()}")  # Debug
                                date_window.destroy()
                                return
                            except ValueError:
                                continue
                
                # Method 3: If both methods fail, try to get current calendar view date
                try:
                    current_year = cal.get_displayed_month()[1]
                    current_month = cal.get_displayed_month()[0]
                    current_day = datetime.now().day  # Default to today's day
                    
                    selected_date = datetime(current_year, current_month, current_day)
                    formatted_date = selected_date.strftime("%d %m %Y")
                    print(f"Using calendar view date: {formatted_date}")  # Debug
                    self.date_var.set(formatted_date)
                    date_window.destroy()
                    return
                except:
                    pass
                
                # If all methods fail, show error
                print("All date retrieval methods failed")  # Debug
                import tkinter.messagebox
                tkinter.messagebox.showerror("Błąd", "Nie udało się pobrać wybranej daty. Spróbuj kliknąć przycisk OK.")
                        
            except Exception as e:
                print(f"Error selecting date: {e}")
                import tkinter.messagebox
                tkinter.messagebox.showerror("Błąd", f"Błąd podczas wyboru daty: {e}")
        
        def cancel():
            date_window.destroy()
        
        # Remove automatic click binding - user must use OK button
        # This ensures proper date selection
        def setup_calendar_focus():
            # Just ensure calendar has focus for keyboard navigation
            try:
                cal.focus_set()
            except:
                pass
        
        date_window.after(100, setup_calendar_focus)
        
        # OK and Cancel buttons
        Button(btn_frame, text="OK", command=select_date, bg='#28a745', fg='black', padx=20, pady=5).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Anuluj", command=cancel, bg='#6c757d', fg='black', padx=20, pady=5).pack(side=LEFT, padx=5)
        
        # Instructions label
        info_label = Label(date_window, text="Wybierz datę i kliknij OK", 
                          font=("Arial", 9), fg='#666666')
        info_label.pack(pady=5)
