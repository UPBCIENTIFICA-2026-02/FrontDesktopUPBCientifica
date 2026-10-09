# -*- coding: utf-8 -*-
"""Vista de inicio. Como HomeScreen.kt del móvil: una cuadrícula con un tile por
servicio. Además muestra la sesión y el estado de conexión de cada servicio."""

import customtkinter as ctk

from ..theme import (
    ON_SURFACE, ON_SURFACE_VARIANT, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH,
    OUTLINE_VARIANT, PRIMARY, font,
)
from ..widgets import card, chip, ghost_button
from ..utils import run_async
from ..config import HOME_DIR


class DashboardView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        api = app.api

        ctk.CTkLabel(self, text="Servicios", font=font("headline_small"),
                     text_color=ON_SURFACE).pack(anchor="w", pady=(0, 14))

        jobs = len(app.config.get("jobs", []))
        tiles = [
            ("storage", "📁", "Mis archivos", "Distributed Storage · REST"),
            ("shared", "🔗", "Compartidos conmigo", "Shared File · REST"),
            ("streaming", "▶", "Streaming", "Catálogo de video · REST"),
            ("sync", "⟳", "Sincronización", "File Sync · gRPC"),
            ("jobs", "⚙", "Trabajos HPC", f"{jobs} en cola local"),
            ("album", "🖼", "Álbum de fotos", "Galería local"),
        ]
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x")
        cols = 3
        for i in range(cols):
            grid.grid_columnconfigure(i, weight=1, uniform="t")
        for i, (key, icon, name, sub) in enumerate(tiles):
            self._tile(grid, i // cols, i % cols, key, icon, name, sub)

        # --- Sesión ---
        s = card(self)
        s.pack(fill="x", pady=(20, 0))
        ctk.CTkLabel(s, text="Sesión", font=font("title_medium"), text_color=ON_SURFACE).pack(anchor="w", padx=20, pady=(16, 6))
        if api.sesion:
            filas = [
                ("Usuario", api.sesion.usuario),
                ("Roles", ", ".join(api.sesion.roles) or "—"),
                ("Servicios autorizados", ", ".join(api.sesion.servicios_autorizados) or "—"),
                ("Token", api.sesion.token[:24] + ("…" if len(api.sesion.token) > 24 else "")),
            ]
        else:
            filas = [
                ("Usuario", api.user or "—"),
                ("Modo", "Demostración: sin servidor, todos los servicios con datos simulados"),
                ("Home local", str(HOME_DIR)),
            ]
        for i, (k, v) in enumerate(filas):
            row = ctk.CTkFrame(s, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(2, 16 if i == len(filas) - 1 else 2))
            ctk.CTkLabel(row, text=k, width=180, anchor="w", text_color=ON_SURFACE_VARIANT).pack(side="left")
            ctk.CTkLabel(row, text=v, anchor="w", text_color=ON_SURFACE).pack(side="left", fill="x")

        # --- Estado de los servicios ---
        st = card(self)
        st.pack(fill="x", pady=(16, 0))
        head = ctk.CTkFrame(st, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(head, text="Estado de los servicios", font=font("title_medium"),
                     text_color=ON_SURFACE).pack(side="left")
        self.btn_probar = ghost_button(head, "Comprobar conexión", self._probar, width=180, height=34)
        self.btn_probar.pack(side="right")

        self.estado_cells = []
        tabla = ctk.CTkFrame(st, fg_color="transparent")
        tabla.pack(fill="x", padx=20, pady=(0, 16))
        pesos = [3, 2, 5, 2, 2]
        for i, h in enumerate(["Servicio", "Protocolo", "Destino", "Modo", "Conexión"]):
            tabla.grid_columnconfigure(i, weight=pesos[i], uniform="s")
            ctk.CTkLabel(tabla, text=h, font=font("label_small"), text_color=ON_SURFACE_VARIANT,
                         anchor="w").grid(row=0, column=i, sticky="ew", pady=(4, 4))
        for r, (nombre, proto, destino, modo) in enumerate(api.servicios(), start=1):
            ctk.CTkLabel(tabla, text=nombre, anchor="w", text_color=ON_SURFACE).grid(row=r, column=0, sticky="ew", pady=4)
            ctk.CTkLabel(tabla, text=proto, anchor="w", text_color=ON_SURFACE_VARIANT).grid(row=r, column=1, sticky="ew")
            ctk.CTkLabel(tabla, text=destino, anchor="w", text_color=ON_SURFACE_VARIANT,
                         font=font("body_small")).grid(row=r, column=2, sticky="ew")
            kind = {"real": "ok", "simulado": "warn", "pendiente": "neutral", "demo": "warn"}.get(modo, "info")
            chip(tabla, modo, kind).grid(row=r, column=3, sticky="w")
            holder = ctk.CTkFrame(tabla, fg_color="transparent")
            holder.grid(row=r, column=4, sticky="w")
            ctk.CTkLabel(holder, text="—", text_color=ON_SURFACE_VARIANT).pack(anchor="w")
            self.estado_cells.append((destino, modo, holder))

    def _tile(self, parent, row, col, key, icon, name, sub):
        """ElevatedCard clicable, como los tiles del Home del móvil."""
        t = ctk.CTkFrame(parent, fg_color=SURFACE_CONTAINER_LOW, corner_radius=12, height=118,
                         border_width=1, border_color=OUTLINE_VARIANT)
        t.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 12, 0), pady=(0, 12))
        t.pack_propagate(False)
        ctk.CTkLabel(t, text=icon, font=ctk.CTkFont(size=26), text_color=PRIMARY).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(t, text=name, font=font("title_medium"), text_color=ON_SURFACE).pack(anchor="w", padx=18)
        ctk.CTkLabel(t, text=sub, font=font("body_small"), text_color=ON_SURFACE_VARIANT).pack(anchor="w", padx=18)

        def enter(_e):
            t.configure(fg_color=SURFACE_CONTAINER_HIGH)

        def leave(_e):
            t.configure(fg_color=SURFACE_CONTAINER_LOW)

        widgets = [t] + list(t.winfo_children())
        for w in widgets:
            w.bind("<Button-1>", lambda _e, k=key: self.app.show_view(k))
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass

    def _probar(self):
        self.btn_probar.configure(state="disabled", text="Comprobando…")
        pendientes = [c for c in self.estado_cells if c[1] not in ("pendiente",)]
        for destino, modo, holder in self.estado_cells:
            if modo == "pendiente":
                self._pintar(holder, "sin cliente", "neutral")
            else:
                self._pintar(holder, "…", "info")

        restantes = {"n": len(pendientes)}

        def terminado():
            restantes["n"] -= 1
            if restantes["n"] <= 0:
                self.btn_probar.configure(state="normal", text="Comprobar conexión")

        for destino, modo, holder in pendientes:
            def ok(alcanzable, h=holder):
                self._pintar(h, "responde" if alcanzable else "sin respuesta",
                             "ok" if alcanzable else "error")
                terminado()
            run_async(self, lambda d=destino: self.app.api.probar_conexion(d), ok,
                      lambda _e: terminado())
        if not pendientes:
            terminado()

    @staticmethod
    def _pintar(holder, texto, kind):
        for w in holder.winfo_children():
            w.destroy()
        chip(holder, texto, kind).pack(anchor="w")
