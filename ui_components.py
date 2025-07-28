from tkinter import *
from tkinter import ttk
import tkinter.messagebox
from datetime import datetime
from tkcalendar import DateEntry, Calendar
from database import get_clients_from_db, get_suppliers_from_db
from config import DEFAULT_COMPANY_DATA, TAX_RATE
from settings import settings_manager

class ClientSearchWindow:
    """Handles client search and selection functionality"""
    
    def __init__(self, parent_window, client_fill_callback):
        self.parent_window = parent_window
        self.client_fill_callback = client_fill_callback
    
    def open_client_search(self):
        """Open client search window"""
        clients = get_clients_from_db()
        if not clients:
            tkinter.messagebox.showinfo("No Clients", "No clients found in database.")
            return
        
        # Create search window
        search_window = Toplevel(self.parent_window)
        search_window.title("Wybierz klienta")
        search_window.geometry("600x400")
        search_window.grab_set()  # Make window modal
        
        # Search label
        Label(search_window, text="Wybierz klienta z listy:", font=("Arial", 12)).pack(pady=10)
        
        # Create listbox with scrollbar
        frame = Frame(search_window)
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = Scrollbar(frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        client_listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        client_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=client_listbox.yview)
        
        # Populate listbox with client data
        for client in clients:
            nip, company_name, address1, address2, alias = client
            display_text = f"{alias} - {company_name} (NIP: {nip})"
            client_listbox.insert(END, display_text)
        
        # Bind double-click to select client
        client_listbox.bind('<Double-1>', lambda event: self._on_client_select(event, search_window, client_listbox, clients))
        
        # Add select button
        button_frame = Frame(search_window)
        button_frame.pack(pady=10)
        
        select_button = Button(button_frame, text="Wybierz", 
                              command=lambda: self._on_client_select(None, search_window, client_listbox, clients))
        select_button.pack(side=LEFT, padx=5)
        
        cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)

    def _on_client_select(self, event, search_window, client_listbox, clients):
        """Handle client selection from the listbox"""
        selection = client_listbox.curselection()
        if selection:
            selected_client = clients[selection[0]]
            self.client_fill_callback(selected_client)
            search_window.destroy()

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

