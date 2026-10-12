# -*- coding: utf-8 -*-
"""Vista "Mis archivos" (Distributed Storage). Igual que StorageScreen.kt del
móvil: buscador, migas de pan, orden (nombre/tamaño), vista de lista o
cuadrícula, secciones CARPETAS / ARCHIVOS, icono por tipo de archivo y hoja de
detalles. Además, lo propio del escritorio: subir, crear carpeta, descargar,
compartir (archivos y carpetas) y eliminar. Imágenes y videos se abren en el
visor de la app (views/visor.py), sin pasar el archivo a otro programa."""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import (ON_SURFACE, ON_SURFACE_VARIANT, ERROR, SURFACE, SURFACE_CONTAINER_HIGH, BACKGROUND,
                     RADIUS_M, RADIUS_S, font, icon_font, tint)
from ..widgets import (primary_button, tonal_button, icon_button, chip, section_header, outlined_card,
                       SearchBar, StatePanel, list_item, icono_tipo, tipo_archivo, bind_click,
                       formatear_tamano, DetailsDialog, ConfirmDialog)
from ..utils import open_with_system, run_async, describir
from ..config import DOWNLOAD_DIR, IMG_EXT, VID_EXT, save_config
from ..data.storage import RAIZ
from .compartir_dialog import CompartirDialog
from .visor import VisorImagen, Reproductor


def _es_imagen(nombre):
    return nombre.lower().endswith(IMG_EXT)


def _es_video(nombre):
    return nombre.lower().endswith(VID_EXT)

ORDENES = {
    "Nombre (A-Z)": (lambda a: a.nombre.lower(), False),
    "Nombre (Z-A)": (lambda a: a.nombre.lower(), True),
    "Tamaño (mayor primero)": (lambda a: (a.tamano_bytes, a.nombre.lower()), True),
    "Tamaño (menor primero)": (lambda a: (a.tamano_bytes, a.nombre.lower()), False),
}
COLS_CUADRICULA = 4


