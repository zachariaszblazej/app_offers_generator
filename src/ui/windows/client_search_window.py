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

from src.data.database_service import (
    get_clients_from_db,
    add_client_to_db,
    update_client_in_db,
    set_client_extended_fields,
    validate_alias,
)
from src.ui.windows.client_edit_window import ClientEditWindow


class ClientSearchWindow:
    """Handles client search and selection functionality"""
    
    def __init__(self, parent_window, client_fill_callback):
        self.parent_window = parent_window
        self.client_fill_callback = client_fill_callback
        self.client_window = None
        self._all_clients = []
    
    def open_client_search(self):
        """Open client search window"""
        # Fetch with extended fields so we can fill offer details when needed
        clients = get_clients_from_db(include_extended=True)
        if not clients:
            tkinter.messagebox.showinfo("No Clients", "No clients found in database.")
            return
        self._all_clients = clients

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

        # Create listbox with scrollbar
        list_frame = Frame(main_frame)
        list_frame.pack(fill=BOTH, expand=True)

        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        client_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        client_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=client_listbox.yview)

        # Sorting radio buttons (after listbox is defined so lambda captures it)
        for text, value in sort_options:
            rb = Radiobutton(
                sort_frame,
                text=text,
                variable=self.sort_var,
                value=value,
                command=lambda: self._update_client_list(self._all_clients, client_listbox),
            )
            rb.pack(side=LEFT, padx=10)

        # Store clients data and listbox for sorting
        self.current_clients = clients
        self.current_listbox = client_listbox

        # Populate listbox with sorted client data
        self._update_client_list(self._all_clients, client_listbox)

        # Bind double-click to select client
        client_listbox.bind(
            '<Double-1>',
            lambda event: self._on_client_select(event, search_window, client_listbox, self.current_clients),
        )

        # Capture mouse wheel events so only this window scrolls (and not the underlying editor)
        def _on_wheel(event, lstbox=client_listbox):
            try:
                if getattr(event, 'delta', 0):
                    delta = event.delta
                    step = -1 if delta > 0 else 1
                elif getattr(event, 'num', None) == 4:
                    step = -1
                elif getattr(event, 'num', None) == 5:
                    step = 1
                else:
                    step = 0
                if step:
                    lstbox.yview_scroll(step, 'units')
            except Exception:
                pass
            return 'break'  # prevent propagation to global bindings

        # Bind wheel to this dialog and relevant children
        for w in (search_window, main_frame, list_frame, client_listbox):
            try:
                w.bind('<MouseWheel>', _on_wheel)
                w.bind('<Button-4>', _on_wheel)
                w.bind('<Button-5>', _on_wheel)
            except Exception:
                pass

        # Buttons
        button_frame = Frame(main_frame)
        button_frame.pack(pady=10)

        add_button = Button(
            button_frame,
            text="Dodaj nowego klienta",
            command=lambda: self._open_add_client(search_window),
        )
        add_button.pack(side=LEFT, padx=5)

        select_button = Button(
            button_frame,
            text="Wybierz",
            command=lambda: self._on_client_select(None, search_window, client_listbox, self.current_clients),
        )
        select_button.pack(side=LEFT, padx=5)

        cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)

        # Keep references for refresh after adding a new client
        self._search_window = search_window
        self._main_frame = main_frame
        self._list_frame = list_frame
        self.current_listbox = client_listbox

    def _open_add_client(self, parent_window):
        """Open the add-client modal from within the search dialog"""
        if self.client_window is None:
            self.client_window = ClientEditWindow(parent_window, self._handle_client_save, validate_alias)
        self.client_window.open(mode='add')

    def _handle_client_save(self, mode, data):
        """Save callback for ClientEditWindow opened from search; refresh list on success"""
        if mode == 'add':
            result = add_client_to_db(
                data['nip'], data['company_name'], data['address_p1'], data['address_p2'], data['alias']
            )
            if result[0]:
                set_client_extended_fields(
                    data['nip'], data.get('termin_realizacji'), data.get('termin_platnosci'),
                    data.get('warunki_dostawy'), data.get('waznosc_oferty'), data.get('gwarancja'), data.get('cena')
                )
        else:
            result = update_client_in_db(
                data['nip'], data['company_name'], data['address_p1'], data['address_p2'], data['alias']
            )
            if result[0]:
                set_client_extended_fields(
                    data['nip'], data.get('termin_realizacji'), data.get('termin_platnosci'),
                    data.get('warunki_dostawy'), data.get('waznosc_oferty'), data.get('gwarancja'), data.get('cena')
                )

        # On success, refresh list
        if result[0]:
            try:
                clients = get_clients_from_db(include_extended=True)
                self._all_clients = clients
                # Reuse current sorting setting
                self._update_client_list(self._all_clients, self.current_listbox)
            except Exception:
                pass
        return result
    
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
            nip = client[0]
            company_name = client[1]
            display_text = f"{company_name} (NIP: {nip})"
            listbox.insert(END, display_text)

    def _on_client_select(self, event, search_window, client_listbox, clients):
        """Handle client selection from the listbox"""
        selection = client_listbox.curselection()
        if selection:
            selected_client = self.current_clients[selection[0]]
            # Determine target UI type to avoid breaking WZ which expects 5 fields
            cb_owner = getattr(self.client_fill_callback, '__self__', None)
            owner_class = cb_owner.__class__.__name__ if cb_owner is not None else ''
            if owner_class == 'UIComponents':
                # Offer UI expects we can handle extended fields too
                payload = selected_client
            else:
                # Default/WZ fallback: only first 5 fields (nip, company_name, address1, address2, alias)
                payload = (selected_client[0], selected_client[1], selected_client[2], selected_client[3], selected_client[4])
            self.client_fill_callback(payload)
            search_window.destroy()
