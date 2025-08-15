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
        # Include version in window title
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
        
        # Perform database synchronization with offers folder
        # self.perform_synchronization()
        
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
    
    def perform_synchronization(self):
        """Perform database synchronization with offers folder"""
        try:
            import tkinter.messagebox
            
            sync_service = OfferSyncService()
            result = sync_service.synchronize()
            
            if result.success:
                # Show brief success notification
                import tkinter.messagebox
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
                
                # Show blocking error dialog
                self.show_sync_error_dialog(result, report)
                
        except Exception as e:
            import tkinter.messagebox
            error_msg = f"Wystąpił błąd podczas synchronizacji:\n{str(e)}"
            tkinter.messagebox.showerror("Błąd synchronizacji", error_msg)
            print(f"Synchronization error: {e}")
            
            # Also block app on sync errors
            self.show_critical_error_dialog(error_msg)
    
    def show_sync_error_dialog(self, result, report):
        """Show blocking sync error dialog with detailed report"""
        import tkinter.messagebox
        from tkinter import Toplevel, Text, Scrollbar, Button, Frame, Label
        
        # Create blocking dialog window
        dialog = Toplevel(self.window)
        dialog.title("❌ Błędy synchronizacji - Aplikacja zablokowana")
        dialog.geometry("800x600")
        dialog.transient(self.window)
        dialog.grab_set()  # Make dialog modal
        dialog.protocol("WM_DELETE_WINDOW", self.close_application)  # Handle window close
        
        # Disable main window
        self.window.withdraw()
        
        # Main frame
        main_frame = Frame(dialog, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = Label(main_frame, 
                           text="🚫 SYNCHRONIZACJA NIEUDANA - APLIKACJA ZABLOKOWANA",
                           font=("Arial", 16, "bold"),
                           bg='#f0f0f0', fg='#d32f2f')
        title_label.pack(pady=(0, 10))
        
        # Summary
        summary_text = (
            f"Wykryto {len(result.missing_files) + len(result.orphaned_files) + len(result.invalid_offer_numbers) + len(result.invalid_client_aliases)} problemów:\n"
            f"• Brakujące pliki: {len(result.missing_files)}\n"
            f"• Pliki sieroty: {len(result.orphaned_files)}\n"
            f"• Nieprawidłowe numery ofert: {len(result.invalid_offer_numbers)}\n"
            f"• Nieprawidłowe aliasy klientów: {len(result.invalid_client_aliases)}\n\n"
            f"Aplikacja zostanie zamknięta. Napraw błędy i uruchom ponownie."
        )
        
        summary_label = Label(main_frame, 
                             text=summary_text,
                             font=("Arial", 12),
                             bg='#f0f0f0', fg='#333333',
                             justify='left')
        summary_label.pack(pady=(0, 20))
        
        # Report frame with scrollbar
        report_frame = Frame(main_frame)
        report_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # Create scrollable text widget for report
        text_widget = Text(report_frame, 
                          wrap='word', 
                          font=("Courier", 10),
                          bg='#ffffff', 
                          fg='#333333',
                          relief='sunken',
                          bd=2)
        
        scrollbar = Scrollbar(report_frame, orient='vertical', command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Insert report
        text_widget.insert('1.0', report)
        text_widget.config(state='disabled')  # Make read-only
        
        # Pack text and scrollbar
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Buttons frame
        buttons_frame = Frame(main_frame, bg='#f0f0f0')
        buttons_frame.pack(fill='x')
        
        # Save report button
        save_btn = Button(buttons_frame, 
                         text="💾 Zapisz raport do pliku",
                         font=("Arial", 12),
                         fg='white',
                         padx=20, pady=10,
                         command=lambda: self.save_sync_report(report),
                         cursor='hand2')
        save_btn.pack(side='left', padx=(0, 10))
        
        # Close application button
        close_btn = Button(buttons_frame, 
                          text="❌ Zamknij aplikację",
                          font=("Arial", 12, "bold"),
                          fg='white',
                          padx=20, pady=10,
                          command=self.close_application,
                          cursor='hand2')
        close_btn.pack(side='right')
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Force dialog to front
        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.deiconify()  # Make sure dialog is not minimized
        dialog.focus_force()
        
        # Small delay to ensure visibility
        dialog.after(100, lambda: dialog.focus_set())
        
        # Print report to console as well
        print("\n" + "="*60)
        print("RAPORT SYNCHRONIZACJI:")
        print("="*60)
        print(report)
        print("="*60 + "\n")
    
    def show_critical_error_dialog(self, error_message):
        """Show blocking critical error dialog"""
        import tkinter.messagebox
        from tkinter import Toplevel, Label, Button, Frame
        
        # Create blocking dialog window
        dialog = Toplevel(self.window)
        dialog.title("❌ Błąd krytyczny")
        dialog.geometry("500x300")
        dialog.transient(self.window)
        dialog.grab_set()  # Make dialog modal
        dialog.protocol("WM_DELETE_WINDOW", self.close_application)
        
        # Disable main window
        self.window.withdraw()
        
        # Main frame
        main_frame = Frame(dialog, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = Label(main_frame, 
                           text="🚫 BŁĄD KRYTYCZNY",
                           font=("Arial", 16, "bold"),
                           bg='#f0f0f0', fg='#d32f2f')
        title_label.pack(pady=(0, 20))
        
        # Error message
        error_label = Label(main_frame, 
                           text=error_message,
                           font=("Arial", 12),
                           bg='#f0f0f0', fg='#333333',
                           wraplength=450,
                           justify='left')
        error_label.pack(pady=(0, 30))
        
        # Close button
        close_btn = Button(main_frame, 
                          text="❌ Zamknij aplikację",
                          font=("Arial", 12, "bold"),
                          fg='white',
                          padx=30, pady=10,
                          command=self.close_application,
                          cursor='hand2')
        close_btn.pack()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
    
    def save_sync_report(self, report):
        """Save synchronization report to file"""
        try:
            from tkinter import filedialog
            from datetime import datetime
            
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"sync_report_{timestamp}.txt"
            
            # Ask user where to save
            file_path = filedialog.asksaveasfilename(
                title="Zapisz raport synchronizacji",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialvalue=default_filename
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                import tkinter.messagebox
                tkinter.messagebox.showinfo("Sukces", f"Raport został zapisany do:\n{file_path}")
                
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Nie udało się zapisać raportu:\n{str(e)}")
    
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
