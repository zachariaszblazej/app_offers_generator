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
        
        # Create search window
        search_window = Toplevel(self.parent_window)
        search_window.title("Wybierz klienta")
        search_window.geometry("600x400")
        search_window.grab_set()  # Make window modal
        
        # Search label
        Label(search_window, text="Wybierz klienta z listy:", font=("Arial", 12)).pack(pady=10)
        
        # Create listbox with scrollbar
        frame = Frame(search_window)
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = Scrollbar(frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        client_listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        client_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=client_listbox.yview)
        
        # Populate listbox with client data
        for client in clients:
            nip, company_name, address1, address2, alias = client
            display_text = f"{alias} - {company_name} (NIP: {nip})"
            client_listbox.insert(END, display_text)
        
        # Bind double-click to select client
        client_listbox.bind('<Double-1>', lambda event: self._on_client_select(event, search_window, client_listbox, clients))
        
        # Add select button
        button_frame = Frame(search_window)
        button_frame.pack(pady=10)
        
        select_button = Button(button_frame, text="Wybierz", 
                              command=lambda: self._on_client_select(None, search_window, client_listbox, clients))
        select_button.pack(side=LEFT, padx=5)
        
        cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)

    def _on_client_select(self, event, search_window, client_listbox, clients):
        """Handle client selection from the listbox"""
        selection = client_listbox.curselection()
        if selection:
            selected_client = clients[selection[0]]
            self.client_fill_callback(selected_client)
            search_window.destroy()
