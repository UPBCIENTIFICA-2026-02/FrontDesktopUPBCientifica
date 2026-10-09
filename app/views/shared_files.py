# -*- coding: utf-8 -*-
"""Vista "Compartidos conmigo" (Shared File). Como SharedFileScreen.kt del móvil:
🔗 nombre, "De: propietario · Permiso: r--". Además permite compartir un
archivo y revocar un recurso compartido."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import ERROR
from ..widgets import section_title, primary_button, ghost_button, text_button, chip, StatePanel, list_item
from ..utils import run_async, describir
from .compartir_dialog import CompartirDialog


class SharedFilesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.shared

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        section_title(top, "Compartidos conmigo",
                      "Archivos y carpetas que otros usuarios o grupos compartieron contigo.").pack(side="left")
        if self.repo.simulado:
            chip(top, "Simulado · el servicio aún no existe en el backend", "warn").pack(side="right", anchor="n")
        else:
            chip(top, "Shared File · conectado", "ok").pack(side="right", anchor="n")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        primary_button(bar, "🔗  Compartir un archivo", self._compartir, width=200).pack(side="left")
        ghost_button(bar, "Actualizar", self.cargar, width=110).pack(side="left", padx=8)

        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self.cargar()

    def cargar(self):
        self.panel.loading()
        run_async(self, self.repo.compartidos_conmigo, self._pintar,
                  lambda e: self.panel.error(describir(e), self.cargar))

    def _pintar(self, recursos):
        if not recursos:
            self.panel.empty("Nadie ha compartido archivos contigo todavía.")
            return
        self.panel.clear()
        for r in recursos:
            _row, tr = list_item(self.panel, "🔗", r.nombre_archivo,
                                 f"De: {r.propietario} · Permiso: {r.permiso_unix}")
            text_button(tr, "Revocar", lambda r=r: self._revocar(r), width=80, color=ERROR).pack(side="right")

    def _revocar(self, r):
        if not messagebox.askyesno("Revocar", f"¿Quitar «{r.nombre_archivo}» de tus compartidos?"):
            return
        run_async(self, lambda: self.repo.revocar(r.compartido_id), lambda _x: self.cargar(),
                  lambda e: messagebox.showerror("Error", describir(e)))

    def _compartir(self):
        CompartirDialog(self, self.app.api, on_done=self.cargar)
