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
            # Calculate total sum of all products (netto)
            products_total_netto = self.product_table.calculate_totals()
            context['total_netto'] = products_total_netto
            
            
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
