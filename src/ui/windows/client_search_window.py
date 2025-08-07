"""
Client search window for selecting clients from database
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import get_clients_from_db


class ClientSearchWindow:
    """Handles client search and selection functionality"""
    
    def __init__(self, parent_window, client_fill_callback):
        self.parent_window = parent_window
        self.client_fill_callback = client_fill_callback
    
    def open_client_search(self):
        """Open client search window"""
        clients = get_clients_from_db()
        if not clients:
            tkinter.messagebox.showinfo("No Clients", "No clients found in database.")
            return
        
        # Sort clients alphabetically by company name (index 1)
        clients_sorted = sorted(clients, key=lambda x: x[1].lower() if x[1] else "")
        
        # Create search window
        search_window = Toplevel(self.parent_window)
        search_window.title("Wybierz klienta")
        search_window.geometry("700x450")
        search_window.grab_set()  # Make window modal
        
        # Main container
        main_frame = Frame(search_window)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Header
        Label(main_frame, text="Wybierz klienta z listy:", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Sorting options
        sort_frame = Frame(main_frame)
        sort_frame.pack(fill=X, pady=(0, 10))
        
        Label(sort_frame, text="Sortowanie:", font=("Arial", 10)).pack(side=LEFT)
        
        self.sort_var = StringVar(value="name")
        sort_options = [
            ("Nazwa firmy", "name"),
            ("NIP", "nip")
        ]
        
        for text, value in sort_options:
            rb = Radiobutton(sort_frame, text=text, variable=self.sort_var, value=value,
                           command=lambda: self._update_client_list(clients, client_listbox))
            rb.pack(side=LEFT, padx=10)
        
        # Create listbox with scrollbar
        list_frame = Frame(main_frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        client_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        client_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=client_listbox.yview)
        
        # Store clients data and listbox for sorting
        self.current_clients = clients
        self.current_listbox = client_listbox
        
        # Populate listbox with sorted client data
        self._update_client_list(clients, client_listbox)
        
        # Bind double-click to select client
        client_listbox.bind('<Double-1>', lambda event: self._on_client_select(event, search_window, client_listbox, self.current_clients))
        
        # Add select button
        button_frame = Frame(main_frame)
        button_frame.pack(pady=10)
        
        select_button = Button(button_frame, text="Wybierz", 
                              command=lambda: self._on_client_select(None, search_window, client_listbox, self.current_clients))
        select_button.pack(side=LEFT, padx=5)
        
        cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)
    
    def _update_client_list(self, clients, listbox):
        """Update client list based on selected sorting"""
        sort_by = self.sort_var.get()
        
        # Sort clients based on selection
        if sort_by == "name":
            sorted_clients = sorted(clients, key=lambda x: x[1].lower() if x[1] else "")
        elif sort_by == "nip":
            sorted_clients = sorted(clients, key=lambda x: x[0] if x[0] else "")
        else:
            sorted_clients = clients
        
        # Update stored clients list
        self.current_clients = sorted_clients
        
        # Clear and repopulate listbox
        listbox.delete(0, END)
        for client in sorted_clients:
            nip, company_name, address1, address2, alias = client
            display_text = f"{company_name} (NIP: {nip})"
            listbox.insert(END, display_text)

    def _on_client_select(self, event, search_window, client_listbox, clients):
        """Handle client selection from the listbox"""
        selection = client_listbox.curselection()
        if selection:
            selected_client = self.current_clients[selection[0]]
            self.client_fill_callback(selected_client)
            search_window.destroy()
