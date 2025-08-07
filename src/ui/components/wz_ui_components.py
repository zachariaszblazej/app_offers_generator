"""
WZ UI Components - simplified version for WZ creation without pricing and some other elements
"""
from tkinter import *
import tkinter.messagebox
from datetime import datetime
from tkcalendar import DateEntry, Calendar
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import get_suppliers_from_db, get_clients_from_db
from src.utils.settings import settings_manager


class WzUIComponents:
    """Handles WZ UI creation and data management - simplified version"""
    
    def __init__(self, window, product_table):
        self.window = window
        self.product_table = product_table
        self.entries = {}
        self.modification_callback = None
        self.selected_client_alias = None
        self.selected_supplier_alias = None
        
        # Load default data
        self.suppliers_data = get_suppliers_from_db() or []
        self.clients_data = get_clients_from_db() or []
        
        # Load company settings data
        self.text_data = settings_manager.get_all_company_data_settings()
        
        # Date variable for date picker
        self.date_var = StringVar()
        self.date_var.set(datetime.now().strftime('%d %m %Y'))
        
        # Variables for specific fields (not needed for WZ but kept for compatibility)
        self.suma_var = StringVar()
        self.suma_var.set("0,00")
        
        # Create all UI components
        self.create_upper_section()
        self.create_offer_section()
        self.create_action_buttons()
    
    def create_upper_section(self, show_offer_number=False):
        """Create the upper section with date and company info"""
        # Town entry
        self.entries['town'] = Entry(self.window, width=10)
        self.entries['town'].place(x=640, y=90)
        self.entries['town'].insert(0, self.text_data.get('town', ''))
        self.entries['town'].bind('<KeyRelease>', self._on_field_modified)

        # Date entry with custom popup solution
        self.entries['date'] = Entry(self.window, width=15, textvariable=self.date_var, state='readonly')
        self.entries['date'].place(x=740, y=90)
        
        # Date picker button
        self.date_btn = Button(self.window, text="📅", width=2, command=self.open_date_picker)
        self.date_btn.place(x=870, y=90)

        # Company info entries
        address1_value = StringVar(self.window, value=self.text_data.get('address_1', ''))
        self.entries['address1'] = Entry(self.window, width=17, textvariable=address1_value)
        self.entries['address1'].place(x=110, y=118)
        self.entries['address1'].bind('<KeyRelease>', self._on_field_modified)

        address2_value = StringVar(self.window, value=self.text_data.get('address_2', ''))
        self.entries['address2'] = Entry(self.window, width=17, textvariable=address2_value)
        self.entries['address2'].place(x=110, y=148)
        self.entries['address2'].bind('<KeyRelease>', self._on_field_modified)

        nip_value = StringVar(self.window, value=self.text_data.get('nip', ''))
        self.entries['nip'] = Entry(self.window, width=15, textvariable=nip_value)
        self.entries['nip'].place(x=300, y=118)
        self.entries['nip'].bind('<KeyRelease>', self._on_field_modified)

        regon_value = StringVar(self.window, value=self.text_data.get('regon', ''))
        self.entries['regon'] = Entry(self.window, width=15, textvariable=regon_value)
        self.entries['regon'].place(x=320, y=148)
        self.entries['regon'].bind('<KeyRelease>', self._on_field_modified)

        email_value = StringVar(self.window, value=self.text_data.get('email', ''))
        self.entries['email'] = Entry(self.window, width=20, textvariable=email_value)
        self.entries['email'].place(x=485, y=118)
        self.entries['email'].bind('<KeyRelease>', self._on_field_modified)

        phone_value = StringVar(self.window, value=self.text_data.get('phone_number', ''))
        self.entries['phone'] = Entry(self.window, width=15, textvariable=phone_value)
        self.entries['phone'].place(x=485, y=148)
        self.entries['phone'].bind('<KeyRelease>', self._on_field_modified)

        bank_name_value = StringVar(self.window, value=self.text_data.get('bank_name', ''))
        self.entries['bank_name'] = Entry(self.window, width=15, textvariable=bank_name_value)
        self.entries['bank_name'].place(x=715, y=118)
        self.entries['bank_name'].bind('<KeyRelease>', self._on_field_modified)

        account_number_value = StringVar(self.window, value=self.text_data.get('account_number', ''))
        self.entries['account_number'] = Entry(self.window, width=25, textvariable=account_number_value)
        self.entries['account_number'].place(x=675, y=148)
        self.entries['account_number'].bind('<KeyRelease>', self._on_field_modified)
    
    def create_offer_section(self):
        """Create the supplier/client section with search buttons"""
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
        
        # Add search buttons for supplier and client
        self.supplier_search_btn = Button(self.window, 
                                        text="SZUKAJ DOSTAWCY",
                                        font=("Arial", 10, "bold"),
                                        bg='#4CAF50', fg='white',
                                        padx=10, pady=5,
                                        cursor='hand2')
        self.supplier_search_btn.place(x=300, y=315)
        
        self.client_search_btn = Button(self.window, 
                                      text="SZUKAJ KLIENTA",
                                      font=("Arial", 10, "bold"),
                                      bg='#2196F3', fg='white',
                                      padx=10, pady=5,
                                      cursor='hand2')
        self.client_search_btn.place(x=900, y=315)
    
    def create_action_buttons(self):
        """Create action buttons for WZ operations"""
        # Add product button
        self.add_product_btn = Button(self.window,
                                    text="DODAJ PRODUKT",
                                    font=("Arial", 12, "bold"),
                                    bg='#FF9800', fg='white',
                                    padx=15, pady=8,
                                    cursor='hand2')
        self.add_product_btn.place(x=50, y=730)
        
        # Generate WZ button
        self.generate_btn = Button(self.window,
                                 text="GENERUJ WZ",
                                 font=("Arial", 14, "bold"),
                                 bg='#f44336', fg='white',
                                 padx=20, pady=10,
                                 cursor='hand2')
        self.generate_btn.place(x=450, y=750)
    
    def set_modification_callback(self, callback):
        """Set callback for field modifications"""
        self.modification_callback = callback
    
    def _on_field_modified(self, event=None):
        """Called when any field is modified"""
        if self.modification_callback:
            self.modification_callback()
    
    def get_all_data(self):
        """Get all form data as dictionary"""
        data = {}
        for key, entry in self.entries.items():
            if isinstance(entry, Entry):
                data[key] = entry.get()
            elif isinstance(entry, Text):
                data[key] = entry.get("1.0", END).strip()
        return data
    
    def get_field_value(self, field_name):
        """Get value of specific field"""
        if field_name in self.entries:
            entry = self.entries[field_name]
            if isinstance(entry, Entry):
                return entry.get()
            elif isinstance(entry, Text):
                return entry.get("1.0", END).strip()
        return ""
    
    def fill_client_data(self, client_data):
        """Fill client entry fields with selected client data"""
        nip, company_name, address1, address2, alias = client_data
        
        # Store the alias for WZ number generation
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
        
        # Make NIP field readonly again
        self.entries['client_nip'].config(state='readonly')
        
        # Trigger modification callback
        if self.modification_callback:
            self.modification_callback()

    def fill_supplier_data(self, supplier_data):
        """Fill supplier entry fields with selected supplier data"""
        nip, company_name, address1, address2 = supplier_data
        
        # For WZ, we don't store supplier alias separately
        self.selected_supplier_alias = company_name  # Use company name as alias
        
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
        
        # Make NIP field readonly again
        self.entries['supplier_nip'].config(state='readonly')
        
        # Trigger modification callback
        if self.modification_callback:
            self.modification_callback()
    
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
                      date_pattern='dd/mm/yyyy')
        cal.pack(pady=15)
        
        # Buttons frame
        btn_frame = Frame(date_window)
        btn_frame.pack(pady=10)
        
        def select_date():
            try:
                # Method 1: Try selection_get() first
                selected_date = cal.selection_get()
                
                if selected_date:
                    # Format to our required format
                    formatted_date = selected_date.strftime("%d %m %Y")
                    self.date_var.set(formatted_date)
                    date_window.destroy()
                    return
                
                # Method 2: Try get_date() as fallback
                date_str = cal.get_date()
                
                if date_str:
                    # Parse the date string and reformat
                    try:
                        # Calendar might return dd/mm/yyyy format
                        parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                        formatted_date = parsed_date.strftime("%d %m %Y")
                        self.date_var.set(formatted_date)
                        date_window.destroy()
                    except ValueError:
                        # Try alternative format
                        try:
                            parsed_date = datetime.strptime(date_str, "%m/%d/%Y")
                            formatted_date = parsed_date.strftime("%d %m %Y")
                            self.date_var.set(formatted_date)
                            date_window.destroy()
                        except ValueError:
                            tkinter.messagebox.showerror("Błąd", f"Nie można przetworzyć daty: {date_str}")
            except Exception as e:
                tkinter.messagebox.showerror("Błąd", f"Błąd podczas wybierania daty: {e}")
        
        # OK button
        ok_btn = Button(btn_frame, text="OK", command=select_date, 
                       bg="#4CAF50", fg="white", padx=20, pady=5)
        ok_btn.pack(side=LEFT, padx=5)
        
        # Cancel button
        cancel_btn = Button(btn_frame, text="Anuluj", command=date_window.destroy,
                           bg="#f44336", fg="white", padx=20, pady=5)
        cancel_btn.pack(side=LEFT, padx=5)
    
    def clear_all_fields(self):
        """Clear all entry fields"""
        for key, entry in self.entries.items():
            if key not in ['address1', 'address2', 'nip', 'regon', 'email', 'phone', 'bank_name', 'account_number']:
                if isinstance(entry, Entry) and entry['state'] != 'readonly':
                    entry.delete(0, END)
                elif isinstance(entry, Text):
                    entry.delete("1.0", END)
        
        # Reset date to current
        self.date_var.set(datetime.now().strftime('%d %m %Y'))
        
        # Clear aliases
        self.selected_client_alias = None
        self.selected_supplier_alias = None
