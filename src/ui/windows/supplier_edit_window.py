"""
Supplier add/edit window in a separate modal dialog
"""
from tkinter import *
import tkinter.messagebox


class SupplierEditWindow:
    """Handles adding/editing a supplier in a separate window"""

    def __init__(self, parent_window, on_save_callback):
        # on_save_callback: def (mode, data_dict) -> (success: bool, message: str)
        self.parent_window = parent_window
        self.on_save_callback = on_save_callback
        self.entries = {}
        self.mode = 'add'
        self.window = None

    def open(self, mode='add', supplier=None):
        """Open the window.
        mode: 'add' | 'edit'
        supplier: optional dict with keys: nip, company_name, address_p1, address_p2
        """
        self.mode = mode

        # Create modal window
        self.window = Toplevel(self.parent_window)
        self.window.title("Dodaj dostawcę" if mode == 'add' else "Edytuj dostawcę")
        self.window.geometry("720x520")
        self.window.resizable(True, True)
        self.window.grab_set()  # modal
        self.window.transient(self.parent_window)
        self.window.configure(bg='#f8f9fa')

        # Title
        title = Label(
            self.window,
            text=("Dodaj nowego dostawcę" if mode == 'add' else "Edytuj dane dostawcy"),
            font=("Arial", 18, "bold"),
            bg='#f8f9fa', fg='#343a40'
        )
        title.pack(pady=(25, 15), fill=X)

        # Form container
        form = Frame(self.window, bg='white', relief=RIDGE, bd=2)
        form.pack(pady=10, padx=40, fill=BOTH, expand=True)

        rows = [
            ('nip', 'NIP (10 cyfr)*:', True if mode == 'edit' else False),
            ('company_name', 'Nazwa firmy*:', False),
            ('address_p1', 'Adres (linia 1)*:', False),
            ('address_p2', 'Adres (linia 2)*:', False),
        ]

        self.entries = {}
        for idx, (key, label, readonly) in enumerate(rows):
            Label(form, text=label, font=("Arial", 12), bg='white').grid(row=idx, column=0, sticky=W, padx=12, pady=8)
            if key == 'company_name':
                txt = Text(form, font=("Arial", 12), width=40, height=3, wrap=WORD)
                txt.grid(row=idx, column=1, sticky=W, padx=12, pady=8)
                self.entries[key] = txt
            else:
                ent = Entry(form, font=("Arial", 12), width=40)
                if readonly:
                    ent.config(state='readonly', bg='#e9ecef')
                ent.grid(row=idx, column=1, sticky=W, padx=12, pady=8)
                self.entries[key] = ent

        # Info label
        Label(form, text="Pola oznaczone gwiazdką (*) są wymagane.", font=("Arial", 10), bg='white', fg='#555555').grid(
            row=len(rows), column=0, columnspan=2, sticky=W, padx=12, pady=(4, 12)
        )

        # Pre-fill when editing
        if mode == 'edit' and supplier:
            # NIP
            self.entries['nip'].config(state='normal')
            self.entries['nip'].delete(0, END)
            self.entries['nip'].insert(0, supplier.get('nip', ''))
            self.entries['nip'].config(state='readonly')
            # Company name: show literal \n as real newlines
            try:
                display_name = (supplier.get('company_name', '') or '').replace('\\n', '\n')
                self.entries['company_name'].delete('1.0', END)
                self.entries['company_name'].insert('1.0', display_name)
            except Exception:
                pass
            # Addresses
            self.entries['address_p1'].insert(0, supplier.get('address_p1', ''))
            self.entries['address_p2'].insert(0, supplier.get('address_p2', ''))

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

        # Focus
        try:
            (self.entries['company_name'] if self.mode == 'edit' else self.entries['nip']).focus_set()
        except Exception:
            pass

    def _save(self):
        """Collect form data and call the provided save callback"""
        # Read
        data = {}
        try:
            raw_name = self.entries['company_name'].get('1.0', 'end-1c')
        except Exception:
            raw_name = ''
        data['company_name'] = (raw_name or '').strip().replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')
        data['nip'] = self.entries['nip'].get().strip()
        data['address_p1'] = self.entries['address_p1'].get().strip()
        data['address_p2'] = self.entries['address_p2'].get().strip()

        # Validate
        if not all([data['nip'], data['company_name'], data['address_p1'], data['address_p2']]):
            tkinter.messagebox.showerror("Błąd", "Proszę wypełnić wymagane pola (NIP, Nazwa, Adres 1, Adres 2).")
            return
        if self.mode == 'add':
            if not data['nip'].isdigit() or len(data['nip']) != 10:
                tkinter.messagebox.showerror("Błąd", "NIP musi składać się z dokładnie 10 cyfr.")
                return

        # Delegate
        success, message = self.on_save_callback(self.mode, data)
        if success:
            self.window.destroy()
        else:
            tkinter.messagebox.showerror("Błąd", message or "Nie udało się zapisać danych dostawcy.")
