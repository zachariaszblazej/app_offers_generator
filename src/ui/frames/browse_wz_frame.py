"""
Browse WZ frame for viewing and managing WZ documents
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.database_service import DatabaseService


class BrowseWzFrame(Frame):
    """Frame for browsing and managing WZ documents"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.db = DatabaseService()
        self.create_ui()
    
    def create_ui(self):
        """Create the WZ browsing UI"""
        # Set background color
        self.configure(bg='white')
        
        # Header frame
        header_frame = Frame(self, bg='white', height=60)
        header_frame.pack(fill=X, padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        # Back button
        back_btn = Button(header_frame, 
                         text="← Powrót do menu głównego",
                         font=("Arial", 12),
                         bg='#9E9E9E', fg='black',
                         padx=15, pady=5,
                         command=self.return_to_main_menu,
                         cursor='hand2')
        back_btn.pack(side=LEFT)
        
        # Title
        title_label = Label(header_frame, 
                           text="PRZEGLĄDAJ WZ",
                           font=("Arial", 20, "bold"),
                           bg='white', fg='#333333')
        title_label.pack(side=RIGHT, padx=20)
        
        # Content frame
        content_frame = Frame(self, bg='white')
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)
        
        # Buttons frame
        buttons_frame = Frame(content_frame, bg='white')
        buttons_frame.pack(fill=X, pady=(0, 10))
        
        # Refresh button
        refresh_btn = Button(buttons_frame,
                           text="Odśwież listę",
                           font=("Arial", 11),
                           bg='#4CAF50', fg='white',
                           padx=20, pady=8,
                           command=self.refresh_wz_list,
                           cursor='hand2')
        refresh_btn.pack(side=LEFT, padx=(0, 10))
        
        # Create new WZ button
        new_wz_btn = Button(buttons_frame,
                           text="Utwórz nowe WZ",
                           font=("Arial", 11),
                           bg='#2196F3', fg='white',
                           padx=20, pady=8,
                           command=self.create_new_wz,
                           cursor='hand2')
        new_wz_btn.pack(side=LEFT, padx=(0, 10))
        
        # WZ list frame with scrollbar
        list_frame = Frame(content_frame, bg='white')
        list_frame.pack(fill=BOTH, expand=True)
        
        # Create Treeview for WZ list
        columns = ('ID', 'Numer WZ', 'Data', 'Klient', 'Status', 'Ścieżka pliku')
        self.wz_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Define column headings and widths
        self.wz_tree.heading('ID', text='ID')
        self.wz_tree.heading('Numer WZ', text='Numer WZ')
        self.wz_tree.heading('Data', text='Data')
        self.wz_tree.heading('Klient', text='Klient')
        self.wz_tree.heading('Status', text='Status')
        self.wz_tree.heading('Ścieżka pliku', text='Ścieżka pliku')
        
        # Set column widths
        self.wz_tree.column('ID', width=50, minwidth=30)
        self.wz_tree.column('Numer WZ', width=150, minwidth=100)
        self.wz_tree.column('Data', width=100, minwidth=80)
        self.wz_tree.column('Klient', width=200, minwidth=150)
        self.wz_tree.column('Status', width=100, minwidth=80)
        self.wz_tree.column('Ścieżka pliku', width=300, minwidth=200)
        
        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.wz_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=HORIZONTAL, command=self.wz_tree.xview)
        self.wz_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.wz_tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        
        # Bind double-click event
        self.wz_tree.bind('<Double-1>', self.on_wz_double_click)
        
        # Context menu for right-click
        self.create_context_menu()
        self.wz_tree.bind('<Button-3>', self.show_context_menu)  # Right-click
        
        # Load WZ list on creation
        self.refresh_wz_list()
    
    def create_context_menu(self):
        """Create context menu for WZ operations"""
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Otwórz WZ", command=self.open_selected_wz)
        self.context_menu.add_command(label="Edytuj WZ", command=self.edit_selected_wz)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Usuń WZ", command=self.delete_selected_wz)
    
    def show_context_menu(self, event):
        """Show context menu at cursor position"""
        # Select the item under cursor
        item = self.wz_tree.identify_row(event.y)
        if item:
            self.wz_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def refresh_wz_list(self):
        """Refresh the WZ list from database"""
        try:
            # Clear existing items
            for item in self.wz_tree.get_children():
                self.wz_tree.delete(item)
            
            # Get WZ list from database
            wz_list = self.db.get_all_wz()
            
            # Populate treeview
            for wz in wz_list:
                # wz should be a tuple: (id, wz_number, date, client_name, status, file_path, ...)
                self.wz_tree.insert('', 'end', values=(
                    wz[0],  # ID
                    wz[1],  # WZ Number
                    wz[2],  # Date
                    wz[3] if len(wz) > 3 else 'N/A',  # Client name
                    wz[4] if len(wz) > 4 else 'Utworzone',  # Status
                    wz[5] if len(wz) > 5 else ''  # File path
                ))
            
            print(f"Loaded {len(wz_list)} WZ documents")
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować listy WZ: {e}")
            print(f"Error loading WZ list: {e}")
    
    def on_wz_double_click(self, event):
        """Handle double-click on WZ item"""
        self.open_selected_wz()
    
    def open_selected_wz(self):
        """Open the selected WZ document"""
        selection = self.wz_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Uwaga", "Proszę wybrać WZ z listy.")
            return
        
        item = self.wz_tree.item(selection[0])
        file_path = item['values'][5]  # File path column
        
        if file_path and os.path.exists(file_path):
            try:
                # Open file with default application
                import subprocess
                import platform
                
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', file_path])
                elif platform.system() == 'Windows':
                    os.startfile(file_path)
                else:  # Linux
                    subprocess.call(['xdg-open', file_path])
            except Exception as e:
                tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku: {e}")
        else:
            tkinter.messagebox.showerror("Błąd", "Plik WZ nie istnieje lub ścieżka jest nieprawidłowa.")
    
    def edit_selected_wz(self):
        """Edit the selected WZ document"""
        selection = self.wz_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Uwaga", "Proszę wybrać WZ z listy.")
            return
        
        item = self.wz_tree.item(selection[0])
        file_path = item['values'][5]  # File path column
        
        # Navigate to WZ editor with the selected file
        self.nav_manager.show_frame('wz_editor', wz_path=file_path)
    
    def delete_selected_wz(self):
        """Delete the selected WZ document"""
        selection = self.wz_tree.selection()
        if not selection:
            tkinter.messagebox.showwarning("Uwaga", "Proszę wybrać WZ z listy.")
            return
        
        item = self.wz_tree.item(selection[0])
        wz_id = item['values'][0]  # ID column
        wz_number = item['values'][1]  # WZ Number column
        file_path = item['values'][5]  # File path column
        
        # Confirm deletion
        if tkinter.messagebox.askyesno("Potwierdzenie", 
                                      f"Czy na pewno chcesz usunąć WZ {wz_number}?\n\n"
                                      "Ta operacja usunie zarówno rekord z bazy danych jak i plik z dysku."):
            try:
                # Delete from database
                self.db.delete_wz(wz_id)
                
                # Delete file if it exists
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                
                # Refresh the list
                self.refresh_wz_list()
                
                tkinter.messagebox.showinfo("Sukces", f"WZ {wz_number} zostało usunięte.")
                
            except Exception as e:
                tkinter.messagebox.showerror("Błąd", f"Nie udało się usunąć WZ: {e}")
    
    def create_new_wz(self):
        """Navigate to WZ creation screen"""
        self.nav_manager.show_frame('wz_creation')
    
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
