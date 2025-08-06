"""
Product table component for managing product list
"""
from tkinter import ttk
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.config import TABLE_COLUMNS, TABLE_COLUMN_HEADERS


def format_currency(value):
    """Format currency value with comma as decimal separator"""
    # Handle both string and numeric values, and values that might already have comma
    if isinstance(value, str):
        # If already has comma, convert back to dot for float conversion
        value = value.replace(',', '.')
    return f"{float(value):.2f}".replace('.', ',')


class ProductTable:
    """Handles product table functionality"""
    
    def __init__(self, parent_window, parent_frame=None, edit_callback=None, delete_callback=None):
        self.parent_window = parent_window
        self.parent_frame = parent_frame  # Reference to containing frame for scroll conflict management
        self.edit_callback = edit_callback  # Callback for double-click edit
        self.delete_callback = delete_callback  # Callback for inline delete
        self.tree = None
        self.count = 0
        self.create_table()
    
    def create_table(self):
        """Create the product table"""
        # Create and configure the treeview
        self.tree = ttk.Treeview(self.parent_window, columns=TABLE_COLUMNS, show='headings', height=10)
        self.tree.place(x=50, y=410, width=950, height=300)

        # Configure columns
        self.tree.column('PID', minwidth=50, width=50, stretch=NO)
        self.tree.column('PNAME', minwidth=250, width=300, stretch=YES)
        self.tree.column('UNIT', minwidth=60, width=60, stretch=NO)
        self.tree.column('QTY', minwidth=60, width=80, stretch=NO)
        self.tree.column('U_PRICE', minwidth=100, width=100, stretch=NO)
        self.tree.column('TOTAL', minwidth=100, width=100, stretch=NO)
        self.tree.column('DELETE', minwidth=40, width=40, stretch=NO)

        # Configure headings
        self.tree.heading('PID', text='Lp.')
        self.tree.heading('PNAME', text='Nazwa')
        self.tree.heading('UNIT', text='j.m.')
        self.tree.heading('QTY', text='ilość')
        self.tree.heading('U_PRICE', text='Cena jednostkowa netto [PLN]')
        self.tree.heading('TOTAL', text='Wartość netto [PLN]')
        self.tree.heading('DELETE', text='❌')
        
        # Add scrollbar and keep reference
        self.scrollbar_y = ttk.Scrollbar(self.parent_window, orient=VERTICAL, command=self.tree.yview)
        self.scrollbar_y.place(x=1000, y=410, height=300)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)
        
        # Bind mouse events for scroll conflict detection
        self.tree.bind("<Enter>", self.on_table_enter)
        self.tree.bind("<Leave>", self.on_table_leave)
        self.scrollbar_y.bind("<Enter>", self.on_table_enter)
        self.scrollbar_y.bind("<Leave>", self.on_table_leave)
        
        # Also bind to motion events to catch cursor movement over table area
        self.tree.bind("<Motion>", self.on_table_motion)
        self.scrollbar_y.bind("<Motion>", self.on_table_motion)
        
        # Bind double-click for editing products
        if self.edit_callback:
            self.tree.bind("<Double-Button-1>", self.on_double_click)
        
        # Bind single click for delete functionality
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)
    
    def input_record(self, product_data):
        """Insert a new product record"""
        product_id, product_name, unit, quantity, unit_price = product_data
        
        if not all([product_id, product_name, unit, quantity, unit_price]):
            tkinter.messagebox.showinfo("WARNING", "Enter all the fields!")
            return False
        
        try:
            product_id = int(product_id)
            quantity = int(quantity)
            unit_price = float(unit_price)
            total = quantity * unit_price
            
            print(f"Adding product: {product_id}, {product_name}, {unit}, {quantity}, {unit_price}, {total}")
            
            if self.tree:
                # Format numbers with comma for display
                unit_price_display = format_currency(unit_price)
                total_display = format_currency(total)
                
                self.tree.insert('', index=END, iid=self.count,
                               values=(product_id, product_name, unit, quantity, unit_price_display, total_display, "❌"))
                self.count += 1
                print(f"Product added to table. Total items: {self.count}")
                return True
            else:
                print("Error: Table not initialized!")
                
        except ValueError:
            tkinter.messagebox.showinfo("WARNING", "Enter valid numeric values!")
            return False
    
    def remove_record(self):
        """Remove selected product record"""
        if self.tree:
            for selected_item in self.tree.selection():
                self.tree.delete(selected_item)
    
    def get_selected_product(self):
        """Get data of the selected product for editing"""
        if self.tree and self.tree.selection():
            selected_item = self.tree.selection()[0]
            values = self.tree.item(selected_item)['values']
            if values:
                # Convert values back to original format (remove commas from prices)
                # Skip the DELETE column (last column)
                product_id, product_name, unit, quantity, unit_price_display, total_display = values[:6]
                
                # Convert prices back to dot format for editing
                unit_price = unit_price_display.replace(',', '.')
                
                return {
                    'item_id': selected_item,
                    'product_id': str(product_id),
                    'product_name': str(product_name),
                    'unit': str(unit),
                    'quantity': str(quantity),
                    'unit_price': str(unit_price)
                }
        return None
    
    def update_record(self, item_id, product_data):
        """Update existing product record"""
        product_id, product_name, unit, quantity, unit_price = product_data
        
        if not all([product_id, product_name, unit, quantity, unit_price]):
            tkinter.messagebox.showinfo("WARNING", "Enter all the fields!")
            return False
        
        try:
            product_id = int(product_id)
            quantity = int(quantity)
            unit_price = float(unit_price)
            total = quantity * unit_price
            
            if self.tree:
                # Format numbers with comma for display
                unit_price_display = format_currency(unit_price)
                total_display = format_currency(total)
                
                # Update the record
                self.tree.item(item_id, values=(product_id, product_name, unit, quantity, unit_price_display, total_display, "❌"))
                print(f"Product updated: {product_id}, {product_name}, {unit}, {quantity}, {unit_price}, {total}")
                return True
            else:
                print("Error: Table not initialized!")
                
        except ValueError:
            tkinter.messagebox.showinfo("WARNING", "Enter valid numeric values!")
            return False
    
    def calculate_totals(self):
        """Calculate totals from all products in the table"""
        if not self.tree:
            return 0.0
        
        total = 0.0
        for i in range(20):  # Based on original logic
            if self.tree.exists(i):
                item = self.tree.item(str(i))
                if item['values']:
                    # Handle values that might have comma as decimal separator
                    total_value = str(item['values'][5]).replace(',', '.')
                    total += float(total_value)  # TOTAL column (now index 5)
        
        return total
    
    def get_all_products(self):
        """Get all products from the table as a list of lists (rows)"""
        products = []
        if self.tree:
            print(f"Getting products from table with {len(self.tree.get_children())} items")
            for child in self.tree.get_children():
                item = self.tree.item(child)
                if item['values']:
                    # Extract values: pid, pname, unit, qty, unit_price, total (skip DELETE column)
                    values = item['values'][:6]  # Take only first 6 values, skip DELETE
                    pid, pname, unit, qty, unit_price, total = values
                    
                    # Create a row as list with formatted values (comma as decimal separator)
                    row = [
                        str(pid),                           # Lp (pozycja)
                        str(pname),                         # Nazwa produktu
                        str(unit),                          # Jednostka miary
                        str(qty),                           # Ilość
                        format_currency(unit_price),        # Cena jednostkowa z przecinkiem
                        format_currency(total)              # Suma z przecinkiem
                    ]
                    products.append(row)
                    print(f"Retrieved product row: {row}")
        else:
            print("Error: Table not initialized when getting products!")
        
        print(f"Total product rows retrieved: {len(products)}")
        return products
    
    def get_all_products_as_dicts(self):
        """Get all products from the table as a list of dictionaries (legacy method)"""
        products = []
        if self.tree:
            print(f"Getting products from table with {len(self.tree.get_children())} items")
            for child in self.tree.get_children():
                item = self.tree.item(child)
                if item['values']:
                    pid, pname, unit, qty, unit_price, total = item['values']
                    product = {
                        'pid': pid,
                        'pname': pname,
                        'unit': unit,
                        'qty': qty,
                        'unit_price': format_currency(unit_price),
                        'total': format_currency(total)
                    }
                    products.append(product)
                    print(f"Retrieved product: {product}")
        else:
            print("Error: Table not initialized when getting products!")
        
        print(f"Total products retrieved: {len(products)}")
        return products

    def has_scrollbar_active(self):
        """Check if the table scrollbar is active (visible and needed)"""
        if not self.tree or not hasattr(self, 'scrollbar_y'):
            return False
        
        try:
            # Simple check: if we have more than 10 items, assume scrollbar is needed
            # This avoids timing issues with widget sizing
            total_items = len(self.tree.get_children())
            
            # Scrollbar is likely needed if many items
            if total_items >= 10:
                return True
            
            # For fewer items, try to calculate more precisely
            try:
                # Check if scrollbar is needed by comparing content height with visible height
                all_children = self.tree.get_children()
                if not all_children:
                    return False
                
                # Get bbox of first and last items to calculate total content height
                first_item = all_children[0]
                last_item = all_children[-1] 
                
                first_bbox = self.tree.bbox(first_item)
                last_bbox = self.tree.bbox(last_item)
                
                if first_bbox and last_bbox:
                    # Content height is from top of first item to bottom of last item
                    content_height = (last_bbox[1] + last_bbox[3]) - first_bbox[1]
                    visible_height = self.tree.winfo_height()
                    
                    # Scrollbar is needed if content height exceeds visible height
                    return content_height > visible_height
                
                # Fallback: check if there are many items (more than estimated visible)
                visible_height = self.tree.winfo_height()
                item_height = 20  # Approximate height of one item in treeview
                visible_items = max(8, visible_height // item_height) if visible_height > 0 else 8
                
                return len(all_children) > visible_items
                
            except Exception:
                # Fallback: assume scrollbar is needed if we have more than 8 items
                return total_items > 8
            
        except Exception:
            # Final fallback
            return False
    
    def is_cursor_over_table(self, x, y):
        """Check if cursor coordinates are over the table or its scrollbar"""
        if not self.tree or not hasattr(self, 'scrollbar_y'):
            return False
        
        try:
            # Get table bounds
            table_x = self.tree.winfo_x()
            table_y = self.tree.winfo_y()
            table_width = self.tree.winfo_width()
            table_height = self.tree.winfo_height()
            
            # Get scrollbar bounds
            scrollbar_x = self.scrollbar_y.winfo_x()
            scrollbar_y = self.scrollbar_y.winfo_y()
            scrollbar_width = self.scrollbar_y.winfo_width()
            scrollbar_height = self.scrollbar_y.winfo_height()
            
            # Check if cursor is over table or scrollbar
            over_table = (table_x <= x <= table_x + table_width and 
                         table_y <= y <= table_y + table_height)
            over_scrollbar = (scrollbar_x <= x <= scrollbar_x + scrollbar_width and 
                             scrollbar_y <= y <= scrollbar_y + scrollbar_height)
            
            return over_table or over_scrollbar
        except:
            return False
    
    def on_table_enter(self, event):
        """Called when mouse enters table area"""
        # Notify parent frames about table focus
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_enter'):
            self.parent_frame.on_product_table_enter()
    
    def on_table_leave(self, event):
        """Called when mouse leaves table area"""
        # Notify parent frames about table focus loss
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_leave'):
            self.parent_frame.on_product_table_leave()
    
    def on_table_motion(self, event):
        """Called when mouse moves over table area"""
        # Ensure that parent frame knows cursor is over table
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_enter'):
            self.parent_frame.on_product_table_enter()
    
    def on_double_click(self, event):
        """Handle double-click on table item to edit product"""
        if self.edit_callback:
            # Get the item that was double-clicked
            item = self.tree.selection()
            if item:
                # Get the selected product data
                selected_product = self.get_selected_product()
                if selected_product:
                    # Call the edit callback with the selected product
                    self.edit_callback()
    
    def on_single_click(self, event):
        """Handle single-click on table to check for delete column clicks"""
        # Get the region that was clicked
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.tree.identify_column(event.x)
            
            # DELETE column should be the last column
            num_columns = len(self.tree['columns'])
            delete_column_index = f"#{num_columns}"
            
            if column == delete_column_index:  
                # Get the item that was clicked
                item = self.tree.identify_row(event.y)
                if item:
                    # Ask for confirmation
                    result = tkinter.messagebox.askyesno(
                        "Potwierdź usunięcie", 
                        "Czy na pewno chcesz usunąć ten produkt z tabeli?"
                    )
                    if result:
                        # Delete the item
                        self.tree.delete(item)
                        
                        # Call delete callback if provided
                        if self.delete_callback:
                            self.delete_callback()
