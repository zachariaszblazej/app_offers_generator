from tkinter import *
from tkinter import ttk
import locale
from navigation import NavigationManager, MainMenuFrame, OfferCreationFrame, BrowseClientsFrame, BrowseSuppliersFrame, SettingsFrame
from ui_components import UIComponents, ClientSearchWindow, SupplierSearchWindow, ProductAddWindow
from offer_generator import generate_offer_document, convert_date
from config import WINDOW_SIZE, BACKGROUND_IMAGE, TAX_RATE, APP_TITLE
from table_manager import ProductTable

class OfferGeneratorMainApp:
    """Main application class with navigation support"""
    
    def __init__(self):
        # Set locale
        locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')
        
        # Create main window
        self.window = Tk()
        self.window.title(APP_TITLE)
        self.window.geometry(WINDOW_SIZE)
        
        # Initialize navigation manager
        self.nav_manager = NavigationManager(self.window)
        
        # Create frames
        self.setup_frames()
        
        # Start with main menu
        self.nav_manager.show_frame('main_menu')
        
        # Initialize offer creation components (but don't show them yet)
        self.setup_offer_components()
    
    def setup_frames(self):
        """Setup navigation frames"""
        # Main menu frame
        self.nav_manager.add_frame('main_menu', MainMenuFrame)
        
        # Offer creation frame
        self.nav_manager.add_frame('offer_creation', OfferCreationFrame, OfferGeneratorApp)
        
        # Browse clients frame (now includes adding new clients)
        self.nav_manager.add_frame('browse_clients', BrowseClientsFrame)
        
        # Browse suppliers frame (now includes adding new suppliers)
        self.nav_manager.add_frame('browse_suppliers', BrowseSuppliersFrame)
        
        # Settings frame
        self.nav_manager.add_frame('settings', SettingsFrame)
    
    def setup_offer_components(self):
        """Setup offer creation components"""
        # These will be initialized when needed
        self.offer_components_initialized = False
    
    def run(self):
        """Start the application"""
        self.window.mainloop()

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
               cursor='hand2').place(x=50, y=800)
               
        Button(self.window, text="USUŃ PRODUKT", 
               font=("Arial", 12, "bold"),
               bg='#dc3545', fg='black',
               padx=15, pady=8,
               command=self.remove_product,
               cursor='hand2').place(x=200, y=800)
               
        Button(self.window, text="OBLICZ SUMĘ", 
               font=("Arial", 12, "bold"),
               bg='#007bff', fg='black',
               padx=15, pady=8,
               command=self.calc_total,
               cursor='hand2').place(x=350, y=800)
                
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

def main():
    """Main entry point with navigation"""
    app = OfferGeneratorMainApp()
    app.run()

if __name__ == "__main__":
    main()
