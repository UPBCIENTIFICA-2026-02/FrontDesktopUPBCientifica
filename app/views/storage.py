# -*- coding: utf-8 -*-
"""Vista "Mis archivos" (Distributed Storage). Como StorageScreen.kt del móvil
(📁/📄, tamaño legible y versión), y además con lo que el móvil aún no tiene en
pantalla: navegar carpetas, subir, descargar, compartir y eliminar."""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import ON_SURFACE_VARIANT, ERROR, font
from ..widgets import (section_title, primary_button, ghost_button, text_button, chip,
                       StatePanel, list_item)
from ..utils import human_size, open_with_system, run_async, describir
from ..config import HOME_DIR, DOWNLOAD_DIR
from ..data.storage import RAIZ
from .compartir_dialog import CompartirDialog


class StorageView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.storage
        self.pila = [(RAIZ, "Mis archivos")]      # migas de pan: (id, nombre)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        section_title(top, "Mis archivos",
                      "Tus archivos en Distributed Storage, con versionado transparente.").pack(side="left")
        if self.repo.simulado:
            chip(top, "Simulado · Home local", "warn").pack(side="right", anchor="n")
        else:
            chip(top, f"node-repository · {app.api.conf.url_storage}", "ok").pack(side="right", anchor="n")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        primary_button(bar, "⬆  Subir archivo(s)", self._upload, width=170).pack(side="left")
        ghost_button(bar, "Actualizar", self.cargar, width=110).pack(side="left", padx=8)
        if self.repo.simulado:
            ghost_button(bar, "Abrir carpeta Home", lambda: open_with_system(str(HOME_DIR)),
                         width=170).pack(side="left")

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 6))
        self.btn_up = text_button(nav, "← Carpeta anterior", self._subir_nivel, width=150)
        self.btn_up.pack(side="left")
        self.l_ruta = ctk.CTkLabel(nav, text="", text_color=ON_SURFACE_VARIANT, font=font("body"))
        self.l_ruta.pack(side="left", padx=8)

        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self.cargar()

    # --- Carga (UiState: Loading -> Success | Error) -------------------------
    @property
    def dir_actual(self):
        return self.pila[-1][0]

    def cargar(self):
        self.l_ruta.configure(text=" / ".join(n for _, n in self.pila))
        self.btn_up.configure(state="normal" if len(self.pila) > 1 else "disabled")
        self.panel.loading()
        run_async(self, lambda: self.repo.listar(self.dir_actual), self._pintar,
                  lambda e: self.panel.error(describir(e), self.cargar))

    def _pintar(self, items):
        if not items:
            self.panel.empty("Esta carpeta está vacía. Sube archivos para comenzar.")
            return
        self.panel.clear()
        for a in items:
            if a.es_directorio:
                row, tr = list_item(self.panel, "📁", a.nombre, "Carpeta")
                text_button(tr, "Abrir", lambda a=a: self._entrar(a), width=70).pack(side="right")
                for w in [row] + list(row.winfo_children()):
                    w.bind("<Double-Button-1>", lambda _e, a=a: self._entrar(a))
            else:
                row, tr = list_item(self.panel, "📄", a.nombre,
                                    f"{human_size(a.tamano_bytes)} · v{a.version}")
                text_button(tr, "Eliminar", lambda a=a: self._eliminar(a), width=80,
                            color=ERROR).pack(side="right")
                text_button(tr, "Compartir", lambda a=a: self._compartir(a), width=90).pack(side="right")
                text_button(tr, "Descargar", lambda a=a: self._descargar(a), width=90).pack(side="right")
                if self.repo.simulado:
                    text_button(tr, "Abrir", lambda a=a: open_with_system(str(self.repo.ruta_local(a.id))),
                                width=60).pack(side="right")

    # --- Navegación ---------------------------------------------------------
    def _entrar(self, carpeta):
        self.pila.append((carpeta.id, carpeta.nombre))
        self.cargar()

    def _subir_nivel(self):
        if len(self.pila) > 1:
            self.pila.pop()
            self.cargar()

    # --- Acciones -----------------------------------------------------------
    def _upload(self):
        paths = filedialog.askopenfilenames(title="Seleccionar archivos para subir")
        if not paths:
            return
        destino = self.dir_actual
        self.panel.loading(f"Subiendo {len(paths)} archivo(s)…")

        def subir_todos():
            errores = []
            for p in paths:
                try:
                    self.repo.subir(p, destino)
                except Exception as e:  # noqa: BLE001
                    errores.append(f"{os.path.basename(p)}: {describir(e)}")
            return len(paths) - len(errores), errores

        def hecho(res):
            ok, errores = res
            self.cargar()
            if errores:
                messagebox.showerror("Error al subir", "\n".join(errores))
            elif ok:
                messagebox.showinfo("Listo", f"{ok} archivo(s) subido(s).")

        run_async(self, subir_todos, hecho, lambda e: self.panel.error(describir(e), self.cargar))

    def _descargar(self, a):
        destino = filedialog.asksaveasfilename(
            title="Guardar como", initialfile=a.nombre,
            initialdir=str(DOWNLOAD_DIR) if DOWNLOAD_DIR.exists() else None)
        if not destino:
            return
        run_async(self, lambda: self.repo.descargar(a.id, destino),
                  lambda p: self._descargado(p),
                  lambda e: messagebox.showerror("Error al descargar", describir(e)))

    def _descargado(self, path):
        if messagebox.askyesno("Descarga completa", f"Guardado en:\n{path}\n\n¿Abrir el archivo?"):
            open_with_system(path)

    def _eliminar(self, a):
        if not messagebox.askyesno("Eliminar", f"¿Eliminar «{a.nombre}»? Esta acción no se puede deshacer."):
            return
        run_async(self, lambda: self.repo.eliminar(a.id), lambda _r: self.cargar(),
                  lambda e: messagebox.showerror("Error al eliminar", describir(e)))

    def _compartir(self, a):
        CompartirDialog(self, self.app.api, archivo_id=a.id, nombre=a.nombre)
