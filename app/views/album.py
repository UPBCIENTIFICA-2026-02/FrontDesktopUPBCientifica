# -*- coding: utf-8 -*-
"""Álbum de fotos (Photo Album, node-media). Cuadrícula con las miniaturas que
genera node-media; al pulsar, la foto original se abre en el visor de la app
(views/visor.py), con zoom y opción de eliminarla.

Lo que se sube a Mis archivos no aparece aquí hasta "Buscar nuevas" (indexar).
"""

import io

import customtkinter as ctk
from tkinter import messagebox

from ..theme import (ON_SURFACE_VARIANT, SURFACE_CONTAINER, SURFACE_CONTAINER_HIGH, font)
from ..widgets import tonal_button, icon_button, chip, StatePanel, SearchBar, bind_click
from ..utils import run_async, describir
from .visor import VisorImagen

try:
    from PIL import Image
except ImportError:
    Image = None

LADO = 150          # miniatura cuadrada
MIN_COL = LADO + 24


class AlbumView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.streaming          # node-media sirve Streaming y Photo Album
        self.datos = None
        self._miniaturas = {}                   # id -> CTkImage (caché de la sesión)
        self._cols = None
        self._pintando = False

        self.busqueda = SearchBar(self, "Buscar fotos", lambda _q: self._pintar())
        self.busqueda.pack(fill="x", pady=(0, 8))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 4))
        if self.repo.simulado:
            chip(bar, "Simulado · sin fotos", "warn").pack(side="left")
        else:
            chip(bar, f"node-media · {app.api.conf.url_media}", "ok").pack(side="left")
        icon_button(bar, "↻", self.cargar).pack(side="right")
        self.btn_indexar = tonal_button(bar, "🔎  Buscar nuevas", self._indexar, width=160, height=36)
        self.btn_indexar.pack(side="right", padx=8)

        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self.panel.bind("<Configure>", self._al_redimensionar, add="+")
        self.cargar()

    @staticmethod
    def _columnas(ancho):
        return max(2, (max(ancho, 600) - 30) // MIN_COL)

    def _al_redimensionar(self, event):
        # Pintar destruye y crea widgets, y eso dispara <Configure> DENTRO del
        # propio pintado: sin la guarda, se llamaría a sí mismo sin fin.
        if self._pintando or self.datos is None:
            return
        if self._columnas(event.width) != self._cols:
            self._pintar()

    def cargar(self):
        self.panel.loading()

        def ok(datos):
            self.datos = datos
            self._pintar()

        run_async(self, lambda: self.repo.fotos(0), ok, lambda e: self.panel.error(describir(e), self.cargar))

    def _indexar(self):
        self.btn_indexar.configure(state="disabled", text="Buscando…")

        def fin(res):
            self.btn_indexar.configure(state="normal", text="🔎  Buscar nuevas")
            if res[0] == 0:
                messagebox.showinfo("Álbum", "No hay fotos ni videos nuevos en Mis archivos.", parent=self)
            self.cargar()

        def err(e):
            self.btn_indexar.configure(state="normal", text="🔎  Buscar nuevas")
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
        visibles = [f for f in self.datos if q in f.titulo.lower()]
        if not self.datos:
            self.panel.empty("Sube fotos a Mis archivos y pulsa \"Buscar nuevas\".", "🖼",
                             "No hay fotos", ("Buscar nuevas", self._indexar))
            return
        if not visibles:
            self.panel.empty(f"Ninguna foto coincide con \"{q}\".", "🔍", "Sin resultados")
            return
        self.panel.clear()
        cols = self._columnas(self.panel.winfo_width())
        self._cols = cols
        grid = ctk.CTkFrame(self.panel, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=8)
        for i, foto in enumerate(visibles):
            celda = ctk.CTkFrame(grid, fg_color=SURFACE_CONTAINER, corner_radius=12, width=LADO, height=LADO + 34)
            celda.grid(row=i // cols, column=i % cols, padx=6, pady=6)
            celda.pack_propagate(False)
            imagen = ctk.CTkLabel(celda, text="🖼", width=LADO, height=LADO, font=ctk.CTkFont(size=30),
                                  text_color=ON_SURFACE_VARIANT)
            imagen.pack()
            ctk.CTkLabel(celda, text=_cortar(foto.titulo, 20), font=font("body_small"),
                         text_color=ON_SURFACE_VARIANT).pack()
            bind_click(celda, lambda f=foto: self._ver(f), hover=SURFACE_CONTAINER_HIGH)
            self._cargar_miniatura(foto, imagen)

    def _cargar_miniatura(self, foto, etiqueta):
        if Image is None:
            return
        if foto.id in self._miniaturas:
            etiqueta.configure(image=self._miniaturas[foto.id], text="")
            return

        def decodificar():
            # node-media solo genera miniaturas si tiene FFmpeg; si no, se usa la
            # original y se reduce aquí (más lento, pero se ve la foto).
            datos = self.repo.miniatura(foto.id) if foto.tiene_miniatura else self.repo.contenido_foto(foto.id)
            img = Image.open(io.BytesIO(datos))
            img.load()
            # Recorte cuadrado centrado, como ContentScale.Crop.
            lado = min(img.size)
            x, y = (img.width - lado) // 2, (img.height - lado) // 2
            return img.crop((x, y, x + lado, y + lado)).resize((LADO, LADO))

        def poner(img):
            ci = ctk.CTkImage(light_image=img, dark_image=img, size=(LADO, LADO))
            self._miniaturas[foto.id] = ci
            try:
                etiqueta.configure(image=ci, text="")
            except Exception:
                pass  # la cuadrícula se redibujó mientras llegaba

        run_async(etiqueta, decodificar, poner, lambda _e: None)

    def _ver(self, foto):
        VisorImagen(self, foto.titulo, lambda: self.repo.contenido_foto(foto.id),
                    on_eliminar=None if self.repo.simulado else (lambda: self._eliminar(foto)))

    def _eliminar(self, foto):
        def hecho(_r):
            self._miniaturas.pop(foto.id, None)
            self.cargar()
        run_async(self, lambda: self.repo.eliminar_foto(foto.id), hecho,
                  lambda e: messagebox.showerror("No se pudo eliminar", describir(e), parent=self))


def _cortar(texto, n):
    return texto if len(texto) <= n else texto[:n - 1] + "…"
