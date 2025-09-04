"""
WZ Product Edit Window - simplified version without pricing
"""
from tkinter import *
import tkinter.messagebox


class WzProductEditWindow:
    """Window for editing products in WZ - simplified without pricing"""
    
    def __init__(self, parent_window, callback):
        self.parent_window = parent_window
        self.callback = callback
        self.window = None
        self.entries = {}
        self.current_item_id = None
    
    def show(self, item_id, product_data):
        """Show the edit product window with existing data"""
        self.current_item_id = item_id

        if self.window:
            self.window.lift()
            return

        self.window = Toplevel(self.parent_window)
        self.window.title("Edytuj produkt WZ")
        self.window.geometry("700x650")
        self.window.resizable(False, False)
        self.window.grab_set()  # Make window modal

        # Center the window
        self.window.transient(self.parent_window)

        self.create_ui(product_data)
    
    def create_ui(self, product_data):
        """Create the UI elements"""
        # Title
        title_label = Label(self.window, text="Edytuj produkt WZ", 
                           font=("Arial", 16, "bold"), fg="#333")
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = Frame(self.window)
        main_frame.pack(expand=True, fill=BOTH, padx=20, pady=10)
        
        # Product name (multi-line up to ~7 lines)
        Label(main_frame, text="Nazwa produktu:", font=("Arial", 12)).grid(row=0, column=0, sticky=W, pady=5)
        self.entries['name'] = Text(main_frame, width=40, height=7, font=("Arial", 11), wrap=WORD)
        self.entries['name'].grid(row=0, column=1, padx=10, pady=5, sticky=W)
        try:
            self.entries['name'].insert('1.0', product_data.get('name', ''))
        except Exception:
            pass
        
        # Unit
        Label(main_frame, text="Jednostka miary:", font=("Arial", 12)).grid(row=1, column=0, sticky=W, pady=5)
        self.entries['unit'] = Entry(main_frame, width=20, font=("Arial", 10))
        self.entries['unit'].grid(row=1, column=1, sticky=W, padx=10, pady=5)
        self.entries['unit'].insert(0, product_data.get('unit', ''))
        
        # Quantity
        Label(main_frame, text="Ilość:", font=("Arial", 12)).grid(row=2, column=0, sticky=W, pady=5)
        self.entries['quantity'] = Entry(main_frame, width=20, font=("Arial", 10))
        self.entries['quantity'].grid(row=2, column=1, sticky=W, padx=10, pady=5)
        self.entries['quantity'].insert(0, product_data.get('quantity', ''))
        
        # Buttons frame
        buttons_frame = Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Save button
        save_btn = Button(buttons_frame, text="Zapisz zmiany", 
                         font=("Arial", 12, "bold"), bg="#4CAF50", fg="white",
                         padx=20, pady=5, command=self.save_changes)
        save_btn.pack(side=LEFT, padx=10)
        
        # Cancel button
        cancel_btn = Button(buttons_frame, text="Anuluj", 
                           font=("Arial", 12), bg="#f44336", fg="white",
                           padx=20, pady=5, command=self.close)
        cancel_btn.pack(side=LEFT, padx=10)
        
        # Focus on name field
        self.entries['name'].focus_set()

        # Bind Enter: submit unless focused in multi-line name Text
        def _on_return(event):
            try:
                if event.widget is self.entries.get('name'):
                    return
                self.save_changes()
            except Exception:
                pass

        try:
            self.entries['unit'].bind('<Return>', _on_return)
            self.entries['quantity'].bind('<Return>', _on_return)
        except Exception:
            pass

        self.window.bind('<Return>', _on_return)
        self.window.bind('<KP_Enter>', _on_return)
        self.window.bind('<Escape>', lambda e: self.close())
    
    def save_changes(self):
        """Save the changes"""
        # Get values
        # Read multi-line name properly from Text widget
        name_widget = self.entries.get('name')
        if hasattr(name_widget, 'get') and name_widget.winfo_class() == 'Text':
            name = name_widget.get('1.0', END).rstrip('\n')
        else:
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
        
        # Call callback with item ID and new data
        if self.callback:
            self.callback(self.current_item_id, product_data)
        
        # Close window
        self.close()
    
    def close(self):
        """Close the window"""
        if self.window:
            self.window.destroy()
            self.window = None
