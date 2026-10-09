# -*- coding: utf-8 -*-
"""Vista Acerca de."""

import customtkinter as ctk

from .. import __version__
from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, font
from ..widgets import section_title, card, chip


class AboutView(ctk.CTkScrollableFrame):
    SERVICIOS = [
        ("Authentication", "SOAP", "Conectado (mock o node-soap)", "ok"),
        ("Distributed Storage", "HTTP/REST", "Conectado a node-repository (8084)", "ok"),
        ("Streaming", "HTTP/REST", "Conectado a node-media (8083)", "ok"),
        ("Shared File", "HTTP/REST", "Simulado: el servicio no existe en el backend", "warn"),
        ("File Sync", "gRPC", "Pendiente: falta generar el stub del .proto", "neutral"),
        ("HPC", "RMI", "Pendiente: RMI solo existe en la JVM", "neutral"),
    ]

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        section_title(self, "Acerca de", "Cliente de escritorio del proyecto UPB-CIENTÍFICA").pack(anchor="w", pady=(0, 16))
        c = card(self)
        c.pack(fill="x")
        txt = (
            f"UPB-CIENTÍFICA — Cliente de Escritorio (Windows / Linux) · v{__version__}\n"
            "Sistemas Distribuidos 2026-20 · Ingeniería de Sistemas e Informática · UPB Bucaramanga\n\n"
            "Consumidor 'Desktop Windows/Linux' de la Figura 1 del proyecto. Python + CustomTkinter.\n"
            "Comparte diseño (Material 3) y contratos con el cliente móvil (Kotlin + Jetpack Compose): se conecta\n"
            "directamente a cada servicio con su protocolo nativo, sin pasar por el gateway del cliente Web."
        )
        ctk.CTkLabel(c, text=txt, justify="left", text_color=ON_SURFACE,
                     font=font("body")).pack(anchor="w", padx=20, pady=20)

        s = card(self)
        s.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(s, text="Estado de cada servicio", font=font("title_medium"),
                     text_color=ON_SURFACE).pack(anchor="w", padx=20, pady=(16, 8))
        tabla = ctk.CTkFrame(s, fg_color="transparent")
        tabla.pack(fill="x", padx=20, pady=(0, 16))
        tabla.grid_columnconfigure(2, weight=1)
        for r, (nombre, proto, estado, kind) in enumerate(self.SERVICIOS):
            ctk.CTkLabel(tabla, text=nombre, width=170, anchor="w", text_color=ON_SURFACE).grid(row=r, column=0, sticky="w", pady=4)
            ctk.CTkLabel(tabla, text=proto, width=100, anchor="w", text_color=ON_SURFACE_VARIANT).grid(row=r, column=1, sticky="w")
            chip(tabla, estado, kind).grid(row=r, column=2, sticky="w")
