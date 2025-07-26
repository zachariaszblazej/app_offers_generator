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
