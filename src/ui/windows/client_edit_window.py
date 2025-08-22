"""
Client add/edit window in a separate modal dialog
"""
from tkinter import *
import tkinter.messagebox


class ClientEditWindow:
    """Handles adding/editing a client in a separate window"""

    def __init__(self, parent_window, on_save_callback, validate_alias_fn=None):
        self.parent_window = parent_window
        self.on_save_callback = on_save_callback  # def (mode, data_dict) -> (success: bool, message: str)
        self.validate_alias_fn = validate_alias_fn
        self.entries = {}
        self.mode = 'add'
        self.window = None

    def open(self, mode='add', client=None):
        """Open the window.
        mode: 'add' | 'edit'
        client: optional dict with keys: nip, company_name, address_p1, address_p2, alias
        """
        self.mode = mode

        # Create modal window
        self.window = Toplevel(self.parent_window)
        self.window.title("Dodaj klienta" if mode == 'add' else "Edytuj klienta")
        self.window.geometry("720x560")
        self.window.resizable(False, False)
        self.window.grab_set()  # modal
        self.window.transient(self.parent_window)
        self.window.configure(bg='#f8f9fa')

        # Title
        title = Label(
            self.window,
            text=("Dodaj nowego klienta" if mode == 'add' else "Edytuj dane klienta"),
            font=("Arial", 18, "bold"),
            bg='#f8f9fa', fg='#343a40'
        )
        title.pack(pady=(25, 15), fill=X)

        # Form container
        form = Frame(self.window, bg='white', relief=RIDGE, bd=2)
        form.pack(pady=10, padx=40, fill=BOTH, expand=True)

        # Fields
        rows = [
            ('nip', 'NIP (10 cyfr):', True if mode == 'edit' else False),
            ('company_name', 'Nazwa firmy:', False),
            ('address_p1', 'Adres (linia 1):', False),
            ('address_p2', 'Adres (linia 2):', False),
            ('alias', 'Alias:', False),
        ]

        self.entries = {}
        for idx, (key, label, readonly) in enumerate(rows):
            Label(form, text=label, font=("Arial", 12), bg='white').grid(row=idx, column=0, sticky=W, padx=12, pady=10)
            ent = Entry(form, font=("Arial", 12), width=36)
            if readonly:
                ent.config(state='readonly', bg='#e9ecef')
            ent.grid(row=idx, column=1, sticky=W, padx=12, pady=10)
            self.entries[key] = ent

        # Pre-fill when editing
        if mode == 'edit' and client:
            # Temporarily enable NIP to set value
            self.entries['nip'].config(state='normal')
            self.entries['nip'].delete(0, END)
            self.entries['nip'].insert(0, client.get('nip', ''))
            self.entries['nip'].config(state='readonly')
            self.entries['company_name'].insert(0, client.get('company_name', ''))
            self.entries['address_p1'].insert(0, client.get('address_p1', ''))
            self.entries['address_p2'].insert(0, client.get('address_p2', ''))
            self.entries['alias'].insert(0, client.get('alias', ''))

        # Buttons
        buttons = Frame(self.window, bg='#f8f9fa', height=90)
        buttons.pack(fill=X, pady=(10, 20))
        buttons.pack_propagate(False)

        primary_text = "✓ ZAPISZ" if mode == 'edit' else "✓ DODAJ"
        action_btn = Button(
            buttons,
            text=primary_text,
            font=("Arial", 16, "bold"),
            fg='black', padx=35, pady=14,
            command=self._save,
            cursor='hand2', relief=RAISED, bd=4
        )
        action_btn.place(relx=0.32, rely=0.5, anchor=CENTER)

        cancel_btn = Button(
            buttons,
            text="✗ Anuluj",
            font=("Arial", 14),
            fg='black', padx=24, pady=12,
            command=self.window.destroy,
            cursor='hand2'
        )
        cancel_btn.place(relx=0.68, rely=0.5, anchor=CENTER)

        # Shortcuts
        self.window.bind('<Return>', lambda e: self._save())
        self.window.bind('<KP_Enter>', lambda e: self._save())

        # Focus
        (self.entries['company_name'] if mode == 'edit' else self.entries['nip']).focus_set()

    def _save(self):
        """Collect form data and call the provided save callback"""
        # Read fields
        data = {k: self.entries[k].get().strip() for k in ['nip', 'company_name', 'address_p1', 'address_p2', 'alias']}

        # Basic validation
        if not all(data.values()):
            tkinter.messagebox.showerror("Błąd", "Proszę wypełnić wszystkie wymagane pola.")
            return

        if self.mode == 'add':
            if not data['nip'].isdigit() or len(data['nip']) != 10:
                tkinter.messagebox.showerror("Błąd", "NIP musi składać się z dokładnie 10 cyfr.")
                return

        if self.validate_alias_fn is not None:
            ok, msg = self.validate_alias_fn(data['alias'])
            if not ok:
                tkinter.messagebox.showerror("Błąd", msg)
                return

        # Delegate save
        success, message = self.on_save_callback(self.mode, data)
        if success:
            self.window.destroy()
        else:
            tkinter.messagebox.showerror("Błąd", message or "Nie udało się zapisać danych klienta.")
