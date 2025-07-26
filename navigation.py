from tkinter import *
from tkinter import ttk
from config import WINDOW_SIZE, BACKGROUND_IMAGE, APP_VERSION

class NavigationManager:
    """Manages navigation between different screens/frames"""
    
    def __init__(self, root_window):
        self.root = root_window
        self.current_frame = None
        self.frames = {}
        
    def add_frame(self, name, frame_class, *args, **kwargs):
        """Add a frame to the navigation manager"""
        frame = frame_class(self.root, self, *args, **kwargs)
        self.frames[name] = frame
        return frame
    
    def show_frame(self, frame_name):
        """Show a specific frame and hide others"""
        if self.current_frame:
            self.current_frame.pack_forget()
        
        if frame_name in self.frames:
            self.current_frame = self.frames[frame_name]
            self.current_frame.pack(fill=BOTH, expand=True)
            
            # Initialize offer app if this is the offer creation frame
            if frame_name == 'offer_creation' and hasattr(self.current_frame, 'initialize_offer_app'):
                self.current_frame.initialize_offer_app()
        else:
            raise ValueError(f"Frame '{frame_name}' not found")

class MainMenuFrame(Frame):
    """Main menu frame with navigation options"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.create_ui()
    
    def create_ui(self):
        """Create the main menu UI"""
        # Set background color to match the application theme
        self.configure(bg='#f0f0f0')
        
        # Main title
        title_label = Label(self, text="Generator Ofert", 
                           font=("Arial", 24, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=50)
        
        # Subtitle
        subtitle_label = Label(self, text="System tworzenia ofert handlowych", 
                              font=("Arial", 14), 
                              bg='#f0f0f0', fg='#666666')
        subtitle_label.pack(pady=10)
        
        # Main menu buttons frame
        buttons_frame = Frame(self, bg='#f0f0f0')
        buttons_frame.pack(pady=50)
        
        # Create new offer button
        new_offer_btn = Button(buttons_frame, 
                              text="Stwórz nową ofertę",
                              font=("Arial", 16, "bold"),
                              bg='#4CAF50', fg='white',
                              padx=30, pady=15,
                              command=self.open_new_offer,
                              cursor='hand2')
        new_offer_btn.pack(pady=15)
        
        # View offers button (placeholder for future functionality)
        view_offers_btn = Button(buttons_frame, 
                                text="Przeglądaj oferty",
                                font=("Arial", 14),
                                bg='#2196F3', fg='white',
                                padx=30, pady=10,
                                command=self.view_offers,
                                cursor='hand2')
        view_offers_btn.pack(pady=10)
        
        # Add client button
        add_client_btn = Button(buttons_frame, 
                               text="Dodaj klienta",
                               font=("Arial", 14),
                               bg='#9C27B0', fg='white',
                               padx=30, pady=10,
                               command=self.add_client,
                               cursor='hand2')
        add_client_btn.pack(pady=10)
        
        # Settings button (placeholder for future functionality)
        settings_btn = Button(buttons_frame, 
                             text="Ustawienia",
                             font=("Arial", 14),
                             bg='#FF9800', fg='white',
                             padx=30, pady=10,
                             command=self.open_settings,
                             cursor='hand2')
        settings_btn.pack(pady=10)
        
        # Exit button
        exit_btn = Button(buttons_frame, 
                         text="Zamknij aplikację",
                         font=("Arial", 12),
                         bg='#f44336', fg='white',
                         padx=20, pady=8,
                         command=self.exit_application,
                         cursor='hand2')
        exit_btn.pack(pady=(30, 10))
        
        # Version info
        version_label = Label(self, text=f"Wersja {APP_VERSION} - Zrefaktorowana", 
                             font=("Arial", 10), 
                             bg='#f0f0f0', fg='#999999')
        version_label.pack(side=BOTTOM, pady=20)
    
    def open_new_offer(self):
        """Navigate to offer creation screen"""
        self.nav_manager.show_frame('offer_creation')
    
    def view_offers(self):
        """Placeholder for viewing offers functionality"""
        import tkinter.messagebox
        tkinter.messagebox.showinfo("Informacja", "Funkcja przeglądania ofert będzie dostępna wkrótce!")
    
    def add_client(self):
        """Navigate to add client screen"""
        self.nav_manager.show_frame('add_client')
    
    def open_settings(self):
        """Placeholder for settings functionality"""
        import tkinter.messagebox
        tkinter.messagebox.showinfo("Informacja", "Funkcja ustawień będzie dostępna wkrótce!")
    
    def exit_application(self):
        """Exit the application"""
        import tkinter.messagebox
        if tkinter.messagebox.askquestion("Potwierdzenie", "Czy na pewno chcesz zamknąć aplikację?") == 'yes':
            self.nav_manager.root.destroy()

class OfferCreationFrame(Frame):
    """Frame for offer creation (current functionality)"""
    
    def __init__(self, parent, nav_manager, offer_app_class):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offer_app_class = offer_app_class
        self.offer_app_instance = None
        self.create_ui()
    
    def create_ui(self):
        """Create the offer creation UI"""
        # Create a container for the offer app
        self.offer_container = Frame(self, bg='white')
        self.offer_container.pack(fill=BOTH, expand=True)
        
        # Back button frame (top-left)
        back_frame = Frame(self.offer_container, bg='white', height=40)
        back_frame.pack(fill=X, padx=10, pady=5)
        back_frame.pack_propagate(False)
        
        back_btn = Button(back_frame, 
                         text="← Powrót do menu głównego",
                         font=("Arial", 12),
                         bg='#9E9E9E', fg='white',
                         padx=15, pady=5,
                         command=self.return_to_main_menu,
                         cursor='hand2')
        back_btn.pack(side=LEFT)
        
        # Create content container for the offer application
        self.content_container = Frame(self.offer_container, bg='white')
        self.content_container.pack(fill=BOTH, expand=True, padx=10, pady=5)
    
    def initialize_offer_app(self):
        """Initialize the offer application components"""
        try:
            if not self.offer_app_instance:
                self.offer_app_instance = self.offer_app_class(self, self.nav_manager)
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować interfejsu tworzenia oferty: {e}")
            print(f"Detailed error: {e}")  # For debugging
    
    def return_to_main_menu(self):
        """Return to main menu"""
        # Clean up any resources if needed
        if self.offer_app_instance:
            # Perform any necessary cleanup
            pass
        self.nav_manager.show_frame('main_menu')

class AddClientFrame(Frame):
    """Frame for adding new clients"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.entries = {}
        self.create_ui()
    
    def create_ui(self):
        """Create the add client UI"""
        # Set background color
        self.configure(bg='#f0f0f0')
        
        # Header with back button
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=10)
        
        back_btn = Button(header_frame, 
                         text="← Powrót do menu głównego",
                         font=("Arial", 12),
                         bg='#6c757d', fg='white',
                         command=self.return_to_main_menu,
                         cursor='hand2')
        back_btn.pack(side=LEFT)
        
        # Title
        title_label = Label(self, text="Dodaj nowego klienta", 
                           font=("Arial", 20, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=(20, 30))
        
        # Form frame
        form_frame = Frame(self, bg='#f0f0f0')
        form_frame.pack(pady=20, padx=50)
        
        # Company name
        Label(form_frame, text="Nazwa firmy:", font=("Arial", 12), bg='#f0f0f0').grid(row=0, column=0, sticky=W, pady=5)
        self.entries['company_name'] = Entry(form_frame, font=("Arial", 12), width=40)
        self.entries['company_name'].grid(row=0, column=1, padx=10, pady=5)
        
        # Address part 1
        Label(form_frame, text="Adres (część 1):", font=("Arial", 12), bg='#f0f0f0').grid(row=1, column=0, sticky=W, pady=5)
        self.entries['address_p1'] = Entry(form_frame, font=("Arial", 12), width=40)
        self.entries['address_p1'].grid(row=1, column=1, padx=10, pady=5)
        
        # Address part 2
        Label(form_frame, text="Adres (część 2):", font=("Arial", 12), bg='#f0f0f0').grid(row=2, column=0, sticky=W, pady=5)
        self.entries['address_p2'] = Entry(form_frame, font=("Arial", 12), width=40)
        self.entries['address_p2'].grid(row=2, column=1, padx=10, pady=5)
        
        # NIP
        Label(form_frame, text="NIP (10 cyfr):", font=("Arial", 12), bg='#f0f0f0').grid(row=3, column=0, sticky=W, pady=5)
        self.entries['nip'] = Entry(form_frame, font=("Arial", 12), width=40)
        self.entries['nip'].grid(row=3, column=1, padx=10, pady=5)
        self.entries['nip'].bind('<KeyRelease>', self.validate_nip_input)
        
        # Alias
        Label(form_frame, text="Alias:", font=("Arial", 12), bg='#f0f0f0').grid(row=4, column=0, sticky=W, pady=5)
        self.entries['alias'] = Entry(form_frame, font=("Arial", 12), width=40)
        self.entries['alias'].grid(row=4, column=1, padx=10, pady=5)
        self.entries['alias'].bind('<KeyRelease>', self.validate_alias_input)
        
        # Validation labels
        self.validation_labels = {}
        for i, field in enumerate(['company_name', 'address_p1', 'address_p2', 'nip', 'alias']):
            self.validation_labels[field] = Label(form_frame, text="", font=("Arial", 10), bg='#f0f0f0')
            self.validation_labels[field].grid(row=i, column=2, padx=10, pady=5, sticky=W)
        
        # Buttons frame
        buttons_frame = Frame(self, bg='#f0f0f0')
        buttons_frame.pack(pady=30)
        
        # Save button
        save_btn = Button(buttons_frame, 
                         text="Zapisz klienta",
                         font=("Arial", 14, "bold"),
                         bg='#28a745', fg='white',
                         padx=30, pady=15,
                         command=self.save_client,
                         cursor='hand2')
        save_btn.pack(side=LEFT, padx=10)
        
        # Clear button
        clear_btn = Button(buttons_frame, 
                          text="Wyczyść formularz",
                          font=("Arial", 12),
                          bg='#6c757d', fg='white',
                          padx=20, pady=10,
                          command=self.clear_form,
                          cursor='hand2')
        clear_btn.pack(side=LEFT, padx=10)
    
    def validate_nip_input(self, event=None):
        """Real-time NIP validation"""
        from database import validate_nip
        nip = self.entries['nip'].get()
        
        if not nip:
            self.validation_labels['nip'].config(text="", fg='black')
            return
        
        is_valid, message = validate_nip(nip)
        if is_valid:
            self.validation_labels['nip'].config(text="✓ " + message, fg='green')
        else:
            self.validation_labels['nip'].config(text="✗ " + message, fg='red')
    
    def validate_alias_input(self, event=None):
        """Real-time alias validation"""
        from database import validate_alias
        alias = self.entries['alias'].get()
        
        if not alias:
            self.validation_labels['alias'].config(text="", fg='black')
            return
        
        is_valid, message = validate_alias(alias)
        if is_valid:
            self.validation_labels['alias'].config(text="✓ " + message, fg='green')
        else:
            self.validation_labels['alias'].config(text="✗ " + message, fg='red')
    
    def save_client(self):
        """Save the new client to database"""
        from database import add_client_to_db
        import tkinter.messagebox
        
        # Get form data
        company_name = self.entries['company_name'].get().strip()
        address_p1 = self.entries['address_p1'].get().strip()
        address_p2 = self.entries['address_p2'].get().strip()
        nip = self.entries['nip'].get().strip()
        alias = self.entries['alias'].get().strip()
        
        # Basic validation
        if not all([company_name, address_p1, address_p2, nip, alias]):
            tkinter.messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione!")
            return
        
        # Try to save
        success, message = add_client_to_db(nip, company_name, address_p1, address_p2, alias)
        
        if success:
            tkinter.messagebox.showinfo("Sukces", message)
            self.clear_form()
            # Optionally return to main menu
            if tkinter.messagebox.askyesno("Pytanie", "Czy chcesz wrócić do menu głównego?"):
                self.return_to_main_menu()
        else:
            tkinter.messagebox.showerror("Błąd", message)
    
    def clear_form(self):
        """Clear all form fields"""
        for entry in self.entries.values():
            entry.delete(0, END)
        
        # Clear validation labels
        for label in self.validation_labels.values():
            label.config(text="")
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
