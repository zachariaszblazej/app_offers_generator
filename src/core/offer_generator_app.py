"""
Core offer generator application logic
"""
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ui.components.ui_components import UIComponents
from src.ui.windows.client_search_window import ClientSearchWindow
from src.ui.windows.supplier_search_window import SupplierSearchWindow
from src.ui.windows.product_add_window import ProductAddWindow
from src.ui.windows.product_edit_window import ProductEditWindow
from src.ui.components.product_table import ProductTable
from src.services.offer_generator_service import generate_offer_document
from src.utils.config import BACKGROUND_IMAGE


class OfferGeneratorApp:
    """Original offer generator app, now embedded within a frame"""
    
    def __init__(self, parent_frame, nav_manager, template_context=None):
        self.parent_frame = parent_frame
        self.nav_manager = nav_manager
        self.template_context = template_context  # Context data to use as template
        # Use content_container instead of offer_container
        self.window = parent_frame.content_container
        
        # Track if user has made any modifications after template load
        self.user_modifications_made = False
        
        # Initialize components
        self.setup_ui()
        
        # Initialize calculation variables
        self.count = 0
        
        # Load template data if provided
        if self.template_context:
            self.load_template_context()
            # Reset modification flag after template load
            self.user_modifications_made = False
    
    def setup_ui(self):
        """Setup all UI components within the parent frame"""
        # Set minimum height for content container to ensure scrolling works
        self.window.configure(height=1200)  # Set explicit height for scrolling
        
        # Set background
        try:
            bg = PhotoImage(file=BACKGROUND_IMAGE)
            label_BG = Label(self.window, image=bg)
            label_BG.place(x=0, y=0)
            label_BG.image = bg  # Keep a reference
        except Exception as e:
            print(f"Could not load background image: {e}")
            # If background image fails, use a clean professional color
            self.window.configure(bg='#f5f5f5')
        
        # Initialize UI components
        # Create product table with edit and delete callbacks
        self.product_table = ProductTable(self.window, self.parent_frame, self.edit_product, self.on_product_deleted)
        self.ui = UIComponents(self.window, self.product_table)
        
        # Set modification callback so UI components can notify about user changes
        self.ui.set_modification_callback(self.mark_as_modified)
        
        self.client_search = ClientSearchWindow(self.window, self.ui.fill_client_data)
        self.supplier_search = SupplierSearchWindow(self.window, self.ui.fill_supplier_data)
        self.product_add = ProductAddWindow(self.window, self.insert_product)
        self.product_edit = ProductEditWindow(self.window, self.update_product)
        
        # Create UI sections
        self.ui.create_upper_section()
        self.ui.create_offer_section()
        self.ui.create_offer_details_section()
        self.ui.create_totals_section()
        
        # Create buttons
        self.create_buttons()
    
    def create_buttons(self):
        """Create all buttons"""
        # Product management buttons
        Button(self.window, text="DODAJ POZYCJĘ", 
               font=("Arial", 12, "bold"),
               bg='#28a745', fg='black',
               padx=15, pady=8,
               command=self.product_add.open_product_add_window,
               cursor='hand2').place(x=50, y=740)
                
        # Client search button
        search_client_button = Button(self.window, text="Szukaj klienta", 
                                    font=("Arial", 10),
                                    command=self.client_search.open_client_search)
        search_client_button.place(x=900, y=360)
        
        # Supplier search button
        search_supplier_button = Button(self.window, text="Szukaj dostawcy", 
                                      font=("Arial", 10),
                                      command=self.supplier_search.open_supplier_search)
        search_supplier_button.place(x=300, y=360)
        
        # Generate offer button
        generate_offer_button = Button(self.window, text="Generuj ofertę", 
                                     font=("Arial", 12, "bold"),
                                     command=self.generate_offer)
        generate_offer_button.place(x=700, y=980)
    
    def insert_product(self, product_data):
        """Insert a new product into the table"""
        if self.product_table.input_record(product_data):
            # Mark user modifications
            self.user_modifications_made = True
            # Automatically recalculate total
            self.calc_total()
            return True
        return False
    
    def on_product_deleted(self):
        """Called when product is deleted via inline delete button"""
        # Mark user modifications
        self.user_modifications_made = True
        # Automatically recalculate total after deletion
        self.calc_total()
    
    def edit_product(self):
        """Edit selected product from the table"""
        selected_product = self.product_table.get_selected_product()
        if selected_product:
            self.product_edit.open_product_edit_window(selected_product)
        else:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do edycji!")
    
    def edit_product(self):
        """Edit selected product from the table"""
        selected_product = self.product_table.get_selected_product()
        if selected_product:
            self.product_edit.open_product_edit_window(selected_product)
        else:
            tkinter.messagebox.showwarning("Uwaga", "Najpierw zaznacz produkt do edycji!")
    
    def update_product(self, item_id, product_data):
        """Update existing product in the table"""
        if self.product_table.update_record(item_id, product_data):
            # Mark user modifications
            self.user_modifications_made = True
            # Automatically recalculate total after update
            self.calc_total()
            return True
        return False
    
    def mark_as_modified(self):
        """Mark that user has made modifications"""
        self.user_modifications_made = True
    
    def calc_total(self):
        """Calculate and display totals"""
        # Calculate totals from product table
        total = self.product_table.calculate_totals()
        
        # Update the suma field using the new method
        self.ui.update_suma(total)
    
    def load_template_context(self):
        """Load data from template context for creating similar offer"""
        try:
            if self.template_context:
                # Load data into UI (without offer number)
                success = self.ui.load_context_for_new_offer(self.template_context)
                
                if success:
                    # Show info message
                    import tkinter.messagebox
                    tkinter.messagebox.showinfo("Dane załadowane", 
                        "Pomyślnie załadowano dane z wybranej oferty." +
                        "Numer oferty zostanie wygenerowany automatycznie po utworzeniu oferty.")
                else:
                    import tkinter.messagebox
                    tkinter.messagebox.showwarning("Błąd ładowania", 
                        "Wystąpił problem podczas ładowania danych z szablonu.")
            else:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Brak danych", 
                    "Nie znaleziono danych kontekstu dla wybranej oferty.")
                    
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", f"Wystąpił błąd podczas ładowania danych: {e}")
    
    def load_template_data(self):
        """Load data from template offer for creating similar offer (deprecated method)"""
        try:
            # Import here to avoid circular imports
            from src.data.database_service import get_offer_context_from_db
            
            # Get offer context from database
            context_data = get_offer_context_from_db(self.template_offer_path)
            
            if context_data:
                # Load data into UI (without offer number)
                success = self.ui.load_context_for_new_offer(context_data)
                
                if success:
                    # Show info message
                    import tkinter.messagebox
                    tkinter.messagebox.showinfo("Dane załadowane", 
                        f"Pomyślnie załadowano dane z oferty:{os.path.basename(self.template_offer_path)}" +
                        "Numer oferty zostanie wygenerowany automatycznie po utworzeniu oferty.")
                else:
                    import tkinter.messagebox
                    tkinter.messagebox.showwarning("Błąd ładowania", 
                        "Wystąpił problem podczas ładowania danych z szablonu.")
            else:
                import tkinter.messagebox
                tkinter.messagebox.showwarning("Brak danych", 
                    f"Nie znaleziono danych kontekstu dla oferty:\\n{os.path.basename(self.template_offer_path)}" +
                    "Oferta została prawdopodobnie utworzona przed implementacją zapisywania kontekstu.")
            # Finally, update scroll region after all data is loaded
            self.update_scroll_region()
                    
        except Exception as e:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Błąd", 
                f"Nie udało się załadować danych z szablonu:{e}")
            print(f"Error loading template data: {e}")  # Debug
    
        # Update scroll region after all data is loaded
        self.update_scroll_region()
        
    def update_scroll_region(self):
        """Update scroll region if parent frame has scrolling capability"""
        try:
            if hasattr(self.parent_frame, 'update_scroll_region'):
                self.parent_frame.update_scroll_region()
        except Exception as e:
            print(f"Could not update scroll region: {e}")
    
    def has_unsaved_changes(self):
        """Check if user has made any changes that would be lost"""
        try:
            # If this is a template-based instance and user hasn't made modifications yet
            if self.template_context and not self.user_modifications_made:
                return False  # Template data is not considered "unsaved changes"
            
            # Check if product table has any items
            if hasattr(self, 'product_table') and self.product_table and self.product_table.tree:
                if len(self.product_table.tree.get_children()) > 0:
                    return True
            
            # Check if client fields are filled (beyond default values)
            if hasattr(self, 'ui') and self.ui and hasattr(self.ui, 'entries'):
                # Check client fields
                client_fields = ['client_name', 'client_address_1', 'client_address_2', 'client_nip']
                for field in client_fields:
                    if field in self.ui.entries:
                        value = self.ui.entries[field].get().strip()
                        if value:  # If any client field has content
                            return True
                
                # Check supplier fields
                supplier_fields = ['supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_nip']
                for field in supplier_fields:
                    if field in self.ui.entries:
                        value = self.ui.entries[field].get().strip()
                        if value:  # If any supplier field has content
                            return True
                
                # Check additional offer details
                additional_fields = ['termin_realizacji', 'termin_platnosci', 'uwagi']
                for field in additional_fields:
                    if field in self.ui.entries:
                        if field == 'uwagi':  # Text widget
                            value = self.ui.entries[field].get('1.0', 'end-1c').strip()
                        else:  # Entry widget
                            value = self.ui.entries[field].get().strip()
                        if value:
                            return True
            
            return False
            
        except Exception as e:
            print(f"Error checking for unsaved changes: {e}")
            return False  # If error, assume no changes to avoid blocking user
    
    def clear_all_data(self):
        """Clear all data from the form"""
        try:
            # Clear product table
            if hasattr(self, 'product_table') and self.product_table and self.product_table.tree:
                for item in self.product_table.tree.get_children():
                    self.product_table.tree.delete(item)
                self.product_table.count = 0
            
            # Clear UI fields
            if hasattr(self, 'ui') and self.ui and hasattr(self.ui, 'entries'):
                # Fields to clear
                fields_to_clear = [
                    'client_name', 'client_address_1', 'client_address_2', 'client_nip',
                    'supplier_name', 'supplier_address_1', 'supplier_address_2', 'supplier_nip','uwagi'
                ]
                
                # Clear all specified fields
                for field_name in fields_to_clear:
                    if field_name in self.ui.entries:
                        if field_name == 'uwagi':  # Text widget
                            self.ui.entries[field_name].delete('1.0', 'end')
                        else:  # Entry widget
                            self.ui.entries[field_name].delete(0, 'end')
                
                # Reset suma to 0
                if hasattr(self.ui, 'clear_suma'):
                    self.ui.clear_suma()
                
                # Clear selected client and supplier aliases
                if hasattr(self.ui, 'selected_client_alias'):
                    self.ui.selected_client_alias = None
                if hasattr(self.ui, 'selected_supplier_alias'):
                    self.ui.selected_supplier_alias = None
            
            # Reset calculation variables
            self.count = 0
            
            # Reset modification flag and template context
            self.user_modifications_made = False
            self.template_context = None
            
            print("All data cleared from offer creator")
            
        except Exception as e:
            print(f"Error clearing data: {e}")
    
    def generate_offer(self):
        """Generate the offer document"""
        # Get form data
        context_data = self.ui.get_context_data()
        
        # Keep date as datetime object for offer generation
        # The conversion to string will be handled in generate_offer_document
        
        # Generate document
        result = generate_offer_document(context_data)
        
        # Handle the result
        if result['success']:
            # Show success message
            tkinter.messagebox.showinfo("Success", 
                                      f"Offer generated successfully!\n"
                                      f"Offer number: {result['offer_number']}\n"
                                      f"File saved to: {result['file_path']}")
            
            # Navigate back to main menu
            if self.nav_manager:
                self.nav_manager.show_frame('main_menu')
        else:
            # Error message was already shown by the service
            pass
