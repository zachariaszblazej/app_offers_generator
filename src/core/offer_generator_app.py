"""
Core offer generator application logic
"""
from tkinter import *
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ui.components.ui_components import UIComponents
from src.ui.windows.client_search_window import ClientSearchWindow
from src.ui.windows.supplier_search_window import SupplierSearchWindow
from src.ui.windows.product_add_window import ProductAddWindow
from src.ui.components.product_table import ProductTable
from src.services.offer_generator_service import generate_offer_document
from src.utils.config import BACKGROUND_IMAGE


class OfferGeneratorApp:
    """Original offer generator app, now embedded within a frame"""
    
    def __init__(self, parent_frame, nav_manager):
        self.parent_frame = parent_frame
        self.nav_manager = nav_manager
        # Use content_container instead of offer_container
        self.window = parent_frame.content_container
        
        # Initialize components
        self.setup_ui()
        
        # Initialize calculation variables
        self.count = 0
    
    def setup_ui(self):
        """Setup all UI components within the parent frame"""
        # Set background
        try:
            bg = PhotoImage(file=BACKGROUND_IMAGE)
            label_BG = Label(self.window, image=bg)
            label_BG.place(x=0, y=0)
            label_BG.image = bg  # Keep a reference
        except Exception as e:
            print(f"Could not load background image: {e}")
            # If background image fails, use a clean professional color
            self.window.configure(bg='#f5f5f5')
        
        # Initialize UI components
        self.product_table = ProductTable(self.window)
        self.ui = UIComponents(self.window, self.product_table)
        self.client_search = ClientSearchWindow(self.window, self.ui.fill_client_data)
        self.supplier_search = SupplierSearchWindow(self.window, self.ui.fill_supplier_data)
        self.product_add = ProductAddWindow(self.window, self.insert_product)
        
        # Create UI sections
        self.ui.create_upper_section()
        self.ui.create_offer_section()
        self.ui.create_totals_section()
        
        # Create buttons
        self.create_buttons()
    
    def create_buttons(self):
        """Create all buttons"""
        # Product management buttons
        Button(self.window, text="DODAJ PRODUKT", 
               font=("Arial", 12, "bold"),
               bg='#28a745', fg='black',
               padx=15, pady=8,
               command=self.product_add.open_product_add_window,
               cursor='hand2').place(x=50, y=740)
               
        Button(self.window, text="USUŃ PRODUKT", 
               font=("Arial", 12, "bold"),
               bg='#dc3545', fg='black',
               padx=15, pady=8,
               command=self.remove_product,
               cursor='hand2').place(x=260, y=740)
                
        # Client search button
        search_client_button = Button(self.window, text="Szukaj klienta", 
                                    font=("Arial", 10),
                                    command=self.client_search.open_client_search)
        search_client_button.place(x=900, y=360)
        
        # Supplier search button
        search_supplier_button = Button(self.window, text="Szukaj dostawcę", 
                                      font=("Arial", 10),
                                      command=self.supplier_search.open_supplier_search)
        search_supplier_button.place(x=300, y=360)
        
        # Generate offer button
        generate_offer_button = Button(self.window, text="Generuj ofertę", 
                                     font=("Arial", 12, "bold"),
                                     command=self.generate_offer)
        generate_offer_button.place(x=700, y=800)
    
    def insert_product(self, product_data):
        """Insert a new product into the table"""
        if self.product_table.input_record(product_data):
            # Automatically recalculate total
            self.calc_total()
            return True
        return False
    
    def remove_product(self):
        """Remove selected product from the table"""
        self.product_table.remove_record()
        # Automatically recalculate total after removal
        self.calc_total()
    
    def calc_total(self):
        """Calculate and display totals"""
        # Calculate totals from product table
        total = self.product_table.calculate_totals()
        
        # Update the suma field using the new method
        self.ui.update_suma(total)
    
    def generate_offer(self):
        """Generate the offer document"""
        # Get form data
        context_data = self.ui.get_context_data()
        
        # Keep date as datetime object for offer generation
        # The conversion to string will be handled in generate_offer_document
        
        # Generate document
        generate_offer_document(context_data)
