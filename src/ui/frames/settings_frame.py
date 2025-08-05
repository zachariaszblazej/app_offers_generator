"""
Settings frame for application configuration
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.settings import settings_manager


class SettingsFrame(Frame):
    """Frame for managing application settings"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.settings_manager = settings_manager
        self.entries = {}
        self.create_ui()
        self.load_current_settings()
    
    def create_ui(self):
        """Create the settings UI"""
        self.configure(bg='#f0f0f0')
        
        # Header
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=20)
        
        # Title
        title_label = Label(header_frame, text="Ustawienia aplikacji", 
                           font=("Arial", 20, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(side=LEFT)
        
        # Return button
        return_btn = Button(header_frame, text="Powrót do menu głównego",
                           font=("Arial", 12),
                           bg='#6c757d', fg='black',
                           padx=15, pady=8,
                           command=self.return_to_main_menu,
                           cursor='hand2')
        return_btn.pack(side=RIGHT)
        
        # Main scrollable frame
        main_canvas = Canvas(self, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_canvas.yview)
        scrollable_frame = Frame(main_canvas, bg='#f0f0f0')
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        main_canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")
        
        # Content container
        content_container = Frame(scrollable_frame, bg='#f0f0f0')
        content_container.pack(fill=BOTH, expand=True, pady=20)
        
        # Company data section
        self.create_company_data_section(content_container)
        
        # Offer details section
        self.create_offer_details_section(content_container)
        
        # Buttons section
        self.create_buttons_section(scrollable_frame)
    
    def create_company_data_section(self, parent):
        """Create company data settings section"""
        # Section title
        company_title = Label(parent, text="Dane firmy", 
                             font=("Arial", 16, "bold"), 
                             bg='#f0f0f0', fg='#333333')
        company_title.pack(anchor=W, pady=(0, 20))
        
        # Main form frame with border
        form_frame = Frame(parent, bg='#ffffff', relief=RIDGE, bd=2)
        form_frame.pack(fill=X, pady=(0, 30))
        
        # Inner frame with padding
        inner_frame = Frame(form_frame, bg='#ffffff')
        inner_frame.pack(fill=BOTH, expand=True, padx=30, pady=30)
        
        # Two column layout
        columns_frame = Frame(inner_frame, bg='#ffffff')
        columns_frame.pack(fill=X)
        
        # Left column
        left_column = Frame(columns_frame, bg='#ffffff')
        left_column.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 20))
        
        # Right column
        right_column = Frame(columns_frame, bg='#ffffff')
        right_column.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Town
        town_frame = Frame(left_column, bg='#ffffff')
        town_frame.pack(fill=X, pady=5)
        Label(town_frame, text="Miasto:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['town'] = Entry(town_frame, width=30, font=("Arial", 11))
        self.entries['town'].pack(fill=X, pady=(5, 0))
        
        # Address 1
        address1_frame = Frame(left_column, bg='#ffffff')
        address1_frame.pack(fill=X, pady=5)
        Label(address1_frame, text="Adres (linia 1):", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['address_1'] = Entry(address1_frame, width=30, font=("Arial", 11))
        self.entries['address_1'].pack(fill=X, pady=(5, 0))
        
        # Address 2
        address2_frame = Frame(left_column, bg='#ffffff')
        address2_frame.pack(fill=X, pady=5)
        Label(address2_frame, text="Adres (linia 2):", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['address_2'] = Entry(address2_frame, width=30, font=("Arial", 11))
        self.entries['address_2'].pack(fill=X, pady=(5, 0))
        
        # NIP
        nip_frame = Frame(left_column, bg='#ffffff')
        nip_frame.pack(fill=X, pady=5)
        Label(nip_frame, text="NIP:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['nip'] = Entry(nip_frame, width=30, font=("Arial", 11))
        self.entries['nip'].pack(fill=X, pady=(5, 0))
        
        # REGON
        regon_frame = Frame(right_column, bg='#ffffff')
        regon_frame.pack(fill=X, pady=5)
        Label(regon_frame, text="REGON:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['regon'] = Entry(regon_frame, width=30, font=("Arial", 11))
        self.entries['regon'].pack(fill=X, pady=(5, 0))
        
        # Email
        email_frame = Frame(right_column, bg='#ffffff')
        email_frame.pack(fill=X, pady=5)
        Label(email_frame, text="Email:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['email'] = Entry(email_frame, width=30, font=("Arial", 11))
        self.entries['email'].pack(fill=X, pady=(5, 0))
        
        # Phone
        phone_frame = Frame(right_column, bg='#ffffff')
        phone_frame.pack(fill=X, pady=5)
        Label(phone_frame, text="Telefon:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['phone_number'] = Entry(phone_frame, width=30, font=("Arial", 11))
        self.entries['phone_number'].pack(fill=X, pady=(5, 0))
        
        # Bank name
        bank_frame = Frame(right_column, bg='#ffffff')
        bank_frame.pack(fill=X, pady=5)
        Label(bank_frame, text="Nazwa banku:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['bank_name'] = Entry(bank_frame, width=30, font=("Arial", 11))
        self.entries['bank_name'].pack(fill=X, pady=(5, 0))
        
        # Account number - full width
        account_frame = Frame(inner_frame, bg='#ffffff')
        account_frame.pack(fill=X, pady=10)
        Label(account_frame, text="Numer konta:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['account_number'] = Entry(account_frame, width=60, font=("Arial", 11))
        self.entries['account_number'].pack(fill=X, pady=(5, 0))
    
    def create_offer_details_section(self, parent):
        """Create offer details settings section"""
        # Section title
        offer_title = Label(parent, text="Szczegóły oferty - domyślne wartości", 
                           font=("Arial", 16, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        offer_title.pack(anchor=W, pady=(20, 20))
        
        # Main form frame with border
        form_frame = Frame(parent, bg='#ffffff', relief=RIDGE, bd=2)
        form_frame.pack(fill=X, pady=(0, 30))
        
        # Inner frame with padding
        inner_frame = Frame(form_frame, bg='#ffffff')
        inner_frame.pack(fill=X, padx=20, pady=20)
        
        # Create two columns
        columns_frame = Frame(inner_frame, bg='#ffffff')
        columns_frame.pack(fill=X)
        
        left_column = Frame(columns_frame, bg='#ffffff')
        left_column.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        right_column = Frame(columns_frame, bg='#ffffff')
        right_column.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))
        
        # Termin realizacji
        termin_realizacji_frame = Frame(left_column, bg='#ffffff')
        termin_realizacji_frame.pack(fill=X, pady=5)
        Label(termin_realizacji_frame, text="Termin realizacji:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['termin_realizacji'] = Entry(termin_realizacji_frame, width=30, font=("Arial", 11))
        self.entries['termin_realizacji'].pack(fill=X, pady=(5, 0))
        
        # Termin płatności
        termin_platnosci_frame = Frame(left_column, bg='#ffffff')
        termin_platnosci_frame.pack(fill=X, pady=5)
        Label(termin_platnosci_frame, text="Termin płatności:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['termin_platnosci'] = Entry(termin_platnosci_frame, width=30, font=("Arial", 11))
        self.entries['termin_platnosci'].pack(fill=X, pady=(5, 0))
        
        # Warunki dostawy
        warunki_dostawy_frame = Frame(left_column, bg='#ffffff')
        warunki_dostawy_frame.pack(fill=X, pady=5)
        Label(warunki_dostawy_frame, text="Warunki dostawy:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['warunki_dostawy'] = Entry(warunki_dostawy_frame, width=30, font=("Arial", 11))
        self.entries['warunki_dostawy'].pack(fill=X, pady=(5, 0))
        
        # Ważność oferty
        waznosc_oferty_frame = Frame(right_column, bg='#ffffff')
        waznosc_oferty_frame.pack(fill=X, pady=5)
        Label(waznosc_oferty_frame, text="Ważność oferty:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['waznosc_oferty'] = Entry(waznosc_oferty_frame, width=30, font=("Arial", 11))
        self.entries['waznosc_oferty'].pack(fill=X, pady=(5, 0))
        
        # Gwarancja
        gwarancja_frame = Frame(right_column, bg='#ffffff')
        gwarancja_frame.pack(fill=X, pady=5)
        Label(gwarancja_frame, text="Gwarancja:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['gwarancja'] = Entry(gwarancja_frame, width=30, font=("Arial", 11))
        self.entries['gwarancja'].pack(fill=X, pady=(5, 0))
        
        # Cena
        cena_frame = Frame(right_column, bg='#ffffff')
        cena_frame.pack(fill=X, pady=5)
        Label(cena_frame, text="Cena:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['cena'] = Entry(cena_frame, width=30, font=("Arial", 11))
        self.entries['cena'].pack(fill=X, pady=(5, 0))
    
    def create_buttons_section(self, parent):
        """Create buttons section"""
        buttons_frame = Frame(parent, bg='#f0f0f0')
        buttons_frame.pack(fill=X, pady=20)
        
        # Save button
        save_btn = Button(buttons_frame, text="Zapisz ustawienia",
                         font=("Arial", 14, "bold"),
                         bg='#28a745', fg='black',
                         padx=30, pady=15,
                         command=self.save_settings,
                         cursor='hand2')
        save_btn.pack(side=LEFT, padx=10)
    
    def load_current_settings(self):
        """Load current settings into the form"""
        # Load company data
        company_settings = self.settings_manager.get_all_company_data_settings()
        company_fields = ['town', 'address_1', 'address_2', 'nip', 'regon', 'email', 'phone_number', 'bank_name', 'account_number']
        
        for field in company_fields:
            if field in self.entries:
                value = company_settings.get(field, '')
                self.entries[field].delete(0, END)
                self.entries[field].insert(0, value)
        
        # Load offer details data
        offer_details_settings = self.settings_manager.get_all_offer_details_settings()
        offer_details_fields = ['termin_realizacji', 'termin_platnosci', 'warunki_dostawy', 'waznosc_oferty', 'gwarancja', 'cena']
        
        for field in offer_details_fields:
            if field in self.entries:
                value = offer_details_settings.get(field, '')
                self.entries[field].delete(0, END)
                self.entries[field].insert(0, value)
    
    def save_settings(self):
        """Save settings to file"""
        # Collect company data settings
        company_fields = ['town', 'address_1', 'address_2', 'nip', 'regon', 'email', 'phone_number', 'bank_name', 'account_number']
        company_settings = {}
        for field in company_fields:
            if field in self.entries:
                company_settings[field] = self.entries[field].get().strip()
        
        # Update settings
        self.settings_manager.update_company_data_settings(company_settings)
        
        # Collect offer details settings
        offer_details_fields = ['termin_realizacji', 'termin_platnosci', 'warunki_dostawy', 'waznosc_oferty', 'gwarancja', 'cena']
        offer_details_settings = {}
        for field in offer_details_fields:
            if field in self.entries:
                offer_details_settings[field] = self.entries[field].get().strip()
        
        # Update offer details settings
        self.settings_manager.update_offer_details_settings(offer_details_settings)
        
        # Save to file
        if self.settings_manager.save_settings():
            # Refresh company data in any existing offer creation windows
            self.refresh_offer_creation_data()
            tkinter.messagebox.showinfo("Sukces", "Ustawienia zostały zapisane pomyślnie!")
        else:
            tkinter.messagebox.showerror("Błąd", "Nie udało się zapisać ustawień.")
    
    def refresh_offer_creation_data(self):
        """Refresh company data in offer creation window if it exists"""
        try:
            if hasattr(self.nav_manager, 'frames') and 'offer_creation' in self.nav_manager.frames:
                offer_frame = self.nav_manager.frames['offer_creation']
                if hasattr(offer_frame, 'offer_app') and hasattr(offer_frame.offer_app, 'ui'):
                    offer_frame.offer_app.ui.refresh_company_data()
        except Exception as e:
            print(f"Could not refresh offer creation data: {e}")
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
