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
        title_label = Label(self, text="Ultra Pro 2137 Kreator dokumentów Hantech", 
                           font=("Arial", 24, "bold"), 
                           bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=50)
        
        # Main menu buttons frame
        buttons_frame = Frame(self, bg='#f0f0f0')
        buttons_frame.pack(pady=50)
        
        # Create new offer button
        new_offer_btn = Button(buttons_frame, 
                              text="Stwórz nową ofertę",
                              font=("Arial", 16, "bold"),
                              bg='#4CAF50', fg='black',
                              padx=30, pady=15,
                              command=self.open_new_offer,
                              cursor='hand2')
        new_offer_btn.pack(pady=15)
        
        # View offers button (placeholder for future functionality)
        view_offers_btn = Button(buttons_frame, 
                                text="Przeglądaj oferty",
                                font=("Arial", 14),
                                bg='#2196F3', fg='black',
                                padx=30, pady=10,
                                command=self.view_offers,
                                cursor='hand2')
        view_offers_btn.pack(pady=10)
        
        # Browse clients button (now includes adding new clients)
        browse_clients_btn = Button(buttons_frame, 
                                   text="Zarządzaj klientami",
                                   font=("Arial", 14),
                                   bg='#3F51B5', fg='black',
                                   padx=30, pady=10,
                                   command=self.browse_clients,
                                   cursor='hand2')
        browse_clients_btn.pack(pady=10)
        
        # Browse suppliers button (now includes adding new suppliers)
        browse_suppliers_btn = Button(buttons_frame, 
                                     text="Zarządzaj dostawcami",
                                     font=("Arial", 14),
                                     bg='#FF5722', fg='black',
                                     padx=30, pady=10,
                                     command=self.browse_suppliers,
                                     cursor='hand2')
        browse_suppliers_btn.pack(pady=10)
        
        # Test data button
        test_data_btn = Button(
            buttons_frame, 
            text="🧪 Generuj dane testowe",
            font=("Arial", 12),
            bg='#ff9800', fg='white',
            padx=30, pady=10,
            command=self.generate_test_data,
            cursor='hand2'
        )
        test_data_btn.pack(pady=10)
        
        # Cleanup test data button
        cleanup_btn = Button(
            buttons_frame, 
            text="🗑️ Usuń dane testowe",
            font=("Arial", 12),
            bg='#f44336', fg='white',
            padx=30, pady=10,
            command=self.cleanup_test_data,
            cursor='hand2'
        )
        cleanup_btn.pack(pady=10)
        
        # Settings button (placeholder for future functionality)
        settings_btn = Button(buttons_frame, 
                             text="Ustawienia",
                             font=("Arial", 14),
                             bg='#FF9800', fg='black',
                             padx=30, pady=10,
                             command=self.open_settings,
                             cursor='hand2')
        settings_btn.pack(pady=10)
        
        # Exit button
        exit_btn = Button(buttons_frame, 
                         text="Zamknij aplikację",
                         font=("Arial", 12),
                         bg='#f44336', fg='black',
                         padx=20, pady=8,
                         command=self.exit_application,
                         cursor='hand2')
        exit_btn.pack(pady=(30, 10))
    
    def open_new_offer(self):
        """Navigate to offer creation screen"""
        self.nav_manager.show_frame('offer_creation')
    
    def view_offers(self):
        """Navigate to browse offers screen"""
        self.nav_manager.show_frame('browse_offers')
    
    def generate_test_data(self):
        """Generate test data for scrolling tests"""
        import tkinter.messagebox
        
        # Ask for confirmation
        result = tkinter.messagebox.askyesno(
            "Generowanie danych testowych",
            "Czy chcesz wygenerować dane testowe?\n\n"
            "To doda:\n"
            "• 100 klientów testowych\n"
            "• 100 dostawców testowych\n"
            "• 100 ofert testowych\n\n"
            "Operacja może potrwać kilka minut."
        )
        
        if result:
            try:
                # Access main app through navigation manager
                if hasattr(self.nav_manager, 'main_app'):
                    self.nav_manager.main_app.generate_test_data()
                else:
                    # Alternative approach - find main app in window
                    main_window = self.nav_manager.window
                    if hasattr(main_window, 'main_app'):
                        main_window.main_app.generate_test_data()
                    else:
                        # Direct import and execution
                        from src.core.main_app import OfferGeneratorMainApp
                        temp_app = OfferGeneratorMainApp()
                        temp_app.generate_test_data()
            except Exception as e:
                tkinter.messagebox.showerror("Błąd", f"Nie udało się wygenerować danych testowych:\n{str(e)}")

    def cleanup_test_data(self):
        """Clean up test data"""
        try:
            # Access main app through navigation manager
            if hasattr(self.nav_manager, 'main_app'):
                self.nav_manager.main_app.cleanup_test_data()
            else:
                import tkinter.messagebox
                tkinter.messagebox.showerror("Błąd", "Nie można uzyskać dostępu do funkcji czyszczenia danych.")
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Nie udało się usunąć danych testowych:\n{str(e)}")

    def browse_clients(self):
        """Navigate to browse clients screen"""
        self.nav_manager.show_frame('browse_clients')
    
    def browse_suppliers(self):
        """Show browse suppliers interface"""
        self.nav_manager.show_frame('browse_suppliers')
    
    def open_settings(self):
        """Open settings window"""
        self.nav_manager.show_frame('settings')
    
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
