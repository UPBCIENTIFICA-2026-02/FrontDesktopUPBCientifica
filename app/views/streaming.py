# -*- coding: utf-8 -*-
"""Vista de Streaming. Dos pestañas:
  - Catálogo del servidor: como StreamingScreen.kt del móvil (▶ título, minutos),
    con búsqueda, paginación y "Reproducir" (pide la sesión y abre el manifest).
  - Videos locales: reproduce videos de una carpeta con el reproductor del sistema.
"""

import os
import webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import ON_SURFACE_VARIANT, BACKGROUND
from ..widgets import (section_title, primary_button, ghost_button, tonal_button, chip,
                       StatePanel, list_item)
from ..utils import human_size, open_with_system, run_async, describir
from ..config import VID_EXT, save_config


class StreamingView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.streaming
        self.pagina = 0
        self.criterio = ""

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))
        section_title(top, "Streaming", "Catálogo de video del servidor y videos locales.").pack(side="left")
        if self.repo.simulado:
            chip(top, "Catálogo simulado", "warn").pack(side="right", anchor="n")
        else:
            chip(top, f"node-media · {app.api.conf.url_media}", "ok").pack(side="right", anchor="n")

        tabs = ctk.CTkTabview(self, fg_color=BACKGROUND, corner_radius=12, anchor="w")
        tabs.pack(fill="both", expand=True)
        self._catalogo_tab(tabs.add("Catálogo del servidor"))
        self._local_tab(tabs.add("Videos locales"))

    # ======================= Catálogo del servidor ===========================
    def _catalogo_tab(self, tab):
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(4, 10))
        self.e_buscar = ctk.CTkEntry(bar, width=320, height=38, placeholder_text="Buscar por título…")
        self.e_buscar.pack(side="left")
        self.e_buscar.bind("<Return>", lambda _e: self._buscar())
        primary_button(bar, "Buscar", self._buscar, width=100, height=38).pack(side="left", padx=8)
        ghost_button(bar, "Ver todo", self._limpiar, width=100, height=38).pack(side="left")

        self.panel = StatePanel(tab)
        self.panel.pack(fill="both", expand=True)

        pag = ctk.CTkFrame(tab, fg_color="transparent")
        pag.pack(fill="x", pady=(8, 0))
        self.btn_prev = ghost_button(pag, "← Anterior", lambda: self._ir(-1), width=120, height=34)
        self.btn_prev.pack(side="left")
        self.l_pag = ctk.CTkLabel(pag, text="", text_color=ON_SURFACE_VARIANT)
        self.l_pag.pack(side="left", padx=12)
        self.btn_next = ghost_button(pag, "Siguiente →", lambda: self._ir(1), width=120, height=34)
        self.btn_next.pack(side="left")
        self.cargar()

    def cargar(self):
        self.panel.loading("Cargando catálogo…")
        if self.criterio:
            self.l_pag.configure(text=f"Resultados para «{self.criterio}»")
            fn = lambda: self.repo.buscar(self.criterio)
        else:
            self.l_pag.configure(text=f"Página {self.pagina + 1}")
            fn = lambda: self.repo.catalogo(self.pagina)
        busqueda = bool(self.criterio)
        self.btn_prev.configure(state="disabled" if busqueda or self.pagina == 0 else "normal")
        self.btn_next.configure(state="disabled" if busqueda else "normal")
        run_async(self, fn, self._pintar, lambda e: self.panel.error(describir(e), self.cargar))

    def _pintar(self, contenidos):
        if not contenidos:
            self.panel.empty("No hay videos para mostrar.")
            if not self.criterio:
                self.btn_next.configure(state="disabled")
            return
        self.panel.clear()
        for c in contenidos:
            _row, tr = list_item(self.panel, "▶", c.titulo, c.duracion_texto)
            tonal_button(tr, "Reproducir", lambda c=c: self._reproducir(c), width=120, height=34).pack(side="right")

    def _buscar(self):
        self.criterio = self.e_buscar.get().strip()
        self.pagina = 0
        self.cargar()

    def _limpiar(self):
        self.e_buscar.delete(0, "end")
        self.criterio = ""
        self.pagina = 0
        self.cargar()

    def _ir(self, delta):
        self.pagina = max(0, self.pagina + delta)
        self.cargar()

    def _reproducir(self, c):
        def ok(sesion):
            if self.repo.simulado:
                messagebox.showinfo(
                    "Reproducir (simulado)",
                    f"«{c.titulo}»\n\nSesión: {sesion.sesion_id}\nManifest: {sesion.manifest_url}\n\n"
                    "Con node-media conectado, el video se abrirá en tu navegador.")
                return
            if not sesion.manifest_url:
                messagebox.showerror("Streaming", "El servidor no devolvió la URL del video.")
                return
            webbrowser.open(sesion.manifest_url)

        run_async(self, lambda: self.repo.reproducir(c.id), ok,
                  lambda e: messagebox.showerror("No se pudo reproducir", describir(e)))

    # ============================ Videos locales =============================
    def _local_tab(self, tab):
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(4, 10))
        primary_button(bar, "Elegir carpeta de videos", self._pick, width=210).pack(side="left")
        self.info = ctk.CTkLabel(bar, text="", text_color=ON_SURFACE_VARIANT)
        self.info.pack(side="left", padx=12)

        self.listing = StatePanel(tab)
        self.listing.pack(fill="both", expand=True)

        folder = self.app.config.get("video_folder")
        if folder and os.path.isdir(folder):
            self._load(folder)
        else:
            self.listing.empty("Elige una carpeta con videos.")

    def _pick(self):
        p = filedialog.askdirectory(title="Carpeta con videos")
        if p:
            self.app.config["video_folder"] = p
            save_config(self.app.config)
            self._load(p)

    def _load(self, folder):
        vids = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(VID_EXT)]
        self.info.configure(text=f"{len(vids)} video(s) en {os.path.basename(folder)}")
        if not vids:
            self.listing.empty("La carpeta no contiene videos.")
            return
        self.listing.clear()
        for name in vids:
            full = os.path.join(folder, name)
            _row, tr = list_item(self.listing, "🎞", name, human_size(os.path.getsize(full)))
            tonal_button(tr, "Reproducir", lambda p=full: open_with_system(p), width=120, height=34).pack(side="right")
