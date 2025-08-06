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

from src.utils.config import get_offers_folder
from src.data.database_service import delete_offer_from_db, find_offer_by_filename


class BrowseOffersFrame(Frame):
    """Frame for browsing and managing generated offers"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offers_list = []
        self.sort_by = 'date'  # default sort by date
        self.sort_reverse = True  # newest first
        self.create_ui()
        self.load_offers()
    
    def create_ui(self):
        """Create the browse offers UI"""
        self.configure(bg='#f0f0f0')
        
        # Header
        header_frame = Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=X, padx=20, pady=20)
        
        # Title
        title_label = Label(header_frame, text="Przeglądaj oferty", 
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
        list_header = Label(list_frame, text="Lista zapytań ofertowych", 
                           font=("Arial", 14, "bold"), 
                           bg='white', fg='#333333')
        list_header.pack(pady=15)
        
        # Treeview for offers
        tree_frame = Frame(list_frame, bg='white')
        tree_frame.pack(fill=BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Create treeview
        columns = ('filename', 'date', 'edit', 'similar', 'delete')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.tree.heading('filename', text='Nazwa pliku', command=lambda: self.sort_by_column('filename'))
        self.tree.heading('date', text='Data utworzenia', command=lambda: self.sort_by_column('date'))
        self.tree.heading('edit', text='✏️')
        self.tree.heading('similar', text='📋')
        self.tree.heading('delete', text='❌')
        
        self.tree.column('filename', width=450, minwidth=350)
        self.tree.column('date', width=170, minwidth=150)
        self.tree.column('edit', minwidth=40, width=40, stretch=NO, anchor=CENTER)
        self.tree.column('similar', minwidth=40, width=40, stretch=NO, anchor=CENTER)
        self.tree.column('delete', minwidth=40, width=40, stretch=NO, anchor=CENTER)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        
        # Bind single click for delete functionality and context menu
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)
        # Bind double click to open in Word
        self.tree.bind("<Double-1>", self.on_double_click)
        
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
        
        # Open folder button
        folder_btn = Button(buttons_frame, text="📁 Otwórz folder",
                           font=("Arial", 12),
                           bg='#6c757d', fg='black',
                           padx=15, pady=8,
                           command=self.open_offers_folder,
                           cursor='hand2')
        folder_btn.pack(side=LEFT, padx=(0, 10))
    
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
        self.load_offers()
    
    def update_column_headers(self):
        """Update column headers to show current sort direction"""
        # Reset all headers
        self.tree.heading('filename', text='Nazwa pliku')
        self.tree.heading('date', text='Data utworzenia')
        
        # Add sort indicator to current sort column
        arrow = " ↓" if self.sort_reverse else " ↑"
        if self.sort_by == 'filename':
            self.tree.heading('filename', text=f'Nazwa pliku{arrow}')
        elif self.sort_by == 'date':
            self.tree.heading('date', text=f'Data utworzenia{arrow}')
    
    def load_offers(self):
        """Load offers from the output folder"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.offers_list = []
        
        # Get current offers folder from settings
        offers_folder = get_offers_folder()
        
        # Check if output folder exists
        if not os.path.exists(offers_folder):
            os.makedirs(offers_folder)
            return
        
        # Get all .docx files from output folder
        try:
            files = [f for f in os.listdir(offers_folder) if f.endswith('.docx')]
            
            # Create list of file info for sorting
            file_info_list = []
            for filename in files:
                filepath = os.path.join(offers_folder, filename)
                stat_info = os.stat(filepath)
                file_info_list.append({
                    'filename': filename,
                    'filepath': filepath,
                    'mtime': stat_info.st_mtime
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
                self.tree.insert('', 'end', values=(file_info['filename'], file_date, "✏️", "📋", "❌"))
                self.offers_list.append(file_info['filepath'])
            
            print(f"Loaded {len(files)} offers from {offers_folder} (sorted by {self.sort_by}, {'desc' if self.sort_reverse else 'asc'})")
            
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować listy ofert: {e}")
    
    def get_selected_offer_path(self):
        """Get the full path of the selected offer"""
        selected = self.tree.selection()
        if not selected:
            return None
        
        item = self.tree.item(selected[0])
        filename = item['values'][0]
        return os.path.join(get_offers_folder(), filename)
    
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
    
    def edit_selected_offer(self):
        """Edit the selected offer"""
        offer_path = self.get_selected_offer_path()
        if not offer_path:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz ofertę do edycji!")
            return
        
        # Navigate to offer editor with the selected file
        self.nav_manager.show_frame('offer_editor', offer_path=offer_path)
    
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
            offers_folder = get_offers_folder()
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', offers_folder])
            elif platform.system() == 'Windows':
                os.startfile(offers_folder)
            else:  # Linux
                subprocess.call(['xdg-open', offers_folder])
                
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć folderu: {e}")
    
    def create_similar_offer(self):
        """Create a new offer based on selected offer"""
        selected_item = self.tree.selection()
        if not selected_item:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw wybierz ofertę z listy!")
            return
            
        # Get selected offer info
        item_values = self.tree.item(selected_item[0])['values']
        if not item_values:
            return
            
        filename = item_values[0]
        offer_path = os.path.join(get_offers_folder(), filename)
        
        # Load context from selected offer
        from src.data.database_service import get_offer_context_from_db
        context_data = get_offer_context_from_db(offer_path)
        
        if not context_data:
            # For older offers without context, show warning
            result = tkinter.messagebox.askyesno(
                "Brak kontekstu", 
                f"Oferta '{filename}' nie ma zapisanego kontekstu.\\n\\n" +
                "Czy chcesz przejść do kreatora ofert z pustymi polami?"
            )
            if result:
                self.nav_manager.show_frame('offer_generator')
            return
        
        # Remove offer_number from context (it will be generated anew)
        if 'offer_number' in context_data:
            del context_data['offer_number']
        
        # Pass context to offer generator with source frame information
        self.nav_manager.show_frame('offer_generator', template_context=context_data, source_frame='browse_offers')
    
    def on_single_click(self, event):
        """Handle single-click on table to check for action column clicks"""
        # Get the region that was clicked
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.tree.identify_column(event.x)
            
            # Get the item that was clicked
            item = self.tree.identify_row(event.y)
            if item:
                # Get filename from the selected item
                item_values = self.tree.item(item)['values']
                filename = item_values[0]
                
                # Check which action column was clicked
                num_columns = len(self.tree['columns'])
                edit_column_index = f"#{num_columns - 2}"      # Third from last (✏️)
                similar_column_index = f"#{num_columns - 1}"   # Second from last (📋)
                delete_column_index = f"#{num_columns}"        # Last column (❌)
                
                if column == edit_column_index:
                    # Edit offer
                    offer_path = os.path.join(get_offers_folder(), filename)
                    self.tree.selection_set(item)
                    self.nav_manager.show_frame('offer_editor', offer_path=offer_path)
                    
                elif column == similar_column_index:
                    # Create similar offer
                    offer_path = os.path.join(get_offers_folder(), filename)
                    self.tree.selection_set(item)
                    
                    # Load context from selected offer
                    from src.data.database_service import get_offer_context_from_db
                    context_data = get_offer_context_from_db(offer_path)
                    
                    if not context_data:
                        # For older offers without context, show warning
                        result = tkinter.messagebox.askyesno(
                            "Brak kontekstu", 
                            f"Oferta '{filename}' nie ma zapisanego kontekstu.\\n\\n" +
                            "Czy chcesz przejść do kreatora ofert z pustymi polami?"
                        )
                        if result:
                            self.nav_manager.show_frame('offer_generator')
                        return
                    
                    # Remove offer_number from context (it will be generated anew)
                    if 'offer_number' in context_data:
                        del context_data['offer_number']
                    
                    # Pass context to offer generator with source frame information
                    self.nav_manager.show_frame('offer_generator', template_context=context_data, source_frame='browse_offers')
                    
                elif column == delete_column_index:
                    # Delete offer
                    result = tkinter.messagebox.askyesno(
                        "Potwierdzenie usunięcia", 
                        f"Czy na pewno chcesz usunąć ofertę:\\n{filename}\\n\\nTej operacji nie można cofnąć!"
                    )
                    if result:
                        # Get full path for deletion
                        offer_path = os.path.join(get_offers_folder(), filename)
                        
                        try:
                            # First, try to remove from database
                            db_success, db_message = delete_offer_from_db(offer_path)
                            
                            # Remove the file regardless of database operation result
                            os.remove(offer_path)
                            
                            # Show appropriate message
                            if db_success:
                                # Silent success - no messagebox, just refresh
                                pass
                            else:
                                tkinter.messagebox.showwarning("Częściowy sukces", 
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

    def on_double_click(self, event):
        """Handle double-click to open offer in Word"""
        # Get the region that was clicked
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            # Get the column that was clicked
            column = self.tree.identify_column(event.x)
            
            # Don't open if clicking on action columns (edit, similar, delete)
            num_columns = len(self.tree['columns'])
            edit_column_index = f"#{num_columns - 2}"      # Third from last (✏️)
            similar_column_index = f"#{num_columns - 1}"   # Second from last (📋)
            delete_column_index = f"#{num_columns}"        # Last column (❌)
            
            if column not in [edit_column_index, similar_column_index, delete_column_index]:
                # Get the item that was clicked
                item = self.tree.identify_row(event.y)
                if item:
                    # Select the clicked item and open it
                    self.tree.selection_set(item)
                    self.open_selected_offer()

    def return_to_main_menu(self):
        """Return to main menu"""
        self.nav_manager.show_frame('main_menu')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame and automatically refresh offers list"""
        self.pack(fill=BOTH, expand=True)
        # Automatically refresh offers list when frame is shown
        self.load_offers()
