"""
WZ Product table component for managing product list - simplified version without prices
"""
from tkinter import ttk
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class WzProductTable:
    """Handles WZ product table functionality - simplified without pricing columns"""
    
    def __init__(self, parent_window, parent_frame=None, edit_callback=None, delete_callback=None):
        self.parent_window = parent_window
        self.parent_frame = parent_frame  # Reference to containing frame for scroll conflict management
        self.edit_callback = edit_callback  # Callback for double-click edit
        self.delete_callback = delete_callback  # Callback for inline delete
        self.tree = None
        self.count = 0
        # Define columns for WZ table (without pricing)
        self.columns = ('PID', 'PNAME', 'UNIT', 'QTY', 'EDIT', 'DELETE')
        self.create_table()
    
    def create_table(self):
        """Create the WZ product table"""
        # Create and configure the treeview
        self.tree = ttk.Treeview(self.parent_window, columns=self.columns, show='headings', height=10)
        self.tree.place(x=50, y=410, width=950, height=300)

        # Configure columns
        self.tree.column('PID', minwidth=50, width=50, stretch=NO)
        self.tree.column('PNAME', minwidth=300, width=400, stretch=YES)  # Wider since no price columns
        self.tree.column('UNIT', minwidth=80, width=80, stretch=NO)
        self.tree.column('QTY', minwidth=100, width=120, stretch=NO)
        self.tree.column('EDIT', minwidth=100, width=100, stretch=NO)
        self.tree.column('DELETE', minwidth=100, width=100, stretch=NO)

        # Configure headings
        self.tree.heading('PID', text='Lp.')
        self.tree.heading('PNAME', text='Nazwa produktu')
        self.tree.heading('UNIT', text='j.m.')
        self.tree.heading('QTY', text='Ilość')
        self.tree.heading('EDIT', text='Edytuj')
        self.tree.heading('DELETE', text='Usuń')
        
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
        
        # Bind single click for edit and delete functionality
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)
    
    def on_table_enter(self, event):
        """Handle mouse entering table area"""
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_enter'):
            self.parent_frame.on_product_table_enter()
    
    def on_table_leave(self, event):
        """Handle mouse leaving table area"""
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_leave'):
            self.parent_frame.on_product_table_leave()
    
    def on_table_motion(self, event):
        """Handle mouse motion over table"""
        # This ensures we're definitely over the table
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_enter'):
            self.parent_frame.on_product_table_enter()
    
    def on_single_click(self, event):
        """Handle single click events for edit and delete"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            column = self.tree.identify_column(event.x)
            
            # Convert column number to column name
            if column == '#5':  # EDIT column
                if self.edit_callback:
                    self.edit_callback(item)
            elif column == '#6':  # DELETE column
                if tkinter.messagebox.askyesno("Potwierdź", "Czy na pewno chcesz usunąć ten produkt?"):
                    self.tree.delete(item)
                    self.update_product_numbers()
                    if self.delete_callback:
                        self.delete_callback()
    
    def insert_product(self, product_data):
        """Insert product into table"""
        self.count += 1
        # For WZ table, we only need: PID, PNAME, UNIT, QTY, EDIT, DELETE
        item_data = (
            self.count,  # PID
            product_data.get('name', ''),  # PNAME
            product_data.get('unit', ''),  # UNIT
            product_data.get('quantity', ''),  # QTY
            'EDYTUJ',  # EDIT
            'USUŃ'  # DELETE
        )
        
        item_id = self.tree.insert('', 'end', values=item_data)
        return item_id
    
    def update_product(self, item_id, product_data):
        """Update existing product in table"""
        # Get current values
        current_values = list(self.tree.item(item_id, 'values'))
        
        # Update with new data (keeping PID unchanged)
        updated_values = (
            current_values[0],  # Keep PID
            product_data.get('name', current_values[1]),  # PNAME
            product_data.get('unit', current_values[2]),  # UNIT
            product_data.get('quantity', current_values[3]),  # QTY
            'EDYTUJ',  # EDIT
            'USUŃ'  # DELETE
        )
        
        self.tree.item(item_id, values=updated_values)
    
    def get_all_products(self):
        """Get all products from table as list of dictionaries"""
        products = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if len(values) >= 4:
                product = {
                    'pid': values[0],
                    'name': values[1],
                    'unit': values[2],
                    'quantity': values[3]
                }
                products.append(product)
        return products
    
    def clear_table(self):
        """Clear all products from table"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.count = 0
    
    def update_product_numbers(self):
        """Update product numbers after deletion"""
        items = self.tree.get_children()
        for i, item in enumerate(items, 1):
            values = list(self.tree.item(item, 'values'))
            values[0] = i  # Update PID
            self.tree.item(item, values=values)
        self.count = len(items)
    
    def get_product_data(self, item_id):
        """Get product data for editing"""
        values = self.tree.item(item_id, 'values')
        if len(values) >= 4:
            return {
                'name': values[1],
                'unit': values[2],
                'quantity': values[3]
            }
        return {}
    
    def remove_product(self, item_id):
        """Remove product from table"""
        self.tree.delete(item_id)
        self.update_product_numbers()
    
    def get_selected_item(self):
        """Get currently selected item"""
        selection = self.tree.selection()
        return selection[0] if selection else None
