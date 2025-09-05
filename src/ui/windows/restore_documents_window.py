"""Window for restoring Word documents from an existing database file."""
from tkinter import *
from tkinter import filedialog
import threading
import tkinter.messagebox
import os

from src.services.restore_documents_service import restore_from_database

class RestoreDocumentsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.top = None
        self.db_path_var = StringVar()
        self.output_path_var = StringVar()
        self.progress_var = StringVar()
        self.restore_thread = None

    def open(self):
        if self.top and self.top.winfo_exists():
            try:
                self.top.lift()
                return
            except Exception:
                pass

        # Build window fresh
        self.top = Toplevel(self.parent)
        self.top.title("Przywróć dokumenty")
        self.top.geometry("760x520")
        self.top.resizable(False, False)
        self.top.grab_set()
        self.top.configure(bg='#f8f9fa')

        Label(self.top, text="Przywracanie dokumentów z bazy danych", font=("Arial", 16, "bold"), bg='#f8f9fa').pack(pady=20)

        form = Frame(self.top, bg='white', relief=RIDGE, bd=2)
        form.pack(fill=BOTH, expand=True, padx=20, pady=10)

        # DB path (read-only display + browse)
        Label(form, text="Plik bazy (.db):", font=("Arial", 12), bg='white').grid(row=0, column=0, sticky=W, padx=10, pady=12)
        db_disp = Entry(form, textvariable=self.db_path_var, width=54, state='readonly')
        db_disp.grid(row=0, column=1, padx=10, pady=12, sticky=W)
        Button(form, text="Przeglądaj...", command=self._choose_db).grid(row=0, column=2, padx=5, pady=12)

        # Output path (read-only display + browse)
        Label(form, text="Folder docelowy:", font=("Arial", 12), bg='white').grid(row=1, column=0, sticky=W, padx=10, pady=12)
        out_disp = Entry(form, textvariable=self.output_path_var, width=54, state='readonly')
        out_disp.grid(row=1, column=1, padx=10, pady=12, sticky=W)
        Button(form, text="Przeglądaj...", command=self._choose_output).grid(row=1, column=2, padx=5, pady=12)

        # Progress area
        Label(form, text="Postęp:", font=("Arial", 12), bg='white').grid(row=2, column=0, sticky=NW, padx=10, pady=12)
        self.progress_box = Text(form, width=50, height=10, state=DISABLED)
        self.progress_box.grid(row=2, column=1, padx=10, pady=12, sticky=W)

        # Action buttons
        btns = Frame(self.top, bg='#f8f9fa')
        btns.pack(fill=X, padx=20, pady=10)
        self.restore_btn = Button(btns, text="Przywracaj", font=("Arial", 14, "bold"), command=self._start_restore, cursor='hand2')
        self.restore_btn.pack(side=LEFT)
        Button(btns, text="Zamknij", font=("Arial", 12), command=self.top.destroy).pack(side=RIGHT)

    def _choose_db(self):
        path = filedialog.askopenfilename(title="Wybierz plik bazy", filetypes=[("SQLite DB", "*.db"), ("Wszystkie pliki", "*.*")])
        if path:
            self.db_path_var.set(path)

    def _choose_output(self):
        path = filedialog.askdirectory(title="Wybierz folder docelowy")
        if path:
            self.output_path_var.set(path)

    def _append_progress(self, msg: str):
        try:
            self.progress_box.configure(state=NORMAL)
            self.progress_box.insert(END, msg + "\n")
            self.progress_box.see(END)
            self.progress_box.configure(state=DISABLED)
        except Exception:
            pass

    def _start_restore(self):
        # Prevent duplicate runs
        if self.restore_thread and self.restore_thread.is_alive():
            tkinter.messagebox.showinfo("Trwa", "Proces przywracania już trwa")
            return

        db_path = self.db_path_var.get().strip()
        out_path = self.output_path_var.get().strip()

        if not db_path or not os.path.isfile(db_path):
            tkinter.messagebox.showerror("Błąd", "Nieprawidłowa ścieżka do bazy danych")
            return
        if not out_path:
            tkinter.messagebox.showerror("Błąd", "Wybierz folder docelowy")
            return

        self._append_progress("Start przywracania...")
        self.restore_btn.config(state=DISABLED)

        # Launch background thread
        self.restore_thread = threading.Thread(
            target=self._run_restore,
            args=(db_path, out_path),
            daemon=True
        )
        self.restore_thread.start()

    def _run_restore(self, db_path: str, out_path: str):
        try:
            report = restore_from_database(db_path, out_path, progress_cb=lambda m: self.parent.after(0, self._append_progress, m))
            def _finish():
                self._append_progress("\n" + report.summary_text())
                self.restore_btn.config(state=NORMAL)
                tkinter.messagebox.showinfo("Zakończono", report.summary_text())
            self.parent.after(0, _finish)
        except Exception as e:
            def _err():
                self.restore_btn.config(state=NORMAL)
                tkinter.messagebox.showerror("Błąd", f"Nie udało się przywrócić dokumentów: {e}")
            self.parent.after(0, _err)
