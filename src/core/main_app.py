"""
Main application entry point and core application classes
"""
from tkinter import *
from tkinter import ttk
import tkinter.font as tkfont
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
from src.data.database_service import get_database_path, is_database_available
import src.data.database_service as _dbs
from src.utils.settings import settings_manager
import shutil
from datetime import datetime


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
        # Ensure all multiline Text widgets use the same default font as Entry across the whole app
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            # Apply to all classic Tk Text widgets created afterwards
            self.window.option_add("*Text*font", default_font)
        except Exception:
            # Non-fatal if fonts aren't available yet
            pass
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

        # Enable DB popups after initial UI is ready
        try:
            import src.data.database_service as _dbs
            _dbs.DB_POPUPS_ENABLED = True
        except Exception:
            pass

        # Enable DB error popups after initial navigation has been decided
        try:
            _dbs.DB_POPUPS_ENABLED = True
        except Exception:
            pass

        # Initialize offer creation components (but don't show them yet)
        self.setup_offer_components()

        # Perform optional database backup after UI initialized
        try:
            self.perform_database_backup_on_start()
        except Exception as e:
            # Non-fatal: log to console
            print(f"Database backup on start failed: {e}")
    
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

    def perform_database_backup_on_start(self):
        """If enabled in settings, copy DB file to backup folder with date suffix.
        Overwrite if exists. Date format DD_MM_YYYY. Filename: {name}_{date}{ext}
        """
        try:
            enabled = bool(settings_manager.get_app_setting('db_backup_enabled'))
            backup_folder = settings_manager.get_app_setting('db_backup_folder') or ''
        except Exception:
            return
        if not enabled:
            return
        # Only proceed if application has access to the configured database
        try:
            if not is_database_available():
                return
        except Exception:
            return
        db_path = get_database_path()
        if not db_path or not os.path.exists(db_path):
            return
        if not backup_folder:
            return
        try:
            os.makedirs(backup_folder, exist_ok=True)
        except Exception:
            pass
        base = os.path.basename(db_path)
        name, ext = os.path.splitext(base)
        today = datetime.now().strftime('%d_%m_%Y')
        dest_name = f"{name}_{today}{ext}"
        dest_path = os.path.join(backup_folder, dest_name)
        shutil.copy2(db_path, dest_path)

    def check_required_folders(self) -> bool:
        """Startup check for folders; do not show prompts at startup.
        - If database is unavailable, skip all prompts and allow startup.
        - If database is available, don't show popup prompts or auto-navigate; allow startup.
        Returns True if we explicitly navigate away (we won't), else False to show main menu.
        """
        try:
            # If DB isn't available, allow startup silently
            if not is_database_available():
                return False

            # When DB is available, we still avoid popups and auto-navigation at startup.
            # We can perform lightweight checks without side effects.
            _ = get_offers_folder()
            from src.utils.config import get_wz_folder as _get_wz_root
            _ = _get_wz_root()
            return False
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
