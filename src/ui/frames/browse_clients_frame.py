"""
Clients management frame
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import (
    get_clients_from_db, add_client_to_db, get_client_by_nip,
    update_client_in_db, delete_client_from_db, validate_nip, validate_alias
)


class BrowseClientsFrame(Frame):
    """Frame for browsing, editing and deleting clients"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.current_editing_nip = None
        self.clients_data = []  # Store current clients data for sorting
        self.sort_column = None
        self.sort_reverse = False
        self.create_ui()
        
    def create_ui(self):
        """Create the browse clients UI"""
        self.configure(bg='#f0f0f0')
        
        # Header frame
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=20)
        
        # Title
        title_label = Label(header_frame, text="Zarządzanie klientami", 
                           font=("Arial", 18, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(side=LEFT)
        
        # Buttons on the right side of header
        header_buttons_frame = Frame(header_frame, bg='#f0f0f0')
        header_buttons_frame.pack(side=RIGHT)
        
        # Add new client button
        add_client_btn = Button(header_buttons_frame, text="Dodaj nowego klienta",
                               font=("Arial", 12),
                               bg='#28a745', fg='black',
                               padx=15, pady=8,
                               command=self.show_add_client_form,
                               cursor='hand2')
        add_client_btn.pack(side=LEFT, padx=10)
        
        # Refresh button
        refresh_btn = Button(header_buttons_frame, text="Odśwież",
                            font=("Arial", 12),
                            bg='#17a2b8', fg='black',
                            padx=15, pady=8,
                            command=self.refresh_clients_list,
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
        
        # Clients list frame
        list_frame = Frame(content_frame, bg='#f0f0f0')
        list_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 20))
        
        # Clients list label
        list_label = Label(list_frame, text="Lista klientów:", 
                          font=("Arial", 14, "bold"), 
                          bg='#f0f0f0', fg='#333333')
        list_label.pack(anchor=W, pady=(0, 10))
        
        # Treeview for clients list
        columns = ('NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'Alias', 'DELETE')
        self.clients_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Define headings with sorting commands
        self.clients_tree.heading('NIP', text='NIP', command=lambda: self.sort_by_column('NIP'))
        self.clients_tree.heading('Nazwa firmy', text='Nazwa firmy', command=lambda: self.sort_by_column('Nazwa firmy'))
        self.clients_tree.heading('Adres 1', text='Adres 1', command=lambda: self.sort_by_column('Adres 1'))
        self.clients_tree.heading('Adres 2', text='Adres 2', command=lambda: self.sort_by_column('Adres 2'))
        self.clients_tree.heading('Alias', text='Alias', command=lambda: self.sort_by_column('Alias'))
        self.clients_tree.heading('DELETE', text='❌')
        
        # Configure column widths
        self.clients_tree.column('NIP', width=100)
        self.clients_tree.column('Nazwa firmy', width=200)
        self.clients_tree.column('Adres 1', width=150)
        self.clients_tree.column('Adres 2', width=150)
        self.clients_tree.column('Alias', width=80)
        self.clients_tree.column('DELETE', width=40, stretch=NO, anchor=CENTER)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.clients_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind selection event
        self.clients_tree.bind('<<TreeviewSelect>>', self.on_client_select)
        
        # Bind double-click for editing clients
        self.clients_tree.bind('<Double-Button-1>', self.on_client_double_click)
        
        # Bind single click for delete functionality
        self.clients_tree.bind('<ButtonRelease-1>', self.on_client_single_click)
        
        # Form frame (for both editing and adding)
        self.form_frame = Frame(content_frame, bg='#f0f0f0', relief=RIDGE, bd=2)
        self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
        
        # Initially hide form frame
        self.form_frame.pack_forget()
        
        # Track current mode
        self.form_mode = None  # 'edit' or 'add'
        
        # Load clients
        self.refresh_clients_list()
    
    def show_add_client_form(self):
        """Show form for adding a new client"""
        self.form_mode = 'add'
        self.current_editing_nip = None
        self.create_client_form()
        self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
    
    def create_client_form(self):
        """Create form for adding or editing a client"""
        # Clear existing widgets
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        
        # Form title
        title_text = "Dodaj nowego klienta" if self.form_mode == 'add' else "Edytuj klienta"
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
            ('address_p2', 'Adres (linia 2):', False),
            ('alias', 'Alias:', False)
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
            elif field_name == 'alias':
                entry.bind('<KeyRelease>', self.validate_alias_input)
            
            # Bind Enter key to save client
            entry.bind('<Return>', lambda event: self.save_client())
        
        # Buttons frame
        form_buttons_frame = Frame(self.form_frame, bg='#f0f0f0')
        form_buttons_frame.pack(pady=20)
        
        # Save button
        save_text = "Zapisz klienta" if self.form_mode == 'add' else "Zapisz zmiany"
        save_btn = Button(form_buttons_frame, text=save_text,
                         font=("Arial", 12, "bold"),
                         bg='#007bff', fg='black',
                         padx=20, pady=10,
                         command=self.save_client,
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
        
        # Bind Enter key globally to the form frame and all its children
        self.form_frame.bind('<Return>', lambda event: self.save_client())
        self.form_frame.bind('<KP_Enter>', lambda event: self.save_client())  # Numpad Enter
        self.form_frame.focus_set()  # Allow form frame to receive key events
        
        # If editing, populate form with current data
        if self.form_mode == 'edit' and self.current_editing_nip:
            self.populate_form_for_edit()
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def refresh_clients_list(self):
        """Refresh the clients list"""
        # Load clients from database
        clients = get_clients_from_db()
        self.clients_data = []
        
        # Convert to list of dictionaries for easier sorting
        for client in clients:
            nip, company_name, address1, address2, alias = client
            self.clients_data.append({
                'NIP': nip,
                'Nazwa firmy': company_name,
                'Adres 1': address1,
                'Adres 2': address2,
                'Alias': alias
            })
        
        # Display the data
        self.display_clients_data()
    
    def display_clients_data(self):
        """Display clients data in the treeview"""
        # Clear existing items
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        # Populate tree with current data
        for client in self.clients_data:
            self.clients_tree.insert('', 'end', values=(
                client['NIP'], 
                client['Nazwa firmy'], 
                client['Adres 1'], 
                client['Adres 2'], 
                client['Alias'],
                "❌"
            ))
    
    def sort_by_column(self, column):
        """Sort clients data by the specified column"""
        # Toggle sort direction if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Sort the data
        self.clients_data.sort(key=lambda x: str(x[column] or '').lower(), reverse=self.sort_reverse)
        
        # Update column headers to show sort direction
        self.update_column_headers()
        
        # Refresh display
        self.display_clients_data()
    
    def update_column_headers(self):
        """Update column headers to show current sort direction"""
        columns = ['NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'Alias']
        
        # Reset all headers
        for col in columns:
            self.clients_tree.heading(col, text=col)
        
        # Add sort indicator to current sort column
        if self.sort_column:
            arrow = " ↓" if self.sort_reverse else " ↑"
            self.clients_tree.heading(self.sort_column, text=f'{self.sort_column}{arrow}')
    
    def on_client_select(self, event):
        """Handle client selection"""
        selection = self.clients_tree.selection()
        if selection:
            item = self.clients_tree.item(selection[0])
            values = item['values']
            if values:
                self.selected_client_nip = values[0]
    
    def on_client_double_click(self, event):
        """Handle double-click on client item to edit client"""
        selection = self.clients_tree.selection()
        if selection:
            # Call edit_selected_client method
            self.edit_selected_client()
    
    def edit_selected_client(self):
        """Edit the selected client"""
        selection = self.clients_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Brak wyboru", "Proszę wybrać klienta do edycji.")
            return
        
        item = self.clients_tree.item(selection[0])
        values = item['values']
        if values:
            self.current_editing_nip = values[0]
            self.form_mode = 'edit'
            self.create_client_form()
            self.form_frame.pack(side=RIGHT, fill=Y, padx=(20, 0))
    
    def delete_selected_client(self):
        """Delete the selected client"""
        selection = self.clients_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Brak wyboru", "Proszę wybrać klienta do usunięcia.")
            return
        
        item = self.clients_tree.item(selection[0])
        values = item['values']
        if values:
            nip = values[0]
            company_name = values[1]
            
            if tkinter.messagebox.askquestion("Potwierdzenie", 
                                             f"Czy na pewno chcesz usunąć klienta:\n{company_name} (NIP: {nip})?") == 'yes':
                success, message = delete_client_from_db(nip)
                
                if success:
                    self.refresh_clients_list()
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
    
    def validate_alias_input(self, event):
        """Validate alias input in real-time"""
        alias_entry = self.form_entries['alias']
        alias_value = alias_entry.get()
        validation_label = self.form_validation_labels['alias']
        
        if not alias_value:
            validation_label.config(text="", fg='red')
            return
        
        is_valid, message = validate_alias(alias_value)
        if is_valid:
            validation_label.config(text="✓ " + message, fg='green')
        else:
            validation_label.config(text="✗ " + message, fg='red')
    
    def populate_form_for_edit(self):
        """Populate form fields when editing"""
        if not self.current_editing_nip:
            return
        
        client = get_client_by_nip(self.current_editing_nip)
        if client:
            nip, company_name, address1, address2, alias = client
            
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
            
            self.form_entries['alias'].delete(0, END)
            self.form_entries['alias'].insert(0, alias)
    
    def save_client(self):
        """Save client (add or update)"""
        # Get form data
        nip = self.form_entries['nip'].get().strip()
        company_name = self.form_entries['company_name'].get().strip()
        address_p1 = self.form_entries['address_p1'].get().strip()
        address_p2 = self.form_entries['address_p2'].get().strip()
        alias = self.form_entries['alias'].get().strip()
        
        # Validate required fields
        if not all([nip, company_name, address_p1, address_p2, alias]):
            tkinter.messagebox.showerror("Błąd", "Proszę wypełnić wszystkie wymagane pola.")
            return
        
        # Validate NIP
        if not nip.isdigit() or len(nip) != 10:
            tkinter.messagebox.showerror("Błąd", "NIP musi składać się z dokładnie 10 cyfr.")
            return
        
        # Validate alias
        is_valid, message = validate_alias(alias)
        if not is_valid:
            tkinter.messagebox.showerror("Błąd", message)
            return
        
        if self.form_mode == 'add':
            success, message = add_client_to_db(nip, company_name, address_p1, address_p2, alias)
        else:  # edit
            success, message = update_client_in_db(nip, company_name, address_p1, address_p2, alias)
        
        if success:
            self.refresh_clients_list()
            self.hide_form()
        else:
            tkinter.messagebox.showerror("Błąd", message)
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
    
    def on_client_single_click(self, event):
        """Handle single-click on clients table to check for delete column clicks"""
        # Get the region that was clicked
        region = self.clients_tree.identify_region(event.x, event.y)
        print(f"Client clicked region: {region}")
        if region == "cell":
            # Get the column that was clicked
            column = self.clients_tree.identify_column(event.x)
            print(f"Client clicked column: {column}")
            # DELETE column is the 6th column (index #6)
            if column == "#6":  
                # Get the item that was clicked
                item = self.clients_tree.identify_row(event.y)
                if item:
                    # Get client data for confirmation
                    values = self.clients_tree.item(item)['values']
                    client_name = values[1]  # Company name
                    client_nip = values[0]   # NIP
                    
                    # Ask for confirmation
                    result = tkinter.messagebox.askyesno(
                        "Potwierdź usunięcie", 
                        f"Czy na pewno chcesz usunąć klienta '{client_name}' (NIP: {client_nip})?"
                    )
                    if result:
                        # Delete from database
                        success, message = delete_client_from_db(client_nip)
                        if success:
                            self.refresh_clients_list()
                        else:
                            tkinter.messagebox.showerror("Błąd", message)
