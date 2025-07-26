from tkinter import *
from tkinter import ttk
import locale
from ui_components import UIComponents, ClientSearchWindow
from offer_generator import generate_offer_document, convert_date
from config import WINDOW_SIZE, BACKGROUND_IMAGE, TAX_RATE
from table_manager import ProductTable

class OfferGeneratorApp:
    """Main application class for the Offer Generator"""
    
    def __init__(self):
        # Set locale
        locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')
        
        # Create main window
        self.window = Tk()
        self.window.geometry(WINDOW_SIZE)
        
        # Set background
        bg = PhotoImage(file=BACKGROUND_IMAGE)
        label_BG = Label(self.window, image=bg)
        label_BG.place(x=0, y=0)
        label_BG.image = bg  # Keep a reference
        
        # Initialize UI components
        self.ui = UIComponents(self.window)
        self.client_search = ClientSearchWindow(self.window, self.ui.fill_client_data)
        self.product_table = ProductTable(self.window)
        
        # Create UI sections
        self.setup_ui()
        
        # Initialize calculation variables
        self.count = 0
        
    def setup_ui(self):
        """Setup all UI components"""
        self.ui.create_upper_section()
        self.ui.create_offer_section()
        input_frame = self.ui.create_product_input_section()
        self.ui.create_totals_section()
        
        # Create buttons
        self.create_buttons(input_frame)
    
    def create_buttons(self, input_frame):
        """Create all buttons"""
        # Product input buttons
        Button(input_frame, text="INSERT PRODUCT", command=self.insert_product).grid(row=2, column=2)
        Button(input_frame, text="REMOVE PRODUCT", command=self.remove_product).grid(row=2, column=1)
        Button(input_frame, text="TOTAL", command=self.calc_total).grid(row=2, column=0)
        Button(input_frame, text="SAVE").grid(row=2, column=3)
        
        # Client search button
        search_client_button = Button(self.window, text="Szukaj klienta", 
                                    command=self.client_search.open_client_search)
        search_client_button.place(x=900, y=360)
        
        # Generate offer button
        generate_offer_button = Button(self.window, text="Twórz ofertę", 
                                     command=self.generate_offer)
        generate_offer_button.place(x=700, y=800)
    
    def insert_product(self):
        """Insert a new product into the table"""
        product_data = [
            self.ui.entries['product_id'].get(),
            self.ui.entries['product_name'].get(),
            self.ui.entries['quantity'].get(),
            self.ui.entries['unit_price'].get()
        ]
        
        if self.product_table.input_record(product_data):
            # Clear entries after successful insert
            self.ui.entries['product_id'].delete(0, END)
            self.ui.entries['product_name'].delete(0, END)
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
        
        # Convert date to proper format
        context_data['date'] = convert_date(context_data['date'])
        
        # Generate document
        generate_offer_document(context_data)
    
    def run(self):
        """Start the application"""
        self.window.mainloop()

def main():
    """Main entry point"""
    app = OfferGeneratorApp()
    app.run()

if __name__ == "__main__":
    main()
