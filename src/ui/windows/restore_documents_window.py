"""Window for restoring Word documents from an existing database file."""
from tkinter import *
from tkinter import filedialog
import threading
import queue
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
        # Counters (init earlier so safe in progress callback)
        self._offers_done = 0
        self._wz_done = 0
        self.status_var = None  # assigned in open()
        # Queue for thread-safe progress passing
        self._progress_queue = queue.Queue()
        self._end_line_inserted = False

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
        self.top.geometry("980x600")  # wider so browse buttons never clip
        self.top.resizable(False, False)
        self.top.grab_set()
        self.top.configure(bg='#f8f9fa')

        Label(self.top, text="Przywracanie dokumentów z bazy danych", font=("Arial", 16, "bold"), bg='#f8f9fa').pack(pady=18)

        form = Frame(self.top, bg='white', relief=RIDGE, bd=2)
        form.pack(fill=BOTH, expand=True, padx=18, pady=10)
        for col in (0,1,2):
            form.grid_columnconfigure(col, weight=1 if col==1 else 0)

        # Paths
        Label(form, text="Plik bazy (.db):", font=("Arial", 12), bg='white').grid(row=0, column=0, sticky=W, padx=8, pady=10)
        db_disp = Entry(form, textvariable=self.db_path_var, state='readonly')
        db_disp.grid(row=0, column=1, padx=8, pady=10, sticky=EW)
        Button(form, text="Przeglądaj", command=self._choose_db, width=14).grid(row=0, column=2, padx=6, pady=10, sticky=E)

        Label(form, text="Folder docelowy:", font=("Arial", 12), bg='white').grid(row=1, column=0, sticky=W, padx=8, pady=10)
        out_disp = Entry(form, textvariable=self.output_path_var, state='readonly')
        out_disp.grid(row=1, column=1, padx=8, pady=10, sticky=EW)
        Button(form, text="Przeglądaj", command=self._choose_output, width=14).grid(row=1, column=2, padx=6, pady=10, sticky=E)

        # Progress
        Label(form, text="Postęp:", font=("Arial", 12), bg='white').grid(row=2, column=0, sticky=NW, padx=8, pady=10)
        progress_wrapper = Frame(form, bg='white')
        progress_wrapper.grid(row=2, column=1, columnspan=2, padx=8, pady=10, sticky=EW)
        progress_wrapper.grid_columnconfigure(0, weight=1)
        self.progress_box = Text(progress_wrapper, height=16, state=DISABLED, wrap='word')
        self.progress_box.grid(row=0, column=0, sticky=EW)
        scroll = Scrollbar(progress_wrapper, orient=VERTICAL, command=self.progress_box.yview)
        scroll.grid(row=0, column=1, sticky=NS)
        self.progress_box.configure(yscrollcommand=scroll.set)
        # Status line
        self._offers_done = 0
        self._wz_done = 0
        self.status_var = StringVar(value="Oferty: 0 | WZ: 0")
        Label(progress_wrapper, textvariable=self.status_var, anchor=W, bg='white', fg='#555').grid(row=1, column=0, columnspan=2, sticky=EW, pady=(4,0))

        # Buttons
        btns = Frame(self.top, bg='#f8f9fa')
        btns.pack(fill=X, padx=18, pady=10)
        self.restore_btn = Button(btns, text="Przywracaj", font=("Arial", 14, "bold"), command=self._start_restore, cursor='hand2')
        self.restore_btn.pack(side=LEFT)
        Button(btns, text="Zamknij", font=("Arial", 12), command=self.top.destroy).pack(side=RIGHT)

        # start polling queue (only once per window open)
        self._poll_progress_queue()

    def _poll_progress_queue(self):
        if not self.top or not self.top.winfo_exists():
            return
        try:
            while True:
                msg = self._progress_queue.get_nowait()
                self._append_progress(msg)
        except queue.Empty:
            pass
        # Fallback: if thread finished, queue empty, final line not yet added
        if (self.restore_thread and not self.restore_thread.is_alive() and not self._end_line_inserted):
            try:
                print("[RestoreWindow DEBUG] fallback final line insertion")
            except Exception:
                pass
            self._append_progress("Zakończono przywracanie (fallback)")
            self._end_line_inserted = True
        # schedule next poll
        self.top.after(120, self._poll_progress_queue)

    def _choose_db(self):
        path = filedialog.askopenfilename(title="Wybierz plik bazy", filetypes=[("SQLite DB", "*.db"), ("Wszystkie pliki", "*.*")])
        if path:
            self.db_path_var.set(path)

    def _choose_output(self):
        path = filedialog.askdirectory(title="Wybierz folder docelowy")
        if path:
            self.output_path_var.set(path)

    def _append_progress(self, msg: str):
        # Debug + normalize
        raw_msg = msg
        msg_strip = msg.lstrip()
        try:
            # Print debug to stdout (terminal) to help diagnose prefix issues
            print(f"[RestoreWindow DEBUG] msg={raw_msg!r} offers={self._offers_done} wz={self._wz_done}")
        except Exception:
            pass
        # Detect counters (ignore leading whitespace)
        if msg_strip.startswith("Oferta:"):
            self._offers_done += 1
        elif msg_strip.startswith("WZ:"):
            self._wz_done += 1
        if self.status_var is not None:
            try:
                self.status_var.set(f"Oferty: {self._offers_done} | WZ: {self._wz_done}")
            except Exception:
                pass
        try:
            self.progress_box.configure(state=NORMAL)
            self.progress_box.insert(END, msg + "\n")
            self.progress_box.see(END)
            self.progress_box.configure(state=DISABLED)
        except Exception as e:
            print(f"[RestoreWindow] progress write error: {e}")

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

        # Clear previous log
        try:
            self.progress_box.configure(state=NORMAL)
            self.progress_box.delete(1.0, END)
            self.progress_box.configure(state=DISABLED)
        except Exception:
            pass
        # Reset counters
        self._offers_done = 0
        self._wz_done = 0
        if self.status_var:
            self.status_var.set("Oferty: 0 | WZ: 0")
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
            report = restore_from_database(
                db_path,
                out_path,
                progress_cb=lambda m: self._progress_queue.put(m)
            )
            def _finish():
                self._append_progress("--- Zakończono ---")
                self._append_progress(report.summary_text())
                # Ensure final counts displayed (in case no progress lines matched)
                if self.status_var is not None:
                    try:
                        self.status_var.set(f"Oferty: {report.offers_ok}/{report.offers_total} | WZ: {report.wz_ok}/{report.wz_total}")
                    except Exception:
                        pass
                self.restore_btn.config(state=NORMAL)
                tkinter.messagebox.showinfo("Zakończono", report.summary_text())
            self.parent.after(0, _finish)
        except Exception as e:
            def _err():
                self.restore_btn.config(state=NORMAL)
                tkinter.messagebox.showerror("Błąd", f"Nie udało się przywrócić dokumentów: {e}")
            self.parent.after(0, _err)
