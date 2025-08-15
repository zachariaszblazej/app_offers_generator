"""
Browse WZ frame for viewing and managing WZ documents
"""
from tkinter import *
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
    """Frame for browsing and managing WZ documents"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.db = DatabaseService()
        self.wz_list = []
        self.sort_by = 'date'  # default sort by date
        self.sort_reverse = True  # newest first
        self.create_ui()
    
    def create_ui(self):
        """Create the WZ browsing UI"""
        # Set background color
        self.configure(bg='#f0f0f0')
        
        # Header frame
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=20)
        
        # Title
        title_label = Label(header_frame, 
                           text="Przeglądaj WZ",
                           font=("Arial", 20, "bold"),
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(side=LEFT)
        
        # Back button
        back_btn = Button(header_frame, 
                         text="Powrót do menu głównego",
                         font=("Arial", 12),
                         fg='black',
                         padx=15, pady=8,
                         command=self.return_to_main_menu,
                         cursor='hand2')
        back_btn.pack(side=RIGHT)
        
        # Content frame
        content_frame = Frame(self, bg='#f0f0f0')
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # WZ list frame
        list_frame = Frame(content_frame, bg='white', relief=RIDGE, bd=2)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # List header
        list_header = Label(list_frame, 
                           text="Lista WZ", 
                           font=("Arial", 14, "bold"), 
                           bg='white', fg='#333333')
        list_header.pack(pady=15)
        
        # Treeview frame
        tree_frame = Frame(list_frame, bg='white')
        tree_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Create Treeview for WZ list
        columns = ('filename', 'date', 'edit', 'load_to_creator', 'delete')
        self.wz_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Define column headings and widths
        self.wz_tree.heading('filename', text='Nazwa pliku', command=lambda: self.sort_by_column('filename'))
        self.wz_tree.heading('date', text='Data utworzenia', command=lambda: self.sort_by_column('date'))
        self.wz_tree.heading('edit', text='Edytuj')
        self.wz_tree.heading('load_to_creator', text='Wczytaj do kreatora')
        self.wz_tree.heading('delete', text='Usuń')
        
        # Set column widths
        self.wz_tree.column('filename', width=450, minwidth=350)
        self.wz_tree.column('date', width=170, minwidth=150)
        self.wz_tree.column('edit', minwidth=70, width=70, stretch=NO, anchor=CENTER)
        self.wz_tree.column('load_to_creator', minwidth=160, width=160, stretch=NO, anchor=CENTER)
        self.wz_tree.column('delete', minwidth=70, width=70, stretch=NO, anchor=CENTER)
        
        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.wz_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.wz_tree.xview)
        self.wz_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.wz_tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        
        # Bind single click for action buttons
        self.wz_tree.bind("<ButtonRelease-1>", self.on_single_click)
        # Bind double click to open WZ
        self.wz_tree.bind("<Double-1>", self.on_double_click)
        
        # Buttons frame (placed below the list)
        buttons_frame = Frame(content_frame, bg='#f0f0f0')
        buttons_frame.pack(fill=X, pady=10)
        
        # Refresh button
        refresh_btn = Button(buttons_frame,
                           text="🔄 Odśwież listę",
                           font=("Arial", 12),
                           fg='black',
                           padx=15, pady=8,
                           command=self.refresh_wz_list,
                           cursor='hand2')
        refresh_btn.pack(side=LEFT, padx=(0, 10))
        
        # Open folder button
        folder_btn = Button(buttons_frame, 
                           text="Otwórz folder",
                           font=("Arial", 12),
                           fg='black',
                           padx=15, pady=8,
                           command=self.open_wz_folder,
                           cursor='hand2')
        folder_btn.pack(side=LEFT, padx=(0, 10))
        
        # Load WZ list on creation
        self.refresh_wz_list()
    
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
        """Refresh the WZ list from database"""
        try:
            # Update column headers first
            self.update_column_headers()
            
            # Clear existing items
            for item in self.wz_tree.get_children():
                self.wz_tree.delete(item)
            
            # Clear wz_list
            self.wz_list = []
            
            # Get WZ list from database
            wz_data = self.db.get_all_wz()
            
            # Convert to file info list with proper paths
            wz_folder = get_wz_folder()
            file_info_list = []
            
            for wz in wz_data:
                # wz should be a tuple: (id, wz_number, date, client_name, status, file_path, ...)
                if len(wz) > 5 and wz[5]:  # Has file path
                    file_path = wz[5]
                    if os.path.exists(file_path):
                        # Get file stats
                        stat = os.stat(file_path)
                        filename = os.path.basename(file_path)
                        
                        file_info_list.append({
                            'filename': filename,
                            'filepath': file_path,
                            'mtime': stat.st_mtime,
                            'wz_data': wz
                        })
            
            # Sort based on selected criteria
            if self.sort_by == 'filename':
                file_info_list.sort(key=lambda x: x['filename'], reverse=self.sort_reverse)
            else:  # sort by date
                file_info_list.sort(key=lambda x: x['mtime'], reverse=self.sort_reverse)
            
            # Add sorted files to treeview
            for file_info in file_info_list:
                file_date = datetime.fromtimestamp(file_info['mtime']).strftime("%Y-%m-%d %H:%M")
                
                # Add to treeview
                self.wz_tree.insert('', 'end', values=(
                    file_info['filename'], 
                    file_date, 
                    "Edytuj", 
                    "Wczytaj do kreatora", 
                    "Usuń"
                ))
                self.wz_list.append(file_info['filepath'])
            
            print(f"Loaded {len(file_info_list)} WZ documents from database that exist in {wz_folder} (sorted by {self.sort_by}, {'desc' if self.sort_reverse else 'asc'})")
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować listy WZ: {e}")
            print(f"Error loading WZ list: {e}")
    
    def get_selected_wz_path(self):
        """Get the full path of the selected WZ"""
        selected = self.wz_tree.selection()
        if not selected:
            return None
        
        item = self.wz_tree.item(selected[0])
        filename = item['values'][0]
        return os.path.join(get_wz_folder(), filename)
    
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
                
                if column == edit_column_index:
                    # Edit WZ - navigate to WZ editor
                    wz_path = os.path.join(get_wz_folder(), filename)
                    self.wz_tree.selection_set(item)
                    self.nav_manager.show_frame('wz_editor', wz_path=wz_path)
                    
                elif column == load_column_index:
                    # Load to WZ creator
                    wz_path = os.path.join(get_wz_folder(), filename)
                    self.wz_tree.selection_set(item)
                    
                    # Load context from selected WZ
                    from src.data.database_service import get_wz_context_from_db
                    context_data = get_wz_context_from_db(wz_path)
                    
                    if not context_data:
                        # For older WZs without context, show warning
                        result = tkinter.messagebox.askyesno(
                            "Brak kontekstu", 
                            f"WZ-ka '{filename}' nie ma zapisanego kontekstu." +
                            "Czy chcesz przejść do kreatora WZ z niewypełnionymi polami?"
                        )
                        if result:
                            self.nav_manager.show_frame('wz_generator')
                        return

                    # Remove wz_number from context (it will be generated anew)
                    if 'wz_number' in context_data:
                        del context_data['wz_number']

                    # Pass context to WZ creator with source frame information
                    self.nav_manager.show_frame('wz_generator', template_context=context_data, source_frame='browse_wz')
                    
                elif column == delete_column_index:
                    # Delete WZ
                    result = tkinter.messagebox.askyesno(
                        "Potwierdzenie usunięcia", 
                        f"Czy na pewno chcesz usunąć WZ: {filename}? Tej operacji nie można cofnąć!"
                    )
                    if result:
                        self.delete_wz_by_filename(filename)
    
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
                # Get the item that was clicked
                item = self.wz_tree.identify_row(event.y)
                if item:
                    # Select the clicked item and open it
                    self.wz_tree.selection_set(item)
                    self.open_selected_wz()
    
    def delete_wz_by_filename(self, filename):
        """Delete WZ by filename"""
        try:
            wz_path = os.path.join(get_wz_folder(), filename)
            
            # Find WZ in database by file path
            wz_data = self.db.get_all_wz()
            wz_id = None
            for wz in wz_data:
                if len(wz) > 5 and wz[5] == wz_path:
                    wz_id = wz[0]  # ID is first element
                    break
            
            # Delete from database if found
            if wz_id:
                self.db.delete_wz(wz_id)
            
            # Delete file if it exists
            if os.path.exists(wz_path):
                os.remove(wz_path)
            
            # Refresh the list
            self.refresh_wz_list()
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się usunąć WZ: {e}")
    
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
        """Open the selected WZ document"""
        wz_path = self.get_selected_wz_path()
        if not wz_path:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz WZ do otwarcia!")
            return
        
        if os.path.exists(wz_path):
            try:
                # Open file with default application
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', wz_path])
                elif platform.system() == 'Windows':
                    os.startfile(wz_path)
                else:  # Linux
                    subprocess.call(['xdg-open', wz_path])
            except Exception as e:
                tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku: {e}")
        else:
            tkinter.messagebox.showerror("Błąd", "Plik WZ nie istnieje lub ścieżka jest nieprawidłowa.")
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame and refresh WZ list"""
        self.pack(fill=BOTH, expand=True)
        self.refresh_wz_list()
