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
    update_supplier_in_db, delete_supplier_from_db
)


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
                                 bg='#28a745', fg='black',
                                 padx=15, pady=8,
                                 command=self.show_add_supplier_form,
                                 cursor='hand2')
        add_supplier_btn.pack(side=LEFT, padx=10)
        
        # Refresh button
        refresh_btn = Button(header_buttons_frame, text="Odśwież",
                            font=("Arial", 12),
                            bg='#17a2b8', fg='black',
                            padx=15, pady=8,
                            command=self.refresh_suppliers_list,
                            cursor='hand2')
        refresh_btn.pack(side=LEFT, padx=5)
        
        # Return button
        return_btn = Button(header_buttons_frame, text="Powrót do menu głównego",
                           font=("Arial", 12),
                           bg='#6c757d', fg='black',
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
        columns = ('NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'DELETE')
        self.suppliers_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Define headings with sorting commands
        self.suppliers_tree.heading('NIP', text='NIP', command=lambda: self.sort_by_column('NIP'))
        self.suppliers_tree.heading('Nazwa firmy', text='Nazwa firmy', command=lambda: self.sort_by_column('Nazwa firmy'))
        self.suppliers_tree.heading('Adres 1', text='Adres 1', command=lambda: self.sort_by_column('Adres 1'))
        self.suppliers_tree.heading('Adres 2', text='Adres 2', command=lambda: self.sort_by_column('Adres 2'))
        self.suppliers_tree.heading('DELETE', text='❌')
        
        # Configure column widths
        self.suppliers_tree.column('NIP', width=100)
        self.suppliers_tree.column('Nazwa firmy', width=250)
        self.suppliers_tree.column('Adres 1', width=200)
        self.suppliers_tree.column('Adres 2', width=200)
        self.suppliers_tree.column('DELETE', width=40, stretch=NO)
        
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
        
        # Form frame (for both editing and adding)
        self.form_frame = Frame(content_frame, bg='#f0f0f0', relief=RIDGE, bd=2)
        self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
        
        # Initially hide form frame
        self.form_frame.pack_forget()
        
        # Track current mode
        self.form_mode = None  # 'edit' or 'add'
        
        # Load suppliers
        self.refresh_suppliers_list()
    
    def show_add_supplier_form(self):
        """Show form for adding a new supplier"""
        self.form_mode = 'add'
        self.current_editing_nip = None
        self.create_supplier_form()
        self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
    
    def create_supplier_form(self):
        """Create form for adding or editing a supplier"""
        # Clear existing widgets
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        
        # Form title
        title_text = "Dodaj nowego dostawcę" if self.form_mode == 'add' else "Edytuj dostawcę"
        form_title = Label(self.form_frame, text=title_text, 
                          font=("Arial", 16, "bold"), 
                          bg='#f0f0f0', fg='#333333')
        form_title.pack(pady=20)
        
        # Form fields
        self.form_entries = {}
        self.form_validation_labels = {}
        
        fields = [
            ('nip', 'NIP (10 cyfr):', self.form_mode == 'edit'),  # NIP read-only only when editing
            ('company_name', 'Nazwa firmy:', False),
            ('address_p1', 'Adres (linia 1):', False),
            ('address_p2', 'Adres (linia 2):', False)
        ]
        
        for field_name, label_text, is_readonly in fields:
            # Label
            label = Label(self.form_frame, text=label_text, 
                         font=("Arial", 12), bg='#f0f0f0')
            label.pack(anchor=W, padx=20, pady=(10, 0))
            
            # Entry
            entry = Entry(self.form_frame, font=("Arial", 12), width=30)
            if is_readonly:
                entry.config(state='readonly', bg='#e9ecef')
            entry.pack(anchor=W, padx=20, pady=(0, 5))
            
            self.form_entries[field_name] = entry
            
            # Validation labels
            validation_label = Label(self.form_frame, text="", 
                                   font=("Arial", 10), bg='#f0f0f0')
            validation_label.pack(anchor=W, padx=20)
            self.form_validation_labels[field_name] = validation_label
            
            # Bind validation events
            if field_name == 'nip' and not is_readonly:
                entry.bind('<KeyRelease>', self.validate_nip_input)
        
        # Buttons frame
        form_buttons_frame = Frame(self.form_frame, bg='#f0f0f0')
        form_buttons_frame.pack(pady=20)
        
        # Save button
        save_text = "Zapisz dostawcę" if self.form_mode == 'add' else "Zapisz zmiany"
        save_btn = Button(form_buttons_frame, text=save_text,
                         font=("Arial", 12, "bold"),
                         bg='#007bff', fg='black',
                         padx=20, pady=10,
                         command=self.save_supplier,
                         cursor='hand2')
        save_btn.pack(side=LEFT, padx=10)
        
        # Cancel button
        cancel_btn = Button(form_buttons_frame, text="Anuluj",
                           font=("Arial", 12),
                           bg='#6c757d', fg='black',
                           padx=20, pady=10,
                           command=self.hide_form,
                           cursor='hand2')
        cancel_btn.pack(side=LEFT, padx=10)
        
        # If editing, populate form with current data
        if self.form_mode == 'edit' and self.current_editing_nip:
            self.populate_form_for_edit()
    
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
            nip, company_name, address1, address2 = supplier
            self.suppliers_data.append({
                'NIP': nip,
                'Nazwa firmy': company_name,
                'Adres 1': address1,
                'Adres 2': address2
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
            self.suppliers_tree.insert('', 'end', values=(
                supplier['NIP'], 
                supplier['Nazwa firmy'], 
                supplier['Adres 1'], 
                supplier['Adres 2'],
                "❌"
            ))
    
    def sort_by_column(self, column):
        """Sort suppliers data by the specified column"""
        # Toggle sort direction if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Sort the data
        self.suppliers_data.sort(key=lambda x: str(x[column] or '').lower(), reverse=self.sort_reverse)
        
        # Update column headers to show sort direction
        self.update_column_headers()
        
        # Refresh display
        self.display_suppliers_data()
    
    def update_column_headers(self):
        """Update column headers to show current sort direction"""
        columns = ['NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2']
        
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
        """Handle double-click on supplier item to edit supplier"""
        selection = self.suppliers_tree.selection()
        if selection:
            # Call edit_selected_supplier method
            self.edit_selected_supplier()
    
    def edit_selected_supplier(self):
        """Edit the selected supplier"""
        selection = self.suppliers_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Brak wyboru", "Proszę wybrać dostawcę do edycji.")
            return
        
        item = self.suppliers_tree.item(selection[0])
        values = item['values']
        if values:
            self.current_editing_nip = values[0]
            self.form_mode = 'edit'
            self.create_supplier_form()
            self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
    
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
                    tkinter.messagebox.showinfo("Sukces", message)
                    self.refresh_suppliers_list()
                else:
                    tkinter.messagebox.showerror("Błąd", message)
    
    def hide_form(self):
        """Hide the form"""
        self.form_frame.pack_forget()
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
        """Populate form fields when editing"""
        if not self.current_editing_nip:
            return
        
        supplier = get_supplier_by_nip(self.current_editing_nip)
        if supplier:
            nip, company_name, address1, address2 = supplier
            
            # Temporarily enable readonly fields for setting values
            self.form_entries['nip'].config(state='normal')
            self.form_entries['nip'].delete(0, END)
            self.form_entries['nip'].insert(0, nip)
            self.form_entries['nip'].config(state='readonly')
            
            self.form_entries['company_name'].delete(0, END)
            self.form_entries['company_name'].insert(0, company_name)
            
            self.form_entries['address_p1'].delete(0, END)
            self.form_entries['address_p1'].insert(0, address1)
            
            self.form_entries['address_p2'].delete(0, END)
            self.form_entries['address_p2'].insert(0, address2)
    
    def save_supplier(self):
        """Save supplier (add or update)"""
        # Get form data
        nip = self.form_entries['nip'].get().strip()
        company_name = self.form_entries['company_name'].get().strip()
        address_p1 = self.form_entries['address_p1'].get().strip()
        address_p2 = self.form_entries['address_p2'].get().strip()
        
        # Validate required fields
        if not all([nip, company_name, address_p1]):
            tkinter.messagebox.showerror("Błąd", "Proszę wypełnić wszystkie wymagane pola.")
            return
        
        # Validate NIP
        if not nip.isdigit() or len(nip) != 10:
            tkinter.messagebox.showerror("Błąd", "NIP musi składać się z dokładnie 10 cyfr.")
            return
        
        if self.form_mode == 'add':
            success, message = add_supplier_to_db(nip, company_name, address_p1, address_p2)
        else:  # edit
            success, message = update_supplier_in_db(nip, company_name, address_p1, address_p2)
        
        if success:
            tkinter.messagebox.showinfo("Sukces", message)
            self.refresh_suppliers_list()
            self.hide_form()
        else:
            tkinter.messagebox.showerror("Błąd", message)
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
    
    def on_supplier_single_click(self, event):
        """Handle single-click on suppliers table to check for delete column clicks"""
        # Get the region that was clicked
        region = self.suppliers_tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.suppliers_tree.identify_column(event.x)
            # DELETE column is the 5th column (index #5)
            if column == "#5":  
                # Get the item that was clicked
                item = self.suppliers_tree.identify_row(event.y)
                if item:
                    # Get supplier data for confirmation
                    values = self.suppliers_tree.item(item)['values']
                    supplier_name = values[1]  # Company name
                    supplier_nip = values[0]   # NIP
                    
                    # Ask for confirmation
                    result = tkinter.messagebox.askyesno(
                        "Potwierdź usunięcie", 
                        f"Czy na pewno chcesz usunąć dostawcę '{supplier_name}' (NIP: {supplier_nip})?"
                    )
                    if result:
                        # Delete from database
                        success, message = delete_supplier_from_db(supplier_nip)
                        if success:
                            tkinter.messagebox.showinfo("Sukces", message)
                            self.refresh_suppliers_list()
                        else:
                            tkinter.messagebox.showerror("Błąd", message)
