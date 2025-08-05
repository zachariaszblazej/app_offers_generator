"""
Browse offers frame for viewing and managing generated offers
"""
from tkinter import *
from tkinter import ttk
import tkinter.messagebox
import tkinter.filedialog
import os
import sys
import subprocess
import platform
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.config import OFFERS_FOLDER
from src.data.database_service import delete_offer_from_db, find_offer_by_filename


class BrowseOffersFrame(Frame):
    """Frame for browsing and managing generated offers"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offers_list = []
        self.create_ui()
        self.load_offers()
    
    def create_ui(self):
        """Create the browse offers UI"""
        self.configure(bg='#f0f0f0')
        
        # Header
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=20)
        
        # Title
        title_label = Label(header_frame, text="Przeglądaj wygenerowane oferty", 
                           font=("Arial", 20, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(side=LEFT)
        
        # Return button
        return_btn = Button(header_frame, text="Powrót do menu głównego",
                           font=("Arial", 12),
                           bg='#6c757d', fg='black',
                           padx=15, pady=8,
                           command=self.return_to_main_menu,
                           cursor='hand2')
        return_btn.pack(side=RIGHT)
        
        # Main content frame
        content_frame = Frame(self, bg='#f0f0f0')
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Offers list frame
        list_frame = Frame(content_frame, bg='white', relief=RIDGE, bd=2)
        list_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # List header
        list_header = Label(list_frame, text="Lista wygenerowanych ofert", 
                           font=("Arial", 14, "bold"), 
                           bg='white', fg='#333333')
        list_header.pack(pady=15)
        
        # Treeview for offers
        tree_frame = Frame(list_frame, bg='white')
        tree_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Create treeview
        columns = ('filename', 'date', 'size')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.tree.heading('filename', text='Nazwa pliku')
        self.tree.heading('date', text='Data utworzenia')
        self.tree.heading('size', text='Rozmiar')
        
        self.tree.column('filename', width=400, minwidth=300)
        self.tree.column('date', width=150, minwidth=100)
        self.tree.column('size', width=100, minwidth=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        
        # Buttons frame
        buttons_frame = Frame(content_frame, bg='#f0f0f0')
        buttons_frame.pack(fill=X, pady=10)
        
        # Refresh button
        refresh_btn = Button(buttons_frame, text="🔄 Odśwież listę",
                            font=("Arial", 12),
                            bg='#28a745', fg='black',
                            padx=15, pady=8,
                            command=self.load_offers,
                            cursor='hand2')
        refresh_btn.pack(side=LEFT, padx=(0, 10))
        
        # Open button
        open_btn = Button(buttons_frame, text="📄 Otwórz ofertę",
                         font=("Arial", 12),
                         bg='#17a2b8', fg='black',
                         padx=15, pady=8,
                         command=self.open_selected_offer,
                         cursor='hand2')
        open_btn.pack(side=LEFT, padx=(0, 10))
        
        # Delete button
        delete_btn = Button(buttons_frame, text="🗑️ Usuń ofertę",
                           font=("Arial", 12),
                           bg='#dc3545', fg='black',
                           padx=15, pady=8,
                           command=self.delete_selected_offer,
                           cursor='hand2')
        delete_btn.pack(side=LEFT, padx=(0, 10))
        
        # Open folder button
        folder_btn = Button(buttons_frame, text="📁 Otwórz folder",
                           font=("Arial", 12),
                           bg='#ffc107', fg='black',
                           padx=15, pady=8,
                           command=self.open_offers_folder,
                           cursor='hand2')
        folder_btn.pack(side=LEFT, padx=(0, 10))
    
    def load_offers(self):
        """Load offers from the output folder"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.offers_list = []
        
        # Check if output folder exists
        if not os.path.exists(OFFERS_FOLDER):
            os.makedirs(OFFERS_FOLDER)
            return
        
        # Get all .docx files from output folder
        try:
            files = [f for f in os.listdir(OFFERS_FOLDER) if f.endswith('.docx')]
            files.sort(reverse=True)  # Sort by name (newest first due to timestamp)
            
            for filename in files:
                filepath = os.path.join(OFFERS_FOLDER, filename)
                
                # Get file stats
                stat_info = os.stat(filepath)
                file_size = self.format_file_size(stat_info.st_size)
                file_date = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                # Add to treeview
                self.tree.insert('', 'end', values=(filename, file_date, file_size))
                self.offers_list.append(filepath)
            
            print(f"Loaded {len(files)} offers from {OFFERS_FOLDER}")
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować listy ofert: {e}")
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        else:
            return f"{size_bytes/(1024**2):.1f} MB"
    
    def get_selected_offer_path(self):
        """Get the full path of the selected offer"""
        selected = self.tree.selection()
        if not selected:
            return None
        
        item = self.tree.item(selected[0])
        filename = item['values'][0]
        return os.path.join(OFFERS_FOLDER, filename)
    
    def open_selected_offer(self):
        """Open the selected offer in default application"""
        offer_path = self.get_selected_offer_path()
        if not offer_path:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz ofertę do otwarcia!")
            return
        
        try:
            # Open file with default application
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', offer_path])
            elif platform.system() == 'Windows':
                os.startfile(offer_path)
            else:  # Linux
                subprocess.call(['xdg-open', offer_path])
                
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku: {e}")
    
    def delete_selected_offer(self):
        """Delete the selected offer"""
        offer_path = self.get_selected_offer_path()
        if not offer_path:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz ofertę do usunięcia!")
            return
        
        filename = os.path.basename(offer_path)
        
        # Confirm deletion
        result = tkinter.messagebox.askyesno(
            "Potwierdzenie usunięcia", 
            f"Czy na pewno chcesz usunąć ofertę:\\n{filename}\\n\\nTej operacji nie można cofnąć!"
        )
        
        if result:
            try:
                # First, try to remove from database
                db_success, db_message = delete_offer_from_db(offer_path)
                
                # Remove the file regardless of database operation result
                os.remove(offer_path)
                
                # Show appropriate message
                if db_success:
                    tkinter.messagebox.showinfo("Sukces", 
                        f"Oferta {filename} została usunięta z plików i bazy danych!")
                else:
                    tkinter.messagebox.showinfo("Częściowy sukces", 
                        f"Plik {filename} został usunięty, ale wystąpił problem z bazą danych:\\n{db_message}")
                
                self.load_offers()  # Refresh the list
                
            except Exception as e:
                # If file deletion fails, try to check if it was in database and show appropriate error
                offer_in_db = find_offer_by_filename(filename)
                if offer_in_db:
                    tkinter.messagebox.showerror("Błąd", 
                        f"Nie udało się usunąć pliku: {e}\\n\\nOferta nadal istnieje w bazie danych.")
                else:
                    tkinter.messagebox.showerror("Błąd", f"Nie udało się usunąć pliku: {e}")
    
    def open_offers_folder(self):
        """Open the offers folder in file explorer"""
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', OFFERS_FOLDER])
            elif platform.system() == 'Windows':
                os.startfile(OFFERS_FOLDER)
            else:  # Linux
                subprocess.call(['xdg-open', OFFERS_FOLDER])
                
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć folderu: {e}")
    
    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
