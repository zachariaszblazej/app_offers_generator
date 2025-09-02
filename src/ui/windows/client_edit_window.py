"""
Client add/edit window in a separate modal dialog
"""
from tkinter import *
import tkinter.messagebox
from src.utils.settings import settings_manager


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
        client: optional dict with keys: nip, company_name, address_p1, address_p2, alias, and extended fields
        """
        self.mode = mode

        # Create modal window
        self.window = Toplevel(self.parent_window)
        self.window.title("Dodaj klienta" if mode == 'add' else "Edytuj klienta")
        self.window.geometry("900x720")
        self.window.resizable(True, True)
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

        # Form container with scrolling
        form_holder = Frame(self.window, bg='white', relief=RIDGE, bd=2)
        form_holder.pack(pady=10, padx=40, fill=BOTH, expand=True)

        canvas = Canvas(form_holder, bg='white', highlightthickness=0)
        vscroll = Scrollbar(form_holder, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        vscroll.pack(side=RIGHT, fill=Y)

        form = Frame(canvas, bg='white')
        form_window = canvas.create_window((0, 0), window=form, anchor='nw')

        def _on_form_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def _on_canvas_configure(event):
            # Make inner frame width follow canvas width
            canvas.itemconfigure(form_window, width=event.width)

        form.bind('<Configure>', _on_form_configure)
        canvas.bind('<Configure>', _on_canvas_configure)

        # Fields
        rows = [
            ('nip', 'NIP (10 cyfr)*:', True if mode == 'edit' else False),
            ('company_name', 'Nazwa firmy*:', False),
            ('address_p1', 'Adres (linia 1)*:', False),
            ('address_p2', 'Adres (linia 2)*:', False),
            ('alias', 'Alias*:', False),
            # Extended fields
            ('termin_realizacji', 'Termin realizacji:', False),
            ('termin_platnosci', 'Termin płatności:', False),
            ('warunki_dostawy', 'Warunki dostawy:', False),
            ('waznosc_oferty', 'Ważność oferty:', False),
            ('gwarancja', 'Gwarancja:', False),
            ('cena', 'Cena:', False),
        ]

        self.entries = {}
        for idx, (key, label, readonly) in enumerate(rows):
            Label(form, text=label, font=("Arial", 12), bg='white').grid(row=idx, column=0, sticky=W, padx=12, pady=6)
            if key == 'company_name':
                # Multi-line Text for company name; will be saved with literal \n between lines
                txt = Text(form, font=("Arial", 12), width=40, height=3, wrap=WORD)
                txt.grid(row=idx, column=1, sticky=W, padx=12, pady=6)
                self.entries[key] = txt
            else:
                ent = Entry(form, font=("Arial", 12), width=40)
                if readonly:
                    ent.config(state='readonly', bg='#e9ecef')
                ent.grid(row=idx, column=1, sticky=W, padx=12, pady=6)
                self.entries[key] = ent

    # No prefill in add mode: leave all fields empty

        # Info label about required fields
        try:
            info_lbl = Label(
                form,
                text="Pola oznaczone gwiazdką (*) są wymagane.",
                font=("Arial", 10),
                bg='white', fg='#555555'
            )
            info_lbl.grid(row=len(rows), column=0, columnspan=2, sticky=W, padx=12, pady=(4, 12))
        except Exception:
            pass

        # Pre-fill when editing
        if mode == 'edit' and client:
            # Temporarily enable NIP to set value
            self.entries['nip'].config(state='normal')
            self.entries['nip'].delete(0, END)
            self.entries['nip'].insert(0, client.get('nip', ''))
            self.entries['nip'].config(state='readonly')
            # Show multi-line name by converting literal \n markers to actual newlines
            try:
                display_name = (client.get('company_name', '') or '').replace('\\n', '\n')
                self.entries['company_name'].delete('1.0', END)
                self.entries['company_name'].insert('1.0', display_name)
            except Exception:
                pass
            self.entries['address_p1'].insert(0, client.get('address_p1', ''))
            self.entries['address_p2'].insert(0, client.get('address_p2', ''))
            self.entries['alias'].insert(0, client.get('alias', ''))
            # Extended
            self.entries['termin_realizacji'].insert(0, client.get('termin_realizacji', ''))
            self.entries['termin_platnosci'].insert(0, client.get('termin_platnosci', ''))
            self.entries['warunki_dostawy'].insert(0, client.get('warunki_dostawy', ''))
            self.entries['waznosc_oferty'].insert(0, client.get('waznosc_oferty', ''))
            self.entries['gwarancja'].insert(0, client.get('gwarancja', ''))
            self.entries['cena'].insert(0, client.get('cena', ''))

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
        # Read fields
        keys = ['nip', 'company_name', 'address_p1', 'address_p2', 'alias',
                'termin_realizacji', 'termin_platnosci', 'warunki_dostawy', 'waznosc_oferty', 'gwarancja', 'cena']
        data = {}
        for k in keys:
            if k == 'company_name':
                # Convert actual newlines to literal \n before saving to DB
                try:
                    raw = self.entries['company_name'].get('1.0', 'end-1c')
                except Exception:
                    raw = ''
                data['company_name'] = (raw or '').strip().replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')
            else:
                data[k] = self.entries[k].get().strip()

        # Basic validation
        required_ok = all(
            data[k] for k in ['nip', 'company_name', 'address_p1', 'address_p2', 'alias']
        )
        if not required_ok:
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
