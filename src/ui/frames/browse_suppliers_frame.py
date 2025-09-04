"""
Suppliers management frame
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import (
    get_suppliers_from_db, add_supplier_to_db, get_supplier_by_nip,
    update_supplier_in_db, delete_supplier_from_db, set_default_supplier
)
from src.ui.windows.supplier_edit_window import SupplierEditWindow


class BrowseSuppliersFrame(Frame):
    """Frame for browsing, editing and deleting suppliers"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.current_editing_nip = None
        self.suppliers_data = []  # Store current suppliers data for sorting
        self.sort_column = None
        self.sort_reverse = False
        self.create_ui()
        
    def create_ui(self):
        """Create the browse suppliers UI"""
        self.configure(bg='#f0f0f0')

        # Header frame
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=20)

        # Title
        title_label = Label(header_frame, text="Zarządzanie dostawcami",
                            font=("Arial", 18, "bold"),
                            bg='#f0f0f0', fg='#333333')
        title_label.pack(side=LEFT)

        # Buttons on the right side of header
        header_buttons_frame = Frame(header_frame, bg='#f0f0f0')
        header_buttons_frame.pack(side=RIGHT)

        # Add new supplier button
        add_supplier_btn = Button(header_buttons_frame, text="Dodaj nowego dostawcę",
                                  font=("Arial", 12),
                                  fg='black',
                                  padx=15, pady=8,
                                  command=self.show_add_supplier_form,
                                  cursor='hand2')
        add_supplier_btn.pack(side=LEFT, padx=10)

        # Refresh button
        refresh_btn = Button(header_buttons_frame, text="Odśwież",
                             font=("Arial", 12),
                             fg='black',
                             padx=15, pady=8,
                             command=self.refresh_suppliers_list,
                             cursor='hand2')
        refresh_btn.pack(side=LEFT, padx=5)

        # Return button
        return_btn = Button(header_buttons_frame, text="Powrót do menu głównego",
                            font=("Arial", 12),
                            fg='black',
                            padx=15, pady=8,
                            command=self.return_to_main_menu,
                            cursor='hand2')
        return_btn.pack(side=LEFT, padx=5)

        # Main content frame
        content_frame = Frame(self, bg='#f0f0f0')
        content_frame.pack(fill=BOTH, expand=True, padx=20)

        # Suppliers list frame
        list_frame = Frame(content_frame, bg='#f0f0f0')
        list_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 20))

        # Suppliers list label
        list_label = Label(list_frame, text="Lista dostawców:",
                           font=("Arial", 14, "bold"),
                           bg='#f0f0f0', fg='#333333')
        list_label.pack(anchor=W, pady=(0, 10))

        # Treeview for suppliers list
        columns = ('NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'Domyślny', 'EDIT', 'DELETE', 'DEFAULT')
        self.suppliers_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # Define headings with sorting commands
        self.suppliers_tree.heading('NIP', text='NIP', command=lambda: self.sort_by_column('NIP'))
        self.suppliers_tree.heading('Nazwa firmy', text='Nazwa firmy', command=lambda: self.sort_by_column('Nazwa firmy'))
        self.suppliers_tree.heading('Adres 1', text='Adres 1', command=lambda: self.sort_by_column('Adres 1'))
        self.suppliers_tree.heading('Adres 2', text='Adres 2', command=lambda: self.sort_by_column('Adres 2'))
        self.suppliers_tree.heading('Domyślny', text='Domyślny', command=lambda: self.sort_by_column('Domyślny'))
        self.suppliers_tree.heading('EDIT', text='Edytuj')
        self.suppliers_tree.heading('DELETE', text='Usuń')
        self.suppliers_tree.heading('DEFAULT', text='Ustaw domyślny')

        # Configure column widths
        self.suppliers_tree.column('NIP', width=100)
        self.suppliers_tree.column('Nazwa firmy', width=200)
        self.suppliers_tree.column('Adres 1', width=150)
        self.suppliers_tree.column('Adres 2', width=150)
        self.suppliers_tree.column('Domyślny', width=80, stretch=NO, anchor=CENTER)
        self.suppliers_tree.column('EDIT', width=70, stretch=NO, anchor=CENTER)
        self.suppliers_tree.column('DELETE', width=70, stretch=NO, anchor=CENTER)
        self.suppliers_tree.column('DEFAULT', width=120, stretch=NO, anchor=CENTER)

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.suppliers_tree.yview)
        self.suppliers_tree.configure(yscrollcommand=scrollbar.set)

        # Pack treeview and scrollbar
        self.suppliers_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Bind selection event
        self.suppliers_tree.bind('<<TreeviewSelect>>', self.on_supplier_select)

        # Bind double-click for editing suppliers
        self.suppliers_tree.bind('<Double-Button-1>', self.on_supplier_double_click)

        # Bind single click for delete functionality
        self.suppliers_tree.bind('<ButtonRelease-1>', self.on_supplier_single_click)

        # No side form anymore; we use a modal window for add/edit like clients
        self.form_frame = None
        self.form_mode = None

        # Load suppliers
        self.refresh_suppliers_list()
    
    def show_add_supplier_form(self):
        """Open modal for adding a new supplier"""
        self.form_mode = 'add'
        self.current_editing_nip = None
        def _on_save(mode, data):
            company_name_db = data['company_name']  # already normalized to literal \n
            if mode == 'add':
                ok, msg = add_supplier_to_db(data['nip'], company_name_db, data['address_p1'], data['address_p2'])
            else:
                ok, msg = update_supplier_in_db(data['nip'], company_name_db, data['address_p1'], data['address_p2'])
            if ok:
                self.refresh_suppliers_list()
            return ok, msg

        win = SupplierEditWindow(self, _on_save)
        win.open('add')
    
    def create_supplier_form(self):
        """Deprecated: no side form; kept for backward compatibility (no-op)."""
        pass
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def refresh_suppliers_list(self):
        """Refresh the suppliers list"""
        # Load suppliers from database
        suppliers = get_suppliers_from_db()
        self.suppliers_data = []
        
        # Convert to list of dictionaries for easier sorting
        for supplier in suppliers:
            nip, company_name, address1, address2, is_default = supplier
            self.suppliers_data.append({
                'NIP': nip,
                'Nazwa firmy': company_name,
                'Adres 1': address1,
                'Adres 2': address2,
                'Domyślny': '✓' if is_default == 1 else ''
            })
        
        # Display the data
        self.display_suppliers_data()
    
    def display_suppliers_data(self):
        """Display suppliers data in the treeview"""
        # Clear existing items
        for item in self.suppliers_tree.get_children():
            self.suppliers_tree.delete(item)
        
        # Populate tree with current data
        for supplier in self.suppliers_data:
            # Use display-safe company name (strip literal \n markers)
            display_company = str(supplier['Nazwa firmy'] or '').replace('\\n', ' ')
            self.suppliers_tree.insert('', 'end', values=(
                supplier['NIP'], 
                display_company, 
                supplier['Adres 1'], 
                supplier['Adres 2'], 
                supplier['Domyślny'],
                "Edytuj",
                "Usuń",
                "Ustaw domyślny"
            ))
    
    def sort_by_column(self, column):
        """Sort suppliers data by the specified column"""
        # Toggle sort direction if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Sort the data (for 'Nazwa firmy' sort by display value without literal \n)
        if column == 'Nazwa firmy':
            self.suppliers_data.sort(
                key=lambda x: str((x[column] or '')).replace('\\n', ' ').lower(),
                reverse=self.sort_reverse
            )
        else:
            self.suppliers_data.sort(key=lambda x: str(x[column] or '').lower(), reverse=self.sort_reverse)
        
        # Update column headers to show sort direction
        self.update_column_headers()
        
        # Refresh display
        self.display_suppliers_data()
    
    def update_column_headers(self):
        """Update column headers to show current sort direction"""
        columns = ['NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'Domyślny']
        
        # Reset all headers
        for col in columns:
            self.suppliers_tree.heading(col, text=col)
        
        # Add sort indicator to current sort column
        if self.sort_column:
            arrow = " ↓" if self.sort_reverse else " ↑"
            self.suppliers_tree.heading(self.sort_column, text=f'{self.sort_column}{arrow}')
    
    def on_supplier_select(self, event):
        """Handle supplier selection"""
        selection = self.suppliers_tree.selection()
        if selection:
            item = self.suppliers_tree.item(selection[0])
            values = item['values']
            if values:
                self.selected_supplier_nip = values[0]
    
    def on_supplier_double_click(self, event):
        """Handle double-click on supplier item - now disabled, use edit column instead"""
        pass
    
    def edit_selected_supplier(self):
        """Edit the selected supplier in a modal dialog"""
        selection = self.suppliers_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Brak wyboru", "Proszę wybrać dostawcę do edycji.")
            return
        item = self.suppliers_tree.item(selection[0])
        values = item['values']
        if not values:
            return
        nip = values[0]
        supplier = get_supplier_by_nip(nip)
        if not supplier:
            tkinter.messagebox.showerror("Błąd", "Nie znaleziono dostawcy w bazie.")
            return
        # supplier tuple: nip, company_name, address1, address2, is_default
        sup_dict = {
            'nip': supplier[0],
            'company_name': supplier[1],
            'address_p1': supplier[2],
            'address_p2': supplier[3]
        }

        def _on_save(mode, data):
            return update_supplier_in_db(data['nip'], data['company_name'], data['address_p1'], data['address_p2'])

        win = SupplierEditWindow(self, _on_save)
        win.open('edit', sup_dict)
        self.refresh_suppliers_list()
    
    def delete_selected_supplier(self):
        """Delete the selected supplier"""
        selection = self.suppliers_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Brak wyboru", "Proszę wybrać dostawcę do usunięcia.")
            return
        
        item = self.suppliers_tree.item(selection[0])
        values = item['values']
        if values:
            nip = values[0]
            company_name = values[1]
            
            if tkinter.messagebox.askquestion("Potwierdzenie", 
                                             f"Czy na pewno chcesz usunąć dostawcę:\n{company_name} (NIP: {nip})?") == 'yes':
                from src.data.database_service import delete_supplier_from_db
                success, message = delete_supplier_from_db(nip)
                
                if success:
                    self.refresh_suppliers_list()
                else:
                    tkinter.messagebox.showerror("Błąd", message)
    
    def hide_form(self):
        """No-op (legacy)."""
        self.form_mode = None
        self.current_editing_nip = None
    
    def validate_nip_input(self, event):
        """Validate NIP input in real-time"""
        nip_entry = self.form_entries['nip']
        nip_value = nip_entry.get()
        validation_label = self.form_validation_labels['nip']
        
        if not nip_value:
            validation_label.config(text="", fg='red')
        elif not nip_value.isdigit():
            validation_label.config(text="NIP może zawierać tylko cyfry", fg='red')
        elif len(nip_value) != 10:
            validation_label.config(text=f"NIP musi mieć 10 cyfr (obecnie: {len(nip_value)})", fg='red')
        else:
            validation_label.config(text="✓ NIP prawidłowy", fg='green')
    
    def populate_form_for_edit(self):
        """Deprecated (modal edit in use)."""
        pass
    
    def save_supplier(self):
        """Deprecated (handled by modal)."""
        pass
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
    
    def on_supplier_single_click(self, event):
        """Handle single-click on suppliers table to check for edit/delete column clicks"""
        # Get the region that was clicked
        region = self.suppliers_tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.suppliers_tree.identify_column(event.x)
            
            # Get the item that was clicked
            item = self.suppliers_tree.identify_row(event.y)
            if item:
                # Get supplier data
                values = self.suppliers_tree.item(item)['values']
                supplier_name = values[1]  # Company name
                supplier_nip = values[0]   # NIP
                
                # EDIT column is the 6th column (index #6)
                if column == "#6":  
                    # Open modal edit for this supplier
                    self.open_edit_supplier_form(supplier_nip, values)
                    
                # DELETE column is the 7th column (index #7)
                elif column == "#7":  
                    # Ask for confirmation
                    result = tkinter.messagebox.askyesno(
                        "Potwierdź usunięcie", 
                        f"Czy na pewno chcesz usunąć dostawcę '{supplier_name}' (NIP: {supplier_nip})?"
                    )
                    if result:
                        # Delete from database
                        success, message = delete_supplier_from_db(supplier_nip)
                        if success:
                            self.refresh_suppliers_list()
                        else:
                            tkinter.messagebox.showerror("Błąd", message)
                            
                # DEFAULT column is the 8th column (index #8)
                elif column == "#8":  
                    # Set as default supplier
                    result = tkinter.messagebox.askyesno(
                        "Potwierdź ustawienie domyślnego", 
                        f"Czy na pewno chcesz ustawić '{supplier_name}' jako domyślnego dostawcę?"
                    )
                    if result:
                        success, message = self.set_default_supplier(supplier_nip)
                        if success:
                            self.refresh_suppliers_list()
                        else:
                            tkinter.messagebox.showerror("Błąd", message)

    def open_edit_supplier_form(self, supplier_nip, supplier_values):
        """Open modal edit window for a specific supplier"""
        supplier = get_supplier_by_nip(supplier_nip)
        if not supplier:
            tkinter.messagebox.showerror("Błąd", "Nie znaleziono dostawcy w bazie.")
            return
        sup_dict = {
            'nip': supplier[0],
            'company_name': supplier[1],
            'address_p1': supplier[2],
            'address_p2': supplier[3]
        }
        def _on_save(mode, data):
            return update_supplier_in_db(data['nip'], data['company_name'], data['address_p1'], data['address_p2'])
        win = SupplierEditWindow(self, _on_save)
        win.open('edit', sup_dict)
        self.refresh_suppliers_list()

    def set_default_supplier(self, supplier_nip):
        """Set supplier as default"""
        from src.data.database_service import set_default_supplier
        return set_default_supplier(supplier_nip)
