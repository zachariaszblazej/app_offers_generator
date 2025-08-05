"""
Offer creation frame for creating new offers
"""
from tkinter import *
import tkinter.messagebox


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
                         bg='#9E9E9E', fg='black',
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
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować interfejsu tworzenia oferty: {e}")
            print(f"Detailed error: {e}")  # For debugging
    
    def return_to_main_menu(self):
        """Return to main menu"""
        # Clean up any resources if needed
        if self.offer_app_instance:
            # Perform any necessary cleanup
            pass
        self.nav_manager.show_frame('main_menu')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
        # Initialize offer app when shown (only if not already initialized)
        if not self.offer_app_instance:
            self.initialize_offer_app()
