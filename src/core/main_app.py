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
from src.ui.frames.browse_clients_frame import BrowseClientsFrame
from src.ui.frames.browse_suppliers_frame import BrowseSuppliersFrame
from src.ui.frames.browse_offers_frame import BrowseOffersFrame
from src.ui.frames.settings_frame import SettingsFrame
from src.core.offer_generator_app import OfferGeneratorApp
from src.services.sync_service import OfferSyncService
from src.utils.config import WINDOW_SIZE, BACKGROUND_IMAGE, TAX_RATE, APP_TITLE


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
        self.window.title(APP_TITLE)
        self.window.geometry(WINDOW_SIZE)
        
        # Initialize navigation manager
        self.nav_manager = NavigationManager(self.window)
        
        # Create frames
        self.setup_frames()
        
        # Perform database synchronization with offers folder
        self.perform_synchronization()
        
        # Start with main menu
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
    
    def perform_synchronization(self):
        """Perform database synchronization with offers folder"""
        try:
            import tkinter.messagebox
            
            sync_service = OfferSyncService()
            result = sync_service.synchronize()
            
            if result.success:
                tkinter.messagebox.showinfo(
                    "Synchronizacja", 
                    f"Synchronizacja zakończona pomyślnie!\n\n"
                    f"Sprawdzono {result.total_offers_db} ofert z bazy danych\n"
                    f"Znaleziono {result.total_offers_folder} plików w folderze ofert\n"
                    f"Wszystkie dane są spójne."
                )
            else:
                # Generate detailed report
                report = sync_service.generate_report(result)
                
                # Show error dialog with option to see full report
                response = tkinter.messagebox.showerror(
                    "Błędy synchronizacji",
                    f"Wykryto problemy podczas synchronizacji!\n\n"
                    f"Problemy:\n"
                    f"- Brakujące pliki: {len(result.missing_files)}\n"
                    f"- Pliki sieroty: {len(result.orphaned_files)}\n"
                    f"- Nieprawidłowe numery ofert: {len(result.invalid_offer_numbers)}\n"
                    f"- Nieprawidłowe aliasy klientów: {len(result.invalid_client_aliases)}\n\n"
                    f"Sprawdź konsolę/terminal aby zobaczyć pełny raport."
                )
                
                # Print full report to console
                print("\n" + "="*60)
                print(report)
                print("="*60 + "\n")
                
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror(
                "Błąd synchronizacji", 
                f"Wystąpił błąd podczas synchronizacji:\n{str(e)}"
            )
            print(f"Synchronization error: {e}")
    
    def run(self):
        """Start the application"""
        self.window.mainloop()


if __name__ == "__main__":
    main()
