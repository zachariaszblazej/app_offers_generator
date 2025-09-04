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


def _to_float(value) -> float:
    """Parse value that may contain spaces as thousand separators and comma decimal."""
    if isinstance(value, str):
        # remove spaces (thousands) and convert comma to dot
        cleaned = value.replace(' ', '').replace('\u00A0', '').replace(',', '.')
        return float(cleaned)
    return float(value)

def format_currency(value):
    """Format number as '36 800,00' (space thousands, comma decimals)."""
    try:
        n = _to_float(value)
        # First format with US grouping, then swap separators
        s = f"{n:,.2f}"
        s = s.replace(',', ' ').replace('.', ',')
        return s
    except Exception:
        # Fallback to string
        return str(value)


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
        # Bump row height to accommodate up to ~7 lines (approx 18px per line)
        try:
            style = ttk.Style()
            base = style.lookup('Treeview', 'rowheight') or 20
            style.configure('Offers.Treeview', rowheight=int(18 * 7))
            tree_style = 'Offers.Treeview'
        except Exception:
            tree_style = 'Treeview'

        self.tree = ttk.Treeview(self.parent_window, columns=TABLE_COLUMNS, show='headings', height=10, style=tree_style)
        self.tree.place(x=50, y=410, width=950, height=300)

        # Configure columns
        self.tree.column('PID', minwidth=50, width=50, stretch=NO)
        self.tree.column('PNAME', minwidth=250, width=280, stretch=YES, anchor=W)
        self.tree.column('UNIT', minwidth=60, width=60, stretch=NO)
        self.tree.column('QTY', minwidth=60, width=80, stretch=NO)
        self.tree.column('U_PRICE', minwidth=100, width=100, stretch=NO)
        self.tree.column('TOTAL', minwidth=100, width=100, stretch=NO)
        self.tree.column('EDIT', minwidth=70, width=70, stretch=NO)
        self.tree.column('DELETE', minwidth=70, width=70, stretch=NO)

        # Configure headings
        self.tree.heading('PID', text='Lp.')
        self.tree.heading('PNAME', text='Nazwa')
        self.tree.heading('UNIT', text='j.m.')
        self.tree.heading('QTY', text='ilość')
        self.tree.heading('U_PRICE', text='Cena jednostkowa netto [PLN]')
        self.tree.heading('TOTAL', text='Wartość netto [PLN]')
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
    
    def input_record(self, product_data):
        """Insert a new product record with auto-generated position number"""
        # Extract data without product_id since it will be auto-generated
        if len(product_data) == 5:
            # Old format with product_id - ignore the first element
            _, product_name, unit, quantity, unit_price = product_data
        else:
            # New format without product_id
            product_name, unit, quantity, unit_price = product_data
        
        if not all([product_name, unit, quantity, unit_price]):
            tkinter.messagebox.showinfo("WARNING", "Enter all the fields!")
            return False
        
        try:
            quantity = int(quantity)
            unit_price = _to_float(unit_price)
            total = quantity * unit_price
            
            # Auto-generate position number (1-based)
            position_number = len(self.tree.get_children()) + 1
            
            print(f"Adding product: {position_number}, {product_name}, {unit}, {quantity}, {unit_price}, {total}")
            
            if self.tree:
                # Format numbers with comma for display
                unit_price_display = format_currency(unit_price)
                total_display = format_currency(total)
                
                # Insert product name as-is (may include newlines); Treeview will display multi-line when rowheight allows
                self.tree.insert('', index=END, iid=self.count,
                               values=(position_number, product_name, unit, quantity, unit_price_display, total_display, "Edytuj", "Usuń"))
                self.count += 1
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
            # Renumber all remaining items
            self.renumber_items()
    
    def renumber_items(self):
        """Renumber all items in the table to maintain sequential order"""
        if not self.tree:
            return
        
        # Get all children (items) in the table
        children = self.tree.get_children()
        
        # Update position numbers sequentially
        for index, child in enumerate(children, 1):
            current_values = list(self.tree.item(child)['values'])
            # Update the position number (first column)
            current_values[0] = index
            # Update the item with new values
            self.tree.item(child, values=current_values)
    
    def get_selected_product(self):
        """Get data of the selected product for editing"""
        if self.tree and self.tree.selection():
            selected_item = self.tree.selection()[0]
            values = self.tree.item(selected_item)['values']
            if values:
                # Convert values back to original format (remove commas from prices)
                # Skip the position number (first column) and DELETE column (last column)
                position_number, product_name, unit, quantity, unit_price_display, total_display = values[:6]
                
                # Convert prices back to normalized dot format for editing
                unit_price = unit_price_display.replace(' ', '').replace('\u00A0', '').replace(',', '.')
                
                return {
                    'item_id': selected_item,
                    'product_name': str(product_name),
                    'unit': str(unit),
                    'quantity': str(quantity),
                    'unit_price': str(unit_price)
                }
        return None
    
    def update_record(self, item_id, product_data):
        """Update existing product record while preserving position number"""
        # Extract data without product_id since position number is auto-managed
        if len(product_data) == 5:
            # Old format with product_id - ignore the first element
            _, product_name, unit, quantity, unit_price = product_data
        else:
            # New format without product_id
            product_name, unit, quantity, unit_price = product_data
        
        if not all([product_name, unit, quantity, unit_price]):
            tkinter.messagebox.showinfo("WARNING", "Enter all the fields!")
            return False
        
        try:
            quantity = int(quantity)
            unit_price = _to_float(unit_price)
            total = quantity * unit_price
            
            if self.tree:
                # Get current position number from the existing record
                current_values = self.tree.item(item_id)['values']
                position_number = current_values[0]  # Keep existing position number
                
                # Format numbers with comma for display
                unit_price_display = format_currency(unit_price)
                total_display = format_currency(total)
                
                # Update the record
                self.tree.item(item_id, values=(position_number, product_name, unit, quantity, unit_price_display, total_display, "Edytuj", "Usuń"))
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
                    # Handle values that might have spaces and comma decimal
                    total_value = _to_float(str(item['values'][5]))
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
                    # Extract values: position, pname, unit, qty, unit_price, total (skip EDIT and DELETE columns)
                    values = item['values'][:6]  # Take only first 6 values, skip EDIT and DELETE
                    position, pname, unit, qty, unit_price, total = values
                    
                    # Create a row as list with formatted values (comma as decimal separator)
                    row = [
                        str(position),                      # Lp (pozycja) - auto-generated
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
                    # Extract values: (position, pname, unit, qty, unit_price, total, edit_icon, delete_icon)
                    pid, pname, unit, qty, unit_price, total = item['values'][:6]  # Take only first 6 values
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
                # Use actual rowheight from style if available
                try:
                    style = ttk.Style()
                    style_name = self.tree.cget('style') or 'Treeview'
                    rh = style.lookup(style_name, 'rowheight')
                    item_height = int(rh) if rh else 20
                except Exception:
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
    
    def move_product_up(self):
        """Move selected product up in the table"""
        if not self.tree or not self.tree.selection():
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do przesunięcia!")
            return False
        
        selected_item = self.tree.selection()[0]
        all_children = self.tree.get_children()
        
        # Find current index
        current_index = all_children.index(selected_item)
        
        # Check if can move up (not already at top)
        if current_index == 0:
            tkinter.messagebox.showinfo("Informacja", "Produkt jest już na górze tabeli!")
            return False
        
        # Get values of current and previous items
        current_values = list(self.tree.item(selected_item)['values'])
        prev_item = all_children[current_index - 1]
        prev_values = list(self.tree.item(prev_item)['values'])
        
        # Swap the items by moving current item before previous
        self.tree.move(selected_item, '', current_index - 1)
        
        # Renumber all items to maintain sequential order
        self.renumber_items()
        
        # Keep selection on moved item
        self.tree.selection_set(selected_item)
        self.tree.focus(selected_item)
        
        return True
    
    def move_product_down(self):
        """Move selected product down in the table"""
        if not self.tree or not self.tree.selection():
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do przesunięcia!")
            return False
        
        selected_item = self.tree.selection()[0]
        all_children = self.tree.get_children()
        
        # Find current index
        current_index = all_children.index(selected_item)
        
        # Check if can move down (not already at bottom)
        if current_index == len(all_children) - 1:
            tkinter.messagebox.showinfo("Informacja", "Produkt jest już na dole tabeli!")
            return False
        
        # Move current item after next item
        self.tree.move(selected_item, '', current_index + 1)
        
        # Renumber all items to maintain sequential order
        self.renumber_items()
        
        # Keep selection on moved item
        self.tree.selection_set(selected_item)
        self.tree.focus(selected_item)
        
        return True

    def on_single_click(self, event):
        """Handle single-click on table to check for edit and delete column clicks"""
        # Get the region that was clicked
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.tree.identify_column(event.x)
            
            # Get the item that was clicked
            item = self.tree.identify_row(event.y)
            if item:
                # Get number of columns to determine column indices
                num_columns = len(self.tree['columns'])
                edit_column_index = f"#{num_columns - 1}"  # Second to last column (EDIT)
                delete_column_index = f"#{num_columns}"    # Last column (DELETE)
                
                if column == edit_column_index:  # EDIT column
                    # Get product data
                    values = self.tree.item(item)['values']
                    if values and self.edit_callback:
                        # Call edit callback with product data
                        # values format: (position, name, unit, qty, price, total, edit_icon, delete_icon)
                        product_data = {
                            'item_id': item,
                            'position': values[0],
                            'product_name': values[1],  # Changed from 'name' to 'product_name'
                            'unit': values[2],
                            'quantity': values[3],
                            'unit_price': values[4].replace(',', '.'),  # Convert back from display format
                            'total': values[5].replace(',', '.')        # Convert back from display format
                        }
                        self.edit_callback(product_data)
                        
                elif column == delete_column_index:  # DELETE column
                    # Ask for confirmation
                    result = tkinter.messagebox.askyesno(
                        "Potwierdź usunięcie", 
                        "Czy na pewno chcesz usunąć ten produkt z tabeli?"
                    )
                    if result:
                        # Delete the item
                        self.tree.delete(item)
                        
                        # Renumber all remaining items
                        self.renumber_items()
                        
                        # Call delete callback if provided
                        if self.delete_callback:
                            self.delete_callback()
