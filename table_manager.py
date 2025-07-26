from tkinter import ttk
from tkinter import *
import tkinter.messagebox
from config import TABLE_COLUMNS, TABLE_COLUMN_HEADERS

class ProductTable:
    """Handles product table functionality"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.tree = None
        self.count = 0
        self.create_table()
    
    def create_table(self):
        """Create the product table (currently commented out in original)"""
        # This was commented out in the original code
        # Uncomment and adapt as needed:
        
        # self.tree = ttk.Treeview(self.parent_window, columns=TABLE_COLUMNS)
        # self.tree.place(x=1000, y=1000)

        # # Configure columns
        # self.tree.column('PID', minwidth=0, width=20, stretch=NO)
        # self.tree.column('PNAME', width=10)
        # self.tree.column('QTY', width=10)
        # self.tree.column('U_PRICE', width=10)
        # self.tree.column('TOTAL', width=10)

        # # Configure headings
        # for col in TABLE_COLUMNS:
        #     self.tree.heading(col, text=TABLE_COLUMN_HEADERS[col])

        # self.tree.pack(side=BOTTOM, expand=True, fill=X)
        pass
    
    def input_record(self, product_data):
        """Insert a new product record"""
        product_id, product_name, quantity, unit_price = product_data
        
        if not all([product_id, product_name, quantity, unit_price]):
            tkinter.messagebox.showinfo("WARNING", "Enter all the fields!")
            return False
        
        try:
            product_id = int(product_id)
            quantity = int(quantity)
            unit_price = float(unit_price)
            total = quantity * unit_price
            
            if self.tree:
                self.tree.insert('', index=END, iid=self.count,
                               values=(product_id, product_name, quantity, unit_price, total))
                self.count += 1
                return True
            
        except ValueError:
            tkinter.messagebox.showinfo("WARNING", "Enter valid numeric values!")
            return False
    
    def remove_record(self):
        """Remove selected product record"""
        if self.tree:
            for selected_item in self.tree.selection():
                self.tree.delete(selected_item)
    
    def calculate_totals(self):
        """Calculate totals from all products in the table"""
        if not self.tree:
            return 0.0
        
        total = 0.0
        for i in range(20):  # Based on original logic
            if self.tree.exists(i):
                item = self.tree.item(str(i))
                if item['values']:
                    total += float(item['values'][4])  # TOTAL column
        
        return total
    
    def get_all_products(self):
        """Get all products from the table"""
        products = []
        if self.tree:
            for child in self.tree.get_children():
                item = self.tree.item(child)
                products.append(item['values'])
        return products
