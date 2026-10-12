# -*- coding: utf-8 -*-
"""Vista de Streaming (node-media). Igual que StreamingScreen.kt del móvil:
cuadrícula de videos con miniatura en degradado, duración y buscador. El video
se reproduce DENTRO de la app (views/visor.py), pidiéndolo por rangos a
node-media con el token; nada se abre en el navegador.

Lo que se sube a Mis archivos no aparece aquí hasta "Buscar nuevos" (indexar).
"""

import tkinter as tk
import zlib

import customtkinter as ctk
from tkinter import messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, SURFACE_CONTAINER_HIGH, font, _mix
from ..widgets import (tonal_button, icon_button, chip, SearchBar, StatePanel, bind_click,
                       formatear_duracion, ConfirmDialog)
from ..utils import run_async, describir
from .visor import Reproductor

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
    if duracion:
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

        self.busqueda = SearchBar(self, "Buscar videos", lambda _q: self._pintar())
        self.busqueda.pack(fill="x", pady=(0, 8))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 4))
        if self.repo.simulado:
            chip(bar, "Catálogo simulado", "warn").pack(side="left")
        else:
            chip(bar, f"node-media · {app.api.conf.url_media}", "ok").pack(side="left")
        icon_button(bar, "↻", self.cargar).pack(side="right")
        self.btn_indexar = tonal_button(bar, "🔎  Buscar nuevos", self._indexar, width=160, height=36)
        self.btn_indexar.pack(side="right", padx=8)

        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self._cols = None
        self._pintando = False
        self.panel.bind("<Configure>", self._al_redimensionar, add="+")
        self.cargar()

    @staticmethod
    def _columnas(ancho):
        return max(2, (max(ancho, 600) - 40) // MIN_COL)

    def _al_redimensionar(self, event):
        """Recalcula las columnas cuando cambia el ancho (cuadrícula adaptable).

        Pintar destruye y crea widgets, y eso dispara <Configure> DENTRO del
        propio pintado: sin la guarda, se llamaría a sí mismo sin fin."""
        if self._pintando or self.datos is None:
            return
        if self._columnas(event.width) != self._cols:
            self._pintar()

    def cargar(self):
        self.panel.loading()

        def ok(datos):
            self.datos = datos
            self._pintar()

        run_async(self, lambda: self.repo.catalogo(0), ok,
                  lambda e: self.panel.error(describir(e), self.cargar))

    def _indexar(self):
        """Busca en Mis archivos videos y fotos nuevos (node-media no se entera solo)."""
        self.btn_indexar.configure(state="disabled", text="Buscando…")

        def fin(res):
            self.btn_indexar.configure(state="normal", text="🔎  Buscar nuevos")
            nuevos, revisados = res
            if nuevos == 0:
                messagebox.showinfo("Streaming", "No hay fotos ni videos nuevos en Mis archivos.", parent=self)
            self.cargar()

        def err(e):
            self.btn_indexar.configure(state="normal", text="🔎  Buscar nuevos")
            messagebox.showerror("No se pudo buscar contenido nuevo", describir(e), parent=self)

        run_async(self, self.repo.indexar, fin, err)

    def _pintar(self):
        if self.datos is None or self._pintando:
            return
        self._pintando = True
        try:
            self._pintar_rejilla()
        finally:
            self._pintando = False

    def _pintar_rejilla(self):
        # Las columnas se fijan SIEMPRE, también si no hay nada que mostrar: si no,
        # cada <Configure> volvería a pintar el estado vacío una y otra vez.
        self._cols = self._columnas(self.panel.winfo_width())
        q = self.busqueda.value.strip().lower()
        visibles = [v for v in self.datos if q in v.titulo.lower()]
        if not self.datos:
            self.panel.empty("Sube videos a Mis archivos y pulsa \"Buscar nuevos\".", "🎬",
                             "No hay videos", ("Buscar nuevos", self._indexar))
            return
        if not visibles:
            self.panel.empty(f"Ningún video coincide con \"{q}\".", "🔍", "Sin resultados")
            return
        self.panel.clear()
        # Columnas según el ancho disponible, como GridCells.Adaptive(170.dp).
        disponible = max(self.panel.winfo_width(), 600) - 40
        cols = self._columnas(self.panel.winfo_width())
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
            pie = ctk.CTkFrame(celda, fg_color="transparent")
            pie.pack(fill="x", padx=6, pady=(8, 8))
            if not self.repo.simulado:
                icon_button(pie, "🗑", lambda v=v: self._pedir_eliminar(v), size=32,
                            color=ON_SURFACE_VARIANT).pack(side="right")
            ctk.CTkLabel(pie, text=v.titulo, font=font("title_small"), text_color=ON_SURFACE,
                         wraplength=thumb_w - 44, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
            bind_click(celda, lambda v=v: self._reproducir(v), hover=SURFACE_CONTAINER_HIGH)

    def _reproducir(self, v):
        if self.repo.simulado:
            messagebox.showinfo("Streaming", "Modo simulado: no hay video real que reproducir.", parent=self)
            return
        Reproductor(self, v.titulo, lambda: self.repo.reproducir(v.id),
                    on_eliminar=lambda: self._eliminar(v))

    def _pedir_eliminar(self, v):
        ConfirmDialog(self, "🗑", "¿Eliminar video?",
                      f"«{v.titulo}» se borrará también de Mis archivos. No se puede deshacer.",
                      "Eliminar", lambda: self._eliminar(v))

    def _eliminar(self, v):
        run_async(self, lambda: self.repo.eliminar_video(v.id), lambda _r: self.cargar(),
                  lambda e: messagebox.showerror("No se pudo eliminar", describir(e), parent=self))
