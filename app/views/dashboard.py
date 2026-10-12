# -*- coding: utf-8 -*-
"""Vista de inicio. Como HomeScreen.kt del móvil: saludo según la hora, franja
con el estado de File Sync y una tarjeta de color por servicio. Debajo, lo
propio del escritorio: la sesión y el estado de conexión de cada servicio."""

from datetime import datetime

import customtkinter as ctk

from ..theme import (
    PRIMARY, PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER, SECONDARY_CONTAINER, ON_SECONDARY_CONTAINER,
    TERTIARY_CONTAINER, ON_TERTIARY_CONTAINER, INVERSE_SURFACE, INVERSE_ON_SURFACE,
    SURFACE_CONTAINER_LOW, ON_SURFACE, ON_SURFACE_VARIANT, EXITO, ERROR, RADIUS_M, RADIUS_L,
    font, icon_font, glifo, tint,
)
from ..widgets import card, chip, circle, ghost_button, section_header, bind_click, formatear_hace
from ..data.filesync import AlDia, Sincronizando, SinConfigurar, ErrorSync
from ..utils import run_async
from ..config import HOME_DIR

# (clave, icono, nombre, descripción) — los cuatro primeros son los del móvil.
SERVICIOS = [
    ("storage", "📁", "Mis archivos", "Tu almacenamiento personal"),
    ("shared", "👥", "Compartidos", "Lo que otros compartieron contigo"),
    ("streaming", "▶", "Streaming", "Videos y material audiovisual"),
    ("hpc", "▣", "Cómputo HPC", "Lanza y sigue trabajos en el clúster"),
    ("sync", "↻", "Sincronización", "Mantén una carpeta al día con el servidor"),
    ("album", "🖼", "Álbum de fotos", "Tus fotos, con miniaturas y visor"),
]
# Cada servicio con su par de colores del tema (igual que en el móvil).
COLORES = [
    (PRIMARY_CONTAINER, ON_PRIMARY_CONTAINER),
    (SECONDARY_CONTAINER, ON_SECONDARY_CONTAINER),
    (TERTIARY_CONTAINER, ON_TERTIARY_CONTAINER),
    (INVERSE_SURFACE, INVERSE_ON_SURFACE),
]


def saludo():
    h = datetime.now().hour
    if 5 <= h <= 11:
        return "Buenos días"
    if 12 <= h <= 18:
        return "Buenas tardes"
    return "Buenas noches"


