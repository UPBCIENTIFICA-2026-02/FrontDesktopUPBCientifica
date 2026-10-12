# -*- coding: utf-8 -*-
"""Vista Compartidos (Shared File). Igual que SharedFileScreen.kt del móvil:

  Conmigo       ListarCompartidosConmigo. Una carpeta se abre aquí mismo (su
                contenido lo lista Storage, que ya aplica el permiso); imágenes
                y videos se ven en el visor; lo demás se descarga.
  Que comparto  ListarQueYoComparto. Cambiar el nivel
                (ActualizarPermisosCompartidos) o dejar de compartir.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..theme import (ERROR, SECONDARY_CONTAINER, ON_SECONDARY_CONTAINER, ON_SURFACE, ON_SURFACE_VARIANT,
                     SURFACE_CONTAINER_HIGH, font)
from ..widgets import (icon_button, chip, SearchBar, StatePanel, list_item, avatar, tipo_archivo,
                       formatear_tamano, DetailsDialog, ConfirmDialog, Dialog, primary_button, ghost_button)
from ..utils import run_async, describir, open_with_system
from ..config import DOWNLOAD_DIR, IMG_EXT, VID_EXT
from ..data.sharedfile import NIVELES, texto_nivel
from .visor import VisorImagen, Reproductor
from .compartir_dialog import CompartirDialog

COMPARTIR = "LECTURA_ESCRITURA_COMPARTIR"     # el nivel que deja volver a compartir

SECCIONES = ("Conmigo", "Que comparto")


class SharedFilesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.shared
        self.storage = app.api.storage
        self.seccion = SECCIONES[0]
        self.ruta = []              # carpetas compartidas abiertas: [(id, nombre)]
        # Nivel con el que se compartió la carpeta por la que se entró: lo que
        # hay dentro lo hereda (Storage aplica la herencia), así que decide si
        # se puede volver a compartir un elemento de dentro.
        self._nivel_carpeta = None
        self.datos = None
        self._peticion = 0

        self.busqueda = SearchBar(self, "Buscar en Compartidos", lambda _q: self._pintar())
        self.busqueda.pack(fill="x", pady=(0, 8))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 6))
        self.selector = ctk.CTkSegmentedButton(bar, values=list(SECCIONES), command=self._cambiar_seccion)
        self.selector.set(self.seccion)
        self.selector.pack(side="left")
        if self.repo.simulado:
            chip(bar, "Shared File desactivado", "warn").pack(side="left", padx=10)
        else:
            chip(bar, f"Shared File · {app.api.conf.url_compartidos}", "ok").pack(side="left", padx=10)
        icon_button(bar, "↻", self.cargar).pack(side="right")

        self.migas = ctk.CTkFrame(self, fg_color="transparent")
        self.panel = StatePanel(self)
        self.panel.pack(fill="both", expand=True)
        self.cargar()

    # --- Carga ---------------------------------------------------------------
    def cargar(self):
        self._pintar_migas()
        self.panel.loading()
        self._peticion += 1
        n = self._peticion
        if self.ruta:
            dir_id = self.ruta[-1][0]
            fn = lambda: self.storage.listar(dir_id)
        elif self.seccion == "Conmigo":
            fn = self.repo.compartidos_conmigo
        else:
            fn = self.repo.que_yo_comparto

        def ok(datos):
            if n == self._peticion:
                self.datos = datos
                self._pintar()

        def err(e):
            if n == self._peticion:
                self.datos = None
                self.panel.error(describir(e), self.cargar)

        run_async(self, fn, ok, err)

    def _cambiar_seccion(self, valor):
        self.seccion = valor
        self.ruta = []
        self._nivel_carpeta = None
        self.cargar()

    # --- Pintar --------------------------------------------------------------
    def _pintar_migas(self):
        for w in self.migas.winfo_children():
            w.destroy()
        if not self.ruta:
            self.migas.pack_forget()
            return
        self.migas.pack(fill="x", before=self.panel)
        niveles = [(None, "Compartidos")] + self.ruta
        for i, (_id, nombre) in enumerate(niveles):
            actual = i == len(niveles) - 1
            if i:
                ctk.CTkLabel(self.migas, text="›", text_color=ON_SURFACE_VARIANT,
                             font=ctk.CTkFont(size=20)).pack(side="left", padx=2)
            ctk.CTkButton(self.migas, text=nombre, width=10, height=40, corner_radius=20,
                          fg_color="transparent", hover_color=SURFACE_CONTAINER_HIGH,
                          text_color=ON_SURFACE if actual else ON_SURFACE_VARIANT, text_color_disabled=ON_SURFACE,
                          font=font("title_large" if actual else "title_medium"),
                          state="disabled" if actual else "normal",
                          command=lambda i=i: self._ir_a(i)).pack(side="left")

    def _ir_a(self, i):
        self.ruta = self.ruta[:i]          # 0 = la lista
        if not self.ruta:
            self._nivel_carpeta = None
        self.cargar()

    def _pintar(self):
        if self.datos is None:
            return
        q = self.busqueda.value.strip().lower()
        if self.ruta:
            return self._pintar_carpeta(q)
        visibles = [r for r in self.datos
                    if q in r.nombre.lower() or q in r.propietario.lower() or q in r.destinatario_id.lower()]
        if not self.datos:
            if self.seccion == "Conmigo":
                self.panel.empty("Cuando alguien comparta un archivo o carpeta contigo, aparecerá aquí.",
                                 "👥", "Nada compartido contigo")
            else:
                self.panel.empty("Comparte desde Mis archivos con el botón Compartir de cada archivo o carpeta.",
                                 "👥", "No compartes nada")
            return
        if not visibles:
            self.panel.empty(f"Nada coincide con \"{q}\".", "🔍", "Sin resultados")
            return
        self.panel.clear()
        conmigo = self.seccion == "Conmigo"
        for r in visibles:
            persona = r.propietario if conmigo else r.destinatario_id

            def secundario(box, r=r, persona=persona):
                fila = ctk.CTkFrame(box, fg_color="transparent")
                fila.pack(anchor="w")
                avatar(fila, persona, 18).pack(side="left")
                ctk.CTkLabel(fila, text=persona if conmigo else f"con {r.destinatario_legible}",
                             font=font("body"), text_color=ON_SURFACE_VARIANT).pack(side="left", padx=6)

            _row, tr = list_item(self.panel, None, r.nombre, secundario, tipo=tipo_archivo(r.nombre, r.es_directorio),
                                 on_click=lambda r=r: self._tocar_relacion(r))
            ctk.CTkLabel(tr, text=f"  {texto_nivel(r.nivel_permiso)}  ", fg_color=SECONDARY_CONTAINER,
                         text_color=ON_SECONDARY_CONTAINER, corner_radius=8, height=24,
                         font=font("label_small")).pack(side="left")
            icon_button(tr, "⋮", lambda r=r: self._detalles(r), size=34).pack(side="left", padx=(6, 0))

    def _pintar_carpeta(self, q):
        visibles = [a for a in self.datos if q in a.nombre.lower()]
        if not visibles:
            self.panel.empty("Todavía no hay nada aquí." if not self.datos else f"Nada coincide con \"{q}\".",
                             "📂", "Esta carpeta está vacía" if not self.datos else "Sin resultados")
            return
        self.panel.clear()
        for a in visibles:
            sub = "Carpeta" if a.es_directorio else formatear_tamano(a.tamano_bytes)
            _row, tr = list_item(self.panel, None, a.nombre, sub, tipo=tipo_archivo(a.nombre, a.es_directorio),
                                 on_click=lambda a=a: self._tocar_elemento(a.id, a.nombre, a.es_directorio))
            icon_button(tr, "⋮", lambda a=a: self._detalles_elemento(a), size=34).pack()

    # --- Acciones ------------------------------------------------------------
    def _tocar_relacion(self, r):
        if self.seccion == "Conmigo":
            if r.es_directorio:
                self._nivel_carpeta = r.nivel_permiso
            self._tocar_elemento(r.elemento_id, r.nombre, r.es_directorio)
        else:
            self._gestionar(r)

    def _tocar_elemento(self, elemento_id, nombre, es_directorio):
        """Carpeta -> se abre aquí; imagen/video -> visor; otro -> descargar."""
        if es_directorio:
            self.ruta.append((elemento_id, nombre))
            self.cargar()
        elif nombre.lower().endswith(VID_EXT):
            Reproductor(self, nombre, lambda: self.storage.fuente_video(elemento_id))
        elif nombre.lower().endswith(IMG_EXT):
            VisorImagen(self, nombre, lambda: self.storage.leer(elemento_id))
        else:
            self._descargar(elemento_id, nombre)

    def _detalles(self, r):
        if self.seccion == "Que comparto":
            return self._gestionar(r)
        filas = [("Propietario", r.propietario), ("Compartido por", r.compartido_por),
                 ("Tu acceso", texto_nivel(r.nivel_permiso))]
        if r.fecha_expiracion:
            filas.append(("Caduca", r.fecha_expiracion[:10]))
        if not r.es_directorio:
            filas.append(("Tamaño", formatear_tamano(r.tamano_bytes)))
        acciones = [("Abrir", lambda: self._tocar_relacion(r), "primary")]
        if not r.es_directorio:
            acciones.insert(0, ("Descargar", lambda: self._descargar(r.elemento_id, r.nombre), "tonal"))
        if r.nivel_permiso == COMPARTIR:
            acciones.insert(0, ("Compartir", lambda: self._compartir(r.elemento_id, r.nombre, r.es_directorio),
                                "outlined"))
        DetailsDialog(self, r.nombre, tipo_archivo(r.nombre, r.es_directorio), filas, acciones)

    def _detalles_elemento(self, a):
        """Algo DENTRO de una carpeta compartida contigo."""
        filas = [("Ubicación", " / ".join(n for _, n in self.ruta)),
                 ("Tu acceso", texto_nivel(self._nivel_carpeta) if self._nivel_carpeta else "—")]
        if not a.es_directorio:
            filas.insert(0, ("Tamaño", formatear_tamano(a.tamano_bytes)))
        acciones = [("Abrir", lambda: self._tocar_elemento(a.id, a.nombre, a.es_directorio), "primary")]
        if not a.es_directorio:
            acciones.insert(0, ("Descargar", lambda: self._descargar(a.id, a.nombre), "tonal"))
        if self._nivel_carpeta == COMPARTIR:
            acciones.insert(0, ("Compartir", lambda: self._compartir(a.id, a.nombre, a.es_directorio), "outlined"))
        DetailsDialog(self, a.nombre, tipo_archivo(a.nombre, a.es_directorio), filas, acciones)

    def _compartir(self, elemento_id, nombre, es_directorio):
        """Volver a compartir algo que te compartieron con el nivel "compartir".
        Storage vuelve a comprobar ese nivel; si no lo tienes, avisa (SHR-002)."""
        CompartirDialog(self, self.app.api, elemento_id=elemento_id, nombre=nombre, es_directorio=es_directorio,
                        on_done=self._ver_que_comparto)

    def _ver_que_comparto(self):
        """Tras compartir, la nueva relación se ve en "Que comparto"."""
        self.selector.set("Que comparto")
        self._cambiar_seccion("Que comparto")

    def _gestionar(self, r):
        GestionarDialog(self, r, self._cambiar_nivel, self._revocar)

    def _cambiar_nivel(self, r, nivel):
        def ok(advertencia):
            if advertencia:
                messagebox.showwarning("Permiso cambiado", advertencia, parent=self)
            self.cargar()
        run_async(self, lambda: self.repo.cambiar_nivel(r.compartido_id, nivel), ok,
                  lambda e: messagebox.showerror("No se pudo cambiar el permiso", describir(e), parent=self))

    def _revocar(self, r):
        def quitar():
            run_async(self, lambda: self.repo.revocar(r.compartido_id), lambda _x: self.cargar(),
                      lambda e: messagebox.showerror("No se pudo dejar de compartir", describir(e), parent=self))
        ConfirmDialog(self, "👥", "¿Dejar de compartir?",
                      f"{r.destinatario_legible} perderá el acceso a «{r.nombre}» de inmediato.",
                      "Dejar de compartir", quitar)

    def _descargar(self, elemento_id, nombre):
        destino = filedialog.asksaveasfilename(
            title="Guardar como", initialfile=nombre,
            initialdir=str(DOWNLOAD_DIR) if DOWNLOAD_DIR.exists() else None)
        if not destino:
            return

        def listo(path):
            if messagebox.askyesno("Descarga completa", f"Guardado en:\n{path}\n\n¿Abrir el archivo?"):
                open_with_system(path)
        run_async(self, lambda: self.storage.descargar(elemento_id, destino), listo,
                  lambda e: messagebox.showerror("Error al descargar", describir(e)))


class GestionarDialog(Dialog):
    """Lo que comparto: cambiar el permiso o dejar de compartir."""

    def __init__(self, master, relacion, on_cambiar, on_revocar):
        super().__init__(master, "Compartido", 480, 400)
        r = relacion
        ctk.CTkLabel(self, text=r.nombre, font=font("title_large"), wraplength=420,
                     justify="left").pack(anchor="w", padx=24, pady=(20, 2))
        ctk.CTkLabel(self, text=f"Compartido con {r.destinatario_legible}",
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=24)
        ctk.CTkLabel(self, text="Permiso", font=font("title_small")).pack(anchor="w", padx=24, pady=(18, 4))
        self.nivel = ctk.StringVar(value=r.nivel_permiso)
        for valor, texto in NIVELES:
            ctk.CTkRadioButton(self, text=texto, variable=self.nivel, value=valor).pack(anchor="w", padx=28, pady=4)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", side="bottom", padx=24, pady=20)

        def guardar():
            self.destroy()
            if self.nivel.get() != r.nivel_permiso:
                on_cambiar(r, self.nivel.get())

        def revocar():
            self.destroy()
            on_revocar(r)

        primary_button(bar, "Guardar", guardar, width=110).pack(side="right")
        ghost_button(bar, "Dejar de compartir", revocar, width=170).pack(side="left")
        bar.winfo_children()[-1].configure(text_color=ERROR)
