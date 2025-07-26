#!/usr/bin/env python3
"""
Launcher for Offer Generator Application
Simple startup screen for the application
"""

import sys
import subprocess
from tkinter import *
from tkinter import ttk
import tkinter.messagebox

class AppLauncher:
    def __init__(self):
        self.root = Tk()
        self.root.title("Generator Ofert")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        self.create_ui()
    
    def create_ui(self):
        """Create the launcher UI"""
        # Title
        title_label = Label(self.root, text="Generator Ofert", 
                           font=("Arial", 20, "bold"),
                           fg='#2c3e50')
        title_label.pack(pady=40)
        
        subtitle_label = Label(self.root, text="System tworzenia ofert handlowych", 
                              font=("Arial", 12),
                              fg='#34495e')
        subtitle_label.pack(pady=10)
        
        # Buttons frame
        buttons_frame = Frame(self.root)
        buttons_frame.pack(pady=40)
        
        # Launch application button
        launch_btn = Button(buttons_frame, 
                           text="🚀 Uruchom aplikację", 
                           font=("Arial", 14, "bold"),
                           bg='#27ae60', fg='white',
                           padx=30, pady=15,
                           command=self.launch_application,
                           cursor='hand2')
        launch_btn.pack(pady=15)
        
        # Exit button
        exit_btn = Button(buttons_frame, 
                         text="Zamknij", 
                         font=("Arial", 12),
                         bg='#e74c3c', fg='white',
                         padx=20, pady=8,
                         command=self.root.destroy,
                         cursor='hand2')
        exit_btn.pack(pady=10)
        
        # Version info
        version_label = Label(self.root, 
                             text="Wersja 2.0 - Zrefaktorowana z nawigacją",
                             font=("Arial", 9),
                             fg='#7f8c8d')
        version_label.pack(side=BOTTOM, pady=15)
    
    def launch_application(self):
        """Launch the main application"""
        try:
            self.root.destroy()
            subprocess.run([sys.executable, "main.py"], check=True)
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się uruchomić aplikacji: {e}")
    
    def run(self):
        """Start the launcher"""
        self.root.mainloop()

if __name__ == "__main__":
    launcher = AppLauncher()
    launcher.run()
