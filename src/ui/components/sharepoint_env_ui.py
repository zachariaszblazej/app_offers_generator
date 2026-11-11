"""Komponenty UI dla środowiska SharePoint (DEV/PROD): oznaczenie środowiska oraz sekcja ustawień."""
import queue
import threading
import tkinter.messagebox
from tkinter import *
from tkinter import ttk

from src.integrations.sharepoint import DEV, PROD, environment_manager, get_environment
from src.integrations.sharepoint.connection_test import run_readonly_test

ENV_COLORS = {DEV: "#2e7d32", PROD: "#c62828"}

# Tylko jeden test naraz (logowanie interaktywne blokuje przełączanie środowiska).
_test_running = threading.Event()


class EnvironmentBadge(Label):
    """Etykieta z aktywnym środowiskiem; aktualizuje się natychmiast po przełączeniu."""

    def __init__(self, parent, font=("Arial", 12, "bold"), **kwargs):
        super().__init__(parent, font=font, fg="white", padx=12, pady=4, **kwargs)
        self._refresh(environment_manager.get_active())
        environment_manager.subscribe(self._on_change)
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _on_change(self, env):
        if self.winfo_exists():
            self._refresh(env)

    def _on_destroy(self, event):
        if event.widget is self:
            environment_manager.unsubscribe(self._on_change)

    def _refresh(self, env):
        self.config(text=f"SharePoint: {env.name}", bg=ENV_COLORS.get(env.name, "#555555"))


class SharePointSection(Frame):
    """Sekcja ustawień: przełączanie DEV/PROD i test połączenia (tylko odczyt)."""

    def __init__(self, parent):
        super().__init__(parent, bg="#f0f0f0")
        self._queue = queue.Queue()
        self._env_var = StringVar(value=environment_manager.get_active().name)
        self._build()
        environment_manager.subscribe(self._on_env_change)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._poll()

    def _build(self):
        Label(self, text="SharePoint", font=("Arial", 16, "bold"),
              bg="#f0f0f0", fg="#333333").pack(anchor=W, pady=(20, 20))

        box = Frame(self, bg="#ffffff", relief=RIDGE, bd=2)
        box.pack(fill=X, pady=(0, 30))
        inner = Frame(box, bg="#ffffff")
        inner.pack(fill=X, padx=20, pady=20)

        Label(inner, text="Środowisko SharePoint:", font=("Arial", 11, "bold"),
              bg="#ffffff").pack(anchor=W)
        Label(inner, text="Aplikacja zawsze startuje w DEV. Wybór PROD obowiązuje tylko do zamknięcia aplikacji.",
              font=("Arial", 9), bg="#ffffff", fg="#666666").pack(anchor=W, pady=(0, 8))

        row = Frame(inner, bg="#ffffff")
        row.pack(fill=X)
        self.badge = EnvironmentBadge(row, font=("Arial", 14, "bold"))
        self.badge.pack(side=LEFT, padx=(0, 20))
        self.radios = []
        for name in (DEV, PROD):
            rb = Radiobutton(row, text=name, value=name, variable=self._env_var,
                             font=("Arial", 12), bg="#ffffff", cursor="hand2",
                             command=self._on_select)
            rb.pack(side=LEFT, padx=10)
            self.radios.append(rb)

        self.site_label = Label(inner, text="", font=("Arial", 10), bg="#ffffff", fg="#333333")
        self.site_label.pack(anchor=W, pady=(8, 10))

        self.test_btn = Button(inner, text="Test połączenia (tylko odczyt)",
                               font=("Arial", 11), fg="black", padx=15, pady=6,
                               command=self._start_test, cursor="hand2")
        self.test_btn.pack(anchor=W)

        text_frame = Frame(inner, bg="#ffffff")
        text_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        self.report = Text(text_frame, height=22, width=140, wrap=NONE,
                           font=("Consolas", 9), state=DISABLED)
        yscroll = ttk.Scrollbar(text_frame, orient=VERTICAL, command=self.report.yview)
        xscroll = ttk.Scrollbar(text_frame, orient=HORIZONTAL, command=self.report.xview)
        self.report.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side=RIGHT, fill=Y)
        xscroll.pack(side=BOTTOM, fill=X)
        self.report.pack(side=LEFT, fill=BOTH, expand=True)

        self._update_site_label()
        self._update_controls()

    def _update_site_label(self):
        env = environment_manager.get_active()
        self.site_label.config(text=f"Aktywna witryna: {env.site_url}")

    def _update_controls(self):
        state = DISABLED if _test_running.is_set() else NORMAL
        for rb in self.radios:
            rb.config(state=state)
        self.test_btn.config(state=state)

    def _on_env_change(self, env):
        if self.winfo_exists():
            self._env_var.set(env.name)
            self._update_site_label()

    def _on_destroy(self, event):
        if event.widget is self:
            environment_manager.unsubscribe(self._on_env_change)

    def _on_select(self):
        selected = self._env_var.get()
        active = environment_manager.get_active()
        if selected == active.name:
            return
        if _test_running.is_set():
            self._env_var.set(active.name)
            return

        if selected == PROD:
            prod = get_environment(PROD)
            confirmed = tkinter.messagebox.askokcancel(
                "UWAGA - środowisko PRODUKCYJNE",
                "Przełączasz aplikację na środowisko PROD (produkcyjne).\n\n"
                f"Witryna: {prod.site_url}\n\n"
                "Kolejne operacje SharePoint będą dotyczyć danych produkcyjnych.\n"
                "Aplikacja po ponownym uruchomieniu wróci do DEV.\n\n"
                "Czy na pewno przełączyć na PROD?",
                icon="warning",
                default="cancel",
            )
            if not confirmed:
                self._env_var.set(active.name)
                return
        environment_manager.set_active(selected)

    def _start_test(self):
        if _test_running.is_set():
            return
        env = environment_manager.get_active()
        _test_running.set()
        self._update_controls()
        self._clear_report()
        self._append(f"Rozpoczynam test odczytowy dla środowiska {env.name}...")

        def worker():
            try:
                run_readonly_test(env, log=lambda line: self._queue.put(("line", line)))
            finally:
                _test_running.clear()

        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                _, line = self._queue.get_nowait()
                self._append(line)
        except queue.Empty:
            pass
        self._update_controls()
        self.after(150, self._poll)

    def _clear_report(self):
        self.report.config(state=NORMAL)
        self.report.delete("1.0", END)
        self.report.config(state=DISABLED)

    def _append(self, line):
        self.report.config(state=NORMAL)
        self.report.insert(END, line + "\n")
        self.report.see(END)
        self.report.config(state=DISABLED)
