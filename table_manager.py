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
        self.tree.heading('PNAME', text='Nazwa produktu')
        self.tree.heading('UNIT', text='j.m.')
        self.tree.heading('QTY', text='Ilość')
        self.tree.heading('U_PRICE', text='Cena jedn.')
        self.tree.heading('TOTAL', text='Suma')
        
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
                self.tree.insert('', index=END, iid=self.count,
                               values=(product_id, product_name, unit, quantity, unit_price, total))
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
    
    def calculate_totals(self):
        """Calculate totals from all products in the table"""
        if not self.tree:
            return 0.0
        
        total = 0.0
        for i in range(20):  # Based on original logic
            if self.tree.exists(i):
                item = self.tree.item(str(i))
                if item['values']:
                    total += float(item['values'][5])  # TOTAL column (now index 5)
        
        return total
    
    def get_all_products(self):
        """Get all products from the table as a list of dictionaries"""
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
                        'unit_price': f"{float(unit_price):.2f}",
                        'total': f"{float(total):.2f}"
                    }
                    products.append(product)
                    print(f"Retrieved product: {product}")
        else:
            print("Error: Table not initialized when getting products!")
        
        print(f"Total products retrieved: {len(products)}")
        return products
