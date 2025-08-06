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
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.tree = None
        self.count = 0
        self.create_table()
    
    def create_table(self):
        """Create the product table"""
        # Create and configure the treeview
        self.tree = ttk.Treeview(self.parent_window, columns=TABLE_COLUMNS, show='headings', height=10)
        self.tree.place(x=50, y=450, width=900, height=300)

        # Configure columns
        self.tree.column('PID', minwidth=50, width=50, stretch=NO)
        self.tree.column('PNAME', minwidth=250, width=300, stretch=YES)
        self.tree.column('UNIT', minwidth=60, width=60, stretch=NO)
        self.tree.column('QTY', minwidth=60, width=80, stretch=NO)
        self.tree.column('U_PRICE', minwidth=100, width=100, stretch=NO)
        self.tree.column('TOTAL', minwidth=100, width=100, stretch=NO)

        # Configure headings
        self.tree.heading('PID', text='Lp.')
        self.tree.heading('PNAME', text='Nazwa')
        self.tree.heading('UNIT', text='j.m.')
        self.tree.heading('QTY', text='ilość')
        self.tree.heading('U_PRICE', text='Cena jednostkowa netto [PLN]')
        self.tree.heading('TOTAL', text='Wartość netto [PLN]')
        
        # Add scrollbar
        scrollbar_y = ttk.Scrollbar(self.parent_window, orient=VERTICAL, command=self.tree.yview)
        scrollbar_y.place(x=950, y=450, height=300)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
    
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
                               values=(product_id, product_name, unit, quantity, unit_price_display, total_display))
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
                product_id, product_name, unit, quantity, unit_price_display, total_display = values
                
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
                self.tree.item(item_id, values=(product_id, product_name, unit, quantity, unit_price_display, total_display))
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
                    # Extract values: pid, pname, unit, qty, unit_price, total
                    pid, pname, unit, qty, unit_price, total = item['values']
                    
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
