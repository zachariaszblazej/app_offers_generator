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
