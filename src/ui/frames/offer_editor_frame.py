"""
Offer editor frame for editing existing offers
"""
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class OfferEditorFrame(Frame):
    """Frame for editing existing offers"""
    
    def __init__(self, parent, nav_manager, offer_app_class, offer_path=None):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offer_app_class = offer_app_class
        self.offer_app_instance = None
        self.offer_path = offer_path
        self.create_ui()
    
    def create_ui(self):
        """Create the offer editor UI"""
        # Create a container for the offer app
        self.offer_container = Frame(self, bg='white')
        self.offer_container.pack(fill=BOTH, expand=True)
        
        # Back button frame (top-left)
        back_frame = Frame(self.offer_container, bg='white', height=40)
        back_frame.pack(fill=X, padx=10, pady=5)
        back_frame.pack_propagate(False)
        
        back_btn = Button(back_frame, 
                         text="← Powrót do przeglądania ofert",
                         font=("Arial", 12),
                         bg='#9E9E9E', fg='black',
                         padx=15, pady=5,
                         command=self.return_to_browse_offers,
                         cursor='hand2')
        back_btn.pack(side=LEFT)
        
        # Title indicating this is edit mode
        title_label = Label(back_frame, 
                           text="EDYCJA OFERTY",
                           font=("Arial", 16, "bold"),
                           bg='white', fg='#ff6600')
        title_label.pack(side=RIGHT, padx=20)
        
        # Create content container for the offer application
        self.content_container = Frame(self.offer_container, bg='white')
        self.content_container.pack(fill=BOTH, expand=True, padx=10, pady=5)
    
    def initialize_offer_app(self, offer_path=None):
        """Initialize the offer application components for editing"""
        try:
            if not self.offer_app_instance:
                # Create a modified offer app for editing
                from src.core.offer_editor_app import OfferEditorApp
                self.offer_app_instance = OfferEditorApp(self, self.nav_manager, offer_path or self.offer_path)
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować interfejsu edycji oferty: {e}")
            print(f"Detailed error: {e}")  # For debugging
    
    def return_to_browse_offers(self):
        """Return to browse offers"""
        # Clean up any resources if needed
        if self.offer_app_instance:
            # Perform any necessary cleanup
            pass
        self.nav_manager.show_frame('browse_offers')