class DashboardView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        api = app.api

        ctk.CTkLabel(self, text=f"{saludo()}, {api.user or 'demo'}", font=font("headline_small"),
                     text_color=ON_SURFACE).pack(anchor="w", padx=4)
        ctk.CTkLabel(self, text="¿Qué quieres hacer hoy?", font=font("body_large"),
                     text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=4, pady=(2, 14))

        # ---------- Franja de sincronización ----------
        self.franja = ctk.CTkFrame(self, fg_color=SURFACE_CONTAINER_LOW, corner_radius=RADIUS_M)
        self.franja.pack(fill="x", padx=4)
        fila = ctk.CTkFrame(self.franja, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=14)
        self.f_icono = ctk.CTkLabel(fila, text=glifo("☁"), font=icon_font(22), width=30)
        self.f_icono.pack(side="left")
        txt = ctk.CTkFrame(fila, fg_color="transparent")
        txt.pack(side="left", padx=14)
        self.f_titulo = ctk.CTkLabel(txt, text="", font=font("title_small"), anchor="w")
        self.f_titulo.pack(anchor="w")
        self.f_detalle = ctk.CTkLabel(txt, text="", font=font("body_small"),
                                      text_color=ON_SURFACE_VARIANT, anchor="w")
        self.f_detalle.pack(anchor="w")
        self.f_barra = ctk.CTkProgressBar(self.franja, height=3, corner_radius=0,
                                          fg_color=SURFACE_CONTAINER_LOW)
        self._pintar_sync(app.sync_estado)
        app.sync_listeners.append(self._pintar_sync)

        # ---------- Servicios ----------
        section_header(self, "Servicios").pack(anchor="w", padx=4, pady=(22, 8))
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=4)
        cols = 3
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1, uniform="t")
        for i, (key, icon, name, desc) in enumerate(SERVICIOS):
            fondo, contenido = COLORES[i % len(COLORES)]
            self._tarjeta(grid, i // cols, i % cols, key, icon, name, desc, fondo, contenido)

        # ---------- Conexión (propio del escritorio) ----------
        section_header(self, "Tu conexión").pack(anchor="w", padx=4, pady=(22, 8))
        s = card(self)
        s.pack(fill="x", padx=4)
        if api.sesion:
            filas = [
                ("Usuario", api.sesion.usuario),
                ("Roles", ", ".join(api.sesion.roles) or "—"),
                ("Servicios autorizados", ", ".join(api.sesion.servicios_autorizados) or "—"),
                ("Token", api.sesion.token[:28] + ("…" if len(api.sesion.token) > 28 else "")),
            ]
        else:
            filas = [
                ("Usuario", api.user or "—"),
                ("Modo", "Demostración: sin servidor, todos los servicios con datos simulados"),
                ("Home local", str(HOME_DIR)),
            ]
        for i, (k, v) in enumerate(filas):
            row = ctk.CTkFrame(s, fg_color="transparent")
            row.pack(fill="x", padx=22, pady=(16 if i == 0 else 2, 16 if i == len(filas) - 1 else 2))
            ctk.CTkLabel(row, text=k, width=190, anchor="w", text_color=ON_SURFACE_VARIANT).pack(side="left")
            ctk.CTkLabel(row, text=v, anchor="w", text_color=ON_SURFACE).pack(side="left", fill="x")

        st = card(self)
        st.pack(fill="x", padx=4, pady=(12, 8))
        head = ctk.CTkFrame(st, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(16, 6))
        ctk.CTkLabel(head, text="Estado de los servicios", font=font("title_medium")).pack(side="left")
        self.btn_probar = ghost_button(head, "Comprobar conexión", self._probar, width=180, height=36)
        self.btn_probar.pack(side="right")

        self.estado_cells = []
        tabla = ctk.CTkFrame(st, fg_color="transparent")
        tabla.pack(fill="x", padx=22, pady=(0, 18))
        pesos = [3, 2, 5, 2, 2]
        for i, h in enumerate(["Servicio", "Protocolo", "Destino", "Modo", "Conexión"]):
            tabla.grid_columnconfigure(i, weight=pesos[i], uniform="s")
            ctk.CTkLabel(tabla, text=h.upper(), font=font("section"), text_color=ON_SURFACE_VARIANT,
                         anchor="w").grid(row=0, column=i, sticky="ew", pady=(4, 4))
        for r, (nombre, proto, destino, modo) in enumerate(api.servicios(), start=1):
            ctk.CTkLabel(tabla, text=nombre, anchor="w").grid(row=r, column=0, sticky="ew", pady=4)
            ctk.CTkLabel(tabla, text=proto, anchor="w", text_color=ON_SURFACE_VARIANT).grid(row=r, column=1, sticky="ew")
            ctk.CTkLabel(tabla, text=destino, anchor="w", text_color=ON_SURFACE_VARIANT,
                         font=font("body_small")).grid(row=r, column=2, sticky="ew")
            kind = {"real": "ok", "simulado": "warn", "demo": "warn"}.get(modo, "info")
            chip(tabla, modo, kind).grid(row=r, column=3, sticky="w")
            holder = ctk.CTkFrame(tabla, fg_color="transparent")
            holder.grid(row=r, column=4, sticky="w")
            ctk.CTkLabel(holder, text="—", text_color=ON_SURFACE_VARIANT).pack(anchor="w")
            self.estado_cells.append((nombre, destino, holder))

    def destroy(self):
        if self._pintar_sync in self.app.sync_listeners:
            self.app.sync_listeners.remove(self._pintar_sync)
        super().destroy()

    # --- Franja de sincronización (FranjaSincronizacion) ---------------------
    def _pintar_sync(self, estado):
        if isinstance(estado, AlDia):
            icono, color, titulo = "☁", EXITO, "Todo sincronizado"
            detalle = (f"Última sincronización {formatear_hace(estado.ultima_sincronizacion)}"
                       if estado.ultima_sincronizacion else "Aún no se ha sincronizado")
        elif isinstance(estado, Sincronizando):
            icono, color, titulo = "↻", PRIMARY, "Sincronizando…"
            detalle = (f"Faltan {estado.pendientes} cambios" if estado.pendientes
                       else (estado.detalle or "Buscando cambios"))
        elif isinstance(estado, SinConfigurar):
            icono, color, titulo = "☁", ON_SURFACE_VARIANT, "Respalda una carpeta del PC"
            detalle = "Elígela en Sincronización; se mantiene al día con tu Home"
        elif isinstance(estado, ErrorSync):
            icono, color, titulo = "⚠", ERROR, "No se pudo sincronizar"
            detalle = estado.mensaje
        else:
            icono, color, titulo = "⊘", ON_SURFACE_VARIANT, "Esperando la red del servidor"
            detalle = "Se sincronizará al volver a alcanzar node-sync"
        self.f_icono.configure(text=glifo(icono), text_color=color)
        self.f_titulo.configure(text=titulo)
        self.f_detalle.configure(text=detalle)
        if isinstance(estado, Sincronizando):
            self.f_barra.set(estado.progreso)
            self.f_barra.pack(fill="x", padx=12, pady=(0, 6))
        else:
            self.f_barra.pack_forget()

    # --- Tarjeta de servicio (TarjetaServicio) -------------------------------
    def _tarjeta(self, parent, row, col, key, icon, name, desc, fondo, contenido):
        t = ctk.CTkFrame(parent, fg_color=fondo, corner_radius=RADIUS_L, height=150)
        t.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 12, 0), pady=(0, 12))
        t.pack_propagate(False)
        circle(t, icon, 44, tint(contenido, 0.12, fondo), contenido, size=19).pack(anchor="w", padx=18, pady=(18, 0))
        ctk.CTkLabel(t, text=desc, font=font("body_small"), text_color=tint(contenido, 0.8, fondo),
                     anchor="w").pack(side="bottom", anchor="w", padx=18, pady=(0, 16))
        ctk.CTkLabel(t, text=name, font=font("title_medium"), text_color=contenido,
                     anchor="w").pack(side="bottom", anchor="w", padx=18)
        bind_click(t, lambda: self.app.show_view(key), hover=tint(contenido, 0.08, fondo))

    # --- Comprobar conexión --------------------------------------------------
    def _probar(self):
        self.btn_probar.configure(state="disabled", text="Comprobando…")
        restantes = {"n": len(self.estado_cells)}

        def terminado():
            restantes["n"] -= 1
            if restantes["n"] <= 0:
                self.btn_probar.configure(state="normal", text="Comprobar conexión")

        for nombre, destino, holder in self.estado_cells:
            self._pintar(holder, "…", "info")

            def ok(alcanzable, h=holder):
                self._pintar(h, "responde" if alcanzable else "sin respuesta",
                             "ok" if alcanzable else "error")
                terminado()
            run_async(self, lambda d=destino: self.app.api.probar_conexion(d), ok,
                      lambda _e: terminado())

    @staticmethod
    def _pintar(holder, texto, kind):
        for w in holder.winfo_children():
            w.destroy()
        chip(holder, texto, kind).pack(anchor="w")
