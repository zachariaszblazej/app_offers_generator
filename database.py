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
