import sqlite3
import tkinter.messagebox
from config import DATABASE_PATH

def get_clients_from_db():
    """Fetch all clients from the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients ORDER BY CompanyName")
        clients = cursor.fetchall()
        conn.close()
        return clients
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return []

def get_suppliers_from_db():
    """Fetch all suppliers from the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2 FROM Suppliers ORDER BY CompanyName")
        suppliers = cursor.fetchall()
        conn.close()
        return suppliers
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return []

def get_next_offer_number():
    """Get the next offer order number from the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(OfferOrderNumber) FROM Offers")
        result = cursor.fetchone()[0]
        conn.close()
        
        # If no offers exist, start with 1, otherwise increment
        return 1 if result is None else result + 1
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return 1

def save_offer_to_db(offer_order_number, offer_file_path):
    """Save offer information to the database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Offers (OfferOrderNumber, OfferFilePath) VALUES (?, ?)", 
                      (offer_order_number, offer_file_path))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error saving offer to database: {e}")
        return False

def validate_nip(nip):
    """Validate NIP format and uniqueness"""
    # Check if NIP has exactly 10 digits
    if not nip.isdigit() or len(nip) != 10:
        return False, "NIP musi składać się z dokładnie 10 cyfr"
    
    # Check if NIP already exists in database
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Nip = ?", (nip,))
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            return False, "Klient z tym NIP już istnieje w bazie"
        
        return True, "NIP jest prawidłowy"
    except sqlite3.Error as e:
        return False, f"Błąd sprawdzania NIP: {e}"

def validate_alias(alias):
    """Validate alias format"""
    if "_" in alias:
        return False, "Alias nie może zawierać znaku '_'"
    
    if not alias.strip():
        return False, "Alias nie może być pusty"
    
    return True, "Alias jest prawidłowy"

def add_client_to_db(nip, company_name, address_p1, address_p2, alias):
    """Add a new client to the database"""
    try:
        # Validate NIP
        nip_valid, nip_message = validate_nip(nip)
        if not nip_valid:
            return False, nip_message
        
        # Validate alias
        alias_valid, alias_message = validate_alias(alias)
        if not alias_valid:
            return False, alias_message
        
        # Insert client
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Clients (Nip, CompanyName, AddressP1, AddressP2, Alias) 
            VALUES (?, ?, ?, ?, ?)
        """, (nip, company_name, address_p1, address_p2, alias))
        conn.commit()
        conn.close()
        
        return True, "Klient został pomyślnie dodany do bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas dodawania klienta: {e}"

def validate_supplier_nip(nip):
    """Validate NIP format and uniqueness for suppliers"""
    # Check if NIP has exactly 10 digits
    if not nip.isdigit() or len(nip) != 10:
        return False, "NIP musi składać się z dokładnie 10 cyfr"
    
    # Check if NIP already exists in supplier database
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Suppliers WHERE Nip = ?", (nip,))
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            return False, "Dostawca z tym NIP już istnieje w bazie"
        
        return True, "NIP jest prawidłowy"
    except sqlite3.Error as e:
        return False, f"Błąd sprawdzania NIP: {e}"

def add_supplier_to_db(nip, company_name, address_p1, address_p2):
    """Add a new supplier to the database"""
    try:
        # Validate NIP
        nip_valid, nip_message = validate_supplier_nip(nip)
        if not nip_valid:
            return False, nip_message
        
        # Insert supplier
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Suppliers (Nip, CompanyName, AddressP1, AddressP2) 
            VALUES (?, ?, ?, ?)
        """, (nip, company_name, address_p1, address_p2))
        conn.commit()
        conn.close()
        
        return True, "Dostawca został pomyślnie dodany do bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas dodawania dostawcy: {e}"

def get_client_by_nip(nip):
    """Get client data by NIP"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients WHERE Nip = ?", (nip,))
        client = cursor.fetchone()
        conn.close()
        return client
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return None

def update_client_in_db(nip, company_name, address_p1, address_p2, alias):
    """Update client data (NIP cannot be changed)"""
    try:
        # Validate alias (but allow current alias to remain the same)
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if alias is used by another client
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Alias = ? AND Nip != ?", (alias, nip))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return False, "Alias już istnieje dla innego klienta"
        
        # Validate alias format
        alias_valid, alias_message = validate_alias(alias)
        if not alias_valid:
            conn.close()
            return False, alias_message
        
        # Update client
        cursor.execute("""
            UPDATE Clients 
            SET CompanyName = ?, AddressP1 = ?, AddressP2 = ?, Alias = ?
            WHERE Nip = ?
        """, (company_name, address_p1, address_p2, alias, nip))
        conn.commit()
        conn.close()
        
        return True, "Dane klienta zostały zaktualizowane"
    except sqlite3.Error as e:
        return False, f"Błąd podczas aktualizacji klienta: {e}"

def delete_client_from_db(nip):
    """Delete client from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # First get client's alias
        cursor.execute("SELECT Alias FROM Clients WHERE Nip = ?", (nip,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, "Klient nie został znaleziony"
        
        client_alias = result[0]
        
        # Check if client has any offers by looking for alias in file path
        cursor.execute("SELECT COUNT(*) FROM Offers WHERE OfferFilePath LIKE ?", (f"%_{client_alias}.docx",))
        offer_count = cursor.fetchone()[0]
        
        if offer_count > 0:
            conn.close()
            return False, f"Nie można usunąć klienta - istnieją {offer_count} ofert(y) dla tego klienta"
        
        # Delete client
        cursor.execute("DELETE FROM Clients WHERE Nip = ?", (nip,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Klient nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Klient został usunięty z bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania klienta: {e}"

def get_supplier_by_nip(nip):
    """Get supplier data by NIP"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2 FROM Suppliers WHERE Nip = ?", (nip,))
        supplier = cursor.fetchone()
        conn.close()
        return supplier
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return None

def update_supplier_in_db(nip, company_name, address_p1, address_p2):
    """Update supplier data (NIP cannot be changed)"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Update supplier
        cursor.execute("""
            UPDATE Suppliers 
            SET CompanyName = ?, AddressP1 = ?, AddressP2 = ?
            WHERE Nip = ?
        """, (company_name, address_p1, address_p2, nip))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Dostawca nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Dane dostawcy zostały zaktualizowane"
    except sqlite3.Error as e:
        return False, f"Błąd podczas aktualizacji dostawcy: {e}"

def delete_supplier_from_db(nip):
    """Delete supplier from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # For suppliers, we could check if they have any related data
        # For now, we'll allow deletion (suppliers don't appear in offer file names)
        
        # Delete supplier
        cursor.execute("DELETE FROM Suppliers WHERE Nip = ?", (nip,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Dostawca nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Dostawca został usunięty z bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania dostawcy: {e}"
