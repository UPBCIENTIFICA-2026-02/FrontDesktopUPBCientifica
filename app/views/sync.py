# -*- coding: utf-8 -*-
"""Vista de Sincronización (File Sync). Equivale a SyncScreen.kt del móvil.

Qué carpeta del PC se respalda, en qué carpeta del Home queda, cuándo se
sincroniza (ProgramarSincronizacion) y qué pasó en la última. La lógica vive en
data/filesync.py; aquí solo se pinta su estado y se guardan las preferencias.

ANTES la vista avisaba de que la sincronización era simulada y "Sincronizar
ahora" solo contaba archivos; la programación se guardaba pero nadie la
ejecutaba. AHORA sincroniza de verdad con node-sync y la programación la
dispara la ventana principal (app.py, _sync_tick).
"""

import customtkinter as ctk
from tkinter import filedialog

from ..theme import (ON_SURFACE, ON_SURFACE_VARIANT, PRIMARY, EXITO, ERROR, TERTIARY, font, icon_font, glifo)
from ..widgets import (section_title, section_header, card, primary_button, ghost_button, StatePanel,
                       list_item, formatear_hace)
from ..data.filesync import (AlDia, Sincronizando, SinConfigurar, ErrorSync,
                             MANUAL, AL_CONECTAR, CADA_HORA, DIARIA)

PROGRAMACIONES = [
    (MANUAL, "Manual (solo con el botón)"),
    (AL_CONECTAR, "Al conectarse a la red del servidor"),
    (CADA_HORA, "Cada hora"),
    (DIARIA, "Todos los días a una hora"),
]
_ETIQUETA = dict(PROGRAMACIONES)
_CLAVE = {v: k for k, v in PROGRAMACIONES}

EVENTOS = {
    "SUBIDO": ("↑", PRIMARY, "Subido al servidor"),
    "BAJADO": ("⬇", PRIMARY, "Bajado al PC"),
    "BORRADO_LOCAL": ("🗑", ON_SURFACE_VARIANT, "Borrado en el PC (se borró en el servidor)"),
    "BORRADO_SERVIDOR": ("🗑", ON_SURFACE_VARIANT, "Borrado en el servidor (se borró en el PC)"),
    "CONFLICTO": ("⚠", TERTIARY, "Conflicto: tu versión quedó como «{}»"),
    "ERROR": ("⚠", ERROR, "{}"),
}

MODOS = {MANUAL: "manual", AL_CONECTAR: "al conectarse", CADA_HORA: "programada", DIARIA: "programada"}


