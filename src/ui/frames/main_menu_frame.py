"""
Main menu frame for navigation
"""
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.config import APP_VERSION
from src.data.database_service import is_database_available
from src.data.database_service import is_database_available
from src.utils.config import get_offers_folder, get_wz_folder


class MainMenuFrame(Frame):
    """Main menu frame with navigation options"""
    
    def __init__(self, parent, nav_manager):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.create_ui()
    
    def create_ui(self):
        """Create the main menu UI"""
        # Set background color to match the application theme
        self.configure(bg='#f0f0f0')

        # Main title
        title_label = Label(
            self,
            text="Ultra Pro 2137 Kreator dokumentów Hantech",
            font=("Arial", 24, "bold"),
            bg='#f0f0f0',
            fg='#333333',
        )
        title_label.pack(pady=50)

        # Main menu buttons frame
        buttons_frame = Frame(self, bg='#f0f0f0')
        buttons_frame.pack(pady=50)

        # Create new offer button
        new_offer_btn = Button(
            buttons_frame,
            text="Stwórz nową ofertę",
            font=("Arial", 16, "bold"),
            fg='black',
            padx=30,
            pady=15,
            command=self.open_new_offer,
            cursor='hand2',
        )
        new_offer_btn.pack(pady=15)

        # View offers button
        view_offers_btn = Button(
            buttons_frame,
            text="Przeglądaj oferty",
            font=("Arial", 14),
            fg='black',
            padx=30,
            pady=10,
            command=self.view_offers,
            cursor='hand2',
        )
        view_offers_btn.pack(pady=10)

        # Create new WZ button
        new_wz_btn = Button(
            buttons_frame,
            text="Stwórz WZkę",
            font=("Arial", 16, "bold"),
            fg='black',
            padx=30,
            pady=15,
            command=self.open_new_wz,
            cursor='hand2',
        )
        new_wz_btn.pack(pady=15)

        # View WZ button
        view_wz_btn = Button(
            buttons_frame,
            text="Przeglądaj WZki",
            font=("Arial", 14),
            fg='black',
            padx=30,
            pady=10,
            command=self.view_wz,
            cursor='hand2',
        )
        view_wz_btn.pack(pady=10)

        # Browse clients button (now includes adding new clients)
        browse_clients_btn = Button(
            buttons_frame,
            text="Zarządzaj klientami",
            font=("Arial", 14),
            fg='black',
            padx=30,
            pady=10,
            command=self.browse_clients,
            cursor='hand2',
        )
        browse_clients_btn.pack(pady=10)

        # Browse suppliers button (now includes adding new suppliers)
        browse_suppliers_btn = Button(
            buttons_frame,
            text="Zarządzaj dostawcami",
            font=("Arial", 14),
            fg='black',
            padx=30,
            pady=10,
            command=self.browse_suppliers,
            cursor='hand2',
        )
        browse_suppliers_btn.pack(pady=10)

        # Restore documents button
        restore_docs_btn = Button(
            buttons_frame,
            text="Przywróć dokumenty",
            font=("Arial", 14),
            fg='black',
            padx=30,
            pady=10,
            command=self.open_restore_documents,
            cursor='hand2',
        )
        restore_docs_btn.pack(pady=10)

        # Settings button
        settings_btn = Button(
            self,
            text="Ustawienia",
            font=("Arial", 14),
            fg='black',
            padx=20,
            pady=10,
            command=lambda: self.nav_manager.show_frame('settings'),
            cursor='hand2',
        )
        settings_btn.pack(pady=10)

        # About button
        about_btn = Button(
            self,
            text="O programie",
            font=("Arial", 14),
            fg='black',
            padx=20,
            pady=10,
            command=self.show_about,
            cursor='hand2',
        )
        about_btn.pack(pady=10)

        # Exit button
        exit_btn = Button(
            self,
            text="Zamknij aplikację",
            font=("Arial", 12),
            fg='black',
            padx=20,
            pady=8,
            command=self.exit_application,
            cursor='hand2',
        )
        exit_btn.pack(pady=(30, 10))

    def show_about(self):
        """Show about dialog with version information"""
        import tkinter.messagebox
        try:
            from src.utils.version import get_full_version_info
            version_info = get_full_version_info()
            tkinter.messagebox.showinfo(
                "O programie", 
                f"Kreator Dokumentów Hantech\n\n{version_info}"
            )
        except ImportError:
            tkinter.messagebox.showinfo(
                "O programie", 
                "Kreator Dokumentów Hantech\n\n© 2025 HANTECH Grzegorz Cieśla"
            )
    
    def open_new_offer(self):
        """Navigate to offer creation screen"""
        if not self._require_database_ready():
            return
        if not self._require_offers_folder_ready():
            return
        self.nav_manager.show_frame('offer_creation')
    
    def view_offers(self):
        """Navigate to browse offers screen"""
        if not self._require_database_ready():
            return
        if not self._require_offers_folder_ready():
            return
        self.nav_manager.show_frame('browse_offers')
    
    def open_new_wz(self):
        """Navigate to WZ creation screen"""
        if not self._require_database_ready():
            return
        if not self._require_wz_folder_ready():
            return
        self.nav_manager.show_frame('wz_creation')
    
    def view_wz(self):
        """Navigate to browse WZ screen"""
        if not self._require_database_ready():
            return
        if not self._require_wz_folder_ready():
            return
        self.nav_manager.show_frame('browse_wz')
    
    def browse_clients(self):
        """Navigate to browse clients screen"""
        if not self._require_database_ready():
            return
        self.nav_manager.show_frame('browse_clients')
    
    def browse_suppliers(self):
        """Show browse suppliers interface"""
        if not self._require_database_ready():
            return
        self.nav_manager.show_frame('browse_suppliers')
    
    def open_settings(self):
        """Open settings window"""
        self.nav_manager.show_frame('settings')

    def open_restore_documents(self):
        """Open restore documents window (lazy create)."""
        try:
            from src.ui.windows.restore_documents_window import RestoreDocumentsWindow
            if not hasattr(self, '_restore_win'):
                self._restore_win = RestoreDocumentsWindow(self.nav_manager.root)
            self._restore_win.open()
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się otworzyć okna przywracania: {e}")
    
    def exit_application(self):
        """Exit the application"""
        if tkinter.messagebox.askquestion("Potwierdzenie", "Czy na pewno chcesz zamknąć aplikację?") == 'yes':
            self.nav_manager.root.destroy()
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)

    def _require_database_ready(self) -> bool:
        """Block navigation if database path is invalid or not set. Shows a blocking prompt."""
        try:
            if is_database_available():
                return True
        except Exception:
            pass
        tkinter.messagebox.showerror(
            "Brak dostępu do bazy danych",
            "Funkcja niedostępna. Brak połączenia z bazą danych lub baza danych nieprawidłowo ustawiona."
        )
        return False

    def _require_offers_folder_ready(self) -> bool:
        """Ensure Offers_Folder is configured and exists when DB is available."""
        try:
            path = get_offers_folder()
        except Exception:
            path = ''
        if not path or not os.path.isdir(path):
            tkinter.messagebox.showerror(
                "Brak dostępu do folderu ofert",
                "Funkcja niedostępna. Połączono z bazą danych, ale brak dostępu do folderu z ofertami lub ścieżka do folderu nieprawidłowo ustawiona."
            )
            return False
        return True

    def _require_wz_folder_ready(self) -> bool:
        """Ensure Wz_Folder is configured and exists when DB is available."""
        try:
            path = get_wz_folder()
        except Exception:
            path = ''
        if not path or not os.path.isdir(path):
            tkinter.messagebox.showerror(
                "Brak dostępu do folderu WZ",
                "Funkcja niedostępna. Połączono z bazą danych, ale brak dostępu do folderu z WZ lub ścieżka do folderu nieprawidłowo ustawiona."
            )
            return False
        return True
