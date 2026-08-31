# -*- coding: utf-8 -*-
"""Vista de configuración."""

import customtkinter as ctk
from tkinter import messagebox

from ..theme import TEXT, MUTED
from ..widgets import section_title, card, primary_button
from ..config import CONFIG_FILE, save_config


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        section_title(self, "Configuración",
                      "Datos de conexión y apariencia. Se guardan localmente en tu equipo.").pack(anchor="w", pady=(0, 16))

        c = card(self)
        c.pack(fill="x")
        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(inner, text="URL del servidor", text_color=TEXT).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        self.e_url = ctk.CTkEntry(inner)
        self.e_url.insert(0, self.app.config.get("server_url", ""))
        self.e_url.grid(row=0, column=1, sticky="ew", pady=8)

        ctk.CTkLabel(inner, text="Usuario", text_color=TEXT).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=8)
        self.e_user = ctk.CTkEntry(inner)
        self.e_user.insert(0, self.app.config.get("username", ""))
        self.e_user.grid(row=1, column=1, sticky="ew", pady=8)

        ctk.CTkLabel(inner, text="Apariencia", text_color=TEXT).grid(row=2, column=0, sticky="w", padx=(0, 12), pady=8)
        self.appearance = ctk.CTkSegmentedButton(inner, values=["light", "dark", "system"],
                                                 command=self._change_appearance)
        self.appearance.set(self.app.config.get("appearance", "light"))
        self.appearance.grid(row=2, column=1, sticky="w", pady=8)

        ctk.CTkLabel(inner, text="Config guardada en", text_color=TEXT).grid(row=3, column=0, sticky="w", padx=(0, 12), pady=8)
        ctk.CTkLabel(inner, text=str(CONFIG_FILE), text_color=MUTED).grid(row=3, column=1, sticky="w", pady=8)

        primary_button(inner, "Guardar cambios", self._save, width=170).grid(row=4, column=1, sticky="w", pady=(12, 0))

    def _change_appearance(self, mode):
        ctk.set_appearance_mode(mode)

    def _save(self):
        self.app.config["server_url"] = self.e_url.get().strip()
        self.app.config["username"] = self.e_user.get().strip()
        self.app.config["appearance"] = self.appearance.get()
        save_config(self.app.config)
        messagebox.showinfo("Guardado", "Configuración guardada correctamente.")
