# -*- coding: utf-8 -*-
"""Vista de configuración: conexión con los servicios y apariencia."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import ON_SURFACE, ON_SURFACE_VARIANT, font
from ..widgets import section_title, card, primary_button
from ..config import CONFIG_FILE, save_config
from .conexion_form import ConexionForm

APARIENCIAS = {"Según el sistema": "system", "Claro": "light", "Oscuro": "dark"}   # mismos nombres que el menú de la cuenta


class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "Configuración",
                      "Conexión con los servicios y apariencia. Se guarda localmente en tu equipo.").pack(anchor="w", pady=(0, 16))

        c = card(self)
        c.pack(fill="x")
        ctk.CTkLabel(c, text="Conexión", font=font("title_medium"), text_color=ON_SURFACE).pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(c, text="Los cambios se aplican al guardar. La sesión actual se mantiene; "
                             "si cambias el servidor de autenticación, vuelve a iniciar sesión.",
                     text_color=ON_SURFACE_VARIANT, wraplength=760, justify="left").pack(anchor="w", padx=20)
        self.form = ConexionForm(c, app.config)
        self.form.pack(fill="x", padx=20, pady=(8, 16))

        a = card(self)
        a.pack(fill="x", pady=(16, 0))
        inner = ctk.CTkFrame(a, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        inner.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(inner, text="Apariencia", font=font("title_medium"),
                     text_color=ON_SURFACE).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ctk.CTkLabel(inner, text="Tema", text_color=ON_SURFACE).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=8)
        self.appearance = ctk.CTkSegmentedButton(inner, values=list(APARIENCIAS),
                                                 command=lambda v: ctk.set_appearance_mode(APARIENCIAS[v]))
        actual = {v: k for k, v in APARIENCIAS.items()}.get(app.config.get("appearance", "light"), "Claro")
        self.appearance.set(actual)
        self.appearance.grid(row=1, column=1, sticky="w", pady=8)
        ctk.CTkLabel(inner, text="Archivo de configuración", text_color=ON_SURFACE).grid(row=2, column=0, sticky="w", padx=(0, 16), pady=8)
        ctk.CTkLabel(inner, text=str(CONFIG_FILE), text_color=ON_SURFACE_VARIANT).grid(row=2, column=1, sticky="w", pady=8)

        primary_button(self, "Guardar cambios", self._save, width=180).pack(anchor="w", pady=16)

    def _save(self):
        self.form.aplicar()
        self.app.config["appearance"] = APARIENCIAS[self.appearance.get()]
        save_config(self.app.config)
        self.app.api.reconfigurar()
        self.app.invalidate_views()
        self.app.refresh_status()
        messagebox.showinfo("Guardado", "Configuración guardada correctamente.")
