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
        product_window.geometry("700x650")
        product_window.resizable(False, False)
        product_window.grab_set()  # Make window modal
        product_window.transient(self.parent_window)
        product_window.configure(bg='#f8f9fa')

        print("DEBUG: Product window created")  # Debug

        # Center the window
        product_window.geometry(
            "+%d+%d" % (
                self.parent_window.winfo_rootx() + 100,
                self.parent_window.winfo_rooty() + 100,
            )
        )

        # Title
        title_label = Label(
            product_window,
            text="Dodaj pozycję do oferty",
            font=("Arial", 18, "bold"),
            bg='#f8f9fa',
            fg='#343a40',
        )
        title_label.pack(pady=(30, 20), fill=X)

        # Main form frame with border
        form_frame = Frame(product_window, bg='white', relief=RIDGE, bd=2)
        form_frame.pack(pady=20, padx=40, fill=BOTH, expand=True)

        # Product name (multi-line up to ~7 lines)
        Label(form_frame, text="Nazwa", font=("Arial", 11)).grid(
            row=0, column=0, sticky=W, padx=5, pady=12
        )
        self.entries['product_name'] = Text(form_frame, width=40, height=7, font=("Arial", 11), wrap=WORD)
        self.entries['product_name'].grid(row=0, column=1, padx=5, pady=12, sticky=W)

        # Unit
        Label(form_frame, text="j.m.", font=("Arial", 11)).grid(
            row=1, column=0, sticky=W, padx=5, pady=12
        )
        self.entries['unit'] = Entry(form_frame, width=12, font=("Arial", 11))
        self.entries['unit'].grid(row=1, column=1, padx=5, pady=12, sticky=W)
        # Default unit
        self.entries['unit'].insert(0, "szt.")

        # Quantity
        Label(form_frame, text="ilość", font=("Arial", 11)).grid(
            row=2, column=0, sticky=W, padx=5, pady=12
        )
        self.entries['quantity'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['quantity'].grid(row=2, column=1, padx=5, pady=12, sticky=W)
        # Default quantity
        self.entries['quantity'].insert(0, "1")

        # Unit price
        Label(form_frame, text="Cena jednostkowa netto [PLN]", font=("Arial", 11)).grid(
            row=3, column=0, sticky=W, padx=5, pady=12
        )
        self.entries['unit_price'] = Entry(form_frame, width=15, font=("Arial", 11))
        self.entries['unit_price'].grid(row=3, column=1, padx=5, pady=12, sticky=W)

        # Bind Enter key to all entry fields except product_name Text (allow newline there)
        def _on_return(event):
            try:
                # If focus is on the multi-line name Text, don't submit
                if event.widget is self.entries.get('product_name'):
                    return
                self._add_product(product_window)
            except Exception:
                pass

        for key, entry in self.entries.items():
            try:
                entry.bind('<Return>', _on_return)
            except Exception:
                pass

        # Add separator line
        separator = Frame(product_window, height=2, bg='#cccccc')
        separator.pack(fill=X, padx=20, pady=(10, 20))

        # Buttons frame with explicit positioning
        buttons_frame = Frame(product_window, bg='#f8f9fa', height=100)
        buttons_frame.pack(fill=X, pady=(0, 20))
        buttons_frame.pack_propagate(False)  # Maintain frame size

        # Add button - prominent
        add_btn = Button(
            buttons_frame,
            text="✓ ZATWIERDŹ I DODAJ",
            font=("Arial", 16, "bold"),
            fg='black',
            padx=40,
            pady=15,
            command=lambda: self._add_product(product_window),
            cursor='hand2',
            relief=RAISED,
            bd=4,
        )
        add_btn.place(relx=0.3, rely=0.5, anchor=CENTER)

        # Cancel button
        cancel_btn = Button(
            buttons_frame,
            text="✗ Anuluj",
            font=("Arial", 14),
            fg='black',
            padx=25,
            pady=12,
            command=product_window.destroy,
            cursor='hand2',
        )
        cancel_btn.place(relx=0.7, rely=0.5, anchor=CENTER)

        # Bind Enter on window to add product only when focus is not in the name Text
        product_window.bind('<Return>', _on_return)
        product_window.bind('<KP_Enter>', _on_return)

        # Set focus to first field
        self.entries['product_name'].focus_set()
    
    def _add_product(self, product_window):
        """Handle product addition"""
        print("DEBUG: _add_product called")  # Debug
        # Get product data (without product_id since it's auto-generated)
        # Read multi-line product name from Text and normalize newlines
        name_widget = self.entries.get('product_name')
        if hasattr(name_widget, 'get') and name_widget.winfo_class() == 'Text':
            pname = name_widget.get('1.0', END).rstrip('\n')
        else:
            pname = self.entries['product_name'].get()
        product_data = [
            pname,
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
            # quantity must be integer
            int(product_data[2])
            # unit_price can contain spaces and comma as decimal
            _price_clean = product_data[3].replace(' ', '').replace('\u00A0', '').replace(',', '.')
            float(_price_clean)
        except ValueError:
            tkinter.messagebox.showerror("Błąd", "Ilość musi być liczbą całkowitą, a cena liczbą!")
            return
        
        # Call the callback function to add product
        if self.product_add_callback(product_data):
            # Clear fields after successful addition (handle Text vs Entry)
            for entry in self.entries.values():
                try:
                    if entry.winfo_class() == 'Text':
                        entry.delete('1.0', END)
                    else:
                        entry.delete(0, END)
                except Exception:
                    pass
            # Close window
            product_window.destroy()
        else:
            tkinter.messagebox.showerror("Błąd", "Nie udało się dodać produktu do tabeli!")
