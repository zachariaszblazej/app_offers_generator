"""
WZ Product table component for managing product list - simplified version without prices, with dynamic row height like offers.
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
        self.parent_frame = parent_frame
        self.edit_callback = edit_callback
        self.delete_callback = delete_callback
        self.tree = None
        self.count = 0
        # Dynamic row height management (same approach as offers)
        self._style = None
        self._style_name = 'WZ.Treeview'
        self._line_px = 18
        self._max_lines = 1
        self.create_table()

    def create_table(self):
        try:
            self._style = ttk.Style()
            base = self._style.lookup('Treeview', 'rowheight') or 18
            self._style.configure(self._style_name, rowheight=int(self._line_px * self._max_lines))
            tree_style = self._style_name
        except Exception:
            tree_style = 'Treeview'

        self.columns = ('PID', 'PNAME', 'UNIT', 'QTY', 'EDIT', 'DELETE')
        self.tree = ttk.Treeview(self.parent_window, columns=self.columns, show='headings', height=10, style=tree_style)
        self.tree.place(x=50, y=410, width=950, height=300)

        self.tree.column('PID', minwidth=50, width=50, stretch=NO)
        self.tree.column('PNAME', minwidth=250, width=420, stretch=YES, anchor=W)
        self.tree.column('UNIT', minwidth=80, width=80, stretch=NO)
        self.tree.column('QTY', minwidth=100, width=120, stretch=NO)
        self.tree.column('EDIT', minwidth=100, width=100, stretch=NO)
        self.tree.column('DELETE', minwidth=100, width=100, stretch=NO)

        self.tree.heading('PID', text='Lp.')
        self.tree.heading('PNAME', text='Nazwa')
        self.tree.heading('UNIT', text='j.m.')
        self.tree.heading('QTY', text='Ilość')
        self.tree.heading('EDIT', text='Edytuj')
        self.tree.heading('DELETE', text='Usuń')

        self.scrollbar_y = ttk.Scrollbar(self.parent_window, orient=VERTICAL, command=self.tree.yview)
        self.scrollbar_y.place(x=1000, y=410, height=300)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)

        self.tree.bind("<Enter>", self.on_table_enter)
        self.tree.bind("<Leave>", self.on_table_leave)
        self.scrollbar_y.bind("<Enter>", self.on_table_enter)
        self.scrollbar_y.bind("<Leave>", self.on_table_leave)
        self.tree.bind("<Motion>", self.on_table_motion)
        self.scrollbar_y.bind("<Motion>", self.on_table_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)

    def _compute_needed_lines(self, product_name: str) -> int:
        try:
            if not isinstance(product_name, str):
                return 1
            lines = product_name.count('\n') + 1
            return max(1, min(7, lines))
        except Exception:
            return 1

    def _refresh_rowheight(self):
        try:
            if not self._style:
                return
            max_lines = 1
            for child in self.tree.get_children():
                vals = self.tree.item(child).get('values') or []
                if len(vals) >= 2:
                    max_lines = max(max_lines, self._compute_needed_lines(str(vals[1])))
            self._max_lines = max_lines
            self._style.configure(self._style_name, rowheight=int(self._line_px * self._max_lines))
        except Exception:
            pass

    def input_record(self, product_data):
        # Accept either [pid, name, unit, qty] or [name, unit, qty]
        if len(product_data) == 4:
            _, product_name, unit, quantity = product_data
        else:
            product_name, unit, quantity = product_data

        if not all([product_name, unit, quantity]):
            tkinter.messagebox.showinfo("WARNING", "Enter all the fields!")
            return False

        try:
            quantity = int(quantity)
            position_number = len(self.tree.get_children()) + 1
            if self.tree:
                self.tree.insert('', index=END, iid=self.count,
                                 values=(position_number, product_name, unit, quantity, 'Edytuj', 'Usuń'))
                self._refresh_rowheight()
                self.count += 1
                return True
        except ValueError:
            tkinter.messagebox.showinfo("WARNING", "Enter valid numeric values!")
            return False

    def insert_product(self, product_data):
        self.count += 1
        self.tree.insert('', 'end',
                         values=(self.count,
                                 product_data.get('name', ''),
                                 product_data.get('unit', ''),
                                 product_data.get('quantity', ''),
                                 'EDYTUJ', 'USUŃ'))
        self._refresh_rowheight()

    def update_product(self, item_id, product_data):
        vals = list(self.tree.item(item_id).get('values') or [])
        if not vals:
            return False
        pid = vals[0]
        name = product_data.get('name', vals[1])
        unit = product_data.get('unit', vals[2])
        qty = product_data.get('quantity', vals[3])
        self.tree.item(item_id, values=(pid, name, unit, qty, 'EDYTUJ', 'USUŃ'))
        self._refresh_rowheight()
        return True

    def get_all_products(self):
        rows = []
        for child in self.tree.get_children():
            vals = self.tree.item(child).get('values') or []
            if len(vals) >= 4:
                pid, name, unit, qty = vals[:4]
                rows.append([str(pid), str(name), str(unit), str(qty)])
        return rows

    def get_product_data(self, item_id):
        vals = self.tree.item(item_id).get('values') or []
        if len(vals) >= 4:
            return {
                'item_id': item_id,
                'name': str(vals[1]),
                'unit': str(vals[2]),
                'quantity': str(vals[3])
            }
        return {}

    def clear_table(self):
        for item in list(self.tree.get_children()):
            self.tree.delete(item)
        self.count = 0
        self._refresh_rowheight()

    def update_product_numbers(self):
        self.renumber_items()
        self.count = len(self.tree.get_children())

    def remove_product(self, item_id):
        self.tree.delete(item_id)
        self.update_product_numbers()
        self._refresh_rowheight()

    def get_selected_item(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def move_product_up(self):
        if not self.tree or not self.tree.selection():
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do przesunięcia!")
            return False
        item = self.tree.selection()[0]
        children = self.tree.get_children()
        idx = children.index(item)
        if idx == 0:
            tkinter.messagebox.showinfo("Informacja", "Produkt jest już na górze tabeli!")
            return False
        self.tree.move(item, '', idx - 1)
        self.renumber_items()
        self.tree.selection_set(item)
        self.tree.focus(item)
        return True

    def move_product_down(self):
        if not self.tree or not self.tree.selection():
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do przesunięcia!")
            return False
        item = self.tree.selection()[0]
        children = self.tree.get_children()
        idx = children.index(item)
        if idx == len(children) - 1:
            tkinter.messagebox.showinfo("Informacja", "Produkt jest już na dole tabeli!")
            return False
        self.tree.move(item, '', idx + 1)
        self.renumber_items()
        self.tree.selection_set(item)
        self.tree.focus(item)
        return True

    def renumber_items(self):
        children = self.tree.get_children()
        for i, child in enumerate(children, 1):
            vals = list(self.tree.item(child).get('values') or [])
            if not vals:
                continue
            vals[0] = i
            self.tree.item(child, values=vals)

    def on_table_enter(self, event):
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_enter'):
            self.parent_frame.on_product_table_enter()

    def on_table_leave(self, event):
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_leave'):
            self.parent_frame.on_product_table_leave()

    def on_table_motion(self, event):
        if self.parent_frame and hasattr(self.parent_frame, 'on_product_table_enter'):
            self.parent_frame.on_product_table_enter()

    def on_single_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item:
            return
        num_columns = len(self.tree['columns'])
        edit_col = f"#{num_columns - 1}"
        delete_col = f"#{num_columns}"
        if column == edit_col and self.edit_callback:
            self.edit_callback(item)
        elif column == delete_col:
            if tkinter.messagebox.askyesno("Potwierdź usunięcie", "Czy na pewno chcesz usunąć ten produkt z tabeli?"):
                self.tree.delete(item)
                self.renumber_items()
                if self.delete_callback:
                    self.delete_callback()
