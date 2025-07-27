from tkinter import *
from tkinter import ttk
from config import COLOR_THEME
from database import get_suppliers_from_db, add_supplier_to_db, delete_supplier_from_db, update_supplier_in_db

class BrowseSuppliersFrame(Frame):
    """Frame for browsing, editing and deleting suppliers"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.current_editing_nip = None
        self.create_ui()
        
    def create_ui(self):
        """Create the browse suppliers UI"""
        self.configure(bg=COLOR_THEME['bg_primary'])
        
        # Header frame
        header_frame = Frame(self, bg=COLOR_THEME['bg_primary'])
        header_frame.pack(fill=X, padx=20, pady=20)
        
        # Title
        title_label = Label(header_frame, text="Zarządzanie dostawcami", 
                           font=("Arial", 18, "bold"), 
                           bg=COLOR_THEME['bg_primary'], fg=COLOR_THEME['text_primary'])
        title_label.pack(side=LEFT)
        
        # Buttons on the right side of header
        header_buttons_frame = Frame(header_frame, bg=COLOR_THEME['bg_primary'])
        header_buttons_frame.pack(side=RIGHT)
        
        # Add new supplier button
        add_supplier_btn = Button(header_buttons_frame, text="Dodaj nowego dostawcę",
                                 font=("Arial", 12),
                                 bg=COLOR_THEME['btn_success'], fg=COLOR_THEME['btn_text'],
                                 padx=15, pady=8,
                                 command=self.show_add_supplier_form,
                                 cursor='hand2')
        add_supplier_btn.pack(side=LEFT, padx=10)
        
        # Refresh button
        refresh_btn = Button(header_buttons_frame, text="Odśwież",
                            font=("Arial", 12),
                            bg=COLOR_THEME['btn_info'], fg=COLOR_THEME['btn_text'],
                            padx=15, pady=8,
                            command=self.refresh_suppliers_list,
                            cursor='hand2')
        refresh_btn.pack(side=LEFT, padx=5)
        
        # Return to main menu button
        return_btn = Button(header_buttons_frame, text="Powrót do menu głównego",
                           font=("Arial", 12),
                           bg=COLOR_THEME['btn_neutral'], fg=COLOR_THEME['btn_text'],
                           padx=15, pady=8,
                           command=lambda: self.nav_manager.show_frame('main_menu'),
                           cursor='hand2')
        return_btn.pack(side=LEFT, padx=5)
        
        # Main content frame
        content_frame = Frame(self, bg=COLOR_THEME['bg_primary'])
        content_frame.pack(fill=BOTH, expand=True, padx=20)
        
        # Suppliers list frame
        list_frame = Frame(content_frame, bg=COLOR_THEME['bg_primary'])
        list_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 20))
        
        # Suppliers list label
        list_label = Label(list_frame, text="Lista dostawców:", 
                          font=("Arial", 14, "bold"), 
                          bg=COLOR_THEME['bg_primary'], fg=COLOR_THEME['text_primary'])
        list_label.pack(anchor=W, pady=(0, 10))
        
        # Treeview for suppliers list
        columns = ('NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2')
        self.suppliers_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.suppliers_tree.heading('NIP', text='NIP')
        self.suppliers_tree.heading('Nazwa firmy', text='Nazwa firmy')
        self.suppliers_tree.heading('Adres 1', text='Adres 1')
        self.suppliers_tree.heading('Adres 2', text='Adres 2')
        
        # Configure column widths
        self.suppliers_tree.column('NIP', width=100)
        self.suppliers_tree.column('Nazwa firmy', width=250)
        self.suppliers_tree.column('Adres 1', width=200)
        self.suppliers_tree.column('Adres 2', width=200)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.suppliers_tree.yview)
        self.suppliers_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.suppliers_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind selection event
        self.suppliers_tree.bind('<<TreeviewSelect>>', self.on_supplier_select)
        
        # Edit/Delete buttons frame
        buttons_frame = Frame(list_frame, bg=COLOR_THEME['bg_primary'])
        buttons_frame.pack(fill=X, pady=10)
        
        edit_btn = Button(buttons_frame, text="Edytuj wybranego dostawcę",
                         font=("Arial", 12),
                         bg=COLOR_THEME['btn_warning'], fg=COLOR_THEME['btn_text'],
                         padx=15, pady=8,
                         command=self.edit_selected_supplier,
                         cursor='hand2')
        edit_btn.pack(side=LEFT, padx=(0, 10))
        
        delete_btn = Button(buttons_frame, text="Usuń wybranego dostawcę",
                           font=("Arial", 12),
                           bg=COLOR_THEME['btn_danger'], fg=COLOR_THEME['btn_text'],
                           padx=15, pady=8,
                           command=self.delete_selected_supplier,
                           cursor='hand2')
        delete_btn.pack(side=LEFT)
        
        # Form frame for editing suppliers (initially hidden)
        self.form_frame = Frame(content_frame, bg=COLOR_THEME['bg_secondary'], relief=RIDGE, bd=2)
        # Note: form_frame is packed later when showing forms
        
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
                          bg=COLOR_THEME['bg_secondary'], fg=COLOR_THEME['text_primary'])
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
                         font=("Arial", 12), bg=COLOR_THEME['bg_secondary'], fg=COLOR_THEME['text_primary'])
            label.pack(anchor=W, padx=20, pady=(10, 0))
            
            # Entry
            entry = Entry(self.form_frame, font=("Arial", 12), width=40)
            if is_readonly:
                entry.config(state='readonly', bg=COLOR_THEME['input_disabled'])
            entry.pack(anchor=W, padx=20, pady=(0, 5))
            
            self.form_entries[field_name] = entry
            
            # Validation labels
            validation_label = Label(self.form_frame, text="", 
                                   font=("Arial", 10), bg=COLOR_THEME['bg_secondary'])
            validation_label.pack(anchor=W, padx=20)
            self.form_validation_labels[field_name] = validation_label
            
            # Bind validation events
            if field_name == 'nip' and not is_readonly:
                entry.bind('<KeyRelease>', self.validate_nip_input)
        
        # Configure grid layout for responsive design
        self.form_frame.columnconfigure(0, weight=1)
        
        # Buttons frame
        form_buttons_frame = Frame(self.form_frame, bg=COLOR_THEME['bg_secondary'])
        form_buttons_frame.pack(pady=20)
        
        # Save button
        save_text = "Zapisz dostawcę" if self.form_mode == 'add' else "Zapisz zmiany"
        save_btn = Button(form_buttons_frame, text=save_text,
                         font=("Arial", 12, "bold"),
                         bg=COLOR_THEME['btn_primary'], fg=COLOR_THEME['btn_text'],
                         padx=20, pady=10,
                         command=self.save_supplier,
                         cursor='hand2')
        save_btn.pack(side=LEFT, padx=10)
        
        # Clear/Cancel button
        clear_text = "Wyczyść formularz" if self.form_mode == 'add' else "Anuluj"
        clear_btn = Button(form_buttons_frame, text=clear_text,
                          font=("Arial", 12),
                          bg=COLOR_THEME['btn_neutral'], fg=COLOR_THEME['btn_text'],
                          padx=20, pady=10,
                          command=self.clear_or_cancel_form,
                          cursor='hand2')
        clear_btn.pack(side=LEFT, padx=10)
    
    def refresh_suppliers_list(self):
        """Refresh the suppliers list"""
        
        # Clear existing items
        for item in self.suppliers_tree.get_children():
            self.suppliers_tree.delete(item)
        
        # Load suppliers
        suppliers = get_suppliers_from_db()
        for supplier in suppliers:
            self.suppliers_tree.insert('', 'end', values=supplier)
    
    def on_supplier_select(self, event):
        """Handle supplier selection"""
        selection = self.suppliers_tree.selection()
        if selection:
            # Get selected supplier data
            item = self.suppliers_tree.item(selection[0])
            values = item['values']
            print(f"Selected supplier: {values}")
    
    def edit_selected_supplier(self):
        """Edit the selected supplier"""
        selection = self.suppliers_tree.selection()
        if not selection:
            import tkinter.messagebox
            tkinter.messagebox.showwarning("Uwaga", "Proszę wybrać dostawcę do edycji!")
            return
        
        # Get selected supplier data
        item = self.suppliers_tree.item(selection[0])
        values = item['values']
        
        # Set form mode and current editing NIP
        self.form_mode = 'edit'
        self.current_editing_nip = values[0]
        
        # Create form
        self.create_supplier_form()
        
        # Fill form with current data
        self.form_entries['nip'].config(state='normal')
        self.form_entries['nip'].delete(0, END)
        self.form_entries['nip'].insert(0, values[0])
        self.form_entries['nip'].config(state='readonly')
        
        self.form_entries['company_name'].delete(0, END)
        self.form_entries['company_name'].insert(0, values[1])
        
        self.form_entries['address_p1'].delete(0, END)
        self.form_entries['address_p1'].insert(0, values[2])
        
        self.form_entries['address_p2'].delete(0, END)
        self.form_entries['address_p2'].insert(0, values[3])
        
        # Show form frame
        self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
    
    def delete_selected_supplier(self):
        """Delete the selected supplier"""
        selection = self.suppliers_tree.selection()
        if not selection:
            import tkinter.messagebox
            tkinter.messagebox.showwarning("Uwaga", "Proszę wybrać dostawcę do usunięcia!")
            return
        
        # Get selected supplier data
        item = self.suppliers_tree.item(selection[0])
        values = item['values']
        supplier_name = values[1]
        supplier_nip = values[0]
        
        # Confirm deletion
        import tkinter.messagebox
        if tkinter.messagebox.askyesno("Potwierdzenie", 
                                      f"Czy na pewno chcesz usunąć dostawcę:\n{supplier_name} (NIP: {supplier_nip})?"):
            from database import delete_supplier_from_db
            success, message = delete_supplier_from_db(supplier_nip)
            
            if success:
                tkinter.messagebox.showinfo("Sukces", message)
                self.refresh_suppliers_list()
                # Hide form frame if it was showing this supplier
                if hasattr(self, 'current_editing_nip') and self.current_editing_nip == supplier_nip:
                    self.hide_form()
            else:
                tkinter.messagebox.showerror("Błąd", message)
    
    def validate_nip_input(self, event=None):
        """Real-time NIP validation for adding new suppliers"""
        from database import validate_supplier_nip
        nip = self.form_entries['nip'].get()
        
        if not nip:
            self.form_validation_labels['nip'].config(text="", fg='black')
            return
        
        is_valid, message = validate_supplier_nip(nip)
        if is_valid:
            self.form_validation_labels['nip'].config(text="✓ " + message, fg='green')
        else:
            self.form_validation_labels['nip'].config(text="✗ " + message, fg='red')
    
    def save_supplier(self):
        """Save supplier data (both add and edit modes)"""
        import tkinter.messagebox
        
        # Get form data
        company_name = self.form_entries['company_name'].get().strip()
        address_p1 = self.form_entries['address_p1'].get().strip()
        address_p2 = self.form_entries['address_p2'].get().strip()
        nip = self.form_entries['nip'].get().strip()
        
        # Basic validation
        if not all([company_name, address_p1, address_p2, nip]):
            tkinter.messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione!")
            return
        
        if self.form_mode == 'add':
            # Add new supplier
            from database import add_supplier_to_db
            success, message = add_supplier_to_db(nip, company_name, address_p1, address_p2)
        else:
            # Update existing supplier
            from database import update_supplier_in_db
            success, message = update_supplier_in_db(self.current_editing_nip, company_name, address_p1, address_p2)
        
        if success:
            tkinter.messagebox.showinfo("Sukces", message)
            self.refresh_suppliers_list()
            self.hide_form()
        else:
            tkinter.messagebox.showerror("Błąd", message)
    
    def clear_or_cancel_form(self):
        """Clear form or cancel operation"""
        if self.form_mode == 'add':
            # Clear all fields
            for entry in self.form_entries.values():
                if entry['state'] != 'readonly':
                    entry.delete(0, END)
            
            # Clear validation labels
            for label in self.form_validation_labels.values():
                label.config(text="")
        else:
            # Cancel edit - hide form
            self.hide_form()
    
    def hide_form(self):
        """Hide the form frame"""
        self.form_frame.pack_forget()
        self.form_mode = None
        self.current_editing_nip = None
    
    def return_to_main_menu(self):
        """Return to the main menu"""
        self.hide_form()  # Hide form if visible
        self.nav_manager.show_frame('main_menu')
