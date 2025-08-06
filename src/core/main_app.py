"""
Main application entry point and core application classes

UWAGA: Aby wygenerować dane testowe do testowania scrollowania:
1. Uruchom aplikację normalnie: python -m src.core.main_app
2. W menu głównym kliknij przycisk "🧪 Generuj dane testowe"
3. Potwierdź generowanie danych
4. Poczekaj na zakończenie procesu
5. Przetestuj scrollowanie w oknie przeglądania klientów, dostawców i ofert

Alternatywnie możesz wywołać generate_test_data() bezpośrednio z kodu.
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
        self.nav_manager = NavigationManager(self.window, self)
        
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
                         bg='#2196f3', fg='white',
                         padx=20, pady=10,
                         command=lambda: self.save_sync_report(report),
                         cursor='hand2')
        save_btn.pack(side='left', padx=(0, 10))
        
        # Close application button
        close_btn = Button(buttons_frame, 
                          text="❌ Zamknij aplikację",
                          font=("Arial", 12, "bold"),
                          bg='#f44336', fg='white',
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
                          bg='#f44336', fg='white',
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
    
    def generate_test_data(self):
        """Generate test data for scrolling tests"""
        try:
            import sqlite3
            import random
            import json
            from datetime import datetime, timedelta
            
            print("Rozpoczynam generowanie danych testowych...")
            
            # Get database path from config
            from src.utils.config import DATABASE_PATH
            
            # Polish test data
            company_names = [
                "ABC Sp. z o.o.", "XYZ S.A.", "Tech Solutions", "Innovation Corp",
                "Global Trading", "Premium Services", "Quality Products", "Best Choice",
                "Smart Systems", "Digital World", "Future Tech", "Modern Solutions",
                "Professional Services", "Excellent Quality", "Top Performance",
                "Advanced Technology", "Reliable Systems", "Perfect Choice",
                "Elite Services", "Superior Products", "Prime Solutions", "Expert Systems",
                "Master Technology", "Pro Services", "Ultra Modern", "High Quality",
                "Super Solutions", "Mega Systems", "Power Tech", "Dynamic Services"
            ]
            
            cities = [
                "Warszawa", "Kraków", "Łódź", "Wrocław", "Poznań", "Gdańsk", "Szczecin",
                "Bydgoszcz", "Lublin", "Katowice", "Białystok", "Częstochowa", "Gdynia",
                "Radom", "Sosnowiec", "Toruń", "Kielce", "Gliwice", "Zabrze", "Bytom"
            ]
            
            streets = [
                "Marszałkowska", "Krakowska", "Warszawska", "Długa", "Krótka", "Nowa",
                "Stara", "Główna", "Centralna", "Piękna", "Zielona", "Słoneczna",
                "Kwiatowa", "Leśna", "Polna", "Ogrodowa", "Parkowa", "Rzeczna"
            ]
            
            first_names = [
                "Jan", "Anna", "Piotr", "Maria", "Tomasz", "Katarzyna", "Michał", "Agnieszka",
                "Krzysztof", "Barbara", "Andrzej", "Ewa", "Stanisław", "Teresa", "Dariusz",
                "Małgorzata", "Marcin", "Joanna", "Grzegorz", "Danuta", "Jerzy", "Jadwiga"
            ]
            
            last_names = [
                "Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamiński",
                "Lewandowski", "Zieliński", "Szymański", "Woźniak", "Dąbrowski", "Kozłowski"
            ]
            
            product_names = [
                "Laptop Dell", "Monitor Samsung", "Klawiatura Logitech", "Mysz Microsoft",
                "Drukarka HP", "Router TP-Link", "Dysk SSD Kingston", "Pamięć RAM Corsair",
                "Karta graficzna NVIDIA", "Procesor Intel", "Płyta główna ASUS", "Zasilacz be quiet!"
            ]
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Generate 100 test clients
            print("Dodawanie 100 klientów testowych...")
            for i in range(100):
                nip = random.randint(1000000000, 9999999999)  # 10-digit NIP
                company_name = f"{random.choice(company_names)} {i+1:03d}"
                contact_person = f"{random.choice(first_names)} {random.choice(last_names)}"
                street = f"ul. {random.choice(streets)} {random.randint(1, 999)}"
                city = random.choice(cities)
                postal_code = f"{random.randint(10, 99)}-{random.randint(100, 999)}"
                phone = f"+48 {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}"
                
                # AddressP1: street + phone, AddressP2: city + postal_code
                address_p1 = f"{street}, tel: {phone}"
                address_p2 = f"{postal_code} {city}"
                alias = f"TEST_CLIENT_{i+1:03d}"
                
                cursor.execute('''
                    INSERT INTO Clients (Nip, CompanyName, AddressP1, AddressP2, Alias)
                    VALUES (?, ?, ?, ?, ?)
                ''', (nip, company_name, address_p1, address_p2, alias))
                
                if (i + 1) % 20 == 0:
                    print(f"Dodano {i + 1} klientów...")
            
            # Generate 100 test suppliers
            print("Dodawanie 100 dostawców testowych...")
            for i in range(100):
                nip = random.randint(1000000000, 9999999999)  # 10-digit NIP
                company_name = f"Dostawca {random.choice(company_names)} {i+1:03d}"
                contact_person = f"{random.choice(first_names)} {random.choice(last_names)}"
                street = f"ul. {random.choice(streets)} {random.randint(1, 999)}"
                city = random.choice(cities)
                postal_code = f"{random.randint(10, 99)}-{random.randint(100, 999)}"
                phone = f"+48 {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}"
                
                # AddressP1: street + phone, AddressP2: city + postal_code
                address_p1 = f"{street}, tel: {phone}"
                address_p2 = f"{postal_code} {city}"
                
                cursor.execute('''
                    INSERT INTO Suppliers (Nip, CompanyName, AddressP1, AddressP2)
                    VALUES (?, ?, ?, ?)
                ''', (nip, company_name, address_p1, address_p2))
                
                if (i + 1) % 20 == 0:
                    print(f"Dodano {i + 1} dostawców...")
            
            conn.commit()
            
            # Get next available OfferOrderNumber
            cursor.execute('SELECT MAX(OfferOrderNumber) FROM Offers')
            max_offer_number = cursor.fetchone()[0]
            next_offer_number = (max_offer_number or 0) + 1
            
            # Get some clients for offers
            cursor.execute('SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients LIMIT 20')
            clients = cursor.fetchall()
            
            # Generate 100 test offers
            print("Dodawanie 100 ofert testowych...")
            for i in range(100):
                current_date = datetime.now()
                offer_number = f"TEST-{current_date.year}-{i+1:04d}"
                
                # Random client
                client = random.choice(clients)
                client_data = {
                    'nip': client[0],
                    'company_name': client[1],
                    'address_p1': client[2],
                    'address_p2': client[3],
                    'alias': client[4] if client[4] else f"CLIENT_{i+1}"
                }
                
                client_alias = f"TEST_{client[1].replace(' ', '_').upper()[:10]}_{i+1:03d}"
                
                # Random date within last 6 months
                start_date = current_date - timedelta(days=180)
                random_date = start_date + timedelta(days=random.randint(0, 180))
                
                # Generate products
                products = []
                num_products = random.randint(1, 3)
                
                for j in range(num_products):
                    product = {
                        'name': f"{random.choice(product_names)} Model {j+1}",
                        'quantity': random.randint(1, 10),
                        'unit_price': round(random.uniform(100, 5000), 2),
                        'description': f"Produkt testowy {j+1}"
                    }
                    products.append(product)
                
                # Calculate totals
                subtotal = sum(p['quantity'] * p['unit_price'] for p in products)
                tax_amount = subtotal * 0.23
                total = subtotal + tax_amount
                
                offer_context = {
                    'offer_number': offer_number,
                    'client_alias': client_alias,
                    'client_data': client_data,
                    'offer_date': random_date.strftime('%Y-%m-%d'),
                    'products': products,
                    'subtotal': round(subtotal, 2),
                    'tax_amount': round(tax_amount, 2),
                    'total': round(total, 2),
                    'notes': f"Oferta testowa nr {i+1} - wygenerowana automatycznie",
                    'is_test_data': True
                }
                
                # Save offer context using proper column names
                context_json = json.dumps(offer_context, default=str, ensure_ascii=False)
                offer_order_number = next_offer_number + i  # Incremental number from last existing
                offer_file_path = f"test_offers/TEST-{current_date.year}-{i+1:04d}.docx"
                
                cursor.execute('''
                    INSERT INTO Offers (OfferOrderNumber, OfferFilePath, OfferContext)
                    VALUES (?, ?, ?)
                ''', (offer_order_number, offer_file_path, context_json))
                
                if (i + 1) % 20 == 0:
                    print(f"Dodano {i + 1} ofert...")
            
            conn.commit()
            conn.close()
            
            print("✓ Generowanie danych testowych zakończone!")
            print("Wygenerowano:")
            print("- 100 klientów testowych")
            print("- 100 dostawców testowych") 
            print("- 100 ofert testowych")
            print("Możesz teraz przetestować scrollowanie w oknie przeglądania.")
            
            import tkinter.messagebox
            tkinter.messagebox.showinfo(
                "Dane testowe", 
                "Pomyślnie wygenerowano dane testowe!\n\n"
                "• 100 klientów\n"
                "• 100 dostawców\n" 
                "• 100 ofert\n\n"
                "Możesz teraz przetestować scrollowanie."
            )
            
        except Exception as e:
            print(f"Błąd podczas generowania danych testowych: {e}")
            import traceback
            traceback.print_exc()
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Nie udało się wygenerować danych testowych:\n{str(e)}")
    
    def cleanup_test_data(self):
        """Remove all test data from database"""
        try:
            import sqlite3
            import tkinter.messagebox
            
            print("Rozpoczynam usuwanie danych testowych...")
            
            # Get database path from config
            from src.utils.config import DATABASE_PATH
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Count test data before deletion
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE Alias LIKE 'TEST_CLIENT_%'")
            test_clients_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM Suppliers WHERE CompanyName LIKE 'Dostawca %'")
            test_suppliers_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM Offers WHERE OfferFilePath LIKE 'test_offers/%'")
            test_offers_count = cursor.fetchone()[0]
            
            if test_clients_count == 0 and test_suppliers_count == 0 and test_offers_count == 0:
                tkinter.messagebox.showinfo(
                    "Czyszczenie danych", 
                    "Nie znaleziono danych testowych do usunięcia."
                )
                conn.close()
                return
            
            # Ask for confirmation
            confirm_msg = (
                f"Czy na pewno chcesz usunąć dane testowe?\n\n"
                f"Do usunięcia:\n"
                f"• {test_clients_count} klientów testowych\n"
                f"• {test_suppliers_count} dostawców testowych\n"
                f"• {test_offers_count} ofert testowych\n\n"
                f"Ta operacja jest nieodwracalna!"
            )
            
            result = tkinter.messagebox.askyesno("Potwierdzenie", confirm_msg)
            
            if not result:
                conn.close()
                return
            
            # Delete test clients
            print(f"Usuwanie {test_clients_count} klientów testowych...")
            cursor.execute("DELETE FROM Clients WHERE Alias LIKE 'TEST_CLIENT_%'")
            deleted_clients = cursor.rowcount
            
            # Delete test suppliers  
            print(f"Usuwanie {test_suppliers_count} dostawców testowych...")
            cursor.execute("DELETE FROM Suppliers WHERE CompanyName LIKE 'Dostawca %'")
            deleted_suppliers = cursor.rowcount
            
            # Delete test offers
            print(f"Usuwanie {test_offers_count} ofert testowych...")
            cursor.execute("DELETE FROM Offers WHERE OfferFilePath LIKE 'test_offers/%'")
            deleted_offers = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            print("✓ Czyszczenie danych testowych zakończone!")
            print(f"Usunięto:")
            print(f"- {deleted_clients} klientów testowych")
            print(f"- {deleted_suppliers} dostawców testowych")
            print(f"- {deleted_offers} ofert testowych")
            
            tkinter.messagebox.showinfo(
                "Czyszczenie zakończone", 
                f"Pomyślnie usunięto dane testowe!\n\n"
                f"Usunięto:\n"
                f"• {deleted_clients} klientów\n"
                f"• {deleted_suppliers} dostawców\n"
                f"• {deleted_offers} ofert\n\n"
                f"Baza danych została oczyszczona."
            )
            
        except Exception as e:
            print(f"Błąd podczas usuwania danych testowych: {e}")
            import traceback
            traceback.print_exc()
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Nie udało się usunąć danych testowych:\n{str(e)}")
    
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
