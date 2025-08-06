"""
Product edit window for editing existing products in the offer
"""
from tkinter import *
import tkinter.messagebox


class ProductEditWindow:
    """Handles product editing in a separate window"""
    
    def __init__(self, parent_window, product_update_callback):
        self.parent_window = parent_window
        self.product_update_callback = product_update_callback
        self.entries = {}
        self.item_id = None
    
    def open_product_edit_window(self, product_data):
        """Open product edit window with pre-filled data"""
        if not product_data:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do edycji!")
            return
            
        self.item_id = product_data['item_id']
        
        print("DEBUG: Opening product edit window")  # Debug
        
        # Create product edit window
        product_window = Toplevel(self.parent_window)
        product_window.title("Edytuj produkt")
        product_window.geometry("700x500")  # Same size as add window
        product_window.resizable(False, False)
        product_window.grab_set()  # Make window modal
        product_window.transient(self.parent_window)
        product_window.configure(bg='#f8f9fa')  # Light background
        
        print("DEBUG: Product edit window created")  # Debug
        
        # Center the window
        product_window.geometry("+%d+%d" % (
            self.parent_window.winfo_rootx() + 100,
            self.parent_window.winfo_rooty() + 100
        ))
        
        # Title
        title_label = Label(product_window, text="✏️ Edytuj pozycję w ofercie", 
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
        self.entries['product_id'].insert(0, product_data['product_id'])
        
        # Product name
        Label(form_frame, text="Nazwa", font=("Arial", 11)).grid(row=1, column=0, sticky=W, padx=5, pady=12)
        self.entries['product_name'] = Entry(form_frame, width=35, font=("Arial", 11))
        self.entries['product_name'].grid(row=1, column=1, padx=5, pady=12, sticky=W)
        self.entries['product_name'].insert(0, product_data['product_name'])
        
        # Unit
        Label(form_frame, text="j.m.", font=("Arial", 11)).grid(row=2, column=0, sticky=W, padx=5, pady=12)
        self.entries['unit'] = Entry(form_frame, width=12, font=("Arial", 11))
        self.entries['unit'].grid(row=2, column=1, padx=5, pady=12, sticky=W)
        self.entries['unit'].insert(0, product_data['unit'])
        
        # Quantity
        Label(form_frame, text="ilość", font=("Arial", 11)).grid(row=3, column=0, sticky=W, padx=5, pady=12)
        self.entries['quantity'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['quantity'].grid(row=3, column=1, padx=5, pady=12, sticky=W)
        self.entries['quantity'].insert(0, product_data['quantity'])
        
        # Unit price
        Label(form_frame, text="Cena jednostkowa netto [PLN]:", font=("Arial", 11)).grid(row=4, column=0, sticky=W, padx=5, pady=12)
        self.entries['unit_price'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['unit_price'].grid(row=4, column=1, padx=5, pady=12, sticky=W)
        self.entries['unit_price'].insert(0, product_data['unit_price'])
        
        # Bind Enter key to all entry fields
        for entry in self.entries.values():
            entry.bind('<Return>', lambda event: self._update_product(product_window))
        
        # Bind Enter key to update product
        product_window.bind('<Return>', lambda event: self._update_product(product_window))
        product_window.bind('<KP_Enter>', lambda event: self._update_product(product_window))  # Numpad Enter
        
        # Add separator line
        separator = Frame(product_window, height=2, bg='#cccccc')
        separator.pack(fill=X, padx=20, pady=(10, 20))
        
        # Buttons frame with explicit positioning
        buttons_frame = Frame(product_window, bg='#f8f9fa', height=100)
        buttons_frame.pack(fill=X, pady=(0, 20))
        buttons_frame.pack_propagate(False)  # Maintain frame size
        
        # Center the buttons using place instead of pack
        # Update button - make it very prominent and centered
        update_btn = Button(buttons_frame, text="✓ ZATWIERDŹ ZMIANY", 
                           font=("Arial", 16, "bold"),
                           bg='#FF8C00', fg='black',  # Orange color to make it very visible
                           padx=40, pady=15,
                           command=lambda: self._update_product(product_window),
                           cursor='hand2',
                           relief=RAISED,
                           bd=4)
        update_btn.place(relx=0.3, rely=0.5, anchor=CENTER)  # Center left
        
        # Cancel button
        cancel_btn = Button(buttons_frame, text="✗ Anuluj", 
                           font=("Arial", 14),
                           bg='#dc3545', fg='black',
                           padx=25, pady=12,
                           command=product_window.destroy,
                           cursor='hand2')
        cancel_btn.place(relx=0.7, rely=0.5, anchor=CENTER)  # Center right
        
        print("DEBUG: Product edit window UI created")  # Debug
    
    def _update_product(self, window):
        """Update product and close window"""
        try:
            # Get values from entries
            product_data = (
                self.entries['product_id'].get().strip(),
                self.entries['product_name'].get().strip(),
                self.entries['unit'].get().strip(),
                self.entries['quantity'].get().strip(),
                self.entries['unit_price'].get().strip()
            )
            
            print(f"DEBUG: Updating product with data: {product_data}")  # Debug
            
            # Call the update callback with item_id and product data
            if self.product_update_callback(self.item_id, product_data):
                print("DEBUG: Product updated successfully")  # Debug
                window.destroy()
            else:
                print("DEBUG: Product update failed")  # Debug
        except Exception as e:
            print(f"DEBUG: Error updating product: {e}")  # Debug
            tkinter.messagebox.showerror("Błąd", f"Nie udało się zaktualizować produktu: {e}")
