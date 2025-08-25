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
                           fg='black',
                           padx=15, pady=8,
                           command=self.return_to_main_menu,
                           cursor='hand2')
        return_btn.pack(side=RIGHT)
        
        # Main scrollable frame
        main_canvas = Canvas(self, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=main_canvas.yview)
        self.scrollable_frame = Frame(main_canvas, bg='#f0f0f0')
        
        # Configure scrolling
        self.scrollable_frame.bind('<Configure>', self.on_frame_configure)
        main_canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.canvas_window = main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar with original layout
        main_canvas.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for scrolling
        self.main_canvas = main_canvas
        
        # Make sure the canvas can receive focus for mouse wheel events
        self.main_canvas.focus_set()
        
        # Bind mouse wheel events for scrolling
        self.bind_mousewheel(self.main_canvas)
        self.bind_mousewheel(self.main_canvas.master)
        self.bind_mousewheel(self)
        
        # Bind globally to the entire frame for universal scrolling
        self.bind_all("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Button-4>", self.on_mousewheel)
        self.bind_all("<Button-5>", self.on_mousewheel)
        self.bind_all("<Shift-MouseWheel>", self.on_mousewheel)
        
        # Content container
        content_container = Frame(self.scrollable_frame, bg='#f0f0f0')
        content_container.pack(fill=BOTH, expand=True, pady=20)
        
        # Company data section
        self.create_company_data_section(content_container)
        
        # Offer details section
        self.create_offer_details_section(content_container)
        
        # App settings section
        self.create_app_settings_section(content_container)
        
        # Buttons section
        self.create_buttons_section(self.scrollable_frame)
        
        # Bind mouse wheel events to all Entry widgets after creating the UI
        self.bind_mousewheel_to_entries()
    
    def update_scroll_region(self):
        """Update the scroll region of the canvas"""
        if hasattr(self, 'main_canvas'):
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
    
    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """Configure the inner frame to fit the canvas"""
        # Don't auto-resize the inner frame width to match canvas
        # This keeps the original layout where content doesn't expand to full width
        pass
    
    def create_company_data_section(self, parent):
        """Create company data settings section"""
        # Section title
        company_title = Label(parent, text="Górna sekcja zapytania ofertowego - domyślne wartości", 
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
        offer_title = Label(parent, text="Dolna sekcja zapytania ofertowego - domyślne wartości", 
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
        self.entries['termin_realizacji'] = Entry(termin_realizacji_frame, width=60, font=("Arial", 11))
        self.entries['termin_realizacji'].pack(fill=X, pady=(5, 0))
        
        # Termin płatności
        termin_platnosci_frame = Frame(left_column, bg='#ffffff')
        termin_platnosci_frame.pack(fill=X, pady=5)
        Label(termin_platnosci_frame, text="Termin płatności:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['termin_platnosci'] = Entry(termin_platnosci_frame, width=60, font=("Arial", 11))
        self.entries['termin_platnosci'].pack(fill=X, pady=(5, 0))
        
        # Warunki dostawy
        warunki_dostawy_frame = Frame(left_column, bg='#ffffff')
        warunki_dostawy_frame.pack(fill=X, pady=5)
        Label(warunki_dostawy_frame, text="Warunki dostawy:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['warunki_dostawy'] = Entry(warunki_dostawy_frame, width=60, font=("Arial", 11))
        self.entries['warunki_dostawy'].pack(fill=X, pady=(5, 0))
        
        # Ważność oferty
        waznosc_oferty_frame = Frame(right_column, bg='#ffffff')
        waznosc_oferty_frame.pack(fill=X, pady=5)
        Label(waznosc_oferty_frame, text="Ważność oferty:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['waznosc_oferty'] = Entry(waznosc_oferty_frame, width=60, font=("Arial", 11))
        self.entries['waznosc_oferty'].pack(fill=X, pady=(5, 0))
        
        # Gwarancja
        gwarancja_frame = Frame(right_column, bg='#ffffff')
        gwarancja_frame.pack(fill=X, pady=5)
        Label(gwarancja_frame, text="Gwarancja:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['gwarancja'] = Entry(gwarancja_frame, width=60, font=("Arial", 11))
        self.entries['gwarancja'].pack(fill=X, pady=(5, 0))
        
        # Cena
        cena_frame = Frame(right_column, bg='#ffffff')
        cena_frame.pack(fill=X, pady=5)
        Label(cena_frame, text="Cena:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        self.entries['cena'] = Entry(cena_frame, width=60, font=("Arial", 11))
        self.entries['cena'].pack(fill=X, pady=(5, 0))
    
    def create_app_settings_section(self, parent):
        """Create app settings section"""
        # Section title
        app_title = Label(parent, text="Inne ustawienia aplikacji", 
                         font=("Arial", 16, "bold"), 
                         bg='#f0f0f0', fg='#333333')
        app_title.pack(anchor=W, pady=(20, 20))
        
        # Main form frame with border
        form_frame = Frame(parent, bg='#ffffff', relief=RIDGE, bd=2)
        form_frame.pack(fill=X, pady=(0, 30))
        
        # Inner frame with padding
        inner_frame = Frame(form_frame, bg='#ffffff')
        inner_frame.pack(fill=X, padx=20, pady=20)
        
        # Offers folder
        offers_folder_frame = Frame(inner_frame, bg='#ffffff')
        offers_folder_frame.pack(fill=X, pady=5)
        
        # Label and description
        label_frame = Frame(offers_folder_frame, bg='#ffffff')
        label_frame.pack(fill=X, pady=(0, 5))
        Label(label_frame, text="Folder z ofertami:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        Label(label_frame, text="Ścieżka do folderu gdzie są przechowywane oferty", 
              font=("Arial", 9), bg='#ffffff', fg='#666666').pack(anchor=W)
        
        # Entry and browse button
        entry_frame = Frame(offers_folder_frame, bg='#ffffff')
        entry_frame.pack(fill=X, pady=(5, 0))
        
        self.entries['offers_folder'] = Entry(entry_frame, width=50, font=("Arial", 11))
        self.entries['offers_folder'].pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        browse_btn = Button(entry_frame, text="Przeglądaj...",
                           font=("Arial", 10),
                           fg='white',
                           padx=15, pady=5,
                           command=self.browse_offers_folder,
                           cursor='hand2')
        browse_btn.pack(side=RIGHT)
        
        # Separator
        separator = Frame(inner_frame, height=1, bg='#dddddd')
        separator.pack(fill=X, pady=20)
        
        # WZ folder
        wz_folder_frame = Frame(inner_frame, bg='#ffffff')
        wz_folder_frame.pack(fill=X, pady=5)
        
        # Label and description
        label_frame = Frame(wz_folder_frame, bg='#ffffff')
        label_frame.pack(fill=X, pady=(0, 5))
        Label(label_frame, text="Folder WZ:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        Label(label_frame, text="Ścieżka do folderu gdzie są przechowywane dokumenty WZ", 
              font=("Arial", 9), bg='#ffffff', fg='#666666').pack(anchor=W)
        
        # Entry and browse button
        entry_frame = Frame(wz_folder_frame, bg='#ffffff')
        entry_frame.pack(fill=X, pady=(5, 0))
        
        self.entries['wz_folder'] = Entry(entry_frame, width=50, font=("Arial", 11))
        self.entries['wz_folder'].pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        browse_btn = Button(entry_frame, text="Przeglądaj...",
                           font=("Arial", 10),
                           fg='white',
                           padx=15, pady=5,
                           command=self.browse_wz_folder,
                           cursor='hand2')
        browse_btn.pack(side=RIGHT)
        
        # Separator
        separator2 = Frame(inner_frame, height=1, bg='#dddddd')
        separator2.pack(fill=X, pady=20)
        
        # Database path
        database_path_frame = Frame(inner_frame, bg='#ffffff')
        database_path_frame.pack(fill=X, pady=5)
        
        # Label and description
        label_frame = Frame(database_path_frame, bg='#ffffff')
        label_frame.pack(fill=X, pady=(0, 5))
        Label(label_frame, text="Ścieżka do bazy danych:", 
              font=("Arial", 11, "bold"), bg='#ffffff').pack(anchor=W)
        Label(label_frame, text="Ścieżka do pliku bazy danych SQLite (.db)", 
              font=("Arial", 9), bg='#ffffff', fg='#666666').pack(anchor=W)
        
        # Entry and browse button
        db_entry_frame = Frame(database_path_frame, bg='#ffffff')
        db_entry_frame.pack(fill=X, pady=(5, 0))
        
        self.entries['database_path'] = Entry(db_entry_frame, width=50, font=("Arial", 11))
        self.entries['database_path'].pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        browse_db_btn = Button(db_entry_frame, text="Przeglądaj...",
                              font=("Arial", 10),
                              fg='white',
                              padx=15, pady=5,
                              command=self.browse_database_file,
                              cursor='hand2')
        browse_db_btn.pack(side=RIGHT)

    def browse_offers_folder(self):
        """Open folder browser for offers folder"""
        from tkinter import filedialog
        
        current_folder = self.entries['offers_folder'].get()
        
        folder_path = filedialog.askdirectory(
            title="Wybierz folder dla ofert",
            initialdir=current_folder if os.path.exists(current_folder) else os.path.expanduser("~")
        )
        
        if folder_path:
            self.entries['offers_folder'].delete(0, END)
            self.entries['offers_folder'].insert(0, folder_path)
    
    def browse_wz_folder(self):
        """Open folder browser for WZ folder"""
        from tkinter import filedialog
        
        current_folder = self.entries['wz_folder'].get()
        
        folder_path = filedialog.askdirectory(
            title="Wybierz folder dla WZ",
            initialdir=current_folder if os.path.exists(current_folder) else os.path.expanduser("~")
        )
        
        if folder_path:
            self.entries['wz_folder'].delete(0, END)
            self.entries['wz_folder'].insert(0, folder_path)
    
    def browse_database_file(self):
        """Open file browser for database file"""
        from tkinter import filedialog
        
        current_path = self.entries['database_path'].get()
        if not current_path:
            current_path = self.settings_manager.get_app_setting('database_path')
        
        # Get initial directory
        if current_path and os.path.exists(current_path):
            initial_dir = os.path.dirname(current_path)
            initial_file = os.path.basename(current_path)
        else:
            initial_dir = os.path.expanduser("~")
            initial_file = "DocumentsCreationData.db"
        
        file_path = filedialog.askopenfilename(
            title="Wybierz plik bazy danych",
            initialdir=initial_dir,
            initialfile=initial_file,
            filetypes=[
                ("SQLite Database", "*.db"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.entries['database_path'].delete(0, END)
            self.entries['database_path'].insert(0, file_path)
    
    def create_buttons_section(self, parent):
        """Create buttons section"""
        buttons_frame = Frame(parent, bg='#f0f0f0')
        buttons_frame.pack(fill=X, pady=20)
        
        # Save button
        save_btn = Button(buttons_frame, text="Zapisz ustawienia",
                         font=("Arial", 14, "bold"),
                         fg='black',
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
        
        # Load app settings data (but not offers_folder)
        app_settings = self.settings_manager.get_all_app_settings()
        # offers_folder comes only from DB (Paths table)
        try:
            from src.data.database_service import get_offers_root_from_db
            offers_folder = get_offers_root_from_db()
            if 'offers_folder' in self.entries:
                self.entries['offers_folder'].delete(0, END)
                self.entries['offers_folder'].insert(0, offers_folder or '')
        except Exception:
            # If DB access fails, leave the entry as-is (empty)
            pass

        # database_path still from app settings; wz_folder from DB Paths
        for field in ['database_path']:
            if field in self.entries:
                value = app_settings.get(field, '')
                self.entries[field].delete(0, END)
                self.entries[field].insert(0, value)

        # Load WZ folder from DB Paths
        try:
            from src.data.database_service import get_wz_root_from_db
            wz_folder = get_wz_root_from_db()
            if 'wz_folder' in self.entries:
                self.entries['wz_folder'].delete(0, END)
                self.entries['wz_folder'].insert(0, wz_folder or '')
        except Exception:
            pass
    
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

        # Collect app settings and check if critical settings changed
        # offers_folder and wz_folder are stored ONLY in DB (Paths); database_path in app settings
        app_fields = ['database_path']
        app_settings = {}
        offers_folder_changed = False
        wz_folder_changed = False
        offers_folder_old = None
        wz_folder_old = None
        database_path_changed = False

        # First handle offers_folder via DB
        new_offers_folder = ''
        try:
            from src.data.database_service import get_offers_root_from_db
            offers_folder_old = get_offers_root_from_db()
        except Exception:
            offers_folder_old = ''
        if 'offers_folder' in self.entries:
            new_offers_folder = self.entries['offers_folder'].get().strip()
            if new_offers_folder != offers_folder_old:
                offers_folder_changed = True

        # Handle remaining app fields (database_path only)
        for field in app_fields:
            if field in self.entries:
                new_value = self.entries[field].get().strip()
                old_value = self.settings_manager.get_app_setting(field)
                app_settings[field] = new_value
                if field == 'database_path' and new_value != old_value:
                    database_path_changed = True

        # Update offers folder in DB and update app settings for remaining fields
        if offers_folder_changed:
            try:
                from src.data.database_service import set_offers_root_in_db
                set_offers_root_in_db(new_offers_folder)
            except Exception as e:
                print(f"Failed to update Offers_Folder in DB: {e}")

        # Update app settings (no DB path migrations for offers/WZ)
        self.settings_manager.update_app_settings(app_settings)

        # Update WZ folder in DB if changed
        new_wz_folder = ''
        try:
            from src.data.database_service import get_wz_root_from_db
            wz_folder_old = get_wz_root_from_db()
        except Exception:
            wz_folder_old = ''
        if 'wz_folder' in self.entries:
            new_wz_folder = self.entries['wz_folder'].get().strip()
            if new_wz_folder != wz_folder_old:
                wz_folder_changed = True
                try:
                    from src.data.database_service import set_wz_root_in_db
                    set_wz_root_in_db(new_wz_folder)
                except Exception as e:
                    print(f"Failed to update Wz_Folder in DB: {e}")

        # Validate database path if it changed
        if database_path_changed:
            new_db_path = app_settings.get('database_path', '')
            if new_db_path and not os.path.exists(new_db_path):
                result = tkinter.messagebox.askyesno(
                    "Uwaga",
                    f"Podana ścieżka do bazy danych nie istnieje:\n{new_db_path}\n\nCzy chcesz kontynuować? Aplikacja może nie działać poprawnie."
                )
                if not result:
                    return  # Don't save if user cancels

        # Save to file
        if self.settings_manager.save_settings():
            # Check if app restart is needed
            if offers_folder_changed or wz_folder_changed or database_path_changed:
                self.show_restart_prompt(database_path_changed)
            else:
                # Refresh company data in any existing offer creation windows
                self.refresh_offer_creation_data()
                tkinter.messagebox.showinfo("Sukces", "Ustawienia zostały zapisane pomyślnie!")
        else:
            tkinter.messagebox.showerror("Błąd", "Nie udało się zapisać ustawień.")
    
    def show_restart_prompt(self, database_changed=False):
        """Show restart prompt when critical settings have changed"""
        import tkinter.messagebox
        
        if database_changed:
            message = ("Ścieżka do bazy danych została zmieniona.\n"
                      "Aplikacja musi zostać uruchomiona ponownie żeby zmiany zaczęły obowiązywać.\n\n"
                      "Kliknij OK aby kontynuować.")
        else:
            message = ("Ścieżka do folderu z ofertami i/lub WZkami została zmieniona.\n"
                      "Aplikacja zostanie uruchomiona ponownie.\n\n"
                      "Kliknij OK aby kontynuować.")
        
        result = tkinter.messagebox.showinfo("Restart wymagany", message, type='ok')
        if result == 'ok':
            self.restart_application()
    
    def restart_application(self):
        """Restart the application"""
        import sys
        import os
        import subprocess
        
        try:
            # Get the current script path
            script_path = os.path.abspath(sys.argv[0])
            
            # Close current application
            self.nav_manager.root.quit()
            self.nav_manager.root.destroy()
            
            # Start new instance
            if sys.platform.startswith('win'):
                subprocess.Popen([sys.executable, script_path])
            else:
                subprocess.Popen([sys.executable, script_path])
                
            # Exit current process
            sys.exit(0)
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się uruchomić aplikacji ponownie: {e}")
            print(f"Restart error: {e}")
    
    def refresh_offer_creation_data(self):
        """Refresh company data in offer creation window if it exists"""
        try:
            # Check both offer_creation and offer_generator frames
            for frame_name in ['offer_creation', 'offer_generator']:
                if hasattr(self.nav_manager, 'frames') and frame_name in self.nav_manager.frames:
                    offer_frame = self.nav_manager.frames[frame_name]
                    # Check if the frame has an initialized offer app instance
                    if hasattr(offer_frame, 'offer_app_instance') and offer_frame.offer_app_instance:
                        if hasattr(offer_frame.offer_app_instance, 'ui'):
                            print(f"Refreshing company data in {frame_name}")
                            offer_frame.offer_app_instance.ui.refresh_company_data()
        except Exception as e:
            print(f"Could not refresh offer creation data: {e}")
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def bind_mousewheel(self, widget):
        """Bind mouse wheel events to a widget"""
        # Bind mousewheel events for different platforms
        widget.bind("<MouseWheel>", self.on_mousewheel)  # Windows and macOS
        widget.bind("<Button-4>", self.on_mousewheel)    # Linux
        widget.bind("<Button-5>", self.on_mousewheel)    # Linux
        
        # Additional macOS touchpad events
        widget.bind("<Shift-MouseWheel>", self.on_mousewheel)
        
        # Try to bind to all child widgets as well for better coverage
        for child in widget.winfo_children():
            try:
                self.bind_mousewheel(child)
            except:
                pass
    
    def bind_mousewheel_to_entries(self):
        """Bind mouse wheel events to all Entry widgets in settings"""
        # Bind to all Entry widgets that were created
        for entry_name, entry_widget in self.entries.items():
            try:
                entry_widget.bind("<MouseWheel>", self.on_mousewheel)
                entry_widget.bind("<Button-4>", self.on_mousewheel)
                entry_widget.bind("<Button-5>", self.on_mousewheel)
                entry_widget.bind("<Shift-MouseWheel>", self.on_mousewheel)
            except:
                pass
        
        # Also bind to all Button widgets in the frame
        def bind_to_all_widgets(widget):
            """Recursively bind mouse wheel to all widgets"""
            try:
                # Skip binding to Entry widgets as they're handled above
                if not isinstance(widget, Entry):
                    widget.bind("<MouseWheel>", self.on_mousewheel)
                    widget.bind("<Button-4>", self.on_mousewheel)
                    widget.bind("<Button-5>", self.on_mousewheel)
                    widget.bind("<Shift-MouseWheel>", self.on_mousewheel)
            except:
                pass
            
            # Recursively bind to all children
            try:
                for child in widget.winfo_children():
                    bind_to_all_widgets(child)
            except:
                pass
        
        # Bind to all widgets in the scrollable frame
        if hasattr(self, 'scrollable_frame'):
            bind_to_all_widgets(self.scrollable_frame)
    
    def unbind_mousewheel(self, widget):
        """Unbind mouse wheel events from a widget"""
        widget.unbind("<MouseWheel>")
        widget.unbind("<Button-4>")
        widget.unbind("<Button-5>")
        widget.unbind("<Shift-MouseWheel>")
    
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        try:
            # Only scroll if this frame is currently visible
            if not self.winfo_viewable():
                return
                
            # Different handling for different platforms and event types
            if hasattr(event, 'delta') and event.delta:
                # Windows and macOS
                delta = event.delta
                # Normalize delta for better scrolling experience
                if abs(delta) > 100:
                    delta = delta // abs(delta) * 120  # Normalize to standard wheel step
            elif hasattr(event, 'num') and event.num == 4:
                # Linux scroll up
                delta = 120
            elif hasattr(event, 'num') and event.num == 5:
                # Linux scroll down
                delta = -120
            else:
                delta = 0
            
            # Apply scrolling to canvas
            if hasattr(self, 'main_canvas') and self.main_canvas:
                self.main_canvas.yview_scroll(int(-1 * (delta / 120)), "units")
                return "break"  # Prevent event propagation
        except Exception as e:
            pass  # Silently ignore scrolling errors
    
    def hide(self):
        """Hide this frame"""
        # Unbind global mouse wheel events to prevent conflicts
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")
        self.unbind_all("<Shift-MouseWheel>")
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
        
        # Re-bind global mouse wheel events when showing
        self.bind_all("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Button-4>", self.on_mousewheel)
        self.bind_all("<Button-5>", self.on_mousewheel)
        self.bind_all("<Shift-MouseWheel>", self.on_mousewheel)
        
        # Re-bind mouse wheel events to all Entry widgets
        self.bind_mousewheel_to_entries()
        
        # Force focus to canvas to ensure mouse wheel events work
        if hasattr(self, 'main_canvas'):
            self.after(100, lambda: self.main_canvas.focus_force())
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
