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
from src.ui.windows.client_edit_window import ClientEditWindow


class BrowseClientsFrame(Frame):
    """Frame for browsing, editing and deleting clients"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.current_editing_nip = None
        self.clients_data = []  # Store current clients data for sorting
        self.sort_column = None
        self.sort_reverse = False
        self.client_window = None
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
                               fg='black',
                               padx=15, pady=8,
                               command=self.show_add_client_form,
                               cursor='hand2')
        add_client_btn.pack(side=LEFT, padx=10)
        
        # Refresh button
        refresh_btn = Button(header_buttons_frame, text="Odśwież",
                            font=("Arial", 12),
                            fg='black',
                            padx=15, pady=8,
                            command=self.refresh_clients_list,
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
        
        # Clients list frame
        list_frame = Frame(content_frame, bg='#f0f0f0')
        list_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 20))
        
        # Clients list label
        list_label = Label(list_frame, text="Lista klientów:", 
                          font=("Arial", 14, "bold"), 
                          bg='#f0f0f0', fg='#333333')
        list_label.pack(anchor=W, pady=(0, 10))
        
        # Treeview for clients list
        columns = (
            'NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'Alias',
            'Termin realizacji', 'Termin płatności', 'Warunki dostawy', 'Ważność oferty', 'Gwarancja', 'Cena',
            'EDIT', 'DELETE'
        )
        self.clients_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # Define headings with sorting commands
        self.clients_tree.heading('NIP', text='NIP', command=lambda: self.sort_by_column('NIP'))
        self.clients_tree.heading('Nazwa firmy', text='Nazwa firmy', command=lambda: self.sort_by_column('Nazwa firmy'))
        self.clients_tree.heading('Adres 1', text='Adres 1', command=lambda: self.sort_by_column('Adres 1'))
        self.clients_tree.heading('Adres 2', text='Adres 2', command=lambda: self.sort_by_column('Adres 2'))
        self.clients_tree.heading('Alias', text='Alias', command=lambda: self.sort_by_column('Alias'))
        self.clients_tree.heading('Termin realizacji', text='Termin realizacji', command=lambda: self.sort_by_column('Termin realizacji'))
        self.clients_tree.heading('Termin płatności', text='Termin płatności', command=lambda: self.sort_by_column('Termin płatności'))
        self.clients_tree.heading('Warunki dostawy', text='Warunki dostawy', command=lambda: self.sort_by_column('Warunki dostawy'))
        self.clients_tree.heading('Ważność oferty', text='Ważność oferty', command=lambda: self.sort_by_column('Ważność oferty'))
        self.clients_tree.heading('Gwarancja', text='Gwarancja', command=lambda: self.sort_by_column('Gwarancja'))
        self.clients_tree.heading('Cena', text='Cena', command=lambda: self.sort_by_column('Cena'))
        self.clients_tree.heading('EDIT', text='Edytuj')
        self.clients_tree.heading('DELETE', text='Usuń')
        
        # Configure column widths
        self.clients_tree.column('NIP', width=100)
        self.clients_tree.column('Nazwa firmy', width=200)
        self.clients_tree.column('Adres 1', width=150)
        self.clients_tree.column('Adres 2', width=150)
        self.clients_tree.column('Alias', width=100)
        self.clients_tree.column('Termin realizacji', width=140)
        self.clients_tree.column('Termin płatności', width=140)
        self.clients_tree.column('Warunki dostawy', width=160)
        self.clients_tree.column('Ważność oferty', width=140)
        self.clients_tree.column('Gwarancja', width=120)
        self.clients_tree.column('Cena', width=100)
        self.clients_tree.column('EDIT', width=70, stretch=NO, anchor=CENTER)
        self.clients_tree.column('DELETE', width=70, stretch=NO, anchor=CENTER)
        
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
        
        # Load clients
        self.refresh_clients_list()
    
    def show_add_client_form(self):
        """Open modal window for adding a new client"""
        if self.client_window is None:
            self.client_window = ClientEditWindow(self.winfo_toplevel(), self._handle_client_save, validate_alias)
        self.client_window.open(mode='add')
    
    # Inline form methods removed in favor of modal window
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def refresh_clients_list(self):
        """Refresh the clients list"""
        # Load clients from database
        clients = get_clients_from_db(include_extended=True)
        self.clients_data = []
        
        # Convert to list of dictionaries for easier sorting
        for client in clients:
            # Extended tuple if include_extended=True
            # (Nip, CompanyName, AddressP1, AddressP2, Alias, TerminRealizacji, TerminPlatnosci, WarunkiDostawy, WaznoscOferty, Gwarancja, Cena)
            nip, company_name, address1, address2, alias, tr, tp, wd, wo, gw, cena = (
                client + ("", "", "", "", "", "") if len(client) == 5 else client
            )
            self.clients_data.append({
                'NIP': nip,
                'Nazwa firmy': company_name,
                'Adres 1': address1,
                'Adres 2': address2,
                'Alias': alias,
                'Termin realizacji': tr,
                'Termin płatności': tp,
                'Warunki dostawy': wd,
                'Ważność oferty': wo,
                'Gwarancja': gw,
                'Cena': cena
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
                client['Termin realizacji'],
                client['Termin płatności'],
                client['Warunki dostawy'],
                client['Ważność oferty'],
                client['Gwarancja'],
                client['Cena'],
                "Edytuj",
                "Usuń"
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
        columns = ['NIP', 'Nazwa firmy', 'Adres 1', 'Adres 2', 'Alias', 'Termin realizacji', 'Termin płatności', 'Warunki dostawy', 'Ważność oferty', 'Gwarancja', 'Cena']
        
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
        """Handle double-click on client item - now disabled, use edit column instead"""
        pass
    
    def edit_selected_client(self):
        """Open modal window to edit the selected client"""
        selection = self.clients_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Brak wyboru", "Proszę wybrać klienta do edycji.")
            return
        item = self.clients_tree.item(selection[0])
        values = item['values']
        if values:
            client = {
                'nip': values[0],
                'company_name': values[1],
                'address_p1': values[2],
                'address_p2': values[3],
                'alias': values[4]
            }
            if self.client_window is None:
                self.client_window = ClientEditWindow(self.winfo_toplevel(), self._handle_client_save, validate_alias)
            self.client_window.open(mode='edit', client=client)
    
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
    
    # No longer used (kept for compatibility if referenced elsewhere)
    def hide_form(self):
        pass
    
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
    
    # Removed inline populate; handled by modal window
    
    # Replaced with handler used by modal window
    def _handle_client_save(self, mode, data):
        """Callback for ClientEditWindow. Returns (success, message)."""
        if mode == 'add':
            result = add_client_to_db(
                data['nip'], data['company_name'], data['address_p1'], data['address_p2'], data['alias']
            )
        else:
            result = update_client_in_db(
                data['nip'], data['company_name'], data['address_p1'], data['address_p2'], data['alias']
            )
        # Refresh list on success for both add and edit
        if result[0]:
            self.refresh_clients_list()
        return result
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
    
    def on_client_single_click(self, event):
        """Handle single-click on clients table to check for edit/delete column clicks"""
        # Get the region that was clicked
        region = self.clients_tree.identify_region(event.x, event.y)
        print(f"Client clicked region: {region}")
        if region == "cell":
            # Get the column that was clicked
            column = self.clients_tree.identify_column(event.x)
            print(f"Client clicked column: {column}")
            
            # Get the item that was clicked
            item = self.clients_tree.identify_row(event.y)
            if item:
                # Get client data
                values = self.clients_tree.item(item)['values']
                client_name = values[1]  # Company name
                client_nip = values[0]   # NIP
                
                # EDIT column is the 12th column (index #12)
                if column == "#12":  
                    # Open edit modal for this client
                    client = {
                        'nip': values[0],
                        'company_name': values[1],
                        'address_p1': values[2],
                        'address_p2': values[3],
                        'alias': values[4]
                    }
                    if self.client_window is None:
                        self.client_window = ClientEditWindow(self.winfo_toplevel(), self._handle_client_save, validate_alias)
                    self.client_window.open(mode='edit', client=client)
                    
                # DELETE column is the 13th column (index #13)
                elif column == "#13":  
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

    # Replaced by modal window; method kept as no-op for backward references
    def open_edit_client_form(self, client_nip, client_values):
        pass