class SyncView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.repo = app.api.filesync
        self._resumen_pintado = object()

        section_title(self, "Sincronización",
                      "Copia síncrona de una carpeta del PC en tu Home del servidor. Lo que cambies en un lado "
                      "se refleja en el otro; si cambia en ambos se guardan las dos versiones.").pack(
            anchor="w", pady=(0, 12))

        # --- Estado + "Sincronizar ahora" -----------------------------------
        est = card(self)
        est.pack(fill="x")
        fila = ctk.CTkFrame(est, fg_color="transparent")
        fila.pack(fill="x", padx=20, pady=(16, 8))
        self.e_icono = ctk.CTkLabel(fila, text=glifo("☁"), font=icon_font(30), width=44)
        self.e_icono.pack(side="left")
        textos = ctk.CTkFrame(fila, fg_color="transparent")
        textos.pack(side="left", fill="x", expand=True, padx=14)
        self.e_titulo = ctk.CTkLabel(textos, text="", font=font("title_medium"), text_color=ON_SURFACE, anchor="w")
        self.e_titulo.pack(anchor="w", fill="x")
        self.e_detalle = ctk.CTkLabel(textos, text="", font=font("body"), text_color=ON_SURFACE_VARIANT,
                                      anchor="w", justify="left", wraplength=620)
        self.e_detalle.pack(anchor="w", fill="x")
        self.b_sync = primary_button(fila, "⟳  Sincronizar ahora", self._sincronizar, width=190)
        self.b_sync.pack(side="right")
        self.e_barra = ctk.CTkProgressBar(est, height=4)
        self.e_pie = ctk.CTkFrame(est, fg_color="transparent", height=8)
        self.e_pie.pack(fill="x")

        # --- Configuración ------------------------------------------------------
        conf = card(self)
        conf.pack(fill="x", pady=(12, 0))
        g = ctk.CTkFrame(conf, fg_color="transparent")
        g.pack(fill="x", padx=20, pady=14)
        g.grid_columnconfigure(1, weight=1)
        c = self.repo.config

        ctk.CTkLabel(g, text="Carpeta del PC", text_color=ON_SURFACE).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=6)
        self.l_carpeta = ctk.CTkLabel(g, text="", anchor="w")
        self.l_carpeta.grid(row=0, column=1, sticky="ew", pady=6)
        ghost_button(g, "Elegir carpeta", self._elegir, width=140).grid(row=0, column=2, padx=(8, 0), pady=6)

        ctk.CTkLabel(g, text="En tu Home, carpeta", text_color=ON_SURFACE).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=6)
        self.e_remota = ctk.CTkEntry(g)
        self.e_remota.insert(0, c.carpeta_remota)
        self.e_remota.grid(row=1, column=1, sticky="ew", pady=6)
        self.e_remota.bind("<Return>", lambda _e: self._guardar_remota())
        ghost_button(g, "Guardar", self._guardar_remota, width=140).grid(row=1, column=2, padx=(8, 0), pady=6)

        ctk.CTkLabel(g, text="Programación", text_color=ON_SURFACE).grid(row=2, column=0, sticky="w", padx=(0, 16), pady=6)
        prog = ctk.CTkFrame(g, fg_color="transparent")
        prog.grid(row=2, column=1, columnspan=2, sticky="w", pady=6)
        self.o_prog = ctk.CTkOptionMenu(prog, values=[t for _, t in PROGRAMACIONES], width=290,
                                        command=lambda _v: self._guardar_programacion())
        self.o_prog.set(_ETIQUETA.get(c.programacion, _ETIQUETA[MANUAL]))
        self.o_prog.pack(side="left")
        self.hora_box = ctk.CTkFrame(prog, fg_color="transparent")
        ctk.CTkLabel(self.hora_box, text="a las").pack(side="left", padx=(12, 6))
        self.o_hora = ctk.CTkOptionMenu(self.hora_box, values=[f"{h:02d}" for h in range(24)], width=70,
                                        command=lambda _v: self._guardar_programacion())
        self.o_hora.set(f"{c.hora:02d}")
        self.o_hora.pack(side="left")
        ctk.CTkLabel(self.hora_box, text=":").pack(side="left", padx=4)
        self.o_min = ctk.CTkOptionMenu(self.hora_box, values=[f"{m:02d}" for m in range(0, 60, 5)], width=70,
                                       command=lambda _v: self._guardar_programacion())
        self.o_min.set(f"{c.minuto - c.minuto % 5:02d}")
        self.o_min.pack(side="left")

        ctk.CTkLabel(g, text="La programación la ejecuta esta aplicación mientras está abierta y con la sesión "
                             "iniciada. «Al conectarse» sincroniza en cuanto el PC vuelve a alcanzar el servidor.",
                     font=font("body_small"), text_color=ON_SURFACE_VARIANT, anchor="w", justify="left",
                     wraplength=760).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # --- Última sincronización ------------------------------------------
        section_header(self, "Última sincronización").pack(anchor="w", pady=(18, 4))
        self.l_resumen = ctk.CTkLabel(self, text="", font=font("body"), text_color=ON_SURFACE_VARIANT,
                                      anchor="w", justify="left", wraplength=800)
        self.l_resumen.pack(anchor="w", fill="x")
        self.lista = StatePanel(self, height=200)
        self.lista.pack(fill="both", expand=True, pady=(6, 0))

        self._pintar_config()
        self._pintar(app.sync_estado)
        app.sync_listeners.append(self._pintar)

    def destroy(self):
        if self._pintar in self.app.sync_listeners:
            self.app.sync_listeners.remove(self._pintar)
        super().destroy()

    # --- Acciones ---------------------------------------------------------------
    def _sin_sesion(self):
        if self.repo.uid:
            return False
        self.e_detalle.configure(text="En modo demostración no hay servidor con el que sincronizar.")
        return True

    def _elegir(self):
        if self._sin_sesion():
            return
        p = filedialog.askdirectory(title="Carpeta del PC que se respaldará")
        if p:
            self.repo.guardar_config(carpeta=p)
            self._pintar_config()
            self.repo.sincronizar_ahora()

    def _guardar_remota(self):
        if self._sin_sesion():
            return
        nombre = self.e_remota.get().strip().strip("/")
        partes = nombre.split("/")
        if not nombre or any(p in ("", ".", "..") for p in partes) or any(ch in nombre for ch in '\\:*?"<>|'):
            self.e_remota.delete(0, "end")
            self.e_remota.insert(0, self.repo.config.carpeta_remota)
            return
        self.repo.guardar_config(carpeta_remota=nombre)
        self._pintar_config()

    def _guardar_programacion(self):
        if self._sin_sesion():
            return
        self.repo.guardar_config(programacion=_CLAVE[self.o_prog.get()],
                                 hora=int(self.o_hora.get()), minuto=int(self.o_min.get()))
        self._pintar_config()

    def _sincronizar(self):
        if not self._sin_sesion():
            self.repo.sincronizar_ahora()

    # --- Pintado ------------------------------------------------------------------
    def _pintar_config(self):
        c = self.repo.config
        self.l_carpeta.configure(text=c.carpeta or "ninguna carpeta seleccionada",
                                 text_color=ON_SURFACE if c.carpeta else ON_SURFACE_VARIANT)
        if c.programacion == DIARIA:
            self.hora_box.pack(side="left")
        else:
            self.hora_box.pack_forget()

    def _pintar(self, estado):
        if isinstance(estado, AlDia):
            icono, color = "☁", EXITO
            titulo = "Todo sincronizado" if estado.ultima_sincronizacion else "Lista para sincronizar"
            detalle = (f"Última sincronización {formatear_hace(estado.ultima_sincronizacion)}"
                       if estado.ultima_sincronizacion else "Aún no se ha sincronizado esta carpeta.")
            if estado.conflictos:
                detalle += f" · {estado.conflictos} conflicto(s): se guardaron ambas versiones"
        elif isinstance(estado, Sincronizando):
            icono, color, titulo = "↻", PRIMARY, "Sincronizando…"
            detalle = (f"Faltan {estado.pendientes} · {estado.detalle}" if estado.pendientes
                       else (estado.detalle or "Buscando cambios"))
        elif isinstance(estado, SinConfigurar):
            icono, color, titulo = "☁", ON_SURFACE_VARIANT, "Sin configurar"
            detalle = "Elige la carpeta del PC que quieres tener respaldada en el servidor."
        elif isinstance(estado, ErrorSync):
            icono, color, titulo, detalle = "⚠", ERROR, "No se pudo sincronizar", estado.mensaje
        else:
            icono, color, titulo = "⊘", ON_SURFACE_VARIANT, "Esperando la red del servidor"
            detalle = "node-sync no responde. Se sincronizará cuando el PC vuelva a alcanzarlo."
        self.e_icono.configure(text=glifo(icono), text_color=color)
        self.e_titulo.configure(text=titulo)
        self.e_detalle.configure(text=detalle)

        sincronizando = isinstance(estado, Sincronizando)
        self.b_sync.configure(state="disabled" if sincronizando or not self.repo.config.carpeta else "normal")
        if sincronizando:
            if estado.pendientes:
                self.e_barra.configure(mode="determinate")
                self.e_barra.stop()
                self.e_barra.set(estado.progreso)
            elif self.e_barra.cget("mode") != "indeterminate":
                self.e_barra.configure(mode="indeterminate")
                self.e_barra.start()
            self.e_barra.pack(fill="x", padx=20, pady=(0, 10), before=self.e_pie)
        else:
            self.e_barra.stop()
            self.e_barra.pack_forget()
            self._pintar_resumen()

    def _pintar_resumen(self):
        r = self.repo.config.ultimo_resumen
        if r is self._resumen_pintado:
            return
        self._resumen_pintado = r
        if not r:
            self.l_resumen.configure(text="Todavía no hay sincronizaciones.")
            self.lista.empty("Aquí verás qué se subió, bajó o borró en cada sincronización.")
            return
        cuando = f"{formatear_hace(r['fecha']).capitalize()} · {MODOS.get(r.get('modo'), 'manual')}"
        if r.get("mensaje_error"):
            self.l_resumen.configure(text=f"{cuando} · {r['mensaje_error']}", text_color=ERROR)
            self.lista.empty("No se aplicó ningún cambio.")
            return
        partes = [f"{r['subidos']} subido(s)", f"{r['bajados']} bajado(s)"]
        partes += [f"{r[k]} {t}" for k, t in (("borrados", "borrado(s)"), ("conflictos", "conflicto(s)"),
                                               ("errores", "con error")) if r.get(k)]
        eventos = r.get("eventos") or []
        self.l_resumen.configure(text=f"{cuando} · " + (" · ".join(partes) if eventos else "sin cambios: todo estaba al día"),
                                 text_color=ON_SURFACE_VARIANT)
        self.lista.clear()
        if not eventos:
            self.lista.empty("No hubo nada que transferir.")
            return
        prefijo = self.repo.config.carpeta_remota.strip("/ ") + "/"
        for ev in reversed(eventos):
            icono, _color, texto = EVENTOS.get(ev["tipo"], EVENTOS["ERROR"])
            ruta = ev["ruta"][len(prefijo):] if ev["ruta"].startswith(prefijo) else ev["ruta"]
            list_item(self.lista, icono, ruta, texto.format(ev.get("detalle") or ""))
