# -*- coding: utf-8 -*-
"""Vista "Compartidos conmigo" (Shared File). Igual que SharedFileScreen.kt del
móvil: buscador (nombre o propietario), icono por tipo, avatar del
propietario, permiso en palabras ("Puede editar", "Solo lectura") y hoja de
detalles. Además: compartir un archivo y revocar."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import ERROR, SECONDARY_CONTAINER, ON_SECONDARY_CONTAINER, ON_SURFACE_VARIANT, font
from ..widgets import (primary_button, icon_button, chip, SearchBar, StatePanel, list_item, avatar,
                       tipo_archivo, DetailsDialog, ConfirmDialog)
from ..utils import run_async, describir
from .compartir_dialog import CompartirDialog


def describir_permiso(permiso_unix):
    """"rw-" -> "Puede editar": el permiso Unix en algo que entienda cualquiera."""
    if "w" in permiso_unix:
        return "Puede editar"
    if "r" in permiso_unix:
        return "Solo lectura"
    if "x" in permiso_unix:
        return "Solo ejecución"
    return "Sin acceso"


class SharedFilesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.shared
        self.datos = None

        self.busqueda = SearchBar(self, "Buscar en Compartidos", lambda _q: self._pintar())
        self.busqueda.pack(fill="x", pady=(0, 8))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 6))
        if self.repo.simulado:
            chip(bar, "Simulado · el servicio aún no existe en el backend", "warn").pack(side="left")
        else:
            chip(bar, "Shared File · conectado", "ok").pack(side="left")
        icon_button(bar, "↻", self.cargar).pack(side="right")
        primary_button(bar, "Compartir un archivo", self._compartir, width=190, height=36).pack(side="right", padx=8)

        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self.cargar()

    def cargar(self):
        self.panel.loading()

        def ok(datos):
            self.datos = datos
            self._pintar()

        run_async(self, self.repo.compartidos_conmigo, ok,
                  lambda e: self.panel.error(describir(e), self.cargar))

    def _pintar(self):
        if self.datos is None:
            return
        q = self.busqueda.value.strip().lower()
        visibles = [r for r in self.datos if q in r.nombre_archivo.lower() or q in r.propietario.lower()]
        if not self.datos:
            self.panel.empty("Cuando alguien comparta un archivo o carpeta contigo, aparecerá aquí.",
                             "👥", "Nada compartido todavía")
            return
        if not visibles:
            self.panel.empty(f"Nada coincide con \"{q}\" en el nombre ni en el propietario.",
                             "🔍", "Sin resultados")
            return
        self.panel.clear()
        for r in visibles:
            def propietario(box, r=r):
                fila = ctk.CTkFrame(box, fg_color="transparent")
                fila.pack(anchor="w")
                avatar(fila, r.propietario, 18).pack(side="left")
                ctk.CTkLabel(fila, text=r.propietario, font=font("body"),
                             text_color=ON_SURFACE_VARIANT).pack(side="left", padx=6)

            _row, tr = list_item(self.panel, None, r.nombre_archivo, propietario,
                                 tipo=tipo_archivo(r.nombre_archivo), on_click=lambda r=r: self._detalles(r))
            ctk.CTkLabel(tr, text=f"  {describir_permiso(r.permiso_unix)}  ", fg_color=SECONDARY_CONTAINER,
                         text_color=ON_SECONDARY_CONTAINER, corner_radius=8, height=24,
                         font=font("label_small")).pack()

    def _detalles(self, r):
        DetailsDialog(self, r.nombre_archivo, tipo_archivo(r.nombre_archivo), [
            ("Propietario", r.propietario),
            ("Tu acceso", f"{describir_permiso(r.permiso_unix)} ({r.permiso_unix})"),
            ("Identificador", r.archivo_id),
        ], [("Quitar de mis compartidos", lambda: self._revocar(r), ERROR)])

    def _revocar(self, r):
        def quitar():
            run_async(self, lambda: self.repo.revocar(r.compartido_id), lambda _x: self.cargar(),
                      lambda e: messagebox.showerror("Error", describir(e)))
        ConfirmDialog(self, "👥", "¿Quitar de tus compartidos?",
                      f"Dejarás de ver «{r.nombre_archivo}».", "Quitar", quitar)

    def _compartir(self):
        CompartirDialog(self, self.app.api, on_done=self.cargar)
