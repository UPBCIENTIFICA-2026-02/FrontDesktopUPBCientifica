# -*- coding: utf-8 -*-
"""Vista de Streaming. Dos pestañas:
  - Catálogo: igual que StreamingScreen.kt del móvil, una cuadrícula de videos
    con miniatura en degradado, botón de reproducir y duración "m:ss", con
    buscador. Al pulsar un video se pide la sesión y se abre el manifest.
  - Videos locales: reproduce videos de una carpeta con el reproductor del sistema.
"""

import os
import tkinter as tk
import webbrowser
import zlib

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, BACKGROUND, SURFACE_CONTAINER_HIGH, font, _mix
from ..widgets import (primary_button, tonal_button, icon_button, chip, SearchBar, StatePanel,
                       list_item, tipo_archivo, formatear_duracion, formatear_tamano, bind_click)
from ..utils import open_with_system, run_async, describir
from ..config import VID_EXT, save_config

# Pares de colores para las miniaturas; se elige uno por video de forma estable.
DEGRADADOS = [
    ("#1A5BC0", "#4FD8E3"),
    ("#7A4E9C", "#E37400"),
    ("#006970", "#9AE6B4"),
    ("#C5221F", "#F6AE2D"),
    ("#2E3A59", "#8E9CC9"),
]
MIN_COL = 210        # ancho mínimo de cada columna (GridCells.Adaptive del móvil)


def miniatura(master, video_id, duracion, THUMB_W=200):
    """Lienzo 16:9 con degradado, círculo de reproducir y la duración."""
    THUMB_H = THUMB_W * 9 // 16
    desde, hasta = DEGRADADOS[zlib.crc32(video_id.encode()) % len(DEGRADADOS)]
    c = tk.Canvas(master, width=THUMB_W, height=THUMB_H, highlightthickness=0, bd=0, cursor="hand2")
    for x in range(0, THUMB_W, 2):
        c.create_rectangle(x, 0, x + 2, THUMB_H, width=0, fill=_mix(hasta, desde, x / THUMB_W))
    cx, cy = THUMB_W // 2, THUMB_H // 2
    centro = _mix(hasta, desde, 0.5)
    c.create_oval(cx - 22, cy - 22, cx + 22, cy + 22, width=0, fill=_mix("#000000", centro, 0.35))
    c.create_polygon(cx - 7, cy - 11, cx - 7, cy + 11, cx + 12, cy, fill="#FFFFFF", width=0)
    texto = formatear_duracion(duracion)
    ancho = 8 + 7 * len(texto)
    c.create_rectangle(THUMB_W - 8 - ancho, THUMB_H - 28, THUMB_W - 8, THUMB_H - 8, width=0,
                       fill=_mix("#000000", hasta, 0.7))
    c.create_text(THUMB_W - 8 - ancho / 2, THUMB_H - 18, text=texto, fill="#FFFFFF",
                  font=("Roboto", 9, "bold"))
    return c


class StreamingView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.streaming
        self.datos = None

        tabs = ctk.CTkTabview(self, fg_color=BACKGROUND, corner_radius=16, anchor="w")
        tabs.pack(fill="both", expand=True)
        self._catalogo_tab(tabs.add("Catálogo"))
        self._local_tab(tabs.add("Videos locales"))

    # ============================== Catálogo ================================
    def _catalogo_tab(self, tab):
        self.busqueda = SearchBar(tab, "Buscar videos", lambda _q: self._pintar())
        self.busqueda.pack(fill="x", pady=(4, 8))
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 4))
        if self.repo.simulado:
            chip(bar, "Catálogo simulado", "warn").pack(side="left")
        else:
            chip(bar, f"node-media · {self.app.api.conf.url_media}", "ok").pack(side="left")
        icon_button(bar, "↻", self.cargar).pack(side="right")

        self.panel = StatePanel(tab)
        self.panel.pack(fill="both", expand=True)
        self._cols = None
        self.panel.bind("<Configure>", self._al_redimensionar, add="+")
        self.cargar()

    def _al_redimensionar(self, event):
        """Recalcula las columnas cuando cambia el ancho (cuadrícula adaptable)."""
        cols = max(2, (event.width - 40) // MIN_COL)
        if self.datos is not None and cols != self._cols:
            self._pintar()

    def cargar(self):
        self.panel.loading()

        def ok(datos):
            self.datos = datos
            self._pintar()

        run_async(self, lambda: self.repo.catalogo(0), ok,
                  lambda e: self.panel.error(describir(e), self.cargar))

    def _pintar(self):
        if self.datos is None:
            return
        q = self.busqueda.value.strip().lower()
        visibles = [v for v in self.datos if q in v.titulo.lower()]
        if not self.datos:
            self.panel.empty("Todavía no hay contenido disponible para reproducir.", "🎬",
                             "El catálogo está vacío")
            return
        if not visibles:
            self.panel.empty(f"Ningún video coincide con \"{q}\".", "🔍", "Sin resultados")
            return
        self.panel.clear()
        # Columnas según el ancho disponible, como GridCells.Adaptive(170.dp).
        disponible = max(self.panel.winfo_width(), 600) - 40
        cols = max(2, disponible // MIN_COL)
        self._cols = cols
        thumb_w = disponible // cols - 30
        grid = ctk.CTkFrame(self.panel, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=8)
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1, uniform="v")
        for i, v in enumerate(visibles):
            celda = ctk.CTkFrame(grid, fg_color="transparent", corner_radius=16)
            celda.grid(row=i // cols, column=i % cols, sticky="nw", padx=6, pady=8)
            miniatura(celda, v.id, v.duracion_segundos, thumb_w).pack(padx=6, pady=(6, 0))
            ctk.CTkLabel(celda, text=v.titulo, font=font("title_small"), text_color=ON_SURFACE,
                         wraplength=thumb_w, justify="left", anchor="w").pack(fill="x", padx=6, pady=(8, 8))
            bind_click(celda, lambda v=v: self._reproducir(v), hover=SURFACE_CONTAINER_HIGH)

    def _reproducir(self, v):
        def ok(sesion):
            if self.repo.simulado:
                messagebox.showinfo(
                    "Reproducir (simulado)",
                    f"«{v.titulo}»\n\nSesión: {sesion.sesion_id}\nManifest: {sesion.manifest_url}\n\n"
                    "Con node-media conectado, el video se abrirá en tu navegador.")
                return
            if not sesion.manifest_url:
                messagebox.showerror("Streaming", "El servidor no devolvió la URL del video.")
                return
            webbrowser.open(sesion.manifest_url)

        run_async(self, lambda: self.repo.reproducir(v.id), ok,
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
            self.listing.empty("Elige una carpeta para ver y reproducir sus videos.", "🎬",
                               "Sin carpeta de videos", ("Elegir carpeta", self._pick))

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
            self.listing.empty("La carpeta no contiene videos.", "🎬", "Sin videos")
            return
        self.listing.clear()
        for name in vids:
            full = os.path.join(folder, name)
            _row, tr = list_item(self.listing, None, name, formatear_tamano(os.path.getsize(full)),
                                 tipo=tipo_archivo(name))
            tonal_button(tr, "Reproducir", lambda p=full: open_with_system(p), width=120, height=34).pack()