class StorageView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.storage
        self.ruta = [(RAIZ, "Mis archivos")]       # migas de pan: (id, nombre)
        self.datos = None                          # última lista recibida (Success)
        self.orden = "Nombre (A-Z)"
        self.cuadricula = app.config.get("vista_archivos") == "cuadricula"
        self._peticion = 0

        self.busqueda = SearchBar(self, "Buscar en Mis archivos", lambda _q: self._pintar())
        self.busqueda.pack(fill="x", pady=(0, 6))

        fila_migas = ctk.CTkFrame(self, fg_color="transparent")
        fila_migas.pack(fill="x")
        self.l_cuota = ctk.CTkLabel(fila_migas, text="", font=font("label_medium"), text_color=ON_SURFACE_VARIANT)
        self.l_cuota.pack(side="right", padx=8)
        self.migas = ctk.CTkFrame(fila_migas, fg_color="transparent")
        self.migas.pack(side="left", fill="x", expand=True)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(2, 6))
        self.sel_orden = ctk.CTkOptionMenu(bar, values=list(ORDENES), command=self._cambiar_orden,
                                           width=210, height=34, fg_color=BACKGROUND,
                                           button_color=BACKGROUND, button_hover_color=SURFACE_CONTAINER_HIGH,
                                           text_color=ON_SURFACE, font=font("label_large"),
                                           dynamic_resizing=False)
        self.sel_orden.set(self.orden)
        self.sel_orden.pack(side="left")
        if self.repo.simulado:
            chip(bar, "Simulado · Home local", "warn").pack(side="left", padx=10)
        else:
            chip(bar, f"node-repository · {app.api.conf.url_storage}", "ok").pack(side="left", padx=10)
        self.btn_vista = icon_button(bar, "☰" if self.cuadricula else "▦", self._toggle_vista)
        self.btn_vista.pack(side="right")
        icon_button(bar, "↻", self.recargar).pack(side="right")
        primary_button(bar, "↑  Subir", self._upload, width=110, height=36).pack(side="right", padx=8)
        tonal_button(bar, "＋  Nueva carpeta", self._nueva_carpeta, width=150, height=36).pack(side="right")

        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self.recargar()

    # --- Carga (UiState) ----------------------------------------------------
    @property
    def dir_actual(self):
        return self.ruta[-1][0]

    def recargar(self):
        self._pintar_migas()
        self.busqueda.reset(f"Buscar en {self.ruta[-1][1]}")
        self.panel.loading()
        # Si se navega rápido, la respuesta de una carpeta anterior no debe
        # pisar la de la carpeta que se está viendo ahora.
        self._peticion += 1
        n = self._peticion
        dir_id = self.dir_actual

        def ok(items):
            if n == self._peticion:
                self.datos = items
                self._pintar()

        def err(e):
            if n == self._peticion:
                self.datos = None
                self.panel.error(describir(e), self.recargar)

        run_async(self, lambda: self.repo.listar(dir_id), ok, err)
        run_async(self, self.repo.cuota, self._pintar_cuota, lambda _e: None)

    def _pintar_cuota(self, cuota):
        if cuota and cuota[1]:
            self.l_cuota.configure(text=f"{formatear_tamano(cuota[0])} usados de {formatear_tamano(cuota[1])}")

    def _pintar(self):
        if self.datos is None:
            return
        q = self.busqueda.value.strip().lower()
        clave, desc = ORDENES[self.orden]
        visibles = sorted([a for a in self.datos if q in a.nombre.lower()], key=clave, reverse=desc)
        carpetas = [a for a in visibles if a.es_directorio]
        archivos = [a for a in visibles if not a.es_directorio]

        if not self.datos:
            self.panel.empty("Los archivos que subas a esta carpeta aparecerán aquí.", "📂",
                             "Esta carpeta está vacía", ("Subir archivos", self._upload))
            return
        if not visibles:
            self.panel.empty(f"Ningún elemento coincide con \"{q}\".", "🔍", "Sin resultados")
            return
        self.panel.clear()
        if self.cuadricula:
            self._cuadricula(carpetas, archivos)
        else:
            self._lista(carpetas, archivos)

    def _lista(self, carpetas, archivos):
        if carpetas:
            section_header(self.panel, "Carpetas").pack(anchor="w", padx=16, pady=(8, 4))
            for c in carpetas:
                _r, tr = list_item(self.panel, None, c.nombre, "Carpeta", tipo=tipo_archivo(c.nombre, True),
                                   on_click=lambda c=c: self._entrar(c))
                icon_button(tr, "⋮", lambda c=c: self._detalles(c), size=34).pack()
        if archivos:
            section_header(self.panel, "Archivos").pack(anchor="w", padx=16, pady=(12, 4))
            for a in archivos:
                _r, tr = list_item(self.panel, None, a.nombre, f"{formatear_tamano(a.tamano_bytes)} · v{a.version}",
                                   tipo=tipo_archivo(a.nombre), on_click=lambda a=a: self._tocar(a))
                icon_button(tr, "⋮", lambda a=a: self._detalles(a), size=34).pack()

    def _cuadricula(self, carpetas, archivos):
        def rejilla():
            g = ctk.CTkFrame(self.panel, fg_color="transparent")
            g.pack(fill="x", padx=12)
            for i in range(COLS_CUADRICULA):
                g.grid_columnconfigure(i, weight=1, uniform="g")
            return g

        if carpetas:
            section_header(self.panel, "Carpetas").pack(anchor="w", padx=16, pady=(8, 6))
            g = rejilla()
            for i, c in enumerate(carpetas):
                # Las carpetas van compactas, como en Drive: solo icono y nombre.
                t = outlined_card(g, corner_radius=RADIUS_M, height=58)
                t.grid(row=i // COLS_CUADRICULA, column=i % COLS_CUADRICULA, sticky="ew", padx=6, pady=6)
                t.pack_propagate(False)
                icono_tipo(t, tipo_archivo(c.nombre, True), 32).pack(side="left", padx=12)
                ctk.CTkLabel(t, text=_cortar(c.nombre, 20), font=font("title_small"), anchor="w").pack(side="left")
                bind_click(t, lambda c=c: self._entrar(c), hover=SURFACE_CONTAINER_HIGH)
                t.bind("<Button-3>", lambda _e, c=c: self._detalles(c))
        if archivos:
            section_header(self.panel, "Archivos").pack(anchor="w", padx=16, pady=(14, 6))
            g = rejilla()
            for i, a in enumerate(archivos):
                tipo = tipo_archivo(a.nombre)
                t = outlined_card(g, corner_radius=RADIUS_M)
                t.grid(row=i // COLS_CUADRICULA, column=i % COLS_CUADRICULA, sticky="ew", padx=6, pady=6)
                ctk.CTkLabel(t, text=tipo.icono, height=110, corner_radius=RADIUS_S,
                             fg_color=tint(tipo.color, 0.10, SURFACE), text_color=tipo.color,
                             font=icon_font(40)).pack(fill="x", padx=8, pady=(8, 6))
                ctk.CTkLabel(t, text=_cortar(a.nombre, 24), font=font("title_small"), anchor="w").pack(
                    fill="x", padx=12)
                ctk.CTkLabel(t, text=formatear_tamano(a.tamano_bytes), font=font("body_small"),
                             text_color=ON_SURFACE_VARIANT, anchor="w").pack(fill="x", padx=12, pady=(0, 10))
                bind_click(t, lambda a=a: self._tocar(a), hover=SURFACE_CONTAINER_HIGH)

    # --- Migas de pan --------------------------------------------------------
    def _pintar_migas(self):
        for w in self.migas.winfo_children():
            w.destroy()
        for i, (_id, nombre) in enumerate(self.ruta):
            actual = i == len(self.ruta) - 1
            if i > 0:
                ctk.CTkLabel(self.migas, text="›", text_color=ON_SURFACE_VARIANT,
                             font=ctk.CTkFont(size=20)).pack(side="left", padx=2)
            ctk.CTkButton(self.migas, text=nombre, width=10, height=40, corner_radius=20,
                          fg_color="transparent", hover_color=SURFACE_CONTAINER_HIGH,
                          text_color=ON_SURFACE if actual else ON_SURFACE_VARIANT,
                          text_color_disabled=ON_SURFACE,
                          font=font("title_large" if actual else "title_medium"),
                          state="disabled" if actual else "normal",
                          command=lambda i=i: self._ir_a_nivel(i)).pack(side="left")

    def _entrar(self, carpeta):
        self.ruta.append((carpeta.id, carpeta.nombre))   # recargar() vacía la búsqueda
        self.recargar()

    def _ir_a_nivel(self, i):
        if i < len(self.ruta) - 1:
            self.ruta = self.ruta[:i + 1]
            self.recargar()

    # --- Barra de herramientas -----------------------------------------------
    def _cambiar_orden(self, valor):
        self.orden = valor
        self._pintar()

    def _toggle_vista(self):
        self.cuadricula = not self.cuadricula
        self.app.config["vista_archivos"] = "cuadricula" if self.cuadricula else "lista"
        save_config(self.app.config)
        self.btn_vista.configure(text="☰" if self.cuadricula else "▦")
        self._pintar()

    # --- Detalles y acciones -------------------------------------------------
    def _tocar(self, a):
        """Imágenes y videos se abren en el visor; lo demás muestra detalles."""
        if _es_imagen(a.nombre) or _es_video(a.nombre):
            self._abrir(a)
        else:
            self._detalles(a)

    def _abrir(self, a):
        borrar = (lambda: self._borrar(a)) if not a.es_directorio else None
        if _es_video(a.nombre):
            Reproductor(self, a.nombre, lambda: self.repo.fuente_video(a.id), on_eliminar=borrar)
        else:
            VisorImagen(self, a.nombre, lambda: self.repo.leer(a.id), on_eliminar=borrar)

    def _compartir(self, a):
        CompartirDialog(self, self.app.api, elemento_id=a.id, nombre=a.nombre, es_directorio=a.es_directorio)

    def _detalles(self, a):
        ubicacion = ("Ubicación", " / ".join(n for _, n in self.ruta))
        if a.es_directorio:
            DetailsDialog(self, a.nombre, tipo_archivo(a.nombre, True), [ubicacion, ("Identificador", a.id)], [
                ("Compartir", lambda: self._compartir(a), "tonal"),
                ("Abrir", lambda: self._entrar(a), "primary"),
            ])
            return
        acciones = [("Eliminar", lambda: self._eliminar(a), ERROR),
                    ("Compartir", lambda: self._compartir(a), "tonal"),
                    ("Descargar", lambda: self._descargar(a), "primary")]
        if _es_imagen(a.nombre) or _es_video(a.nombre):
            acciones.insert(1, ("Abrir", lambda: self._abrir(a), "outlined"))
        DetailsDialog(self, a.nombre, tipo_archivo(a.nombre), [
            ("Tamaño", formatear_tamano(a.tamano_bytes)),
            ("Versión", f"v{a.version}"),
            ubicacion,
            ("Identificador", a.id),
        ], acciones)

    def _nueva_carpeta(self):
        dialogo = ctk.CTkInputDialog(title="Nueva carpeta", text=f"Nombre de la carpeta en «{self.ruta[-1][1]}»:")
        nombre = (dialogo.get_input() or "").strip()
        if not nombre:
            return
        destino = self.dir_actual
        run_async(self, lambda: self.repo.crear_carpeta(nombre, destino), lambda _c: self.recargar(),
                  lambda e: messagebox.showerror("No se pudo crear la carpeta", describir(e)))

    def _upload(self):
        paths = filedialog.askopenfilenames(title="Seleccionar archivos para subir")
        if not paths:
            return
        destino = self.dir_actual
        self.panel.loading()

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
            self.recargar()
            if errores:
                messagebox.showerror("Error al subir", "\n".join(errores))
            elif ok:
                messagebox.showinfo("Listo", f"{ok} archivo(s) subido(s).")

        run_async(self, subir_todos, hecho, lambda e: self.panel.error(describir(e), self.recargar))

    def _descargar(self, a):
        destino = filedialog.asksaveasfilename(
            title="Guardar como", initialfile=a.nombre,
            initialdir=str(DOWNLOAD_DIR) if DOWNLOAD_DIR.exists() else None)
        if not destino:
            return
        run_async(self, lambda: self.repo.descargar(a.id, destino), self._descargado,
                  lambda e: messagebox.showerror("Error al descargar", describir(e)))

    def _descargado(self, path):
        if messagebox.askyesno("Descarga completa", f"Guardado en:\n{path}\n\n¿Abrir el archivo?"):
            open_with_system(path)

    def _borrar(self, a):
        run_async(self, lambda: self.repo.eliminar(a.id), lambda _r: self.recargar(),
                  lambda e: messagebox.showerror("Error al eliminar", describir(e)))

    def _eliminar(self, a):
        ConfirmDialog(self, "🗑", "¿Eliminar archivo?",
                      f"«{a.nombre}» se eliminará. Esta acción no se puede deshacer.", "Eliminar",
                      lambda: self._borrar(a))


def _cortar(texto, n):
    return texto if len(texto) <= n else texto[:n - 1] + "…"
