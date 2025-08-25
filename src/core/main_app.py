"""
Main application entry point and core application classes
"""
from tkinter import *
from tkinter import ttk
import locale
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.navigation_manager import NavigationManager
from src.ui.frames.main_menu_frame import MainMenuFrame
from src.ui.frames.offer_creation_frame import OfferCreationFrame
from src.ui.frames.offer_editor_frame import OfferEditorFrame
from src.ui.frames.wz_creation_frame import WzCreationFrame
from src.ui.frames.wz_editor_frame import WzEditorFrame
from src.ui.frames.browse_wz_frame import BrowseWzFrame
from src.ui.frames.browse_clients_frame import BrowseClientsFrame
from src.ui.frames.browse_suppliers_frame import BrowseSuppliersFrame
from src.ui.frames.browse_offers_frame import BrowseOffersFrame
from src.ui.frames.settings_frame import SettingsFrame
from src.core.offer_generator_app import OfferGeneratorApp
from src.core.wz_generator_app import WzGeneratorApp
from src.utils.config import WINDOW_SIZE, APP_TITLE
from src.utils.config import get_offers_folder, get_wz_folder
from src.data.database_service import get_database_path


def main():
    """Main entry point with navigation"""
    app = OfferGeneratorMainApp()
    app.run()


class OfferGeneratorMainApp:
    """Main application class with navigation support"""
    
    def __init__(self):
        # Set locale
        locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')

        # Create main window
        self.window = Tk()
        try:
            from src.utils.version import get_version_string
            version_str = get_version_string()
            self.window.title(f"{APP_TITLE} - {version_str}")
        except ImportError:
            self.window.title(APP_TITLE)
        self.window.geometry(WINDOW_SIZE)

        # Initialize navigation manager
        self.nav_manager = NavigationManager(self.window)

        # Create frames
        self.setup_frames()

        # Verify required folders (offers & WZ); navigate to settings if any missing
        missing = self.check_required_folders()
        if not missing:
            self.nav_manager.show_frame('main_menu')

        # Initialize offer creation components (but don't show them yet)
        self.setup_offer_components()
    
    def setup_frames(self):
        """Setup navigation frames"""
        # Main menu frame
        self.nav_manager.add_frame('main_menu', MainMenuFrame)
        
        # Offer creation frame
        from src.core.offer_generator_app import OfferGeneratorApp
        self.nav_manager.add_frame('offer_creation', OfferCreationFrame, OfferGeneratorApp)
        
        # Alias for offer_generator (same as offer_creation but different name for template functionality)
        self.nav_manager.add_frame('offer_generator', OfferCreationFrame, OfferGeneratorApp)
        
        # Offer editor frame
        self.nav_manager.add_frame('offer_editor', OfferEditorFrame, OfferGeneratorApp)
        
        # WZ creation frame
        from src.core.wz_generator_app import WzGeneratorApp
        self.nav_manager.add_frame('wz_creation', WzCreationFrame, WzGeneratorApp)

        # Alias for offer_generator (same as offer_creation but different name for template functionality)
        self.nav_manager.add_frame('wz_generator', WzCreationFrame, WzGeneratorApp)
        
        # WZ editor frame
        from src.core.wz_editor_app import WzEditorApp
        self.nav_manager.add_frame('wz_editor', WzEditorFrame, WzEditorApp)
        
        # Browse WZ frame
        self.nav_manager.add_frame('browse_wz', BrowseWzFrame)
        
        # Browse clients frame (now includes adding new clients)
        self.nav_manager.add_frame('browse_clients', BrowseClientsFrame)
        
        # Browse suppliers frame (now includes adding new suppliers)
        self.nav_manager.add_frame('browse_suppliers', BrowseSuppliersFrame)
        
        # Browse offers frame
        self.nav_manager.add_frame('browse_offers', BrowseOffersFrame)
        
        # Settings frame
        self.nav_manager.add_frame('settings', SettingsFrame)
    
    def setup_offer_components(self):
        """Setup offer creation components"""
        # These will be initialized when needed
        self.offer_components_initialized = False

    def check_required_folders(self) -> bool:
        """Check existence of offers and WZ folders.
        Logic:
        - WZ folder must exist always (we can't infer it from DB), otherwise navigate to settings.
        - Offers folder: if it doesn't exist but there are offers in DB, allow startup (files may be on a network share not mounted yet) and only show a non-blocking warning later on usage.
          If there are no offers in DB and the folder is missing, navigate to settings.
        Returns True if navigation to settings occurred, else False.
        """
        try:
            offers_ok = False
            wz_ok = False
            try:
                offers_path = get_offers_folder()
                offers_ok = bool(offers_path and os.path.isdir(offers_path))
            except Exception:
                offers_ok = False
            try:
                # Validation based on presence in DB (Paths.Name='Wz_Folder'), not filesystem
                from src.data.database_service import get_wz_root_from_db
                wz_path = get_wz_root_from_db()
                wz_ok = bool(wz_path)
            except Exception:
                wz_ok = False

            # If WZ folder path missing in DB, block
            if not wz_ok:
                import tkinter.messagebox
                title = 'Brak folderu WZ'
                msg = 'W bazie danych nie ustawiono ścieżki do folderu WZ. Zostaniesz przeniesiony do Ustawień aby wskazać poprawny folder.'
                tkinter.messagebox.showwarning(title, msg)
                self.nav_manager.show_frame('settings')
                return True

            # WZ is OK. If offers folder OK, proceed
            if offers_ok:
                return False

            # Offers folder missing: check if there are offers in DB; if yes, allow startup
            has_offers_in_db = False
            try:
                import sqlite3
                conn = sqlite3.connect(get_database_path())
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM Offers LIMIT 1")
                has_offers_in_db = cur.fetchone() is not None
                conn.close()
            except Exception:
                has_offers_in_db = False

            if has_offers_in_db:
                # Allow startup silently; users can set folder later in Settings if needed
                return False

            # No offers in DB and folder missing -> navigate to settings
            import tkinter.messagebox
            title = 'Brak folderu ofert'
            msg = 'Folder ofert nie istnieje, a w bazie nie ma żadnych ofert. Zostaniesz przeniesiony do Ustawień aby wskazać poprawny folder.'
            tkinter.messagebox.showwarning(title, msg)
            self.nav_manager.show_frame('settings')
            return True
        except Exception as e:
            print(f"Required folders check error: {e}")
            return False
    
    def close_application(self):
        """Close the application"""
        try:
            self.window.quit()
            self.window.destroy()
        except:
            pass
        
        import sys
        sys.exit(0)
    
    def run(self):
        """Start the application"""
        self.window.mainloop()


if __name__ == "__main__":
    main()
