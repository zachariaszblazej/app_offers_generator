from tkinter import *
from tkinter import ttk
import locale
from navigation import NavigationManager, MainMenuFrame, OfferCreationFrame, BrowseClientsFrame, BrowseSuppliersFrame, SettingsFrame
from ui_components import UIComponents, ClientSearchWindow, SupplierSearchWindow
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
        
        # Create UI sections
        self.ui.create_upper_section()
        self.ui.create_offer_section()
        input_frame = self.ui.create_product_input_section()
        self.ui.create_totals_section()
        
        # Create buttons
        self.create_buttons(input_frame)
    
    def create_buttons(self, input_frame):
        """Create all buttons"""
        # Product input buttons
        Button(input_frame, text="DODAJ PRODUKT", 
               command=self.insert_product).grid(row=2, column=2, padx=5, pady=5)
        Button(input_frame, text="USUŃ PRODUKT", 
               command=self.remove_product).grid(row=2, column=1, padx=5, pady=5)
        Button(input_frame, text="OBLICZ SUMĘ", 
               command=self.calc_total).grid(row=2, column=0, padx=5, pady=5)
        Button(input_frame, text="ZAPISZ").grid(row=2, column=3, padx=5, pady=5)
        
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
    
    def insert_product(self):
        """Insert a new product into the table"""
        product_data = [
            self.ui.entries['product_id'].get(),
            self.ui.entries['product_name'].get(),
            self.ui.entries['unit'].get(),
            self.ui.entries['quantity'].get(),
            self.ui.entries['unit_price'].get()
        ]
        
        if self.product_table.input_record(product_data):
            # Clear entries after successful insert
            self.ui.entries['product_id'].delete(0, END)
            self.ui.entries['product_name'].delete(0, END)
            self.ui.entries['unit'].delete(0, END)
            self.ui.entries['quantity'].delete(0, END)
            self.ui.entries['unit_price'].delete(0, END)
    
    def remove_product(self):
        """Remove selected product from the table"""
        self.product_table.remove_record()
    
    def calc_total(self):
        """Calculate and display totals"""
        # Clear existing totals
        self.ui.entries['subtotal'].delete(0, END)
        self.ui.entries['grandtotal'].delete(0, END)
        self.ui.entries['tax'].delete(0, END)

        # Calculate totals from product table
        total = self.product_table.calculate_totals()
        
        self.ui.entries['subtotal'].insert(0, str(total))
        self.ui.entries['tax'].insert(0, str(total * TAX_RATE))
        self.ui.entries['grandtotal'].insert(0, str(total * (1 + TAX_RATE)))
    
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
