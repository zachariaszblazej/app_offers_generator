"""Browse WZ frame with year-folder navigation (mirrors offers implementation)."""
from tkinter import *  # noqa: F401,F403
from tkinter import ttk
import tkinter.messagebox
import sys
import os
import subprocess
import platform
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import DatabaseService
from src.utils.config import get_wz_folder


class BrowseWzFrame(Frame):
    """Browse and manage WZ documents with year navigation."""

    def __init__(self, parent, nav_manager):
     super().__init__(parent)
     self.nav_manager = nav_manager
     self.db = DatabaseService()
     self.wz_list: list[str] = []  # list of full paths (files only)
     self.item_path: dict[str, str] = {}  # tree item id -> full path
     self.current_year_folder: str | None = None
     self.sort_by = 'date'
     self.sort_reverse = True
     self._build_ui()
     self.refresh_wz_list()

    def _build_ui(self):
     self.configure(bg='#f0f0f0')
     header = Frame(self, bg='#f0f0f0')
     header.pack(fill=X, padx=20, pady=20)
     self.back_btn = Button(header, text='Powrót do menu głównego', font=('Arial', 12), fg='black', padx=15, pady=8,
                   command=self.return_to_main_menu, cursor='hand2')
     self.back_btn.pack(side=LEFT)
     self.up_btn = Button(header, text='⬆ Foldery z latami', font=('Arial', 12), fg='black', padx=15, pady=8,
                 command=self.navigate_up, cursor='hand2')
     self.up_btn.pack(side=LEFT, padx=(10, 0))
     self.up_btn.forget()

     content = Frame(self, bg='#f0f0f0')
     content.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
     list_frame = Frame(content, bg='white', relief=RIDGE, bd=2)
     list_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
     Label(list_frame, text='Lista WZ', font=('Arial', 14, 'bold'), bg='white', fg='#333333').pack(pady=15)

     tree_wrap = Frame(list_frame, bg='white')
     tree_wrap.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
     cols = ('filename', 'date', 'edit', 'load_to_creator', 'delete')
     self.wz_tree = ttk.Treeview(tree_wrap, columns=cols, show='headings', height=15)
     self.wz_tree.heading('filename', text='Nazwa pliku', command=lambda: self.sort_by_column('filename'))
     self.wz_tree.heading('date', text='Data utworzenia', command=lambda: self.sort_by_column('date'))
     self.wz_tree.heading('edit', text='Edytuj')
     self.wz_tree.heading('load_to_creator', text='Wczytaj do kreatora')
     self.wz_tree.heading('delete', text='Usuń')
     self.wz_tree.column('filename', width=450, minwidth=350)
     self.wz_tree.column('date', width=170, minwidth=150)
     self.wz_tree.column('edit', width=70, stretch=NO, anchor=CENTER)
     self.wz_tree.column('load_to_creator', width=160, stretch=NO, anchor=CENTER)
     self.wz_tree.column('delete', width=70, stretch=NO, anchor=CENTER)
     vs = ttk.Scrollbar(tree_wrap, orient=VERTICAL, command=self.wz_tree.yview)
     hs = ttk.Scrollbar(tree_wrap, orient=HORIZONTAL, command=self.wz_tree.xview)
     self.wz_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
     self.wz_tree.pack(side=LEFT, fill=BOTH, expand=True)
     vs.pack(side=RIGHT, fill=Y)
     hs.pack(side=BOTTOM, fill=X)
     self.wz_tree.bind('<ButtonRelease-1>', self.on_single_click)
     self.wz_tree.bind('<Double-1>', self.on_double_click)

     buttons = Frame(content, bg='#f0f0f0')
     buttons.pack(fill=X, pady=10)
     Button(buttons, text='🔄 Odśwież listę', font=('Arial', 12), fg='black', padx=15, pady=8,
         command=self.refresh_wz_list, cursor='hand2').pack(side=LEFT, padx=(0, 10))
     Button(buttons, text='Otwórz folder', font=('Arial', 12), fg='black', padx=15, pady=8,
         command=self.open_wz_folder, cursor='hand2').pack(side=LEFT, padx=(0, 10))
    
    def sort_by_column(self, column):
        """Sort by clicking on column header"""
        if self.sort_by == column:
            # If already sorting by this column, toggle order
            self.sort_reverse = not self.sort_reverse
        else:
            # New column, start with descending
            self.sort_by = column
            self.sort_reverse = True
        
        # Update column headers and reload
        self.update_column_headers()
        self.refresh_wz_list()
    
    def update_column_headers(self):
        """Update column headers to show current sort direction"""
        # Reset all headers
        self.wz_tree.heading('filename', text='Nazwa pliku')
        self.wz_tree.heading('date', text='Data utworzenia')
        
        # Add sort indicator to current sort column
        arrow = " ↓" if self.sort_reverse else " ↑"
        if self.sort_by == 'filename':
            self.wz_tree.heading('filename', text=f'Nazwa pliku{arrow}')
        else:  # sort by date
            self.wz_tree.heading('date', text=f'Data utworzenia{arrow}')
    
    def refresh_wz_list(self):
        """Refresh list; show year folders at root, filter by selected year."""
        try:
            self.update_column_headers()
            for item in self.wz_tree.get_children():
                self.wz_tree.delete(item)
            self.wz_list.clear()
            self.item_path.clear()

            wz_root = get_wz_folder()
            if not os.path.isdir(wz_root):
                return

            wz_data = self.db.get_all_wz()
            file_infos = []
            for wz in wz_data:
                if len(wz) > 5 and wz[5]:
                    file_path = wz[5]
                    if os.path.exists(file_path) and file_path.endswith('.docx'):
                        try:
                            stat = os.stat(file_path)
                            filename = os.path.basename(file_path)
                            # Determine top-level year folder (immediate after wz_root)
                            rel = os.path.relpath(file_path, wz_root)
                            parts = rel.split(os.sep)
                            year = parts[0] if len(parts) > 1 and parts[0].isdigit() and len(parts[0]) == 4 else None
                            file_infos.append({'filename': filename, 'filepath': file_path, 'mtime': stat.st_mtime, 'year': year})
                        except OSError:
                            pass

            # Year folder rows (only at root view)
            if self.current_year_folder is None:
                years = sorted({fi['year'] for fi in file_infos if fi['year']}, reverse=True)
                for y in years:
                    self.wz_tree.insert('', 'end', values=(f'📁 {y}', '', '', '', ''))

            # Filter by current year
            if self.current_year_folder is None:
                visible_files = [fi for fi in file_infos if fi['year'] is None]
            else:
                visible_files = [fi for fi in file_infos if fi['year'] == self.current_year_folder]

            # Sort
            if self.sort_by == 'filename':
                visible_files.sort(key=lambda x: x['filename'], reverse=self.sort_reverse)
            else:
                visible_files.sort(key=lambda x: x['mtime'], reverse=self.sort_reverse)

            for fi in visible_files:
                date_str = datetime.fromtimestamp(fi['mtime']).strftime('%Y-%m-%d %H:%M')
                iid = self.wz_tree.insert('', 'end', values=(fi['filename'], date_str, 'Edytuj', 'Wczytaj do kreatora', 'Usuń'))
                self.item_path[iid] = fi['filepath']
                self.wz_list.append(fi['filepath'])
        except Exception as e:  # noqa: BLE001
            tkinter.messagebox.showerror('Błąd', f'Nie udało się załadować listy WZ: {e}')
            print(f'Error loading WZ list: {e}')
    
    def get_selected_wz_path(self):
        sel = self.wz_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        vals = self.wz_tree.item(iid)['values']
        if not vals:
            return None
        filename = vals[0]
        if isinstance(filename, str) and filename.startswith('📁 '):
            return None
        return self.item_path.get(iid)
    
    def on_single_click(self, event):
        """Handle single-click on table to check for action column clicks"""
        # Get the region that was clicked
        region = self.wz_tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.wz_tree.identify_column(event.x)
            
            # Get the item that was clicked
            item = self.wz_tree.identify_row(event.y)
            if item:
                # Get filename from the selected item
                item_values = self.wz_tree.item(item)['values']
                filename = item_values[0]
                
                # Check which action column was clicked
                num_columns = len(self.wz_tree['columns'])
                edit_column_index = f"#{num_columns - 2}"      # Third from last (Edytuj)
                load_column_index = f"#{num_columns - 1}"      # Second from last (Wczytaj do kreatora)
                delete_column_index = f"#{num_columns}"        # Last column (Usuń)
                
                # Folder navigation moved to double-click only

                path = self.get_selected_wz_path()
                if not path:
                    return

                if column == edit_column_index:
                    self.wz_tree.selection_set(item)
                    self.nav_manager.show_frame('wz_editor', wz_path=path)
                elif column == load_column_index:
                    self.wz_tree.selection_set(item)
                    from src.data.database_service import get_wz_context_from_db
                    context_data = get_wz_context_from_db(path)
                    if not context_data:
                        if tkinter.messagebox.askyesno('Brak kontekstu', f"WZ-ka '{filename}' nie ma zapisanego kontekstu.\n\nCzy przejść do kreatora WZ z pustymi polami?"):
                            self.nav_manager.show_frame('wz_generator')
                        return
                    context_data.pop('wz_number', None)
                    self.nav_manager.show_frame('wz_generator', template_context=context_data, source_frame='browse_wz')
                elif column == delete_column_index:
                    if tkinter.messagebox.askyesno('Potwierdzenie usunięcia', f"Czy na pewno chcesz usunąć WZ: {filename}? Tej operacji nie można cofnąć!"):
                        self.delete_wz_by_path(path)
    
    def on_double_click(self, event):
        """Handle double-click to open WZ"""
        # Get the region that was clicked
        region = self.wz_tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.wz_tree.identify_column(event.x)
            
            # Don't open if clicking on action columns
            num_columns = len(self.wz_tree['columns'])
            edit_column_index = f"#{num_columns - 2}"      # Third from last (Edytuj)
            load_column_index = f"#{num_columns - 1}"      # Second from last (Wczytaj do kreatora)
            delete_column_index = f"#{num_columns}"        # Last column (Usuń)
            
            if column not in [edit_column_index, load_column_index, delete_column_index]:
                item = self.wz_tree.identify_row(event.y)
                if item:
                    vals = self.wz_tree.item(item)['values']
                    if vals and isinstance(vals[0], str) and vals[0].startswith('📁 '):
                        # treat double click on folder same as single select
                        year = vals[0].replace('📁', '').strip()
                        self.current_year_folder = year
                        if not self.up_btn.winfo_ismapped():
                            self.up_btn.pack(side=LEFT, padx=(10, 0))
                        self.refresh_wz_list()
                        return
                    self.wz_tree.selection_set(item)
                    self.open_selected_wz()
    
    def delete_wz_by_path(self, wz_path: str):
        try:
            # Delete using unique file path to avoid removing same order numbers in other years
            self.db.delete_wz_by_file_path(wz_path)
            if os.path.exists(wz_path):
                try:
                    os.remove(wz_path)
                except OSError as fe:
                    print(f"Ostrzeżenie: nie udało się usunąć pliku z dysku: {fe}")
            self.refresh_wz_list()
        except Exception as e:  # noqa: BLE001
            tkinter.messagebox.showerror('Błąd', f'Nie udało się usunąć WZ: {e}')
    
    def open_wz_folder(self):
        """Open the WZ folder in file explorer"""
        try:
            wz_folder = get_wz_folder()
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', wz_folder])
            elif platform.system() == 'Windows':
                os.startfile(wz_folder)
            else:  # Linux
                subprocess.call(['xdg-open', wz_folder])
                
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć folderu: {e}")
    
    def open_selected_wz(self):
        wz_path = self.get_selected_wz_path()
        if not wz_path:
            tkinter.messagebox.showwarning('Uwaga', 'Najpierw zaznacz WZ do otwarcia!')
            return
        if os.path.exists(wz_path):
            try:
                if platform.system() == 'Darwin':
                    subprocess.call(['open', wz_path])
                elif platform.system() == 'Windows':
                    os.startfile(wz_path)  # type: ignore[attr-defined]
                else:
                    subprocess.call(['xdg-open', wz_path])
            except Exception as e:  # noqa: BLE001
                tkinter.messagebox.showerror('Błąd', f'Nie udało się otworzyć pliku: {e}')
        else:
            tkinter.messagebox.showerror('Błąd', 'Plik WZ nie istnieje lub ścieżka jest nieprawidłowa.')
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        self.pack(fill=BOTH, expand=True)
        self.current_year_folder = None
        if self.up_btn.winfo_ismapped():
            self.up_btn.forget()
        self.refresh_wz_list()

    def navigate_up(self):
        if self.current_year_folder is not None:
            self.current_year_folder = None
            if self.up_btn.winfo_ismapped():
                self.up_btn.forget()
            self.refresh_wz_list()
