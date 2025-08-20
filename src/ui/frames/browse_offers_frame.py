"""Browse offers frame (clean implementation with year-folder navigation)."""
from tkinter import *  # noqa: F401,F403
from tkinter import ttk
import tkinter.messagebox
import os
import sys
import subprocess
import platform
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.config import get_offers_folder
from src.data.database_service import delete_offer_from_db, find_offer_by_filename


class BrowseOffersFrame(Frame):
    """Browse and manage generated offers; supports year subfolders."""

    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offers_list: list[str] = []
        self.current_year_folder: str | None = None
        self.sort_by = 'date'
        self.sort_reverse = True
        self._build_ui()
        self.load_offers()

    # UI --------------------------------------------------------------
    def _build_ui(self):
        self.configure(bg='#f0f0f0')
        header = Frame(self, bg='#f0f0f0')
        header.pack(fill=X, padx=20, pady=20)
        self.title_label = Label(header, text='Przeglądaj oferty', font=('Arial', 20, 'bold'), bg='#f0f0f0', fg='#333')
        self.title_label.pack(side=LEFT)
        Button(header, text='Powrót do menu głównego', font=('Arial', 12), fg='black', padx=15, pady=8,
               command=self.return_to_main_menu, cursor='hand2').pack(side=RIGHT)

        content = Frame(self, bg='#f0f0f0')
        content.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        list_frame = Frame(content, bg='white', relief=RIDGE, bd=2)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        Label(list_frame, text='Lista zapytań ofertowych', font=('Arial', 14, 'bold'), bg='white', fg='#333').pack(pady=15)

        tree_wrap = Frame(list_frame, bg='white')
        tree_wrap.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        cols = ('filename', 'date', 'edit', 'similar', 'delete')
        self.tree = ttk.Treeview(tree_wrap, columns=cols, show='headings', height=15)
        self.tree.heading('filename', text='Nazwa pliku', command=lambda: self.sort_by_column('filename'))
        self.tree.heading('date', text='Data utworzenia', command=lambda: self.sort_by_column('date'))
        self.tree.heading('edit', text='Edytuj')
        self.tree.heading('similar', text='Wczytaj do kreatora')
        self.tree.heading('delete', text='Usuń')
        self.tree.column('filename', width=450, minwidth=350)
        self.tree.column('date', width=170, minwidth=150)
        self.tree.column('edit', width=70, stretch=NO, anchor=CENTER)
        self.tree.column('similar', width=160, stretch=NO, anchor=CENTER)
        self.tree.column('delete', width=70, stretch=NO, anchor=CENTER)
        vs = ttk.Scrollbar(tree_wrap, orient=VERTICAL, command=self.tree.yview)
        hs = ttk.Scrollbar(tree_wrap, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vs.pack(side=RIGHT, fill=Y)
        hs.pack(side=BOTTOM, fill=X)
        self.tree.bind('<ButtonRelease-1>', self.on_single_click)
        self.tree.bind('<Double-1>', self.on_double_click)

        buttons = Frame(content, bg='#f0f0f0')
        buttons.pack(fill=X, pady=10)
        self.up_btn = Button(buttons, text='⬆ Rok', font=('Arial', 12), fg='black', padx=15, pady=8,
                              command=self.navigate_up, cursor='hand2')
        self.up_btn.pack(side=LEFT, padx=(0, 10))
        self.up_btn.forget()
        Button(buttons, text='🔄 Odśwież listę', font=('Arial', 12), fg='black', padx=15, pady=8,
               command=self.load_offers, cursor='hand2').pack(side=LEFT, padx=(0, 10))
        Button(buttons, text='Otwórz folder', font=('Arial', 12), fg='black', padx=15, pady=8,
               command=self.open_offers_folder, cursor='hand2').pack(side=LEFT, padx=(0, 10))

    # Sorting ----------------------------------------------------------
    def sort_by_column(self, column: str):
        if self.sort_by == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_by = column
            self.sort_reverse = True
        self.update_column_headers()
        self.load_offers()

    def update_column_headers(self):
        self.tree.heading('filename', text='Nazwa pliku')
        self.tree.heading('date', text='Data utworzenia')
        arrow = ' ↓' if self.sort_reverse else ' ↑'
        if self.sort_by == 'filename':
            self.tree.heading('filename', text=f'Nazwa pliku{arrow}')
        elif self.sort_by == 'date':
            self.tree.heading('date', text=f'Data utworzenia{arrow}')

    # Data loading -----------------------------------------------------
    def load_offers(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.offers_list.clear()

        offers_root = get_offers_folder()
        if not os.path.exists(offers_root):
            os.makedirs(offers_root)
            return

        from src.data.database_service import get_all_offer_file_paths

        if self.current_year_folder is None:
            try:
                years = [d for d in os.listdir(offers_root)
                         if os.path.isdir(os.path.join(offers_root, d)) and d.isdigit() and len(d) == 4]
                years.sort(reverse=True)
                for y in years:
                    self.tree.insert('', 'end', values=(f'📁 {y}', '', '', '', ''))
            except Exception as e:  # noqa: BLE001
                print(f'Year folder listing error: {e}')

        try:
            db_paths = get_all_offer_file_paths()
            scope = offers_root if self.current_year_folder is None else os.path.join(offers_root, self.current_year_folder)
            if not os.path.isdir(scope):
                return
            file_infos = []
            for p in db_paths:
                name = os.path.basename(p)
                if self.current_year_folder is None:
                    candidate = os.path.join(offers_root, name)
                    if not os.path.exists(candidate):
                        continue  # skip year-scoped entries
                    full = candidate
                else:
                    full = os.path.join(offers_root, self.current_year_folder, name)
                    if not os.path.exists(full):
                        continue
                if name.endswith('.docx') and os.path.isfile(full):
                    st = os.stat(full)
                    file_infos.append({'filename': name, 'filepath': full, 'mtime': st.st_mtime})
            if self.sort_by == 'filename':
                file_infos.sort(key=lambda x: x['filename'], reverse=self.sort_reverse)
            else:
                file_infos.sort(key=lambda x: x['mtime'], reverse=self.sort_reverse)
            for info in file_infos:
                date_str = datetime.fromtimestamp(info['mtime']).strftime('%Y-%m-%d %H:%M')
                self.tree.insert('', 'end', values=(info['filename'], date_str, 'Edytuj', 'Wczytaj do kreatora', 'Usuń'))
                self.offers_list.append(info['filepath'])
        except Exception as e:  # noqa: BLE001
            tkinter.messagebox.showerror('Błąd', f'Nie udało się załadować listy ofert: {e}')
            print(f'Error loading offers: {e}')

    # Helpers ----------------------------------------------------------
    def _build_offer_path(self, filename: str) -> str:
        base = get_offers_folder()
        if self.current_year_folder:
            return os.path.join(base, self.current_year_folder, filename)
        return os.path.join(base, filename)

    def get_selected_offer_path(self):
        sel = self.tree.selection()
        if not sel:
            return None
        filename = self.tree.item(sel[0])['values'][0]
        if isinstance(filename, str) and filename.startswith('📁 '):
            return None
        return self._build_offer_path(filename)

    # Actions ----------------------------------------------------------
    def open_selected_offer(self):
        path = self.get_selected_offer_path()
        if not path:
            tkinter.messagebox.showwarning('Uwaga', 'Najpierw zaznacz ofertę do otwarcia!')
            return
        try:
            if platform.system() == 'Darwin':
                subprocess.call(['open', path])
            elif platform.system() == 'Windows':
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.call(['xdg-open', path])
        except Exception as e:  # noqa: BLE001
            tkinter.messagebox.showerror('Błąd', f'Nie udało się otworzyć pliku: {e}')

    def edit_selected_offer(self):
        path = self.get_selected_offer_path()
        if not path:
            tkinter.messagebox.showwarning('Uwaga', 'Najpierw zaznacz ofertę do edycji!')
            return
        self.nav_manager.show_frame('offer_editor', offer_path=path)

    def delete_selected_offer(self):
        path = self.get_selected_offer_path()
        if not path:
            tkinter.messagebox.showwarning('Uwaga', 'Najpierw zaznacz ofertę do usunięcia!')
            return
        filename = os.path.basename(path)
        if not tkinter.messagebox.askyesno('Potwierdzenie usunięcia', f'Czy na pewno chcesz usunąć ofertę:\n{filename}\n\nTej operacji nie można cofnąć!'):
            return
        try:
            db_success, db_message = delete_offer_from_db(path)
            os.remove(path)
            if not db_success:
                tkinter.messagebox.showwarning('Częściowy sukces', f'Plik {filename} usunięty, problem z bazą:\n{db_message}')
            self.load_offers()
        except Exception as e:  # noqa: BLE001
            exists = find_offer_by_filename(filename)
            if exists:
                tkinter.messagebox.showerror('Błąd', f'Nie udało się usunąć pliku: {e}\nOferta nadal w bazie danych.')
            else:
                tkinter.messagebox.showerror('Błąd', f'Nie udało się usunąć pliku: {e}')

    def open_offers_folder(self):
        try:
            folder = get_offers_folder()
            if platform.system() == 'Darwin':
                subprocess.call(['open', folder])
            elif platform.system() == 'Windows':
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                subprocess.call(['xdg-open', folder])
        except Exception as e:  # noqa: BLE001
            tkinter.messagebox.showerror('Błąd', f'Nie udało się otworzyć folderu: {e}')

    def create_similar_offer(self):
        sel = self.tree.selection()
        if not sel:
            tkinter.messagebox.showwarning('Uwaga', 'Najpierw wybierz ofertę z listy!')
            return
        filename = self.tree.item(sel[0])['values'][0]
        path = self._build_offer_path(filename)
        from src.data.database_service import get_offer_context_from_db
        ctx = get_offer_context_from_db(path)
        if not ctx:
            if tkinter.messagebox.askyesno('Brak kontekstu', f"Oferta '{filename}' nie ma zapisanego kontekstu.\n\nCzy przejść do kreatora z pustymi polami?"):
                self.nav_manager.show_frame('offer_generator')
            return
        ctx.pop('offer_number', None)
        self.nav_manager.show_frame('offer_generator', template_context=ctx, source_frame='browse_offers')

    # Event handlers ---------------------------------------------------
    def on_single_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item:
            return
        vals = self.tree.item(item)['values']
        if not vals:
            return
        filename = vals[0]
        if isinstance(filename, str) and filename.startswith('📁 '):
            year = filename.replace('📁', '').strip()
            self.current_year_folder = year
            self.title_label.config(text=f'Przeglądaj oferty – {year}')
            self.up_btn.pack(side=LEFT, padx=(0, 10))
            self.load_offers()
            return
        n = len(self.tree['columns'])
        edit_idx = f'#{n - 2}'
        sim_idx = f'#{n - 1}'
        del_idx = f'#{n}'
        if col == edit_idx:
            self.tree.selection_set(item)
            self.edit_selected_offer()
        elif col == sim_idx:
            self.tree.selection_set(item)
            self.create_similar_offer()
        elif col == del_idx:
            self.tree.selection_set(item)
            self.delete_selected_offer()

    def on_double_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        col = self.tree.identify_column(event.x)
        n = len(self.tree['columns'])
        if col in {f'#{n - 2}', f'#{n - 1}', f'#{n}'}:
            return
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.open_selected_offer()

    # Navigation -------------------------------------------------------
    def return_to_main_menu(self):
        self.nav_manager.show_frame('main_menu')

    def hide(self):
        self.pack_forget()

    def show(self):
        self.pack(fill=BOTH, expand=True)
        self.current_year_folder = None
        self.title_label.config(text='Przeglądaj oferty')
        if self.up_btn.winfo_ismapped():
            self.up_btn.forget()
        self.load_offers()

    def navigate_up(self):
        if self.current_year_folder is not None:
            self.current_year_folder = None
            self.title_label.config(text='Przeglądaj oferty')
            if self.up_btn.winfo_ismapped():
                self.up_btn.forget()
            self.load_offers()
