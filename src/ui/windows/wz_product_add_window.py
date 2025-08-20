"""
WZ Product Add Window - simplified version without pricing
"""
from tkinter import *
import tkinter.messagebox


class WzProductAddWindow:
    """Window for adding products to WZ - simplified without pricing"""
    
    def __init__(self, parent_window, callback):
        self.parent_window = parent_window
        self.callback = callback
        self.window = None
        self.entries = {}
        
        # For WZ, we don't need to load products from database
        # Users can enter products manually
        self.products_data = []
    
    def show(self):
        """Show the add product window"""
        if self.window:
            self.window.lift()
            return
        
        self.window = Toplevel(self.parent_window)
        self.window.title("Dodaj produkt do WZ")
        self.window.geometry("500x300")
        self.window.resizable(False, False)
        self.window.grab_set()  # Make window modal
        
        # Center the window
        self.window.transient(self.parent_window)
        
        self.create_ui()
    
    def create_ui(self):
        """Create the UI elements"""
        # Title
        title_label = Label(self.window, text="Dodaj produkt do WZ", 
                           font=("Arial", 16, "bold"), fg="#333")
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = Frame(self.window)
        main_frame.pack(expand=True, fill=BOTH, padx=20, pady=10)
        
        # Product name
        Label(main_frame, text="Nazwa produktu:", font=("Arial", 12)).grid(row=0, column=0, sticky=W, pady=5)
        self.entries['name'] = Entry(main_frame, width=40, font=("Arial", 10))
        self.entries['name'].grid(row=0, column=1, padx=10, pady=5)
        
        # Unit
        Label(main_frame, text="Jednostka miary:", font=("Arial", 12)).grid(row=1, column=0, sticky=W, pady=5)
        self.entries['unit'] = Entry(main_frame, width=20, font=("Arial", 10))
        self.entries['unit'].grid(row=1, column=1, sticky=W, padx=10, pady=5)
        self.entries['unit'].insert(0, "szt.")  # Default unit
        
        # Quantity
        Label(main_frame, text="Ilość:", font=("Arial", 12)).grid(row=2, column=0, sticky=W, pady=5)
        self.entries['quantity'] = Entry(main_frame, width=20, font=("Arial", 10))
        self.entries['quantity'].grid(row=2, column=1, sticky=W, padx=10, pady=5)
        self.entries['quantity'].insert(0, "1")  # Default quantity
        
        # Buttons frame
        buttons_frame = Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Add button
        add_btn = Button(buttons_frame, text="Dodaj produkt", 
                        font=("Arial", 12, "bold"), fg="black",
                        padx=20, pady=5, command=self.add_product)
        add_btn.pack(side=LEFT, padx=10)
        
        # Cancel button
        cancel_btn = Button(buttons_frame, text="Anuluj", 
                           font=("Arial", 12), fg="black",
                           padx=20, pady=5, command=self.close)
        cancel_btn.pack(side=LEFT, padx=10)
        
        # Focus on name entry
        self.entries['name'].focus_set()
        
        # Bind Enter key to add product
        self.window.bind('<Return>', lambda e: self.add_product())
        self.window.bind('<Escape>', lambda e: self.close())
    
    def add_product(self):
        """Add the product"""
        # Get values
        name = self.entries['name'].get().strip()
        unit = self.entries['unit'].get().strip()
        quantity = self.entries['quantity'].get().strip()
        
        # Validate
        if not name:
            tkinter.messagebox.showerror("Błąd", "Proszę podać nazwę produktu.")
            return
        
        if not unit:
            tkinter.messagebox.showerror("Błąd", "Proszę podać jednostkę miary.")
            return
        
        if not quantity:
            tkinter.messagebox.showerror("Błąd", "Proszę podać ilość.")
            return
        
        # Validate quantity is a number
        try:
            float(quantity.replace(',', '.'))
        except ValueError:
            tkinter.messagebox.showerror("Błąd", "Ilość musi być liczbą.")
            return
        
        # Prepare product data
        product_data = {
            'name': name,
            'unit': unit,
            'quantity': quantity
        }
        
        # Call callback
        if self.callback:
            self.callback(product_data)
        
        # Close window
        self.close()
    
    def close(self):
        """Close the window"""
        if self.window:
            self.window.destroy()
            self.window = None
