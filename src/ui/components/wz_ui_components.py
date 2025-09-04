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
    
    def __init__(self, window, product_table, show_generate_button=True):
        self.window = window
        self.product_table = product_table
        self.show_generate_button = show_generate_button  # Control generate button visibility
        self.entries = {}
        self.modification_callback = None
        self.selected_client_alias = None
        self.selected_supplier_alias = None
        self.wz_number = None  # Initialize WZ number attribute
        self.locked_year = None  # Locked year (editor mode)

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

    def lock_year(self, year: int):
        """Lock calendar year (editor mode)."""
        try:
            self.locked_year = int(year)
        except Exception:
            self.locked_year = None
    
    
    def create_upper_section(self, show_wz_number=False):

        # Town entry
        self.entries['town'] = Entry(self.window, width=50)
        self.entries['town'].place(x=600, y=90)
        self.entries['town'].insert(0, self.text_data.get('town', ''))
        self.entries['town'].bind('<KeyRelease>', self._on_field_modified)

        # Date entry with custom popup solution
        self.entries['date'] = Entry(self.window, width=15, textvariable=self.date_var, state='readonly')
        self.entries['date'].place(x=740, y=90)
        
        # Date picker button
        self.date_btn = Button(self.window, text="📅", width=2, command=self.open_date_picker)
        self.date_btn.place(x=870, y=90)

        """Create the upper section with date and company info"""
        # WZ number display (only in editor mode)
        if show_wz_number:
            self.entries['wz_number_display'] = Entry(self.window, width=20, state='readonly',
                                                     bg='#f0f0f0', fg='#666666')
            self.entries['wz_number_display'].place(x=400, y=200)

        # Company info entries
        address1_value = StringVar(self.window, value=self.text_data.get('address_1', ''))
        self.entries['address_1'] = Entry(self.window, width=28, textvariable=address1_value)
        self.entries['address_1'].place(x=110, y=118)
        self.entries['address_1'].bind('<KeyRelease>', self._on_field_modified)

        address2_value = StringVar(self.window, value=self.text_data.get('address_2', ''))
        self.entries['address_2'] = Entry(self.window, width=28, textvariable=address2_value)
        self.entries['address_2'].place(x=110, y=148)
        self.entries['address_2'].bind('<KeyRelease>', self._on_field_modified)

        nip_value = StringVar(self.window, value=self.text_data.get('nip', ''))
        self.entries['nip'] = Entry(self.window, width=15, textvariable=nip_value)
        self.entries['nip'].place(x=300, y=118)
        self.entries['nip'].bind('<KeyRelease>', self._on_field_modified)

        regon_value = StringVar(self.window, value=self.text_data.get('regon', ''))
        self.entries['regon'] = Entry(self.window, width=15, textvariable=regon_value)
        self.entries['regon'].place(x=320, y=148)
        self.entries['regon'].bind('<KeyRelease>', self._on_field_modified)

        email_value = StringVar(self.window, value=self.text_data.get('email', ''))
        self.entries['email'] = Entry(self.window, width=32, textvariable=email_value)
        self.entries['email'].place(x=485, y=118)
        self.entries['email'].bind('<KeyRelease>', self._on_field_modified)

        phone_value = StringVar(self.window, value=self.text_data.get('phone_number', ''))
        self.entries['phone_number'] = Entry(self.window, width=18, textvariable=phone_value)
        self.entries['phone_number'].place(x=485, y=148)
        self.entries['phone_number'].bind('<KeyRelease>', self._on_field_modified)

        bank_name_value = StringVar(self.window, value=self.text_data.get('bank_name', ''))
        self.entries['bank_name'] = Entry(self.window, width=28, textvariable=bank_name_value)
        self.entries['bank_name'].place(x=735, y=118)
        self.entries['bank_name'].bind('<KeyRelease>', self._on_field_modified)

        account_number_value = StringVar(self.window, value=self.text_data.get('account_number', ''))
        self.entries['account_number'] = Entry(self.window, width=37, textvariable=account_number_value)
        self.entries['account_number'].place(x=675, y=148)
        self.entries['account_number'].bind('<KeyRelease>', self._on_field_modified)
    
    def create_wz_section(self):
        """Create the supplier/client section using one-column tables with 2-line Text for names (like offers)"""
        # Supplier entries as a one-column table with header
        supplier_frame = Frame(self.window, bg='white')
        supplier_frame.place(x=60, y=220)

        Label(supplier_frame, text='DOSTAWCA', font=("Arial", 16, "bold"), bg='white').grid(row=0, column=0, sticky='w', pady=(0, 6))

        # Row 1: Text for supplier name (2 lines)
        self.entries['supplier_name'] = Text(supplier_frame, width=45, height=2, wrap=WORD)
        self.entries['supplier_name'].grid(row=1, column=0, sticky='w', pady=(0, 6))
        self.entries['supplier_name'].bind('<KeyRelease>', self._on_field_modified)

        # Row 2: Entry for address 1
        self.entries['supplier_address_1'] = Entry(supplier_frame, width=45)
        self.entries['supplier_address_1'].grid(row=2, column=0, sticky='w', pady=(0, 6))
        self.entries['supplier_address_1'].bind('<KeyRelease>', self._on_field_modified)

        # Row 3: Entry for address 2
        self.entries['supplier_address_2'] = Entry(supplier_frame, width=45)
        self.entries['supplier_address_2'].grid(row=3, column=0, sticky='w', pady=(0, 6))
        self.entries['supplier_address_2'].bind('<KeyRelease>', self._on_field_modified)

        # Row 4: Entry for NIP (readonly)
        self.entries['supplier_nip'] = Entry(supplier_frame, width=25, state='readonly', bg='#f0f0f0')
        self.entries['supplier_nip'].grid(row=4, column=0, sticky='w')

        # Client entries as a one-column table with header
        client_frame = Frame(self.window, bg='white')
        client_frame.place(x=600, y=220)

        Label(client_frame, text='KLIENT', font=("Arial", 16, "bold"), bg='white').grid(row=0, column=0, sticky='w', pady=(0, 6))

        # Row 1: Text for client name (2 lines)
        self.entries['client_name'] = Text(client_frame, width=45, height=2, wrap=WORD)
        self.entries['client_name'].grid(row=1, column=0, sticky='w', pady=(0, 6))
        self.entries['client_name'].bind('<KeyRelease>', self._on_field_modified)

        # Row 2: Entry for address 1
        self.entries['client_address_1'] = Entry(client_frame, width=45)
        self.entries['client_address_1'].grid(row=2, column=0, sticky='w', pady=(0, 6))
        self.entries['client_address_1'].bind('<KeyRelease>', self._on_field_modified)

        # Row 3: Entry for address 2
        self.entries['client_address_2'] = Entry(client_frame, width=45)
        self.entries['client_address_2'].grid(row=3, column=0, sticky='w', pady=(0, 6))
        self.entries['client_address_2'].bind('<KeyRelease>', self._on_field_modified)

        # Row 4: Entry for NIP (readonly)
        self.entries['client_nip'] = Entry(client_frame, width=25, state='readonly', bg='#f0f0f0')
        self.entries['client_nip'].grid(row=4, column=0, sticky='w')
    
    def create_action_buttons(self):
        """Create action buttons for WZ operations"""
        # Add product button
        self.add_product_btn = Button(self.window,
                                    text="DODAJ POZYCJĘ",
                                    font=("Arial", 12, "bold"),
                                    bg='#FF9800', fg='black',
                                    padx=15, pady=8,
                                    cursor='hand2')
        self.add_product_btn.place(x=50, y=730)

        # Product movement buttons (same as in offers)
        self.move_up_btn = Button(self.window, text="▲", anchor='center',
                                font=("Arial", 16, "bold"),
                                bg='#6c757d', fg='black',
                                width=3, height=1,
                                cursor='hand2')
        self.move_up_btn.place(x=250, y=730)
        
        self.move_down_btn = Button(self.window, text="▼", anchor='center',
                                  font=("Arial", 16, "bold"),
                                  bg='#6c757d', fg='black',
                                  width=3, height=1,
                                  cursor='hand2')
        self.move_down_btn.place(x=320, y=730)

        # Generate WZ button (only show in creator, not in editor)
        if self.show_generate_button:
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
                raw = entry.get("1.0", END).strip()
                # Normalize to literal \n markers for downstream processing
                data[key] = raw.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')
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
        if isinstance(self.entries.get('client_name'), Text):
            self.entries['client_name'].delete('1.0', END)
        else:
            self.entries['client_name'].delete(0, END)
        self.entries['client_address_1'].delete(0, END)
        self.entries['client_address_2'].delete(0, END)
        
        # Clear NIP field (temporarily enable it)
        self.entries['client_nip'].config(state='normal')
        self.entries['client_nip'].delete(0, END)
        
        # Fill with selected client data
        disp_name = str(company_name or '').replace('\\n', '\n')
        if isinstance(self.entries.get('client_name'), Text):
            self.entries['client_name'].insert('1.0', disp_name)
        else:
            self.entries['client_name'].insert(0, disp_name)
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
        if isinstance(self.entries.get('supplier_name'), Text):
            self.entries['supplier_name'].delete('1.0', END)
        else:
            self.entries['supplier_name'].delete(0, END)
        self.entries['supplier_address_1'].delete(0, END)
        self.entries['supplier_address_2'].delete(0, END)
        
        # Clear NIP field (temporarily enable it)
        self.entries['supplier_nip'].config(state='normal')
        self.entries['supplier_nip'].delete(0, END)
        
        # Fill with selected supplier data
        disp_name = str(company_name or '').replace('\\n', '\n')
        if isinstance(self.entries.get('supplier_name'), Text):
            self.entries['supplier_name'].insert('1.0', disp_name)
        else:
            self.entries['supplier_name'].insert(0, disp_name)
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
        cal_kwargs = dict(
            selectmode='day',
            year=current_date.year,
            month=current_date.month,
            day=current_date.day,
            showweeknumbers=False,
            showothermonthdays=False,
            date_pattern='dd/mm/yyyy'
        )
        if self.locked_year is not None:
            from datetime import datetime as _dt
            cal_kwargs['year'] = self.locked_year
            if current_date.year != self.locked_year:
                current_date = current_date.replace(year=self.locked_year)
            cal_kwargs['month'] = current_date.month
            cal_kwargs['day'] = current_date.day
            cal_kwargs['mindate'] = _dt(self.locked_year, 1, 1)
            cal_kwargs['maxdate'] = _dt(self.locked_year, 12, 31)
        cal = Calendar(date_window, **cal_kwargs)
        cal.pack(pady=15)
        
        # Buttons frame
        btn_frame = Frame(date_window)
        btn_frame.pack(pady=10)
        
        def select_date():
            try:
                # Method 1: Try selection_get() first
                selected_date = cal.selection_get()
                
                if selected_date:
                    if self.locked_year is not None and selected_date.year != self.locked_year:
                        from datetime import datetime as _dt
                        try:
                            selected_date = _dt(self.locked_year, selected_date.month, selected_date.day)
                        except ValueError:
                            selected_date = _dt(self.locked_year, 1, 1)
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
                        if self.locked_year is not None and parsed_date.year != self.locked_year:
                            from datetime import datetime as _dt
                            try:
                                parsed_date = _dt(self.locked_year, parsed_date.month, parsed_date.day)
                            except ValueError:
                                parsed_date = _dt(self.locked_year, 1, 1)
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
            if key not in ['address_1', 'address_2', 'nip', 'regon', 'email', 'phone_number', 'bank_name', 'account_number']:
                if isinstance(entry, Entry) and entry['state'] != 'readonly':
                    entry.delete(0, END)
                elif isinstance(entry, Text):
                    entry.delete("1.0", END)
        
        # Reset date to current
        self.date_var.set(datetime.now().strftime('%d %m %Y'))
        
        # Clear aliases
        self.selected_client_alias = None
        self.selected_supplier_alias = None
    
    def set_editor_mode(self):
        """Set fields to read-only mode for WZ editing"""
        # Fields that should be read-only in editor mode
        readonly_fields = [
            # WZ number should be read-only in editor
            'wz_number_display'
        ]
        
        for field in readonly_fields:
            if field in self.entries:
                self.entries[field].config(state='readonly')
                # Add visual indication for read-only fields
                self.entries[field].config(bg='#f0f0f0', fg='#666666')
        
        # Make company data fields editable with standard styling
        company_editable_fields = ['address_1', 'address_2', 'nip', 'regon', 'email', 'phone_number', 'bank_name', 'account_number']
        for field in company_editable_fields:
            if field in self.entries:
                self.entries[field].config(state='normal')
                # Standard white background, no special coloring
    
    def get_context_data(self):
        """Get all form data as context for WZ document generation"""
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
        
        # Helper to read name fields and normalize newlines to literal markers
        def _name_value(field: str) -> str:
            widget = self.entries.get(field)
            if isinstance(widget, Text):
                raw = widget.get('1.0', END).strip()
                return raw.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')
            if isinstance(widget, Entry):
                return widget.get()
            return ''

        context = {
            'town': self.entries['town'].get(),
            'address_1': self.entries['address_1'].get(),
            'address_2': self.entries['address_2'].get(),
            'nip': self.entries['nip'].get(),
            'regon': self.entries['regon'].get(),
            'email': self.entries['email'].get(),
            'phone_number': self.entries['phone_number'].get(),
            'bank_name': self.entries['bank_name'].get(),
            'account_number': self.entries['account_number'].get(),
            'date': parsed_date,
            'supplier_name': _name_value('supplier_name'),
            'supplier_address_1': self.entries['supplier_address_1'].get(),
            'supplier_address_2': self.entries['supplier_address_2'].get(),
            'supplier_nip': self.entries['supplier_nip'].get(),
            'client_name': _name_value('client_name'),
            'client_address_1': self.entries['client_address_1'].get(),
            'client_address_2': self.entries['client_address_2'].get(),
            'client_nip': self.entries['client_nip'].get(),
            'client_alias': self.selected_client_alias,  # Add client alias
            'supplier_alias': self.selected_supplier_alias,  # Add supplier alias
            'wz_number': self.wz_number,  # Preserve original WZ number
            'products': []  # Initialize empty products list
        }
        
        # Add products from product table if available
        if self.product_table and hasattr(self.product_table, 'get_all_products'):
            context['products'] = self.product_table.get_all_products()
        
        return context
    
    def load_context_for_new_wz(self, context_data):
        """Load context data for creating new WZ based on existing one (without WZ number)"""
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
                        if isinstance(self.entries[field], Text):
                            self.entries[field].delete('1.0', END)
                            self.entries[field].insert('1.0', str(context_data.get(field, '') or '').replace('\\n', '\n'))
                        else:
                            self.entries[field].delete(0, END)
                            self.entries[field].insert(0, context_data.get(field, ''))
            
            # Store client alias for new WZ generation
            if 'client_alias' in context_data:
                self.selected_client_alias = context_data.get('client_alias')
            
            # Fallback: if alias missing or empty, attempt DB lookup by NIP
            if not self.selected_client_alias:
                client_nip = context_data.get('client_nip', '')
                if client_nip:
                    from src.data.database_service import get_client_by_nip
                    try:
                        clean_nip = ''.join(c for c in client_nip if c.isdigit())
                        client_data = get_client_by_nip(clean_nip)
                        if client_data and len(client_data) >= 5:
                            self.selected_client_alias = client_data[4]
                    except Exception as e:
                        print(f"Debug: Error looking up client alias by NIP: {e}")
            
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
                        if isinstance(self.entries[field], Text):
                            self.entries[field].delete('1.0', END)
                            self.entries[field].insert('1.0', str(context_data.get(field, '') or '').replace('\\n', '\n'))
                        else:
                            self.entries[field].delete(0, END)
                            self.entries[field].insert(0, context_data.get(field, ''))
        
            
            # Load town
            if 'town' in context_data and 'town' in self.entries:
                self.entries['town'].delete(0, END)
                self.entries['town'].insert(0, context_data.get('town', ''))
        
            
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
                    if isinstance(product, list) and len(product) >= 4:
                        
                        # Create tuple for input_record (expects 5 elements)
                        product_tuple = (
                            str(product[0]),    # pid
                            str(product[1]),    # pname
                            str(product[2]),    # unit
                            str(product[3]),    # qty
                        )
                        
                        try:
                            self.product_table.input_record(product_tuple)
                        except Exception as e:
                            print(f"Error adding product {product}: {e}")
                
                # Recalculate totals
                if hasattr(self.product_table, 'calculate_totals'):
                    total = self.product_table.calculate_totals()
                    if hasattr(self, 'update_suma'):
                        self.update_suma(total)
                    
            return True
            
        except Exception as e:
            print(f"Error loading context for new offer: {e}")
            return False
