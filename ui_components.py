from tkinter import *
from tkinter import ttk
import tkinter.messagebox
from tkcalendar import DateEntry
from database import get_clients_from_db
from config import DEFAULT_COMPANY_DATA, TAX_RATE

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

class UIComponents:
    """Handles UI component creation and management"""
    
    def __init__(self, window):
        self.window = window
        self.entries = {}
        self.text_data = DEFAULT_COMPANY_DATA
    
    def create_upper_section(self):
        """Create the upper section of the form"""
        # Town entry
        self.entries['town'] = Entry(self.window, width=10)
        self.entries['town'].place(x=640, y=90)
        self.entries['town'].insert(0, self.text_data['town'])

        # Date entry
        self.entries['date'] = DateEntry(self.window, width=15, date_pattern="dd MM yyyy", borderwidth=2)
        self.entries['date'].place(x=740, y=90)

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
    
    def create_product_input_section(self):
        """Create the product input section"""
        input_frame = Frame(self.window)
        input_frame.place(x=875, y=825)

        # Labels
        Label(input_frame, text="ProductID").grid(row=0, column=0)
        Label(input_frame, text="ProductName").grid(row=0, column=1)
        Label(input_frame, text="Quantity").grid(row=0, column=2)
        Label(input_frame, text="UNIT PRICE").grid(row=0, column=3)

        # Entries
        self.entries['product_id'] = Entry(input_frame)
        self.entries['product_id'].grid(row=1, column=0)

        self.entries['product_name'] = Entry(input_frame)
        self.entries['product_name'].grid(row=1, column=1)

        self.entries['quantity'] = Entry(input_frame)
        self.entries['quantity'].grid(row=1, column=2)

        self.entries['unit_price'] = Entry(input_frame)
        self.entries['unit_price'].grid(row=1, column=3)

        return input_frame
    
    def create_totals_section(self):
        """Create the totals section"""
        # Labels
        Label(self.window, text='SUBTOTAL :>>>', font="times 14").place(x=1000, y=915)
        Label(self.window, text='18% GST:>>>', font="times 14").place(x=1000, y=950)
        Label(self.window, text='TOTAL:>>>', font="times 14").place(x=1000, y=985)

        # Entries
        self.entries['subtotal'] = Entry(self.window, width=10, font=('Arial', 16))
        self.entries['subtotal'].place(x=1150, y=915)

        self.entries['tax'] = Entry(self.window, width=10, font=('Arial', 16))
        self.entries['tax'].place(x=1150, y=950)

        self.entries['grandtotal'] = Entry(self.window, width=10, font=('Arial', 16))
        self.entries['grandtotal'].place(x=1150, y=985)
    
    def fill_client_data(self, client_data):
        """Fill client entry fields with selected client data"""
        nip, company_name, address1, address2, alias = client_data
        
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
    
    def get_context_data(self):
        """Get all form data as context for document generation"""
        return {
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
            'date': self.entries['date'].get_date(),
            'supplier_name': self.entries['supplier_name'].get(),
            'supplier_address_1': self.entries['supplier_address_1'].get(),
            'supplier_address_2': self.entries['supplier_address_2'].get(),
            'supplier_nip': self.entries['supplier_nip'].get(),
            'client_name': self.entries['client_name'].get(),
            'client_address_1': self.entries['client_address_1'].get(),
            'client_address_2': self.entries['client_address_2'].get(),
            'client_nip': self.entries['client_nip'].get()
        }