class ProductAddWindow:
    """Handles product addition in a separate window"""
    
    def __init__(self, parent_window, product_add_callback):
        self.parent_window = parent_window
        self.product_add_callback = product_add_callback
        self.entries = {}
    
    def open_product_add_window(self):
        """Open product addition window"""
        print("DEBUG: Opening product add window")  # Debug
        
        # Create product add window
        product_window = Toplevel(self.parent_window)
        product_window.title("Dodaj produkt")
        product_window.geometry("700x500")  # Increased size
        product_window.resizable(False, False)
        product_window.grab_set()  # Make window modal
        product_window.transient(self.parent_window)
        product_window.configure(bg='#f8f9fa')  # Light background
        
        print("DEBUG: Product window created")  # Debug
        
        # Center the window
        product_window.geometry("+%d+%d" % (
            self.parent_window.winfo_rootx() + 100,
            self.parent_window.winfo_rooty() + 100
        ))
        
        # Title
        title_label = Label(product_window, text="🛒 Dodaj nowy produkt do oferty", 
                           font=("Arial", 18, "bold"),
                           bg='#f8f9fa', fg='#343a40')
        title_label.pack(pady=(30, 20), fill=X)
        
        # Main form frame with border
        form_frame = Frame(product_window, bg='white', relief=RIDGE, bd=2)
        form_frame.pack(pady=20, padx=40, fill=BOTH, expand=True)
        
        # Product ID
        Label(form_frame, text="ID produktu:", font=("Arial", 11)).grid(row=0, column=0, sticky=W, padx=5, pady=12)
        self.entries['product_id'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['product_id'].grid(row=0, column=1, padx=5, pady=12, sticky=W)
        
        # Product name
        Label(form_frame, text="Nazwa produktu:", font=("Arial", 11)).grid(row=1, column=0, sticky=W, padx=5, pady=12)
        self.entries['product_name'] = Entry(form_frame, width=35, font=("Arial", 11))
        self.entries['product_name'].grid(row=1, column=1, padx=5, pady=12, sticky=W)
        
        # Unit
        Label(form_frame, text="Jednostka miary (j.m.):", font=("Arial", 11)).grid(row=2, column=0, sticky=W, padx=5, pady=12)
        self.entries['unit'] = Entry(form_frame, width=12, font=("Arial", 11))
        self.entries['unit'].grid(row=2, column=1, padx=5, pady=12, sticky=W)
        
        # Quantity
        Label(form_frame, text="Ilość:", font=("Arial", 11)).grid(row=3, column=0, sticky=W, padx=5, pady=12)
        self.entries['quantity'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['quantity'].grid(row=3, column=1, padx=5, pady=12, sticky=W)
        
        # Unit price
        Label(form_frame, text="Cena jednostkowa:", font=("Arial", 11)).grid(row=4, column=0, sticky=W, padx=5, pady=12)
        self.entries['unit_price'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['unit_price'].grid(row=4, column=1, padx=5, pady=12, sticky=W)
        
        # Add separator line
        separator = Frame(product_window, height=2, bg='#cccccc')
        separator.pack(fill=X, padx=20, pady=(10, 20))
        
        # Buttons frame with explicit positioning
        buttons_frame = Frame(product_window, bg='#f8f9fa', height=100)
        buttons_frame.pack(fill=X, pady=(0, 20))
        buttons_frame.pack_propagate(False)  # Maintain frame size
        
        # Center the buttons using place instead of pack
        # Add button - make it very prominent and centered
        add_btn = Button(buttons_frame, text="✓ ZATWIERDŹ I DODAJ", 
                        font=("Arial", 16, "bold"),
                        bg='#FF4500', fg='white',  # Orange color to make it very visible
                        padx=40, pady=15,
                        command=lambda: self._add_product(product_window),
                        cursor='hand2',
                        relief=RAISED,
                        bd=4)
        add_btn.place(relx=0.3, rely=0.5, anchor=CENTER)  # Center left
        
        # Cancel button
        cancel_btn = Button(buttons_frame, text="✗ Anuluj", 
                           font=("Arial", 14),
                           bg='#dc3545', fg='white',
                           padx=25, pady=12,
                           command=product_window.destroy,
                           cursor='hand2')
        cancel_btn.place(relx=0.7, rely=0.5, anchor=CENTER)  # Center right
        
        # Bind Enter key to add product
        product_window.bind('<Return>', lambda event: self._add_product(product_window))
        product_window.bind('<KP_Enter>', lambda event: self._add_product(product_window))  # Numpad Enter
        
        # Set focus to first field
        self.entries['product_id'].focus_set()
        
        # Add instruction label at the bottom - make it more visible
        instruction_label = Label(product_window, 
                                text="📝 Wypełnij wszystkie pola i kliknij pomarańczowy przycisk 'ZATWIERDŹ I DODAJ'",
                                font=("Arial", 12, "bold"), 
                                fg='#FF4500',  # Orange color
                                bg='#f8f9fa')
        instruction_label.pack(pady=(10, 20))
        
        print("DEBUG: Product add window setup complete")  # Debug
    
    def _add_product(self, product_window):
        """Handle product addition"""
        print("DEBUG: _add_product called")  # Debug
        # Get product data
        product_data = [
            self.entries['product_id'].get(),
            self.entries['product_name'].get(),
            self.entries['unit'].get(),
            self.entries['quantity'].get(),
            self.entries['unit_price'].get()
        ]
        print(f"DEBUG: Product data: {product_data}")  # Debug
        
        # Validate data
        if not all([field.strip() for field in product_data]):
            tkinter.messagebox.showwarning("Błąd", "Proszę wypełnić wszystkie pola!")
            return
        
        # Try to validate numeric fields
        try:
            int(product_data[0])  # product_id
            int(product_data[3])  # quantity  
            float(product_data[4])  # unit_price
        except ValueError:
            tkinter.messagebox.showerror("Błąd", "ID produktu i ilość muszą być liczbami całkowitymi, a cena liczbą!")
            return
        
        # Call the callback function to add product
        if self.product_add_callback(product_data):
            # Show success message
            tkinter.messagebox.showinfo("Sukces", "Produkt został pomyślnie dodany do tabeli!")
            # Clear fields after successful addition
            for entry in self.entries.values():
                entry.delete(0, END)
            # Close window
            product_window.destroy()
        else:
            tkinter.messagebox.showerror("Błąd", "Nie udało się dodać produktu do tabeli!")

class UIComponents:
    """Handles UI component creation and management"""
    
    def __init__(self, window, product_table=None):
        self.window = window
        self.entries = {}
        # Load company data from settings instead of config
        self.text_data = settings_manager.get_all_company_data_settings()
        self.selected_client_alias = None  # Store selected client alias
        self.date_var = StringVar(value=datetime.now().strftime("%d %m %Y"))
        self.suma_var = StringVar(value="0")  # Add StringVar for suma field
        self.product_table = product_table  # Reference to product table
    
    def refresh_company_data(self):
        """Refresh company data from settings"""
        self.text_data = settings_manager.get_all_company_data_settings()
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
    
    def create_upper_section(self):
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
        # Offer number
        offer_number_value = StringVar(self.window, value=self.text_data['offer_number'])
        self.entries['offer_number'] = Entry(self.window, width=25, textvariable=offer_number_value)
        self.entries['offer_number'].place(x=380, y=203)

        # Supplier entries
        self.entries['supplier_name'] = Entry(self.window, width=25)
        self.entries['supplier_name'].place(x=60, y=270)

        self.entries['supplier_address_1'] = Entry(self.window, width=25)
        self.entries['supplier_address_1'].place(x=60, y=300)

        self.entries['supplier_address_2'] = Entry(self.window, width=25)
        self.entries['supplier_address_2'].place(x=60, y=330)

        self.entries['supplier_nip'] = Entry(self.window, width=25)
        self.entries['supplier_nip'].place(x=60, y=360)

        # Client entries
        self.entries['client_name'] = Entry(self.window, width=25)
        self.entries['client_name'].place(x=660, y=270)

        self.entries['client_address_1'] = Entry(self.window, width=25)
        self.entries['client_address_1'].place(x=660, y=300)

        self.entries['client_address_2'] = Entry(self.window, width=25)
        self.entries['client_address_2'].place(x=660, y=330)

        self.entries['client_nip'] = Entry(self.window, width=25)
        self.entries['client_nip'].place(x=660, y=360)
    
    def create_totals_section(self):
        """Create the totals section"""
        Label(self.window, text='SUMA', font="times 14").place(x=800, y=740)
        self.entries['suma'] = Entry(self.window, width=10, font=('Arial', 16), state='readonly', textvariable=self.suma_var)
        self.entries['suma'].place(x=900, y=740)
    
    def update_suma(self, value):
        """Update the suma field value"""
        self.suma_var.set(str(value))
    
    def clear_suma(self):
        """Clear the suma field"""
        self.suma_var.set("0")

    def fill_client_data(self, client_data):
        """Fill client entry fields with selected client data"""
        nip, company_name, address1, address2, alias = client_data
        
        # Store the alias for offer number generation
        self.selected_client_alias = alias
        
        # Clear existing data
        self.entries['client_name'].delete(0, END)
        self.entries['client_address_1'].delete(0, END)
        self.entries['client_address_2'].delete(0, END)
        self.entries['client_nip'].delete(0, END)
        
        # Fill with selected client data
        self.entries['client_name'].insert(0, company_name)
        self.entries['client_address_1'].insert(0, address1)
        self.entries['client_address_2'].insert(0, address2)
        self.entries['client_nip'].insert(0, str(nip))
    
    def fill_supplier_data(self, supplier_data):
        """Fill supplier entry fields with selected supplier data"""
        nip, company_name, address1, address2 = supplier_data
        
        # Clear existing data
        self.entries['supplier_name'].delete(0, END)
        self.entries['supplier_address_1'].delete(0, END)
        self.entries['supplier_address_2'].delete(0, END)
        self.entries['supplier_nip'].delete(0, END)
        
        # Fill with selected supplier data
        self.entries['supplier_name'].insert(0, company_name)
        self.entries['supplier_address_1'].insert(0, address1)
        self.entries['supplier_address_2'].insert(0, address2)
        self.entries['supplier_nip'].insert(0, str(nip))
    
    def get_context_data(self):
        """Get all form data as context for document generation"""
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
            'offer_number': self.entries['offer_number'].get(),
            'date': datetime.strptime(self.date_var.get(), "%d %m %Y").date(),
            'supplier_name': self.entries['supplier_name'].get(),
            'supplier_address_1': self.entries['supplier_address_1'].get(),
            'supplier_address_2': self.entries['supplier_address_2'].get(),
            'supplier_nip': self.entries['supplier_nip'].get(),
            'client_name': self.entries['client_name'].get(),
            'client_address_1': self.entries['client_address_1'].get(),
            'client_address_2': self.entries['client_address_2'].get(),
            'client_nip': self.entries['client_nip'].get(),
            'client_alias': self.selected_client_alias,  # Add client alias
            'products': []  # Initialize empty products list
        }
        
        # Add products from product table if available
        if self.product_table and hasattr(self.product_table, 'get_all_products'):
            context['products'] = self.product_table.get_all_products()
            
        return context
    
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
