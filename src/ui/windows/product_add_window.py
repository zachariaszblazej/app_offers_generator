"""
Product add window for adding new products to the offer
"""
from tkinter import *
import tkinter.messagebox


class ProductAddWindow:
    """Handles product addition in a separate window"""
    
    def __init__(self, parent_window, product_add_callback):
        self.parent_window = parent_window
        self.product_add_callback = product_add_callback
        self.entries = {}
    
    def open_product_add_window(self):
        """Open product addition window"""
        print("DEBUG: Opening product add window")  # Debug
        
        # Create product add window
        product_window = Toplevel(self.parent_window)
        product_window.title("Dodaj produkt")
        product_window.geometry("700x500")  # Increased size
        product_window.resizable(False, False)
        product_window.grab_set()  # Make window modal
        product_window.transient(self.parent_window)
        product_window.configure(bg='#f8f9fa')  # Light background
        
        # Bind Enter key to the window for global shortcut
        product_window.bind('<Return>', lambda event: self._add_product(product_window))
        
        print("DEBUG: Product window created")  # Debug
        
        # Center the window
        product_window.geometry("+%d+%d" % (
            self.parent_window.winfo_rootx() + 100,
            self.parent_window.winfo_rooty() + 100
        ))
        
        # Title
        title_label = Label(product_window, text="Dodaj pozycję do oferty", 
                           font=("Arial", 18, "bold"),
                           bg='#f8f9fa', fg='#343a40')
        title_label.pack(pady=(30, 20), fill=X)
        
        # Main form frame with border
        form_frame = Frame(product_window, bg='white', relief=RIDGE, bd=2)
        form_frame.pack(pady=20, padx=40, fill=BOTH, expand=True)
        
        # Product ID
        Label(form_frame, text="Lp.", font=("Arial", 11)).grid(row=0, column=0, sticky=W, padx=5, pady=12)
        self.entries['product_id'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['product_id'].grid(row=0, column=1, padx=5, pady=12, sticky=W)
        
        # Product name
        Label(form_frame, text="Nazwa", font=("Arial", 11)).grid(row=1, column=0, sticky=W, padx=5, pady=12)
        self.entries['product_name'] = Entry(form_frame, width=35, font=("Arial", 11))
        self.entries['product_name'].grid(row=1, column=1, padx=5, pady=12, sticky=W)
        
        # Unit
        Label(form_frame, text="j.m.", font=("Arial", 11)).grid(row=2, column=0, sticky=W, padx=5, pady=12)
        self.entries['unit'] = Entry(form_frame, width=12, font=("Arial", 11))
        self.entries['unit'].grid(row=2, column=1, padx=5, pady=12, sticky=W)
        
        # Quantity
        Label(form_frame, text="ilość", font=("Arial", 11)).grid(row=3, column=0, sticky=W, padx=5, pady=12)
        self.entries['quantity'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['quantity'].grid(row=3, column=1, padx=5, pady=12, sticky=W)
        
        # Unit price
        Label(form_frame, text="Cena jednostkowa netto [PLN]", font=("Arial", 11)).grid(row=4, column=0, sticky=W, padx=5, pady=12)
        self.entries['unit_price'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['unit_price'].grid(row=4, column=1, padx=5, pady=12, sticky=W)
        
        # Bind Enter key to all entry fields
        for entry in self.entries.values():
            entry.bind('<Return>', lambda event: self._add_product(product_window))
        
        # Add separator line
        separator = Frame(product_window, height=2, bg='#cccccc')
        separator.pack(fill=X, padx=20, pady=(10, 20))
        
        # Buttons frame with explicit positioning
        buttons_frame = Frame(product_window, bg='#f8f9fa', height=100)
        buttons_frame.pack(fill=X, pady=(0, 20))
        buttons_frame.pack_propagate(False)  # Maintain frame size
        
        # Center the buttons using place instead of pack
        # Add button - make it very prominent and centered
        add_btn = Button(buttons_frame, text="✓ ZATWIERDŹ I DODAJ", 
                        font=("Arial", 16, "bold"),
                        bg='#FF4500', fg='black',  # Orange color to make it very visible
                        padx=40, pady=15,
                        command=lambda: self._add_product(product_window),
                        cursor='hand2',
                        relief=RAISED,
                        bd=4)
        add_btn.place(relx=0.3, rely=0.5, anchor=CENTER)  # Center left
        
        # Cancel button
        cancel_btn = Button(buttons_frame, text="✗ Anuluj", 
                           font=("Arial", 14),
                           bg='#dc3545', fg='black',
                           padx=25, pady=12,
                           command=product_window.destroy,
                           cursor='hand2')
        cancel_btn.place(relx=0.7, rely=0.5, anchor=CENTER)  # Center right
        
        # Bind Enter key to add product
        product_window.bind('<Return>', lambda event: self._add_product(product_window))
        product_window.bind('<KP_Enter>', lambda event: self._add_product(product_window))  # Numpad Enter
        
        # Set focus to first field
        self.entries['product_id'].focus_set()
    
    def _add_product(self, product_window):
        """Handle product addition"""
        print("DEBUG: _add_product called")  # Debug
        # Get product data
        product_data = [
            self.entries['product_id'].get(),
            self.entries['product_name'].get(),
            self.entries['unit'].get(),
            self.entries['quantity'].get(),
            self.entries['unit_price'].get()
        ]
        print(f"DEBUG: Product data: {product_data}")  # Debug
        
        # Validate data
        if not all([field.strip() for field in product_data]):
            tkinter.messagebox.showwarning("Błąd", "Proszę wypełnić wszystkie pola!")
            return
        
        # Try to validate numeric fields
        try:
            int(product_data[0])  # product_id
            int(product_data[3])  # quantity  
            float(product_data[4])  # unit_price
        except ValueError:
            tkinter.messagebox.showerror("Błąd", "ID produktu i ilość muszą być liczbami całkowitymi, a cena liczbą!")
            return
        
        # Call the callback function to add product
        if self.product_add_callback(product_data):
            # Clear fields after successful addition
            for entry in self.entries.values():
                entry.delete(0, END)
            # Close window
            product_window.destroy()
        else:
            tkinter.messagebox.showerror("Błąd", "Nie udało się dodać produktu do tabeli!")
